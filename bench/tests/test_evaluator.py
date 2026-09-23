import asyncio
from collections import Counter
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace

import numpy as np
import pytest
from cave_agent import StopReason
from cave_agent.models import TokenUsage

import core.evaluator as evaluator_module
from core.errors import InfrastructureError
from core.evaluator import classify_failure
from core.results import json_default
from core.validation import ValidatorResult
from tests.fixtures import filing_case


def test_failure_classification_preserves_strict_first_pass_semantics():
    assert classify_failure(
        ValidatorResult(True, "correct"), StopReason.COMPLETED
    ) is None
    assert classify_failure(
        ValidatorResult(False, "missing", variables_not_set=True),
        StopReason.COMPLETED,
    ) == "variables_not_set"
    assert classify_failure(
        ValidatorResult(False, "wrong"), StopReason.COMPLETED
    ) == "wrong_value"
    assert classify_failure(
        ValidatorResult(False, "wrong"), StopReason.MAX_STEPS
    ) == "max_steps"


def _single_turn_case(monkeypatch, agent_stop):
    """The filing fixture cut to one turn, run by an agent that stops as told."""

    class FakeRuntime:
        def __init__(self, *, functions, variables, types, security_checker):
            self.values = {variable.name: variable.value for variable in variables}

        async def retrieve(self, name):
            return self.values[name]

    class StoppingAgent:
        def __init__(self, model, *, runtime, max_steps, **kwargs):
            self.max_steps = max_steps
            self.messages = []
            self.loop_events = Counter()
            self.spent = Counter()
            self.stop_cause = None

        async def run(self, prompt):
            self.spent["model_calls"] += 4
            self.stop_cause = agent_stop["cause"]
            return SimpleNamespace(
                stop_reason=StopReason.MODEL_ERROR, content="[{\"row\": 1}, {\"ro",
                steps=4, usage=TokenUsage(), elapsed=1.0, code_snippets=["print(table)"],
            )

    monkeypatch.setattr(evaluator_module, "IPythonRuntime", FakeRuntime)
    monkeypatch.setattr(evaluator_module, "FencedCodeAgent", StoppingAgent)
    monkeypatch.setattr(evaluator_module, "runtime_variables", lambda *_: [])
    spec = deepcopy(filing_case.SPEC)
    spec["conversations"][0]["turns"] = spec["conversations"][0]["turns"][:1]
    case_module = importlib.import_module(spec["module"])
    monkeypatch.setattr(case_module, "variables", case_module.variables[:3])
    return spec


def test_a_stop_the_conversation_caused_is_scored_not_retried(monkeypatch):
    spec = _single_turn_case(monkeypatch, {"cause": "output_truncated"})
    result = asyncio.run(evaluator_module.evaluate_case(None, spec, max_protocol_nudges=1))
    (turn,) = result.turns
    assert not turn.success and turn.stop_cause == "output_truncated"
    assert turn.stop_reason == "model_error" and turn.protocol_repair is None
    assert turn.spent == {"model_calls": 4}


def test_an_outage_is_raised_with_what_the_attempt_spent(monkeypatch):
    spec = _single_turn_case(monkeypatch, {"cause": None})
    with pytest.raises(InfrastructureError) as raised:
        asyncio.run(evaluator_module.evaluate_case(None, spec))
    assert raised.value.spent == {"model_calls": 4}


