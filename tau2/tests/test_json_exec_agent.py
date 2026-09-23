"""Tests for the JSON-tool-call arm: what it shares with the fenced arm, and what it does not.

Local and deterministic — no model is called and no tau2 domain is loaded. The
first class is the load-bearing one: it asserts that everything a paradigm
comparison has to hold fixed really is identical between the two arms, so the
claim "they differ only in the action format" is mechanised rather than asserted
in prose. The rest covers what differs, and the three places where a silent
mistake would leave one arm reading instructions for the other's action.
"""

from importlib.metadata import version
from types import SimpleNamespace

import pytest
from cave_agent import CaveAgent
from cave_agent.prompts import DEFAULT_SYSTEM_INSTRUCTIONS, EXECUTION_OUTPUT_PROMPT
from pydantic import BaseModel
from tau2.data_model.message import UserMessage

from tau2_cave.agent import Tau2CaveAgent
from tau2_json_exec.agent import EMPTY_TURN_REPLY, Tau2JsonExecAgent
from tau2_json_exec.prompts import (
    MALFORMED_ARGUMENTS, NEXT_STEP_TOOL_CALL, SYSTEM_INSTRUCTION_SUBSTITUTIONS, TOOL_NAME,
    TOOL_SCHEMA, UNKNOWN_TOOL, UPSTREAM_NEXT_STEP,
)
from cave_agent.models import PromptTooLongError
from tau2_json_exec.tool_call_agent import ToolCall, ToolCallAgent


class Database(BaseModel):
    counter: int = 0


class Toolkit:
    """Stands in for a tau2 toolkit: tools are bound methods over one database."""

    def __init__(self, db: Database):
        self.db = db

    def increment(self, amount: int = 1) -> int:
        """Add to the counter."""
        self.db.counter += amount
        return self.db.counter

    def get_tools(self) -> dict:
        return {"increment": SimpleNamespace(name="increment", _func=self.increment)}


def build(agent_class, live=None):
    live = live if live is not None else Toolkit(Database())
    return agent_class(
        tools=list(live.get_tools().values()), domain_policy="policy",
        llm="test-model", llm_args={"api_key": "k"},
    )


class TestTheArmsDifferOnlyInTheAction:
    """The comparison's premise, as a test.

    Each of these is a factor reviewer R3 #3 asks to be held fixed while the
    action format changes: the persistent runtime, the operations reachable
    through it, and the budgets. If one of them drifts, a difference in reward
    is not attributable to the action.
    """

    @pytest.fixture
    def arms(self):
        return build(Tau2CaveAgent), build(Tau2JsonExecAgent)

    def test_the_same_budgets(self, arms):
        cave, json_exec = arms
        assert cave._agent.max_steps == json_exec._agent.max_steps
        assert cave._agent.max_exec_output == json_exec._agent.max_exec_output
        assert (cave._agent.model.kwargs["num_retries"]
                == json_exec._agent.model.kwargs["num_retries"])

    def test_the_same_operations_in_the_same_kind_of_runtime(self, arms):
        cave, json_exec = arms
        assert type(cave._agent.runtime) is type(json_exec._agent.runtime)
        assert (cave._agent.runtime.describe_functions()
                == json_exec._agent.runtime.describe_functions())
        assert cave._agent.runtime.describe_types() == json_exec._agent.runtime.describe_types()

    def test_both_work_on_a_copy_of_the_database(self, arms):
        for agent in arms:
            assert agent._shadow is not agent._live
            assert agent._shadow.db is not agent._live.db

    def test_both_resync_that_copy(self, arms):
        for agent in arms:
            agent._live.db.counter = 42          # tau2's initialize() runs after construction
            agent._sync_shadow()
            assert agent._shadow.db.counter == 42

    def test_both_record_the_calls_the_model_makes(self, arms):
        for agent in arms:
            agent._recorder.wrap(agent._shadow.increment)(amount=3)
            (call,) = agent._recorder.take()
            assert (call.name, call.arguments) == ("increment", {"amount": 3})

    def test_the_action_is_what_differs(self, arms):
        cave, json_exec = arms
        assert type(cave._agent) is CaveAgent
        assert type(json_exec._agent) is ToolCallAgent
        assert isinstance(json_exec._agent, CaveAgent)


class TestTheToolOffered:
    def test_one_tool_named_execute_python(self):
        assert TOOL_SCHEMA["function"]["name"] == TOOL_NAME == "execute_python"
        assert TOOL_SCHEMA["function"]["parameters"]["required"] == ["code"]

    def test_the_domain_tools_are_not_offered_as_json_tools(self):
        """They reach the model as Python in the runtime, which is the point."""
        agent = build(Tau2JsonExecAgent)
        assert "increment" in agent._agent.runtime.describe_functions()
        assert TOOL_SCHEMA["function"]["name"] not in agent._agent.runtime.describe_functions()


