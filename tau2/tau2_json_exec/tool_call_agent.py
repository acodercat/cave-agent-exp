"""The tool-call loop, vendored from cave-bench so the two projects run one arm.

Source: ``cave-bench/core/agents.py`` at commit b5a6dae (md5
3d21234bbfde8442d9823864c3f0f4d7), where it is the ``json_exec`` paradigm of the
X1 ablation. Copied rather than imported: that module reaches ``core.prompts``,
which pulls in the FinBench data catalog and pandas, and cave-bench declares no
``[build-system]``, so it cannot be a dependency. It is also frozen at tag
``x1-frozen-v1`` and owned by other work, so a one-way import would be pressure
to edit it.

What is copied is exact, so that the tau2 arm and the cave-bench arm are the
same intervention: the reply is read to its first complete ``execute_python``
call and no further, the call — not a fence — is written back into the history
the provider sees, and a call the output limit cut off is made again rather than
resumed. The one addition is ``_execute``, which replaces cave-agent's own
closing sentence: "provide the next code block" tells an arm whose only way to
run code is a JSON call to do the one thing that will not run.

Not copied: cave-bench's ``_BenchAgent`` counters (``loop_events``, ``spent``,
``stop_cause``). tau2 accounts for a turn through ``AssistantMessage.usage`` and
``raw_data``, which ``tau2_cave.agent`` already fills.

These overrides reach into cave-agent 0.8.0 internals (``_stream_once``,
``_handle_turn``, ``_prepare_messages``); ``tests/test_json_exec_agent.py`` pins
the version and ``_prepare_messages`` raises if upstream's rendering changes.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from functools import cached_property
import json
from typing import Any

from cave_agent import CaveAgent
from cave_agent.agent import _close_stream, _conclude_turn
from cave_agent.events import CodeEvent, Event, ExecutionResultEvent, TextEvent
from cave_agent.messages import CodeExecutionMessage, ExecutionResultMessage, Message
from cave_agent.models import (
    PromptTooLongError, StreamDelta, StreamResponse, stream_with_idle_timeout,
)
from cave_agent.models.errors import raise_model_error
from cave_agent.models.litellm import LiteLLMModel, _LiteLLMStreamResponse

from tau2_json_exec.prompts import (
    MALFORMED_ARGUMENTS, NEXT_STEP_TOOL_CALL, TOOL_NAME, TOOL_SCHEMA, UNKNOWN_TOOL,
    UPSTREAM_NEXT_STEP,
)


@dataclass(frozen=True)
class ToolCall:
    """One complete tool call, as the model wrote it."""

    id: str
    name: str
    arguments: str

    @cached_property
    def code(self) -> str | None:
        """The code to run, or None when the call cannot run."""
        if self.name != TOOL_NAME:
            return None
        try:
            code = json.loads(self.arguments).get("code")
        except (json.JSONDecodeError, AttributeError):
            return None
        return code if isinstance(code, str) else None

    @property
    def refusal(self) -> str:
        """What the model is told in place of an execution result."""
        if self.name != TOOL_NAME:
            return UNKNOWN_TOOL.format(name=self.name)
        return MALFORMED_ARGUMENTS

    def as_wire(self) -> dict[str, Any]:
        return {
            "id": self.id, "type": "function",
            "function": {"name": self.name, "arguments": self.arguments},
        }


class ToolCallMessage(CodeExecutionMessage):
    """An assistant turn that ended in a tool call.

    A :class:`CodeExecutionMessage`, so compaction and the recovery of a dangling
    execution treat it as the turn it is. ``content`` shows the call the way a
    fenced turn shows its block, which is what compaction measures and
    summarises; the provider is sent ``text`` and the call itself.
    """

    def __init__(self, text: str, call: ToolCall):
        code = call.code
        shown = f"```python\n{code}\n```" if code is not None else call.arguments
        super().__init__(f"{text}\n{shown}" if text else shown)
        self.text = text
        self.call = call


@dataclass
class _PartialCall:
    id: str | None = None
    name: str = ""
    arguments: str = ""


class _ToolCallStream(_LiteLLMStreamResponse):
    """A LiteLLM stream offered the tool, collecting tool calls as they stream.

    A chunk that carries only part of a call yields an empty delta, so the
    stream counts it as output received (a connection is never replayed over a
    call already under way) and the idle watchdog sees progress.
    """

    def __init__(self, model: LiteLLMModel, messages: list[dict[str, Any]]):
        super().__init__(model, messages)
        self.calls: dict[int, _PartialCall] = {}

    async def _open_stream(self):
        # Once per connection attempt, which is where a replay begins.
        self.calls = {}
        params = self._model._prepare_params(self._messages)
        if self._model._supports_stream_options():
            params.setdefault("stream_options", {"include_usage": True})
        params["tools"] = [TOOL_SCHEMA]
        params["stream"] = True
        return await self._model._litellm.acompletion(**params)

    def _process_stream_chunk(self, chunk: Any) -> StreamDelta | None:
        delta = super()._process_stream_chunk(chunk)
        choices = getattr(chunk, "choices", None) or []
        parts = getattr(choices[0].delta, "tool_calls", None) if choices else None
        for part in parts or ():
            call = self.calls.setdefault(part.index or 0, _PartialCall())
            call.id = call.id or part.id
            function = part.function
            if function is not None:
                # The name arrives whole, in the call's first part; the arguments
                # arrive in pieces. Some gateways repeat the name in later parts.
                call.name = call.name or function.name or ""
                call.arguments += function.arguments or ""
        if delta is None and parts:
            return StreamDelta()
        return delta


class ToolCallAgent(CaveAgent):
    """The agent of every paradigm whose action is an ``execute_python`` call.

    Its model must be a ``LiteLLMModel``: the call is requested through LiteLLM's
    streaming completion, with the tool offered.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The call the current step's reply ended in, from streaming it to handling it.
        self._call: ToolCall | None = None

    def _tool_stream(self, wire: list[dict[str, Any]]) -> StreamResponse:
        return _ToolCallStream(self.model, wire)

    async def _execute(self, code: str) -> tuple[Event, str]:
        """Run the code, closing its result with the sentence this action needs.

        cave-agent ends every execution result with "provide the next code
        block". This arm has no block to provide: the only way to run code is a
        call. Left unchanged, the loop would end each step by asking for the one
        thing it cannot do.
        """
        event, prompt = await super()._execute(code)
        return event, prompt.replace(UPSTREAM_NEXT_STEP, NEXT_STEP_TOOL_CALL)

    async def _stream_once(self, turn) -> AsyncGenerator[Event, None]:
        """Stream one reply, keeping its first complete call.

        Mirrors ``CaveAgent._stream_once``: the reply is read until a second
        call begins, as a fenced reply is read until its first block closes;
        usage is taken from the provider or estimated; and the turn is concluded
        by the same rules. A call is complete unless the output limit cut the
        reply before its arguments closed; an incomplete one is not code, and
        the step recovers as it does from an unterminated block.
        """
        turn.error = None
        turn.code = None
        self._call = None
        wire = self._prepare_messages()
        try:
            stream = self._tool_stream(wire)
        except Exception as error:
            raise_model_error(error)

        chunks: list[str] = []
        stopped_at_call = False
        fatal_stream_error: Exception | None = None
        try:
            async for delta in stream_with_idle_timeout(stream, self.stream_idle_timeout):
                if delta.content:
                    chunks.append(delta.content)
                    yield TextEvent(delta.content)
                if len(stream.calls) > 1:
                    stopped_at_call = True
                    break
        except PromptTooLongError:
            raise
        except Exception as error:
            if not chunks and not stream.calls:
                fatal_stream_error = error
            else:
                turn.error = error
        finally:
            try:
                await _close_stream(stream)
            finally:
                arguments = "".join(call.arguments for call in stream.calls.values())
                self._finalize_turn_usage(turn, stream, wire, "".join(chunks) + arguments)
        if fatal_stream_error is not None:
            raise fatal_stream_error

        turn.text = "".join(chunks)
        turn.finish_reason = stream.finish_reason
        if stream.calls and turn.error is None:
            first = stream.calls[min(stream.calls)]
            call = ToolCall(
                id=first.id or f"call_{len(self.messages)}", name=first.name,
                arguments=first.arguments,
            )
            if stopped_at_call or stream.finish_reason != "length" or call.code is not None:
                self._call = call
                # Present, so the step reads the turn as whole; what runs is decided
                # when it is handled.
                turn.code = call.code if call.code is not None else ""

        refusal_event = _conclude_turn(
            turn, stream, stopped_at_code=stopped_at_call, defer_execution=False,
        )
        if refusal_event is not None:
            yield refusal_event

    async def _handle_turn(self, turn, state) -> AsyncGenerator[Event, None]:
        """Run the turn's call, or record the turn as the final answer."""
        call, self._call = self._call, None
        if call is None:
            async for event in super()._handle_turn(turn, state):
                yield event
            return

        state.final_content = turn.full
        self.add_message(ToolCallMessage(turn.text, call))
        code = call.code
        if code is None:
            self.add_message(ExecutionResultMessage(call.refusal))
            yield ExecutionResultEvent(output=call.refusal, success=False)
            return
        state.code_snippets.append(code)
        yield CodeEvent(code)
        event, next_prompt = await self._execute(code)
        self.add_message(ExecutionResultMessage(next_prompt))
        yield event

    def _prepare_messages(self) -> list[dict[str, Any]]:
        """The history as the provider sees it: calls as calls, results as their answers.

        CaveAgent's rendering supplies the time reminder, which is the one
        message its wire holds that the history does not.
        """
        upstream = super()._prepare_messages()
        rendered = _tool_wire(self.messages)
        # CaveAgent inserts the reminder right after the system prompt, which
        # opens every history it builds.
        if len(upstream) != len(rendered) + 1 or upstream[0]["role"] != "system":
            raise RuntimeError("cave-agent no longer renders history as ToolCallAgent expects")
        return [rendered[0], upstream[1], *rendered[1:]]


def _tool_wire(messages: list[Message]) -> list[dict[str, Any]]:
    """Render history, pairing each call with the execution result after it.

    Pairing is by order, not by object: compaction replaces a result message
    with a new one, and the pair must survive that.
    """
    wire: list[dict[str, Any]] = []
    open_call: ToolCall | None = None
    for message in messages:
        if isinstance(message, ToolCallMessage):
            wire.append({
                "role": "assistant", "content": message.text,
                "tool_calls": [message.call.as_wire()],
            })
            open_call = message.call
        elif isinstance(message, ExecutionResultMessage) and open_call is not None:
            wire.append({"role": "tool", "tool_call_id": open_call.id, "content": message.content})
            open_call = None
        else:
            wire.append({"role": message.wire_role, "content": message.content})
    return wire