def test_protocol_repair_preserves_first_pass_and_shares_total_budget(monkeypatch):
    seen_budgets = []

    class FakeRuntime:
        def __init__(self, *, functions, variables, types, security_checker):
            self.values = {variable.name: variable.value for variable in variables}

        async def retrieve(self, name):
            return self.values[name]

    class FakeAgent:
        def __init__(self, model, *, runtime, max_steps, **kwargs):
            self.runtime = runtime
            self.max_steps = max_steps
            self.calls = 0
            self.messages = [{"role": "system", "content": "runtime description"}]
            self.loop_events = Counter()
            self.spent = Counter()
            self.stop_cause = None

        async def run(self, prompt):
            self.calls += 1
            self.loop_events["usage_provider"] += self.calls
            self.spent["model_calls"] += self.calls
            self.messages.append({"role": "user", "content": prompt})
            seen_budgets.append(self.max_steps)
            if self.calls == 1:
                return SimpleNamespace(
                    stop_reason=StopReason.COMPLETED,
                    content="I will inspect the data.",
                    steps=1,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
                    elapsed=1.0,
                    code_snippets=[],
                )
            assert "filing_accession" in prompt
            self.runtime.values["filing_accession"] = "accession"
            self.runtime.values["fiscal_period_end"] = "2025-01-31"
            self.runtime.values["acceptance_datetime"] = "2025-03-14T12:00:00Z"
            return SimpleNamespace(
                stop_reason=StopReason.COMPLETED,
                content="Computed from the runtime.",
                steps=3,
                usage=TokenUsage(prompt_tokens=20, completion_tokens=5, total_tokens=25),
                elapsed=2.0,
                code_snippets=["filing_accession = 'accession'"],
            )

    monkeypatch.setattr(evaluator_module, "IPythonRuntime", FakeRuntime)
    monkeypatch.setattr(evaluator_module, "FencedCodeAgent", FakeAgent)
    monkeypatch.setattr(evaluator_module, "runtime_variables", lambda *_: [])
    # This unit test exercises one protocol-repair cycle, not the case's later
    # state-dependent revenue turn.
    spec = deepcopy(filing_case.SPEC)
    spec["conversations"][0]["turns"] = spec["conversations"][0]["turns"][:1]
    case_module = importlib.import_module(spec["module"])
    monkeypatch.setattr(case_module, "variables", case_module.variables[:3])
    monkeypatch.setattr(
        case_module,
        "ground_truth",
        lambda: (
            "accession",
            "2025-01-31",
            "2025-03-14T12:00:00Z",
            "2024-02-01",
            680.985,
        ),
    )
    result = asyncio.run(
        evaluator_module.evaluate_case(None, spec, max_protocol_nudges=2)
    )
    turn = result.conversations[0].turns[0]
    assert not turn.success
    assert turn.failure_type == "variables_not_set"
    assert turn.protocol_nudges == 1
    assert seen_budgets == [14, 13]
    repair = turn.protocol_repair
    assert repair["success"]
    # Each run's loop events are its own, and the repair arm sums them.
    assert turn.loop_events == {"usage_provider": 1}
    assert repair["attempts"][0]["loop_events"] == {"usage_provider": 2}
    assert repair["loop_events"] == {"usage_provider": 3}
    assert turn.spent == {"model_calls": 1} and repair["spent"] == {"model_calls": 3}
    assert result.spent() == {"model_calls": 3}
    assert repair["steps"] == 4
    assert repair["total_tokens"] == 37
    assert repair["elapsed"] == 3.0
    assert repair["code_snippets"] == ["filing_accession = 'accession'"]
    assert len(result.conversations[0].messages) == 3
    assert result.conversations[0].messages[-1]["content"].startswith("Your previous response")


@pytest.mark.parametrize("code_snippets, stop_reason, steps, repaired", [
    ([], StopReason.COMPLETED, 1, True),         # code in a form that never ran
    (["x = 1"], StopReason.COMPLETED, 3, False), # ran code: an answer, scored as it stands
    ([], StopReason.MAX_STEPS, 3, False),        # stopped by the runtime, not a format slip
    ([], StopReason.COMPLETED, 14, False),       # no budget left to repair with
])
def test_only_a_completed_turn_that_ran_no_code_is_repaired(
    code_snippets, stop_reason, steps, repaired
):
    result = SimpleNamespace(code_snippets=code_snippets, stop_reason=stop_reason)
    unset = ValidatorResult(False, "required output not set", variables_not_set=True)
    assert evaluator_module._needs_protocol_repair(result, unset, steps, 14) is repaired
    answered = ValidatorResult(False, "wrong value")
    assert not evaluator_module._needs_protocol_repair(result, answered, steps, 14)


def test_executed_code_reveals_which_registered_tables_were_named():
    names = ["facts_df", "filings_df", "companies_df"]
    referenced = evaluator_module.referenced_names(
        ["merged = facts_df.merge(companies_df, on='cik')", "print(merged.head())"],
        names,
    )
    assert referenced == ["companies_df", "facts_df"]


