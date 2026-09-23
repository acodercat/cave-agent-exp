"""Tests for the tau2 <-> CaveAgent bridge.

Local and deterministic: no model is called and no tau2 domain is loaded. What
is covered is what the bridge is responsible for — recording the calls CaveAgent
makes, keeping those calls serializable, handing CaveAgent tools that work on a
copy of the database rather than the real one, describing that database's types,
and the per-turn budget, format correction and token accounting around a turn.
"""

from enum import Enum
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from tau2.data_model.message import UserMessage

from tau2_cave.agent import (
    MAX_STEPS_PER_TURN,
    Tau2CaveAgent,
    ToolCallRecorder,
    _as_json,
    _data_types,
    _live_toolkit,
    _looks_like_an_unexecuted_call,
    _shadow_toolkit,
    _unexecuted_call_pattern,
)


class Database(BaseModel):
    """Stands in for a domain database."""

    counter: int = 0


class Passenger(BaseModel):
    first_name: str
    last_name: str


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


class TestToolCallRecorder:
    def test_records_name_and_arguments(self):
        recorder = ToolCallRecorder()
        toolkit = Toolkit(Database())

        recorder.wrap(toolkit.increment)(amount=3)

        (call,) = recorder.take()
        assert (call.name, call.arguments) == ("increment", {"amount": 3})
        assert call.requestor == "assistant"

    def test_records_defaults_the_model_did_not_pass(self):
        """tau2 replays the call, so an omitted default still has to be in it."""
        recorder = ToolCallRecorder()

        recorder.wrap(Toolkit(Database()).increment)()

        assert recorder.take()[0].arguments == {"amount": 1}

    def test_call_still_runs_and_returns(self):
        recorder = ToolCallRecorder()
        toolkit = Toolkit(Database())

        assert recorder.wrap(toolkit.increment)(amount=5) == 5
        assert toolkit.db.counter == 5

    def test_signature_and_docstring_survive(self):
        """CaveAgent describes a tool to the model from exactly these two."""
        import inspect

        wrapped = ToolCallRecorder().wrap(Toolkit(Database()).increment)

        assert "amount" in inspect.signature(wrapped).parameters
        assert inspect.getdoc(wrapped) == "Add to the counter."
        assert wrapped.__name__ == "increment"

    def test_take_is_per_turn(self):
        recorder = ToolCallRecorder()
        increment = recorder.wrap(Toolkit(Database()).increment)

        increment()
        assert len(recorder.take()) == 1
        assert recorder.take() == []

        increment()
        assert len(recorder.take()) == 1

    def test_calls_keep_their_order(self):
        recorder = ToolCallRecorder()
        increment = recorder.wrap(Toolkit(Database()).increment)

        for amount in (1, 2, 3):
            increment(amount=amount)

        assert [call.arguments["amount"] for call in recorder.take()] == [1, 2, 3]


class TestArgumentSerialization:
    def test_pydantic_models_become_dicts(self):
        assert _as_json(Passenger(first_name="Ada", last_name="Lovelace")) == {
            "first_name": "Ada", "last_name": "Lovelace",
        }

    def test_nested_structures(self):
        value = {"passengers": [Passenger(first_name="Ada", last_name="Lovelace")], "seats": 2}
        assert _as_json(value) == {
            "passengers": [{"first_name": "Ada", "last_name": "Lovelace"}], "seats": 2,
        }

    def test_primitives_pass_through(self):
        assert _as_json({"a": 1, "b": None, "c": True, "d": "x"}) == {
            "a": 1, "b": None, "c": True, "d": "x",
        }

    def test_unknown_types_fall_back_to_str(self):
        class Opaque:
            def __repr__(self) -> str:
                return "<opaque>"

        assert _as_json(Opaque()) == "<opaque>"

    def test_a_model_class_is_not_mistaken_for_an_instance(self):
        assert _as_json(Passenger) == str(Passenger)

    def test_result_is_json_encodable(self):
        import json

        json.dumps(_as_json({"p": Passenger(first_name="Ada", last_name="Lovelace")}))