class TestACallThatCannotRun:
    """Answered, and nothing runs — the provider cannot catch either of these."""

    def test_a_call_to_another_tool(self):
        call = ToolCall(id="1", name="get_customer", arguments='{"code": "print(1)"}')
        assert call.code is None
        assert call.refusal == UNKNOWN_TOOL.format(name="get_customer")

    @pytest.mark.parametrize("arguments", ['{not json', '{"code": 3}', '[]'])
    def test_arguments_that_are_not_a_code_string(self, arguments):
        call = ToolCall(id="1", name=TOOL_NAME, arguments=arguments)
        assert call.code is None
        assert call.refusal == MALFORMED_ARGUMENTS

    def test_a_well_formed_call_carries_its_code(self):
        call = ToolCall(id="1", name=TOOL_NAME, arguments='{"code": "print(1)"}')
        assert call.code == "print(1)"


class TestUnexecutedCode:
    """A fenced block means opposite things in the two arms.

    Both arms also catch a reply that names one of their own tools, whatever
    wraps it — that half of the pattern is the robust one, added because
    enumerating each model's favourite markup kept missing new ones. So the
    difference between the arms shows on a block that calls no tool: for the
    tool-call arm that is still code that never ran, for the fenced arm it is
    the normal way code runs.
    """

    def test_an_opening_python_fence_divides_the_arms(self):
        """Only the opening fence separates them; see the class docstring.

        The fenced arm's pattern excludes ` ```python ` but not the bare ` ``` `
        that closes a block, so a whole block trips it on the closing fence. That
        is pre-existing and harmless there — `_looks_like_an_unexecuted_call`
        only consults the pattern for a turn that executed nothing, and a turn
        holding a real block executed it. What matters here is the opening fence,
        which for this arm is the failure and for the fenced arm is how code runs.
        """
        assert build(Tau2JsonExecAgent)._unexecuted_call.search("```python\nx = 1")
        assert not build(Tau2CaveAgent)._unexecuted_call.search("```python\nx = 1")

    def test_a_python_block_calling_a_tool_is_caught_by_both(self):
        """The fenced arm catches it on the tool name, which is the robust half."""
        reply = "```python\nincrement(2)\n```"
        assert build(Tau2JsonExecAgent)._unexecuted_call.search(reply)
        assert build(Tau2CaveAgent)._unexecuted_call.search(reply).group(0) == "increment("

    @pytest.mark.parametrize("reply", [
        "<code>\nincrement(2)\n</code>", "increment(2)", "<code_block>increment(2)</code_block>",
    ])
    def test_both_arms_agree_on_the_other_forms(self, reply):
        assert build(Tau2JsonExecAgent)._unexecuted_call.search(reply)
        assert build(Tau2CaveAgent)._unexecuted_call.search(reply)

    def test_prose_is_not_a_failure_in_either_arm(self):
        reply = "Your line is active and your bill is paid."
        assert not build(Tau2JsonExecAgent)._unexecuted_call.search(reply)
        assert not build(Tau2CaveAgent)._unexecuted_call.search(reply)


class TestWhatEachArmIsTold:
    """The three places a stale sentence would tell one arm to use the other's action."""

    def test_the_next_step_sentence_is_replaced_for_this_action(self):
        assert TOOL_NAME in NEXT_STEP_TOOL_CALL
        assert "code block" not in NEXT_STEP_TOOL_CALL

    def test_the_upstream_sentence_is_still_the_one_being_replaced(self):
        """A cave-agent reword must fail here, not leave the wrong sentence in place."""
        assert UPSTREAM_NEXT_STEP in EXECUTION_OUTPUT_PROMPT

    def test_the_system_instructions_are_the_upstream_ones_with_named_changes(self):
        text = build(Tau2JsonExecAgent)._agent_kwargs()["system_instructions"]
        for upstream, replacement in SYSTEM_INSTRUCTION_SUBSTITUTIONS:
            text = text.replace(replacement, upstream, 1)
        assert text == DEFAULT_SYSTEM_INSTRUCTIONS

    def test_the_fenced_arm_still_reads_cave_agents_own(self):
        assert build(Tau2CaveAgent)._agent_kwargs() == {}

    def test_each_arm_names_its_own_action_in_its_prompt(self):
        cave_prompt = build(Tau2CaveAgent).system_prompt
        json_prompt = build(Tau2JsonExecAgent).system_prompt
        assert "```python" in cave_prompt
        assert TOOL_NAME in json_prompt
        assert "provide the next code block" not in json_prompt


