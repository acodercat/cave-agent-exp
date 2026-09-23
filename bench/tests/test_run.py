import asyncio
from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest

import core.evaluator as evaluator_module
import scripts.run as run_module
from core.errors import BenchmarkSpecificationError, InfrastructureError
from scripts.run import (
    _pending_specs, completion_state,
    experiment_name,
)
from core.results import atomic_write_json, result_path
from core.transcripts import read_transcript


def _case_result(name="case", *, success=True, turns=1):
    """A real CaseResult, so a shape change breaks the double with the code.

    These tests replace _evaluate_and_write, so a SimpleNamespace here would let
    the runner keep reading fields the evaluator no longer returns.
    """
    return evaluator_module.CaseResult(
        name=name,
        conversations=[evaluator_module.ConversationResult(
            id="main",
            turns=[evaluator_module.TurnResult(
                turn=index + 1, query="q", stores=[], success=success,
                failure_type=None if success else "wrong_value", response="r",
                outputs={}, validation_message="m", variables_not_set=False,
                steps=1, prompt_tokens=1, completion_tokens=1, total_tokens=2,
                elapsed=0.1, stop_reason="completed", executed_code=True,
                code_snippets=[], protocol_nudges=0, protocol_repair=None,
            ) for index in range(turns)],
        )],
    )


def test_experiment_name_is_model_id_plus_timestamp():
    assert experiment_name(
        "provider/model:version", datetime(2026, 8, 7, 18, 3, 4)
    ) == "provider-model-version_20260807_180304"


def test_parallel_runner_replenishes_up_to_concurrency(monkeypatch, tmp_path):
    active = 0
    maximum_active = 0
    started = []

    async def fake_evaluate(
        model, cfg, spec, experiment_dir, max_protocol_nudges,
        run_id, arm, score_inline, total_step_budget, injection,
        paradigm, max_exec_output, failed_attempts,
    ):
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        started.append(spec["name"])
        assert total_step_budget == 64
        await asyncio.sleep(0.01)
        active -= 1
        return _case_result(spec["name"])

    monkeypatch.setattr(run_module, "_evaluate_and_write", fake_evaluate)
    cfg = SimpleNamespace(api_model="model", name="alias", base_url="https://example.test")
    specs = [{"name": f"case_{index}"} for index in range(7)]
    summary = asyncio.run(
        run_module.run_cases(
            None, cfg, specs, tmp_path, concurrency=3, total_step_budget=64,
        )
    )
    assert maximum_active == 3
    assert started == [f"case_{index}" for index in range(7)]
    assert summary == {
        "passed": 7,
        "passed_after_repair": 7,
        "repair_attempted": 0,
        "repair_successes": 0,
        "completed": 7,
        "total": 7,
        "infrastructure_errors": 0,
        "failed_after_retry": 0,
        "final_concurrency": 3,
    }


def test_a_case_the_endpoint_always_refuses_halves_the_pool_once(monkeypatch, tmp_path):
    """One request the gateway refuses must not serialise the whole study.

    The first failure is the pool's signal that the provider is unwell, so it
    backs off. The retry of that same case fails for the same reason it failed
    the first time and says nothing new; halving again for it would cost five
    consecutive successes per step to climb back.
    """
    async def always_refused(model, cfg, spec, *args, **kwargs):
        if spec["name"] == "refused_case":
            raise InfrastructureError("bad_response_status_code")
        return _case_result(spec["name"])

    monkeypatch.setattr(run_module, "_evaluate_and_write", always_refused)
    cfg = SimpleNamespace(api_model="model", name="alias", base_url="https://example.test")
    specs = [{"name": "refused_case"}] + [{"name": f"case_{i}"} for i in range(3)]
    summary = asyncio.run(
        run_module.run_cases(None, cfg, specs, tmp_path, concurrency=8,
                             total_step_budget=64)
    )
    assert summary["infrastructure_errors"] == 2      # both attempts failed
    assert summary["failed_after_retry"] == 1         # the case was abandoned
    assert summary["final_concurrency"] == 4          # halved once, not twice