class TestDatabaseIsolation:
    """CaveAgent executes as it works and tau2 replays; only one may hit the live db."""

    def test_writes_go_to_the_copy(self):
        live = Toolkit(Database())
        shadow = _shadow_toolkit(live)

        shadow.increment(amount=7)

        assert live.db.counter == 0
        assert shadow.db.counter == 7

    def test_same_tools_are_exposed(self):
        live = Toolkit(Database())
        assert list(_shadow_toolkit(live).get_tools()) == list(live.get_tools())

    def test_toolkit_is_found_from_any_tool(self):
        live = Toolkit(Database())
        assert _live_toolkit(list(live.get_tools().values())) is live

    def test_no_tools_is_an_error(self):
        with pytest.raises(ValueError, match="at least one tool"):
            _live_toolkit([])


class TestShadowSync:
    """The shadow database follows the live one turn by turn.

    tau2 applies a task's initial state after the agent is built, and the
    telecom environment lets the user side write into the agent database during
    the conversation; both would be invisible to a copy taken once.
    """

    @staticmethod
    def make_agent(live: Toolkit) -> Tau2CaveAgent:
        return Tau2CaveAgent(
            tools=list(live.get_tools().values()), domain_policy="policy",
            llm="test-model", llm_args={"api_key": "k"},
        )

    def test_state_applied_after_construction_is_seen(self):
        live = Toolkit(Database())
        agent = self.make_agent(live)
        live.db.counter = 42                       # tau2's initialize() runs here

        agent._sync_shadow()

        assert agent._shadow.db.counter == 42

    def test_state_changed_between_turns_is_seen(self):
        live = Toolkit(Database())
        agent = self.make_agent(live)
        agent._sync_shadow()
        live.db.counter = 5                        # the user pays a bill

        agent._sync_shadow()

        assert agent._shadow.db.counter == 5

    def test_sync_does_not_leak_writes_back(self):
        live = Toolkit(Database())
        agent = self.make_agent(live)
        agent._sync_shadow()
        agent._shadow.increment(amount=3)

        agent._sync_shadow()

        assert live.db.counter == 0
        assert agent._shadow.db.counter == 0       # tau2's replay, not this copy, carries writes

    def test_runtime_tools_read_the_refreshed_copy(self):
        """The functions registered with CaveAgent are bound to the shadow, so a
        swapped-in database reaches them without re-registering anything."""
        live = Toolkit(Database())
        agent = self.make_agent(live)
        live.db.counter = 10

        agent._sync_shadow()

        increment = agent._shadow.get_tools()["increment"]._func
        assert increment() == 11


class Status(str, Enum):
    OPEN = "Open"
    PAID = "Paid"


class Item(BaseModel):
    label: str


class Bill(BaseModel):
    total_due: float
    status: Status
    items: list[Item]


class Account(BaseModel):
    bills: dict[str, Bill]
    latest: Bill | None = None


class TestDataTypes:
    """The model is told the fields of what tools return, instead of guessing them."""

    def test_models_and_enums_are_found_through_containers(self):
        """Each once, in the order met, and not the database class itself."""
        assert _data_types(Account) == [Bill, Status, Item]

    def test_a_database_of_plain_fields_has_none(self):
        assert _data_types(Database) == []

    def test_the_agent_describes_its_database_types(self):
        class Ledger(BaseModel):
            counter: int = 0
            bills: list[Bill] = []

        live = Toolkit(Ledger())
        agent = Tau2CaveAgent(
            tools=list(live.get_tools().values()), domain_policy="policy",
            llm="test-model", llm_args={"api_key": "k"},
        )

        prompt = agent.system_prompt
        assert "total_due" in prompt and "PAID = 'Paid'" in prompt


def response(content: str, *, code=(), stop=None, prompt=0, completion=0, steps=1):
    """An AgentResponse as cave-agent returns one."""
    from cave_agent import AgentResponse, StopReason, TokenUsage

    return AgentResponse(
        content=content, stop_reason=stop or StopReason.COMPLETED, steps=steps,
        elapsed=0.1, code_snippets=list(code),
        usage=TokenUsage(prompt_tokens=prompt, completion_tokens=completion,
                         total_tokens=prompt + completion),
    )