class TestABareCallHasNothingToSay:
    """tau2 rejects an assistant message that is neither text nor calls."""

    @staticmethod
    def agent_with_replies(replies):
        """An agent whose loop returns `replies` and really calls a recorded tool.

        The recorder is what makes a turn a tool-call turn, so the fake has to go
        through it — otherwise the turn reports no calls and the pending-reply
        path is never taken.
        """
        agent = build(Tau2JsonExecAgent)
        queue = list(replies)

        async def fake_run(query):
            agent._recorder.wrap(agent._shadow.increment)()
            return queue.pop(0)

        agent._agent.run = fake_run
        return agent

    def test_a_turn_with_no_prose_still_yields_a_valid_reply(self):
        from tests.test_agent import response

        agent = self.agent_with_replies([response("", code=["increment()"])])
        state = agent.get_init_state()
        calls_message, state = agent.generate_next_message(
            UserMessage(role="user", content="add one"), state)
        assert calls_message.tool_calls

        reply, state = agent.generate_next_message(
            SimpleNamespace(role="tool", content="1"), state)
        assert reply.content == EMPTY_TURN_REPLY
        assert reply.raw_data["empty_replies"] == 1

    def test_a_turn_with_prose_keeps_it(self):
        from tests.test_agent import response

        agent = self.agent_with_replies([response("Added.", code=["increment()"])])
        state = agent.get_init_state()
        _, state = agent.generate_next_message(
            UserMessage(role="user", content="add one"), state)
        reply, _ = agent.generate_next_message(
            SimpleNamespace(role="tool", content="1"), state)
        assert reply.content == "Added."


def test_the_pinned_cave_agent_version():
    """The vendored loop overrides internals of this exact release."""
    assert version("cave-agent").startswith("0.8.")


class TestWhereTheTokenFiguresComeFrom:
    """Both arms read cave-agent's accounting, which estimates what the provider omits.

    A fenced reply is read only to its first closed block, before the provider's
    usage arrives; a tool call is read to its end. So the arms' token figures can
    come from different sources, and a comparison has to be able to say how often
    rather than assert they are alike.
    """

    def test_both_arms_count_which_source_each_call_used(self):
        from types import SimpleNamespace as NS

        for cls in (Tau2CaveAgent, Tau2JsonExecAgent):
            agent = build(cls)
            assert agent._usage_sources() == {"reported": 0, "estimated": 0}

            turn = NS(usage=None)
            wire, output = [{"role": "user", "content": "hi"}], "done"
            agent._agent._finalize_turn_usage(turn, NS(usage=None), wire, output)
            agent._agent._finalize_turn_usage(
                turn, NS(usage=NS(total_tokens=10, prompt_tokens=7, completion_tokens=3)),
                wire, output)

            assert agent._usage_sources() == {"reported": 1, "estimated": 1}, cls.__name__

    def test_the_count_rides_on_the_turn_it_describes(self):
        from tests.test_agent import response

        agent = build(Tau2JsonExecAgent)

        async def fake_run(query):
            agent._recorder.wrap(agent._shadow.increment)()
            return response("Added.", code=["increment()"])

        agent._agent.run = fake_run
        message, _ = agent.generate_next_message(
            UserMessage(role="user", content="add one"), agent.get_init_state())
        assert message.raw_data["usage_sources"] == {"reported": 0, "estimated": 0}


class TestAStreamThatDiesMidReply:
    """The arm's own recovery must be reachable, not shadowed by a NameError.

    ``_stream_once`` ends with ``except PromptTooLongError: raise`` followed by
    the clause that records a partial turn. Vendoring once dropped that name
    from the imports while keeping the clause, so evaluating it raised
    ``NameError`` and *both* paths were lost: a partial turn crashed the run
    instead of being recorded, and an overflow stopped reaching the compaction
    that handles it. Neither shows up in a run that never fails, which is why
    the three formal runs passed with the defect in place.
    """

    @staticmethod
    def stream_once(failure, *, content="partial "):
        """Drive one reply whose stream yields `content`, then raises `failure`."""
        import asyncio

        from cave_agent.models import StreamDelta

        class DyingStream:
            # What the shared turn-conclusion code reads off a stream.
            finish_reason = None
            refusal = None
            thinking = ""

            def __init__(self):
                self.calls = {}

            async def __aiter__(self):
                yield StreamDelta(content=content)
                raise failure

            async def aclose(self):
                pass

        agent = build(Tau2JsonExecAgent)._agent
        # A history the wire can be rendered from; the guard in
        # `_prepare_messages` rejects an empty one.
        agent._initialize_conversation("do something")
        agent._tool_stream = lambda wire: DyingStream()
        agent._finalize_turn_usage = lambda *a, **k: None
        turn = SimpleNamespace(error=None, code=None, text="", finish_reason=None, full="")

        async def drive():
            return [event async for event in agent._stream_once(turn)]

        return turn, asyncio.run(drive())

    def test_a_partial_reply_is_recorded_on_the_turn(self):
        failure = RuntimeError("the gateway hung up")
        turn, _ = self.stream_once(failure)
        assert turn.error is failure

    def test_an_overflow_is_re_raised_for_the_loop_to_compact(self):
        with pytest.raises(PromptTooLongError):
            self.stream_once(PromptTooLongError("context exhausted"))
