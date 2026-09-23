"""The two agent loops the paradigms run, alike in everything but the action.

A comparison of action formats is only as clean as the loops that carry them.
Both agents here are CaveAgent: the same step count and budget, the same
recovery from a response cut off at the output limit, the same compaction, the
same usage accounting and estimate when a provider reports none, the same time
reminder, the same system prompt wrapper, and the same shaping of execution
output. What differs is the action, and only where it must:

* :class:`FencedCodeAgent` reads code from the first closed ```python block in
  a streamed reply and stops reading there.
* :class:`ToolCallAgent` reads code from the first ``execute_python`` call in a
  streamed reply and stops reading when a second call begins. The call, not a
  fence, is written back into the history the provider sees.

Each action also has the repair that belongs to it and not the other. A fenced
reply passes through :mod:`core.stream_repair`, which turns a provider's leaked
native tool envelope into the fence the parser reads; a call needs no such
repair, because the provider itself parses its envelope into a call.

Each turns one step into at most one execution: a later block, or a later call,
is never run, and never enters the history.

Both close every execution result with the sentence :data:`core.prompts.NEXT_STEP`
gives their action, in place of CaveAgent's own, which names a code block and
asks for a plain-text answer (see there).

Both count what their loop did that a run's totals hide (:attr:`_BenchAgent.loop_events`)
and what every model call cost (:attr:`_BenchAgent.spent`). One thing differs by
action and cannot be made not to: a fenced reply is read only to its first
closed block, before the provider's usage report arrives, so its recorded cost
is CaveAgent's estimate, while a tool call is read to its end and its recorded
cost is the provider's count. So every call is also estimated the same way from
the text it was sent and the text it produced, a tool call's arguments included,
and costs compared across actions are compared on that estimate. Neither count
includes the calls CaveAgent makes to summarise a history it compacts, which it
does not report; compactions are counted in ``loop_events``.

Both say why a run ended in a model error when the conversation, not the
provider, caused it (:attr:`_BenchAgent.stop_cause`): a reply still cut off by the
output limit after every resumption, or a history that no longer fits the
context window after compaction. A paradigm that writes a large table into its
reply meets both, so these are failures to score, not outages to retry.

:class:`ToolCallAgent` overrides three internal methods of ``cave_agent`` 0.8.0
(``_stream_once``, ``_handle_turn``, ``_prepare_messages``), and reuses two of
its private helpers; the version is pinned in ``pyproject.toml``, and
``tests/test_agents.py`` checks the behaviour these rely on.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import AsyncGenerator
from dataclasses import asdict, dataclass
from functools import cached_property
import inspect
import json
from typing import Any

from cave_agent import CaveAgent
from cave_agent.agent import _close_stream, _conclude_turn
from cave_agent.compaction import default_token_estimate
from cave_agent.events import (
    CodeEvent, Event, ExecutionResultEvent, StatusEvent, StatusType, TextEvent,
)
from cave_agent.messages import CodeExecutionMessage, ExecutionResultMessage, Message
from cave_agent.models import (
    PromptTooLongError, StreamDelta, StreamResponse, TokenUsage, stream_with_idle_timeout,
)
from cave_agent.models.errors import raise_model_error
from cave_agent.models.litellm import LiteLLMModel, _LiteLLMStreamResponse

from core.paradigms import Action
from core.prompts import (
    MALFORMED_ARGUMENTS, NEXT_STEP, OUTPUTS_ASSIGNED, TOOL_NAME, TOOL_SCHEMA, UNKNOWN_TOOL,
    UPSTREAM_NEXT_STEP,
)


# Why a run ended in a model error the conversation caused (see the module docstring).
OUTPUT_TRUNCATED = "output_truncated"
CONTEXT_OVERFLOW = "context_overflow"


class _BenchAgent(CaveAgent):
    """CaveAgent, closing each execution result with its action's next-step sentence."""

    action: Action

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Since the agent was built: model calls whose usage the provider reported
        # and calls whose usage was estimated, replies resumed after being cut off,
        # and compactions of the history.
        self.loop_events: Counter[str] = Counter()
        # Since the agent was built: model calls, their tokens as recorded (the
        # provider's count, or the estimate when it sent none), and their tokens
        # as estimated for every call alike.
        self.spent: Counter[str] = Counter()
        # For the latest run: OUTPUT_TRUNCATED, CONTEXT_OVERFLOW or None.
        self.stop_cause: str | None = None

    async def stream_events(self, query: str) -> AsyncGenerator[Event, None]:
        self.stop_cause = None
        async for event in super().stream_events(query):
            if isinstance(event, StatusEvent) and event.status in _COUNTED_STATUSES:
                self.loop_events[event.status.value] += 1
            yield event

    async def _stream_turn(self, turn) -> AsyncGenerator[Event, None]:
        try:
            async for event in super()._stream_turn(turn):
                yield event
        except PromptTooLongError:
            # CaveAgent compacts once on an overflow; this is the overflow after it.
            self.stop_cause = CONTEXT_OVERFLOW
            raise

    async def _handle_turn(self, turn, state) -> AsyncGenerator[Event, None]:
        if turn.code is None and turn.error is None and turn.finish_reason == "length":
            # Handed over still cut off: the resumptions are spent, and CaveAgent
            # ends the run with a model error.
            self.stop_cause = OUTPUT_TRUNCATED
        async for event in super()._handle_turn(turn, state):
            yield event

    def _finalize_turn_usage(self, turn, stream, wire, output) -> None:
        reported = getattr(stream, "usage", None)
        provider = reported is not None and reported.total_tokens != 0
        self.loop_events["usage_provider" if provider else "usage_estimated"] += 1
        super()._finalize_turn_usage(turn, stream, wire, output)
        written = output + (getattr(stream, "refusal", "") or "")
        estimate = self._estimate_turn_usage(wire, written, getattr(stream, "thinking", "") or "")
        self.spent.update({
            "model_calls": 1,
            "prompt_tokens": turn.usage.prompt_tokens,
            "completion_tokens": turn.usage.completion_tokens,
            "estimated_prompt_tokens": estimate.prompt_tokens,
            "estimated_completion_tokens": estimate.completion_tokens,
        })

    def _estimate_turn_usage(
        self, wire: list[dict[str, Any]], text: str, thinking: str = "",
    ) -> TokenUsage:
        """CaveAgent's estimate, counting a tool call's arguments with the content.

        CaveAgent counts each message's content, and a call's code is in its
        arguments; left out, a tool-call history would be estimated on less text
        than the same history written as fences.
        """
        count = self.compactor.token_estimator or default_token_estimate
        prompt = sum(
            count(message.get("content") or "")
            + sum(count(call["function"]["arguments"]) for call in message.get("tool_calls", ()))
            for message in wire
        )
        completion = count(text) + count(thinking)
        if (text or thinking) and completion == 0:
            completion = 1
        return TokenUsage(
            prompt_tokens=prompt, completion_tokens=completion, total_tokens=prompt + completion,
        )

    async def _execute(self, code: str) -> tuple[Event, str]:
        event, prompt = await super()._execute(code)
        return event, prompt.replace(UPSTREAM_NEXT_STEP, NEXT_STEP[self.action])