class TestUnparsedCallDetection:
    """A turn that executed nothing while reaching for code is a missed turn."""

    PATTERN = _unexecuted_call_pattern(["get_details_by_id", "enable_roaming"])

    def caught(self, content, code=()):
        return _looks_like_an_unexecuted_call(response(content, code=code), self.PATTERN)

    @pytest.mark.parametrize("content", [
        "<python>\nx = get_details_by_id('L1')\n</python>",
        "<code_block>\nx = 1\n</code_block>",
        "Let me look that up <｜DSML｜tool_calls><｜DSML｜invoke name=\"get\">",
        "```\nx = 1\n```",
    ])
    def test_known_markup_without_execution_is_caught(self, content):
        assert self.caught(content)

    @pytest.mark.parametrize("content", [
        # deepseek-v4-flash, which the markup list missed
        "Let me check.\n\n<code>\nline = get_details_by_id(\"L1001\")\nprint(line)\n</code>",
        # qwen3.8-flash's own tool-calling markup, also missed
        "<tool_call>\n<function=code>\n<parameter=code>\nx = get_details_by_id(\"L1\")",
        # no wrapping at all
        "enable_roaming(customer_id=\"C1\", line_id=\"L1\")",
    ])
    def test_a_tool_call_is_caught_whatever_wraps_it(self, content):
        assert self.caught(content)

    def test_a_fenced_block_that_ran_is_fine(self):
        assert not self.caught("```python\nx = 1\n```", code=["x = 1"])

    @pytest.mark.parametrize("content", [
        "Your balance is $42.00 and the line is active.",
        "I have enabled roaming on your line; please restart the phone.",
        "I'll use get_details_by_id to look at your line.",
    ])
    def test_plain_replies_are_left_alone(self, content):
        assert not self.caught(content)

    def test_a_call_alongside_real_execution_is_ignored(self):
        """Only a turn that ran nothing can be a missed call."""
        assert not self.caught("I ran get_details_by_id(\"L1\") above", code=["x = 1"])

    def test_the_agent_builds_its_pattern_from_its_own_tools(self):
        agent = Tau2CaveAgent(
            tools=list(Toolkit(Database()).get_tools().values()), domain_policy="policy",
            llm="test-model", llm_args={"api_key": "k"},
        )
        assert agent._unexecuted_call.search("<code>\nincrement(2)\n</code>")


class TestFenceCorrection:
    """The harness gives one nudge, then takes what it gets."""

    @staticmethod
    def agent_with_replies(live, replies):
        """A Tau2CaveAgent whose CaveAgent returns `replies` in order."""
        agent = Tau2CaveAgent(
            tools=list(live.get_tools().values()), domain_policy="policy",
            llm="test-model", llm_args={"api_key": "k"},
        )
        queue, asked = list(replies), []

        async def fake_run(query):
            asked.append(query)
            return queue.pop(0)

        agent._agent.run = fake_run
        return agent, asked

    def test_an_unparsed_turn_is_retried_once(self):
        agent, asked = self.agent_with_replies(Toolkit(Database()), [
            response("<python>\nincrement()\n</python>"),
            response("Done.", code=["increment()"]),
        ])

        message, _ = agent.generate_next_message(
            UserMessage(role="user", content="fix it"), agent.get_init_state())

        assert len(asked) == 2
        assert "```python" in asked[1]
        assert message.content == "Done."
        assert message.raw_data["format_corrections"] == 1

    def test_a_good_turn_is_not_retried(self):
        agent, asked = self.agent_with_replies(Toolkit(Database()), [
            response("Done.", code=["increment()"]),
        ])

        message, _ = agent.generate_next_message(
            UserMessage(role="user", content="fix it"), agent.get_init_state())

        assert asked == ["fix it"]
        assert message.raw_data["format_corrections"] == 0

    def test_a_second_failure_is_reported_not_retried_again(self):
        """Two strikes means the model cannot comply; the turn stands as it is."""
        agent, asked = self.agent_with_replies(Toolkit(Database()), [
            response("<python>\nincrement()\n</python>"),
            response("<python>\nincrement()\n</python>"),
        ])

        message, _ = agent.generate_next_message(
            UserMessage(role="user", content="fix it"), agent.get_init_state())

        assert len(asked) == 2
        assert message.raw_data["format_corrections"] == 1


