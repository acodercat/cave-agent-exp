import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.results import (
    RESULT_SCHEMA, atomic_write_json, experiment_summary, iter_result_files,
    load_result, result_is_complete, result_path, verification_path,
)
from core.evaluator import (
    CaseResult, ConversationResult, TurnResult, write_result,
)


def _run_payload():
    return {
        "schema": RESULT_SCHEMA,
        "model": {"model_id": "provider/model:v1"},
        "conversations": [{"id": "main", "turns": [
            {"turn": 1, "query": "q", "response": "answer", "outputs": {"v": 1}}
        ]}],
    }


def test_run_directory_is_the_only_main_artifact(tmp_path):
    experiment = tmp_path / "experiment"
    run = result_path(experiment, "case", "provider/model:v1", "20260821_120000")
    atomic_write_json(run, _run_payload())
    atomic_write_json(verification_path(run), {"schema": "verification"})
    atomic_write_json(run.parent / "future_channel.json", {"schema": "future"})
    assert list(iter_result_files(experiment)) == [("case", run)]


def test_unknown_or_flat_result_contract_is_rejected(tmp_path):
    experiment = tmp_path / "experiment"
    flat = experiment / "case" / "model.json"
    atomic_write_json(flat, {"result": {"success": True}})
    assert list(iter_result_files(experiment)) == []
    with pytest.raises(ValueError, match="invalid FinBench result payload"):
        load_result(flat)
    with pytest.raises(ValueError, match="expected a run.json artifact"):
        verification_path(flat)


def test_completeness_and_summary_use_separate_pv_and_infra_records(tmp_path):
    experiment = tmp_path / "experiment"
    passed = result_path(experiment, "pass", "model", "run-1")
    failed = result_path(experiment, "fail", "model", "run-1")
    atomic_write_json(passed, _run_payload())
    atomic_write_json(failed, _run_payload())
    for path, success in ((passed, True), (failed, False)):
        atomic_write_json(verification_path(path), {"conversations": [{"id": "main", "turns": [
            {"turn": 1, "status": "scored", "programmatic_verification": {"success": success}},
        ]}]})
    error = result_path(experiment, "infra", "model", "run-1").with_name("error.json")
    atomic_write_json(error, {"error": "API down"})
    assert result_is_complete(_run_payload())
    assert experiment_summary(experiment) == {
        "completed": 2, "pv_scored": 2, "passed": 1, "failed": 1,
        "infrastructure_errors": 1,
    }


def test_summary_reads_multi_turn_programmatic_verification(tmp_path):
    experiment = tmp_path / "experiment"
    passed = result_path(experiment, "pass", "model", "run-1")
    failed = result_path(experiment, "fail", "model", "run-1")
    atomic_write_json(passed, _run_payload())
    atomic_write_json(failed, _run_payload())

    def channel(successes):
        return {"conversations": [{"id": "main", "turns": [
            {"turn": index, "status": "scored", "programmatic_verification": {
                "success": success,
            }}
            for index, success in enumerate(successes, 1)
        ]}]}

    atomic_write_json(verification_path(passed), channel([True, True]))
    atomic_write_json(verification_path(failed), channel([True, False]))
    assert experiment_summary(experiment) == {
        "completed": 2, "pv_scored": 2, "passed": 1, "failed": 1,
        "infrastructure_errors": 0,
    }


def test_result_path_sanitizes_model_and_marks_run_directory(tmp_path):
    path = result_path(tmp_path, "case", "provider/model:v1", "repeat:1")
    assert path.name == "run.json"
    assert path.parts[-4:] == ("case", "provider-model-v1", "repeat-1", "run.json")


def test_trajectory_does_not_embed_programmatic_verdict(tmp_path):
    path = result_path(tmp_path, "case", "model", "run-1")
    result = CaseResult(name="case", conversations=[ConversationResult(
        id="main", turns=[TurnResult(
            turn=1, query="q", stores=["x"], success=True, failure_type=None,
            response="answer", outputs={"x": 1}, validation_message="correct",
            variables_not_set=False, steps=1, prompt_tokens=2,
            completion_tokens=3, total_tokens=5, elapsed=0.2,
            stop_reason="completed", executed_code=True,
            code_snippets=["x = 1"], protocol_nudges=0, protocol_repair=None,
        )],
    )])
    write_result(path, result, {"model_id": "model"}, {"run_id": "run-1"})
    saved = json.loads(path.read_text())
    assert saved["schema"] == RESULT_SCHEMA
    turn = saved["conversations"][0]["turns"][0]
    assert turn["outputs"] == {"x": 1}
    for key in ("success", "failure_type", "validation_message", "variables_not_set"):
        assert key not in turn


def test_atomic_writes_to_the_same_report_never_share_a_temp_file(tmp_path):
    path = tmp_path / "report.json"
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda value: atomic_write_json(path, {"value": value}), range(40)))
    assert json.loads(path.read_text())["value"] in range(40)
    assert list(tmp_path.glob("*.tmp")) == []