def test_a_table_named_only_in_a_string_or_comment_does_not_count():
    referenced = evaluator_module.referenced_names(
        ["# could have used filings_df\nlabel = 'filings_df'\nx = facts_df.shape"],
        ["facts_df", "filings_df"],
    )
    assert referenced == ["facts_df"]


def test_lazy_handle_calls_name_the_table_they_load():
    """datasets.load("x") is a reference; the same name in any other string is not."""
    referenced = evaluator_module.referenced_names(
        [
            'frame = datasets.load("filings_df")\n'
            'print(datasets.describe("facts_df"))\n'
            "other = 'companies_df'",
        ],
        ["facts_df", "filings_df", "companies_df"],
    )
    assert referenced == ["facts_df", "filings_df"]


def test_a_table_read_from_a_file_is_named_by_its_path():
    """Paradigms that read files name a table by its file, not by a variable."""
    referenced = evaluator_module.referenced_names(
        [
            'facts = pd.read_parquet("/data/tables/facts_df.parquet")\n'
            "path = '/data/tables/other.parquet'\n"
            "label = 'filings_df'",
        ],
        ["facts_df", "filings_df"],
    )
    assert referenced == ["facts_df"]


def test_code_the_runtime_rejected_still_shows_intent():
    """A syntax error is not evidence the agent ignored the table."""
    referenced = evaluator_module.referenced_names(
        ["totals = filings_df.groupby('form'"], ["facts_df", "filings_df"]
    )
    assert referenced == ["filings_df"]


def test_result_json_default_preserves_numpy_scalar_types():
    assert json_default(np.float64(1.25)) == 1.25
    assert json_default(np.bool_(False)) is False
    # Anything else is kept as text, and named by the detector derived from the
    # same rule so the two cannot disagree about what survived.
    assert json_default(object()).startswith("<object object")


def test_result_json_cites_transcript_without_embedding_messages(tmp_path):
    turn = evaluator_module.TurnResult(
        turn=1, query="q", stores=[], success=True, failure_type=None,
        response="done", outputs={}, validation_message="correct",
        variables_not_set=False, steps=1, prompt_tokens=2, completion_tokens=3,
        total_tokens=5, elapsed=0.1, stop_reason="completed", executed_code=True,
        code_snippets=["x = 1"], protocol_nudges=0, protocol_repair=None,
    )
    result = evaluator_module.CaseResult(
        name="case",
        conversations=[evaluator_module.ConversationResult(
            id="main", turns=[turn],
            loop_events={"usage_provider": 2}, spent={"model_calls": 2},
            transcript="transcripts/model_main.jsonl",
            messages=[{"role": "system", "content": "large prompt"}],
        )],
    )
    path = tmp_path / "model.json"
    evaluator_module.write_result(path, result, {"model_id": "model"})
    saved = json.loads(path.read_text())
    assert saved["conversations"][0]["transcript"] == "transcripts/model_main.jsonl"
    assert "messages" not in saved["conversations"][0]["turns"][0]
    # A conversation's spend and loop events, repair arms included, are the run's cost.
    assert saved["conversations"][0]["loop_events"] == {"usage_provider": 2}
    assert saved["conversations"][0]["spent"] == saved["spent"] == {"model_calls": 2}


def test_a_reply_is_waited_for_as_long_as_the_request_may_take():
    """A slow first chunk is not an outage, and the pool must not read it as one.

    CaveAgent waits 120s for a reply to begin. A four-turn imported case whose
    prompt has grown past a hundred thousand tokens can take longer than that to
    produce its first token, and the stall is raised as a model error, so the
    runner halves its concurrency for a request that was only slow. The model is
    already configured with how long a request may take; that is the number.
    """
    model = SimpleNamespace(kwargs={"timeout": 600})
    assert evaluator_module.idle_timeout(model) == 600
    # A model configured without one, and the None the unit tests pass, keep the
    # framework's default rather than waiting forever.
    assert evaluator_module.idle_timeout(SimpleNamespace(kwargs={})) == 120.0
    assert evaluator_module.idle_timeout(None) == 120.0
