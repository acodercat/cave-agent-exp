"""The two agent loops: each action runs as specified, and nothing else differs.

The provider is scripted beneath LiteLLM, so both agents run their real stream,
step, recovery, usage and execution paths; the runtime is a real IPython
runtime with the benchmark's security checker.
"""

import asyncio
import json
from types import SimpleNamespace

from cave_agent import StopReason
from cave_agent._placeholders import OUTPUT_RECOVERY_PROMPT
from cave_agent.models.litellm import LiteLLMModel
from cave_agent.prompts import EXECUTION_OUTPUT_PROMPT
from cave_agent.runtime import IPythonRuntime

from core.agents import (
    CONTEXT_OVERFLOW, OUTPUT_TRUNCATED, FencedCodeAgent, ToolCallAgent, ToolCallMessage,
)
from core.paradigms import Action
from core.prompts import (
    MALFORMED_ARGUMENTS, NEXT_STEP, TOOL_NAME, TOOL_SCHEMA, UNKNOWN_TOOL, UPSTREAM_NEXT_STEP,
)
from core.security import SECURITY_CHECKER
from core.transcripts import message_to_dict


# -- a scripted provider ---------------------------------------------------------

def chunk(content=None, *, calls=None, finish=None, usage=None):
    delta = SimpleNamespace(
        content=content, tool_calls=calls, reasoning_content=None, refusal=None,
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=delta, finish_reason=finish)], usage=usage,
    )


def usage(prompt=10, completion=2):
    return SimpleNamespace(
        prompt_tokens=prompt, completion_tokens=completion, total_tokens=prompt + completion,
    )


def call_part(index=0, *, id=None, name=None, arguments=None):
    function = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(index=index, id=id, function=function)