def test_an_outage_is_retried_but_a_broken_case_stops_the_run(monkeypatch, tmp_path):
    """The two failure classes must not share a response.

    Retrying an outage can succeed. Retrying a broken case buys a second paid
    model call and the identical failure, so it has to surface immediately.
    """
    attempts = []
    seen_failed_attempts = []

    async def flaky(model, cfg, spec, *args, failed_attempts=(), **kwargs):
        attempts.append(spec["name"])
        seen_failed_attempts.append(failed_attempts)
        if attempts.count(spec["name"]) == 1:
            raise InfrastructureError("endpoint down", spent={"model_calls": 4})
        return _case_result(spec["name"])

    monkeypatch.setattr(run_module, "_evaluate_and_write", flaky)
    cfg = SimpleNamespace(api_model="model", name="alias", base_url="https://example.test")
    summary = asyncio.run(
        run_module.run_cases(None, cfg, [{"name": "flaky_case"}], tmp_path, concurrency=1)
    )
    assert attempts == ["flaky_case", "flaky_case"]
    assert summary["infrastructure_errors"] == 1
    assert summary["passed"] == 1
    assert seen_failed_attempts == [(), ({
        "attempt": 1, "error_type": "InfrastructureError", "error": "endpoint down",
        "spent": {"model_calls": 4},
    },)]

    async def broken(model, cfg, spec, *args, **kwargs):
        raise BenchmarkSpecificationError("validator raised ZeroDivisionError")

    monkeypatch.setattr(run_module, "_evaluate_and_write", broken)
    with pytest.raises(BenchmarkSpecificationError):
        asyncio.run(
            run_module.run_cases(
                None, cfg, [{"name": "broken_case"}], tmp_path, concurrency=1
            )
        )


def test_a_validator_crash_is_a_case_defect_not_an_outage():
    def explode(response, runtime, turn):
        raise ZeroDivisionError("boom")

    with pytest.raises(BenchmarkSpecificationError, match="ZeroDivisionError"):
        evaluator_module._validate(explode, "some_case", "", None, None)


def test_an_output_json_cannot_hold_is_reported_not_silently_stringified():
    class Opaque:
        pass

    lossy = evaluator_module.unserializable_outputs({
        "good": 1.5, "also_good": np.float64(2.5), "bad": Opaque(),
    })
    assert lossy == ["bad"]


def test_resume_skips_clean_pass_and_clean_failure_but_retries_missing(tmp_path):
    cfg = SimpleNamespace(api_model="model", name="alias", base_url="https://example.test")
    specs = [{"name": name} for name in ("pass", "fail", "missing")]
    atomic_write_json(
        result_path(tmp_path, "pass", "model"), {
            "schema": "finbench-run-v4",
            "conversations": [{"id": "main", "turns": [
                {"turn": 1, "query": "q", "response": "x", "outputs": {"v": 1}}
            ]}],
        }
    )
    atomic_write_json(
        result_path(tmp_path, "fail", "model"), {
            "schema": "finbench-run-v4",
            "conversations": [{"id": "main", "turns": [
                {"turn": 1, "query": "q", "response": "x", "outputs": {"v": 1}}
            ]}],
        }
    )
    pending, skipped = _pending_specs(tmp_path, cfg, specs)
    assert [spec["name"] for spec in pending] == ["missing"]
    assert skipped == 2

    other_cfg = SimpleNamespace(
        api_model="other-model", name="other", base_url="https://example.test"
    )
    other_pending, other_skipped = _pending_specs(tmp_path, other_cfg, specs)
    assert [spec["name"] for spec in other_pending] == ["pass", "fail", "missing"]
    assert other_skipped == 0


def test_partial_case_resume_cannot_mark_full_experiment_complete():
    status, summary = completion_state(
        {"completed": 2, "passed": 2, "failed": 0, "infrastructure_errors": 0},
        expected=3,
    )
    assert status == "incomplete"
    assert summary["remaining"] == 1


def test_evaluate_and_write_cites_separate_full_transcript(monkeypatch, tmp_path):
    result = _case_result("case")
    result.conversations[0].messages = [
        {"role": "system", "content": "runtime schema"},
        {"role": "assistant", "content": "```python\nx = 1\n```"},
    ]

    async def fake_evaluate(
        model, spec, max_protocol_nudges, total_step_budget, injection,
        paradigm, max_exec_output,
    ):
        assert total_step_budget == 14
        assert injection == "lazy"
        assert paradigm.name == "cave" and max_exec_output == 10000
        return result

    captured = {}

    def fake_write(path, saved_result, model_config, run_metadata):
        captured.update(
            path=path, result=saved_result, model=model_config,
            run_metadata=run_metadata,
        )

    monkeypatch.setattr(run_module, "evaluate_case", fake_evaluate)
    monkeypatch.setattr(run_module, "write_result", fake_write)
    cfg = SimpleNamespace(
        api_model="provider/model", name="alias", base_url="https://example.test"
    )
    returned = asyncio.run(run_module._evaluate_and_write(
        None, cfg, {"name": "case"}, tmp_path, 2,
    ))

    assert returned is result
    assert result.conversations[0].transcript == "transcripts/main.jsonl"
    transcript = captured["path"].parent / result.conversations[0].transcript
    assert [record["content"] for record in read_transcript(transcript)] == [
        "runtime schema", "```python\nx = 1\n```",
    ]