def test_model_gets_tau2s_retry_budget():
    """FC retries transient gateway errors three times; CaveAgent must too."""
    from tau2.config import DEFAULT_MAX_RETRIES

    live = Toolkit(Database())
    agent = Tau2CaveAgent(
        tools=list(live.get_tools().values()), domain_policy="policy",
        llm="test-model", llm_args={"api_key": "k"},
    )

    assert agent._agent.model.kwargs["num_retries"] == DEFAULT_MAX_RETRIES


def test_a_turn_is_capped_at_a_few_steps():
    live = Toolkit(Database())
    agent = Tau2CaveAgent(
        tools=list(live.get_tools().values()), domain_policy="policy",
        llm="test-model", llm_args={"api_key": "k"},
    )

    assert agent._agent.max_steps == MAX_STEPS_PER_TURN


class TestTokenAccounting:
    """CaveAgent's usage must be counted in full, and where tau2 looks for it."""

    agent_with_replies = staticmethod(TestFenceCorrection.agent_with_replies)

    def test_usage_is_on_the_message_in_tau2s_shape(self):
        agent, _ = self.agent_with_replies(Toolkit(Database()), [
            response("Done.", code=["increment()"], prompt=900, completion=40),
        ])

        message, _ = agent.generate_next_message(
            UserMessage(role="user", content="fix it"), agent.get_init_state())

        assert message.usage == {"prompt_tokens": 900, "completion_tokens": 40}

    def test_tau2s_own_accounting_reads_it(self):
        """The FC baseline is counted by get_token_usage; CaveAgent must be too."""
        from tau2.utils.llm_utils import get_token_usage

        agent, _ = self.agent_with_replies(Toolkit(Database()), [
            response("Done.", code=["increment()"], prompt=900, completion=40),
        ])
        message, _ = agent.generate_next_message(
            UserMessage(role="user", content="fix it"), agent.get_init_state())

        assert get_token_usage([message]) == {"prompt_tokens": 900, "completion_tokens": 40}

    def test_a_corrected_turn_counts_both_attempts(self):
        """The attempt that ran nothing still cost tokens and time."""
        agent, _ = self.agent_with_replies(Toolkit(Database()), [
            response("<python>\nincrement()\n</python>", prompt=800, completion=30),
            response("Done.", code=["increment()"], prompt=950, completion=45, steps=2),
        ])

        message, _ = agent.generate_next_message(
            UserMessage(role="user", content="fix it"), agent.get_init_state())

        assert message.usage == {"prompt_tokens": 1750, "completion_tokens": 75}
        assert message.raw_data["usage"]["total_tokens"] == 1825
        assert message.raw_data["steps"] == 3
        assert message.raw_data["elapsed"] == pytest.approx(0.2)
        assert message.raw_data["format_corrections"] == 1

    def test_the_held_back_reply_carries_no_usage(self):
        """It is released after tau2's replay and made no model call of its own."""
        agent, _ = self.agent_with_replies(Toolkit(Database()), [])

        async def run_with_a_call(query):
            # the runtime calls tools through the recorder's wrappers
            agent._recorder.wrap(agent._shadow.increment)()
            return response("Done.", code=["increment()"], prompt=900, completion=40)

        agent._agent.run = run_with_a_call
        calls, state = agent.generate_next_message(
            UserMessage(role="user", content="fix it"), agent.get_init_state())
        reply, _ = agent._release_pending_reply(state)

        assert calls.usage is not None and calls.tool_calls
        assert reply.usage is None