def tool_reply(*codes, content=None, reported=True):
    """A reply making one call per code; a code may be a (name, arguments) pair."""
    chunks = [chunk(content)] if content else []
    for index, code in enumerate(codes):
        if isinstance(code, tuple):
            name, arguments = code
        else:
            name, arguments = TOOL_NAME, json.dumps({"code": code})
        head, tail = arguments[:len(arguments) // 2], arguments[len(arguments) // 2:]
        chunks += [
            chunk(calls=[call_part(index, id=f"call_{index}", name=name, arguments=head)]),
            chunk(calls=[call_part(index, arguments=tail)]),
        ]
    chunks.append(chunk(finish="tool_calls", usage=usage() if reported else None))
    return chunks


def fenced_reply(*codes, content=None, reported=True):
    text = (content or "") + "".join(f"```python\n{code}\n```\n" for code in codes)
    return [chunk(text), chunk(finish="stop", usage=usage() if reported else None)]


def text_reply(text, *, finish="stop", reported=True):
    return [chunk(text), chunk(finish=finish, usage=usage() if reported else None)]


class ScriptedLiteLLM:
    """Stands in for the litellm module: serves one scripted reply per request."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def get_supported_openai_params(self, **_):
        return ["stream_options"]

    async def acompletion(self, **request):
        self.requests.append(request)
        reply = self.replies.pop(0)

        async def stream():
            for item in reply:
                yield item

        return stream()


def make_agent(agent_type, replies, *, max_steps=5, max_exec_output=10_000):
    model = LiteLLMModel(model_id="model", api_key="key", base_url="url", temperature=0.1)
    provider = ScriptedLiteLLM(replies)
    model._litellm = provider
    runtime = IPythonRuntime(
        functions=[], variables=[], types=[], security_checker=SECURITY_CHECKER,
    )
    agent = agent_type(
        model=model, runtime=runtime, system_instructions="system", max_steps=max_steps,
        max_exec_output=max_exec_output,
    )
    return agent, provider


def tool_results(provider):
    return [m["content"] for m in provider.requests[-1]["messages"] if m["role"] == "tool"]


def execution_results(provider):
    """The execution results a fenced loop sent back, in order."""
    return [
        m["content"] for m in provider.requests[-1]["messages"]
        if m["role"] == "user" and m["content"].lstrip().startswith("<execution_output>")
    ]


# -- the tool-call loop ------------------------------------------------------------

def test_a_turn_runs_calls_until_the_model_answers_in_text():
    agent, provider = make_agent(ToolCallAgent, [
        tool_reply("x = 6 * 7\nprint(x)"),
        tool_reply("print(x + 1)"),              # the session persists between calls
        text_reply("The answer is 43."),
    ])
    result = asyncio.run(agent.run("compute"))

    assert result.stop_reason is StopReason.COMPLETED
    assert result.content == "The answer is 43."
    assert result.steps == 3
    assert result.code_snippets == ["x = 6 * 7\nprint(x)", "print(x + 1)"]
    assert (result.usage.prompt_tokens, result.usage.completion_tokens) == (30, 6)
    first = provider.requests[0]
    assert first["tools"] == [TOOL_SCHEMA] and first["stream"] is True
    outputs = tool_results(provider)
    assert "42" in outputs[0] and "43" in outputs[1]
    assert all(NEXT_STEP[Action.TOOL_CALL] in output for output in outputs)


def test_only_the_first_call_of_a_reply_runs_or_enters_the_history():
    agent, provider = make_agent(ToolCallAgent, [
        tool_reply("print('first')", "print('second')"),
        text_reply("done"),
    ])
    result = asyncio.run(agent.run("go"))

    assert result.code_snippets == ["print('first')"]
    calls = [m for m in provider.requests[-1]["messages"] if m.get("tool_calls")]
    assert len(calls) == 1 and len(calls[0]["tool_calls"]) == 1
    assert len(tool_results(provider)) == 1


def test_a_call_that_cannot_run_is_answered_and_runs_nothing():
    agent, provider = make_agent(ToolCallAgent, [
        tool_reply(("run_sql", json.dumps({"code": "x"}))),
        tool_reply((TOOL_NAME, "{not json")),
        tool_reply((TOOL_NAME, json.dumps({"code": 5}))),
        text_reply("gave up"),
    ])
    result = asyncio.run(agent.run("go"))

    assert result.code_snippets == []
    assert tool_results(provider) == [
        UNKNOWN_TOOL.format(name="run_sql"), MALFORMED_ARGUMENTS, MALFORMED_ARGUMENTS,
    ]


def test_blocked_code_is_reported_as_the_fenced_loop_reports_it():
    agent, provider = make_agent(ToolCallAgent, [
        tool_reply("import os\nprint(os.getcwd())"), text_reply("ok"),
    ])
    asyncio.run(agent.run("go"))
    assert "Code blocked for security reasons" in tool_results(provider)[0]


def test_the_step_budget_ends_a_turn_that_keeps_calling():
    agent, provider = make_agent(ToolCallAgent, [tool_reply("print(1)")] * 3, max_steps=3)
    result = asyncio.run(agent.run("go"))
    assert result.stop_reason is StopReason.MAX_STEPS
    assert result.steps == 3 and len(provider.requests) == 3


def test_output_too_long_to_show_is_kept_in_a_runtime_variable():
    agent, provider = make_agent(
        ToolCallAgent,
        [tool_reply("print('x' * 9000)"), tool_reply("print(len(_output_1))"), text_reply("done")],
        max_exec_output=1000,
    )
    asyncio.run(agent.run("go"))
    shown, length = tool_results(provider)
    assert "_output_1" in shown and len(shown) < 9000
    assert "9001" in length


def test_the_conversation_carries_over_to_the_next_turn():
    agent, provider = make_agent(ToolCallAgent, [
        tool_reply("y = 2"), text_reply("set"), text_reply("still 2"),
    ])
    asyncio.run(agent.run("first"))
    asyncio.run(agent.run("second"))
    roles = [m["role"] for m in provider.requests[-1]["messages"]]
    assert roles == ["system", "user", "user", "assistant", "tool", "assistant", "user"]


def test_a_transcript_keeps_the_call():
    agent, _ = make_agent(
        ToolCallAgent, [tool_reply("z = 1", content="Setting z."), text_reply("ok")])
    asyncio.run(agent.run("go"))
    (message,) = [m for m in agent.messages if isinstance(m, ToolCallMessage)]
    record = message_to_dict(0, message)
    assert record["text"] == "Setting z."
    assert record["tool_call"]["arguments"] == json.dumps({"code": "z = 1"})
    assert "```python\nz = 1\n```" in record["content"]


def test_a_call_keeps_its_result_after_compaction_replaces_the_result_message():
    from cave_agent.messages import ExecutionResultMessage, SystemMessage, UserMessage

    from core.agents import ToolCall, _tool_wire

    call = ToolCall(id="c1", name=TOOL_NAME, arguments=json.dumps({"code": "x = 1"}))
    history = [
        SystemMessage("system"), UserMessage("go"), ToolCallMessage("", call),
        ExecutionResultMessage("[Old execution result cleared to save context space]"),
    ]
    wire = _tool_wire(history)
    assert wire[2]["tool_calls"][0]["id"] == "c1"
    assert wire[3] == {
        "role": "tool", "tool_call_id": "c1",
        "content": "[Old execution result cleared to save context space]",
    }


def test_a_name_repeated_in_later_parts_of_a_call_is_not_doubled():
    arguments = json.dumps({"code": "print(5)"})
    agent, provider = make_agent(ToolCallAgent, [
        [chunk(calls=[call_part(0, id="c", name=TOOL_NAME, arguments=arguments[:5])]),
         chunk(calls=[call_part(0, name=TOOL_NAME, arguments=arguments[5:])]),
         chunk(finish="tool_calls", usage=usage())],
        text_reply("5"),
    ])
    result = asyncio.run(agent.run("go"))
    assert result.code_snippets == ["print(5)"]


# -- what the two loops share ------------------------------------------------------

def test_the_next_step_sentence_replaces_cave_agents_own():
    """The replacement must not silently become a no-op if cave-agent rewords."""
    assert UPSTREAM_NEXT_STEP in EXECUTION_OUTPUT_PROMPT
    agent, provider = make_agent(FencedCodeAgent, [fenced_reply("print(1)"), text_reply("1")])
    asyncio.run(agent.run("go"))
    result = provider.requests[-1]["messages"][-1]["content"]
    assert NEXT_STEP[Action.FENCED_CODE] in result and UPSTREAM_NEXT_STEP not in result


def test_both_loops_build_the_same_system_prompt_and_time_reminder():
    fenced, fenced_provider = make_agent(FencedCodeAgent, [text_reply("a")])
    tool, tool_provider = make_agent(ToolCallAgent, [text_reply("a")])
    asyncio.run(fenced.run("go"))
    asyncio.run(tool.run("go"))
    fenced_wire = fenced_provider.requests[0]["messages"]
    tool_wire = tool_provider.requests[0]["messages"]
    assert fenced_wire[:3] == tool_wire[:3]    # system prompt, time reminder, question


def test_both_loops_run_the_same_computation_in_the_same_steps():
    codes = ["rows = [1, 2, 3]", "print(sum(rows))"]
    fenced, fenced_provider = make_agent(
        FencedCodeAgent, [fenced_reply(code) for code in codes] + [text_reply("6")])
    tool, tool_provider = make_agent(
        ToolCallAgent, [tool_reply(code) for code in codes] + [text_reply("6")])
    fenced_result = asyncio.run(fenced.run("sum"))
    tool_result = asyncio.run(tool.run("sum"))

    assert fenced_result.code_snippets == tool_result.code_snippets == codes
    assert (fenced_result.steps, fenced_result.stop_reason) == (
        tool_result.steps, tool_result.stop_reason)
    fenced_outputs = execution_results(fenced_provider)
    tool_outputs = tool_results(tool_provider)
    to_neutral = {NEXT_STEP[Action.FENCED_CODE]: "", NEXT_STEP[Action.TOOL_CALL]: ""}
    def neutral(text):
        for sentence, blank in to_neutral.items():
            text = text.replace(sentence, blank)
        return text
    assert [neutral(t) for t in fenced_outputs] == [neutral(t) for t in tool_outputs]


def test_both_loops_recover_the_same_way_from_a_reply_cut_at_the_output_limit():
    """The same recovery, each resumed as its action allows: a cut fence stays in
    the history and is finished, a cut call's arguments cannot be, so the call
    is made again."""
    cut_arguments = json.dumps({"code": "print(1)"})[:9]
    tool, tool_provider = make_agent(ToolCallAgent, [
        [chunk(calls=[call_part(0, id="c", name=TOOL_NAME, arguments=cut_arguments)]),
         chunk(finish="length", usage=usage())],
        tool_reply("print(1)"), text_reply("1"),
    ])
    fenced, fenced_provider = make_agent(FencedCodeAgent, [
        text_reply("```python\nprint(", finish="length"),
        text_reply("1)\n```\n"), text_reply("1"),
    ])
    tool_result = asyncio.run(tool.run("go"))
    fenced_result = asyncio.run(fenced.run("go"))

    for agent, result, provider in (
        (tool, tool_result, tool_provider), (fenced, fenced_result, fenced_provider),
    ):
        assert result.stop_reason is StopReason.COMPLETED and result.steps == 3
        assert result.code_snippets == ["print(1)"]
        assert OUTPUT_RECOVERY_PROMPT in [m["content"] for m in provider.requests[1]["messages"]]
        assert agent.loop_events["output_recovery"] == 1


def test_both_loops_estimate_a_call_the_provider_does_not_report_and_say_so():
    tool, _ = make_agent(
        ToolCallAgent, [tool_reply("x = 1", reported=False), text_reply("ok")])
    fenced, _ = make_agent(
        FencedCodeAgent, [fenced_reply("x = 1", reported=False), text_reply("ok")])
    for agent in (tool, fenced):
        result = asyncio.run(agent.run("go"))
        assert result.usage.prompt_tokens > 10 and result.usage.completion_tokens > 2
        assert agent.loop_events["usage_estimated"] == 1
        assert agent.loop_events["usage_provider"] == 1


def test_a_fenced_reply_is_read_only_to_its_block_so_its_usage_is_estimated():
    """The one accounting difference between the actions, which is why it is recorded."""
    fenced, _ = make_agent(FencedCodeAgent, [fenced_reply("x = 1"), text_reply("ok")])
    tool, _ = make_agent(ToolCallAgent, [tool_reply("x = 1"), text_reply("ok")])
    asyncio.run(fenced.run("go"))
    asyncio.run(tool.run("go"))
    assert fenced.loop_events["usage_estimated"] == 1 and fenced.loop_events["usage_provider"] == 1
    assert tool.loop_events["usage_provider"] == 2 and "usage_estimated" not in tool.loop_events


def test_a_model_failure_ends_the_run_as_a_model_error():
    class Failing(ScriptedLiteLLM):
        async def acompletion(self, **request):
            raise ValueError("gateway rejected the request")

    for agent_type in (ToolCallAgent, FencedCodeAgent):
        agent, _ = make_agent(agent_type, [])
        agent.model._litellm = Failing([])
        assert asyncio.run(agent.run("go")).stop_reason is StopReason.MODEL_ERROR


def test_both_loops_name_a_reply_still_cut_off_after_every_resumption():
    cut = text_reply("[" + '{"row": 1}, ' * 40, finish="length")
    for agent_type in (FencedCodeAgent, ToolCallAgent):
        agent, _ = make_agent(agent_type, [cut] * 4)
        result = asyncio.run(agent.run("deliver the table"))
        assert result.stop_reason is StopReason.MODEL_ERROR
        assert agent.stop_cause == OUTPUT_TRUNCATED
        assert agent.loop_events["output_recovery"] == 3


def test_both_loops_name_a_history_that_no_longer_fits():
    class Overflowing(ScriptedLiteLLM):
        async def acompletion(self, **request):
            error = ValueError("This model's maximum context length is 8192 tokens")
            error.status_code = 413
            raise error

    for agent_type in (FencedCodeAgent, ToolCallAgent):
        agent, _ = make_agent(agent_type, [])
        agent.model._litellm = Overflowing([])
        result = asyncio.run(agent.run("go"))
        assert result.stop_reason is StopReason.MODEL_ERROR
        assert agent.stop_cause == CONTEXT_OVERFLOW


def test_an_outage_names_no_stop_cause():
    class Failing(ScriptedLiteLLM):
        async def acompletion(self, **request):
            raise ValueError("gateway rejected the request")

    agent, _ = make_agent(ToolCallAgent, [])
    agent.model._litellm = Failing([])
    assert asyncio.run(agent.run("go")).stop_reason is StopReason.MODEL_ERROR
    assert agent.stop_cause is None


def test_every_call_is_also_estimated_with_a_calls_arguments_counted():
    from cave_agent.compaction import default_token_estimate

    code = "rows = " + repr(list(range(300)))
    tool, _ = make_agent(ToolCallAgent, [tool_reply(code), text_reply("done")])
    fenced, _ = make_agent(FencedCodeAgent, [fenced_reply(code), text_reply("done")])
    for agent in (tool, fenced):
        asyncio.run(agent.run("go"))
        assert agent.spent["model_calls"] == 2
        # The second request carries the code, as a call's arguments or as a fence;
        # an estimate that read message content alone would miss the arguments.
        assert agent.spent["estimated_prompt_tokens"] >= default_token_estimate(code)
    # What was recorded is the provider's count wherever it reported one.
    assert tool.spent["prompt_tokens"] == 20


# -- the signalling fenced loop --------------------------------------------------------

def _signalling_agent(replies, outputs, *, max_steps=5):
    from cave_agent import Variable
    from core.agents import SignallingFencedCodeAgent
    agent, provider = make_agent(SignallingFencedCodeAgent, replies, max_steps=max_steps)
    for name in outputs:
        agent.runtime.inject_variable(Variable(name, None, f"output {name}"))
    agent.outputs = tuple(outputs)
    return agent, provider


def test_the_signalling_agent_says_nothing_while_an_output_is_still_unassigned():
    agent, provider = _signalling_agent([
        fenced_reply("a = 1"),                 # b still unassigned
        fenced_reply("b = 2"),
        text_reply("done"),
    ], outputs=["a", "b"])
    asyncio.run(agent.run("go"))
    first, second = execution_results(provider)
    assert NEXT_STEP[Action.FENCED_CODE] in first
    assert "is now assigned" not in first
    assert "Every required output (`a`, `b`) is now assigned" in second
    assert NEXT_STEP[Action.FENCED_CODE] not in second


def test_the_signalling_agent_with_no_outputs_reads_the_ordinary_sentence():
    agent, provider = _signalling_agent([fenced_reply("x = 1"), text_reply("done")], outputs=[])
    asyncio.run(agent.run("go"))
    assert NEXT_STEP[Action.FENCED_CODE] in execution_results(provider)[0]


def test_the_plain_fenced_agent_never_signals():
    """The frozen studies' agent: an assignment changes nothing it says."""
    from cave_agent import Variable
    agent, provider = make_agent(FencedCodeAgent, [fenced_reply("a = 1"), text_reply("done")])
    agent.runtime.inject_variable(Variable("a", None, "output a"))
    asyncio.run(agent.run("go"))
    sentence = execution_results(provider)[0]
    assert NEXT_STEP[Action.FENCED_CODE] in sentence
    assert "is now assigned" not in sentence


def test_an_output_assigned_to_none_does_not_count_as_assigned():
    agent, provider = _signalling_agent([
        fenced_reply("a = None"),
        text_reply("done"),
    ], outputs=["a"])
    asyncio.run(agent.run("go"))
    assert "is now assigned" not in execution_results(provider)[0]