_COUNTED_STATUSES = {StatusType.OUTPUT_RECOVERY, StatusType.COMPACTED}


class FencedCodeAgent(_BenchAgent):
    """The agent of every paradigm whose action is a fenced ```python block."""

    action = Action.FENCED_CODE


class SignallingFencedCodeAgent(FencedCodeAgent):
    """A fenced-code agent told when every output it was asked for is assigned.

    The runtime registers the turn's output variables and can see which are
    bound; the model cannot, because an assignment looks like any other line of
    code, where writing a file is a visible act of delivery. Left to infer it, an
    agent that had assigned its last output was seen to spend the rest of its
    step budget re-typing the variable's name — half of the runs that hit the
    step limit in the pipeline study had their table correct by step seven.

    So after each execution this agent asks the runtime whether every name in
    ``outputs`` is bound, and when all are, closes the result with
    :data:`core.prompts.OUTPUTS_ASSIGNED` instead of the usual next-step
    sentence. Nothing else changes: the same loop, prompt and budget. The
    frozen studies never use this class, and ``outputs`` is set per turn by the
    caller, so a turn that asks for nothing signals nothing.
    """

    outputs: tuple[str, ...] = ()

    async def _execute(self, code: str) -> tuple[Event, str]:
        event, prompt = await super()._execute(code)
        if self.outputs and await self._all_assigned():
            names = ", ".join(f"`{name}`" for name in self.outputs)
            prompt = prompt.replace(
                NEXT_STEP[self.action], OUTPUTS_ASSIGNED.format(names=names),
            )
        return event, prompt

    async def _all_assigned(self) -> bool:
        for name in self.outputs:
            try:
                value = self.runtime.retrieve(name)
                value = await value if inspect.isawaitable(value) else value
            except KeyError:
                return False
            if value is None:
                return False
        return True


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

    def transcript_fields(self) -> dict[str, Any]:
        """What a transcript records of this turn beyond its role and content."""
        return {"text": self.text, "tool_call": asdict(self.call)}


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


class ToolCallAgent(_BenchAgent):
    """The agent of every paradigm whose action is an ``execute_python`` call.

    Its model must be a ``LiteLLMModel``: the call is requested through LiteLLM's
    streaming completion, with the tool offered.
    """

    action = Action.TOOL_CALL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The call the current step's reply ended in, from streaming it to handling it.
        self._call: ToolCall | None = None

    def _tool_stream(self, wire: list[dict[str, Any]]) -> StreamResponse:
        return _ToolCallStream(self.model, wire)

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
