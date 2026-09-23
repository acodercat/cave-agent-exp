"""Tests for the Evaluator's turn/conversation loop error semantics.

Ported from a sibling harness (current semantics). These are load-bearing for a
fair benchmark:

- a validator PASS/FAIL is recorded per turn with metrics accounted once;
- an agent/API outage becomes an `error` TurnResult — retryable, NOT a
  plain model failure — and later turns in that conversation are skipped,
  while turns already evaluated are preserved;
- deterministic benchmark defects (no validation mechanism, unknown
  validator name, crashing validator) fail loudly with
  `BenchmarkSpecificationError` and are never recorded as retryable —
  otherwise the resume loop would re-run the same defect forever.
"""

import asyncio
import types

import pytest

from core.agent import AgentResponse, TokenUsage
from core.errors import BenchmarkSpecificationError
from core.evaluator import Evaluator
from core.types import Conversation, Turn
from core.validation import ValidatorResult


class FakeAgent:
    """Scripted agent: returns canned responses, can raise on demand."""

    def __init__(self, behaviors):
        # behaviors: list of "ok" | Exception instances, consumed per run()
        self._behaviors = list(behaviors)
        self.runtime = None

    async def run(self, query: str) -> AgentResponse:
        behavior = self._behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return AgentResponse(
            content=f"answer to {query}",
            tool_calls=[],
            steps=2,
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


class FakeFactory:
    def __init__(self, agent):
        self._agent = agent

    def create_agent(self, **kwargs):
        return self._agent


def make_module(validators):
    mod = types.ModuleType("fake_benchmark")
    mod.tools = []
    mod.variables = []
    mod.validators = validators
    return mod


def run_scenario(agent, validators, turns, conv_id="conv"):
    evaluator = Evaluator(FakeFactory(agent))
    conversations = [Conversation(id=conv_id, turns=turns)]
    return asyncio.run(
        evaluator.evaluate("scenario", make_module(validators), conversations)
    )


def passing_validator(content, runtime, turn, actual_calls):
    return ValidatorResult(True, "ok")


def failing_validator(content, runtime, turn, actual_calls):
    return ValidatorResult(False, "wrong value")


class TestTurnOutcomes:
    def test_pass_and_fail_recorded_with_metrics(self):
        agent = FakeAgent(["ok", "ok"])
        result = run_scenario(
            agent,
            {"v_pass": passing_validator, "v_fail": failing_validator},
            [Turn(query="q1", validator="v_pass"), Turn(query="q2", validator="v_fail")],
        )
        turns = result.conversations[0].turns
        assert [t.success for t in turns] == [True, False]
        assert turns[0].error is None and turns[1].error is None
        assert "wrong value" in turns[1].validation_errors[0]
        m = result.metrics
        assert (m.total_turns, m.successful_turns, m.failed_turns) == (2, 1, 1)
        assert m.total_tokens == 30 and m.total_steps == 4
        assert m.success_rate == 0.5

    def test_no_validation_mechanism_is_spec_error(self):
        # A turn with no validator AND no expected calls/variable access has
        # nothing checking it — it must fail loudly, not silently pass and
        # not become a retryable error the resume loop re-runs forever.
        agent = FakeAgent(["ok"])
        with pytest.raises(BenchmarkSpecificationError, match="no validation mechanism"):
            run_scenario(agent, {}, [Turn(query="q1")])

    def test_unknown_validator_name_is_spec_error(self):
        agent = FakeAgent(["ok"])
        with pytest.raises(BenchmarkSpecificationError, match="missing_name"):
            run_scenario(agent, {"other": passing_validator},
                         [Turn(query="q1", validator="missing_name")])


class TestErrorIsolation:
    def test_crash_preserves_prior_turns_and_skips_rest(self):
        # Turn 2 crashes: turn 1's PASS must survive, turn 3 must be skipped
        # (conversation context is broken), and both 2 and 3 carry `error`.
        agent = FakeAgent(["ok", RuntimeError("API down"), "ok"])
        result = run_scenario(
            agent,
            {"v": passing_validator},
            [Turn(query=f"q{i}", validator="v") for i in (1, 2, 3)],
        )
        turns = result.conversations[0].turns
        assert len(turns) == 3
        assert turns[0].success is True and turns[0].error is None
        assert turns[1].success is False and "API down" in turns[1].error
        assert turns[2].success is False and "skipped" in turns[2].error
        m = result.metrics
        assert (m.total_turns, m.successful_turns, m.failed_turns) == (3, 1, 2)

    def test_validator_bug_fails_loudly(self):
        # Validator bugs are deterministic spec/code failures, not outages —
        # recording them as retryable would re-run the same crash forever.
        def buggy_validator(content, runtime, turn, actual_calls):
            raise TypeError("validator bug")

        agent = FakeAgent(["ok"])
        with pytest.raises(BenchmarkSpecificationError, match="validator bug"):
            run_scenario(agent, {"v": buggy_validator},
                         [Turn(query="q1", validator="v")])

    def test_error_result_detected_as_incomplete(self):
        # The resume contract: an errored result must be flagged retryable.
        from core.results import result_has_infra_error, result_is_complete

        agent = FakeAgent(["ok", RuntimeError("boom")])
        result = run_scenario(
            agent, {"v": passing_validator},
            [Turn(query="q1", validator="v"), Turn(query="q2", validator="v")],
        )
        data = {"scenario": result.to_dict()}
        assert result_has_infra_error(data) is True
        assert result_is_complete(data) is False

    def test_clean_fail_detected_as_complete(self):
        # A legitimate model failure (validator FAIL, no exception) is a
        # COMPLETE result — resume must not endlessly re-run it.
        from core.results import result_has_infra_error, result_is_complete

        agent = FakeAgent(["ok"])
        result = run_scenario(agent, {"v": failing_validator},
                              [Turn(query="q1", validator="v")])
        data = {"scenario": result.to_dict()}
        assert result_has_infra_error(data) is False
        assert result_is_complete(data) is True
