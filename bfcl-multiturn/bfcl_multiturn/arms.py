"""The two paradigms, given the same tools over the same state.

Both are handed the same instances, the same bound methods in the same order and
the same task text; they differ only in how an action is expressed. That is what
R3 asks for: a baseline whose backend and operations match, so a difference is
attributable to the action format rather than to capability.

* ``cave`` writes Python against the instances, in a persistent runtime.
* ``fc`` emits JSON tool calls, each dispatched to the same bound method. It has
  no runtime between calls, which is the paradigm the paper compares against. It
  calls litellm directly rather than through cave-agent's model layer, because
  the protocol under test is the provider's own.

A turn is one call to the arm; the conversation's state lives in the instances,
so an arm keeps whatever context it keeps and the benchmark reads the state.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import litellm
from cave_agent import CaveAgent, Function, IPythonRuntime, StopReason

from bfcl_multiturn.prompts import CAVE, FC, FENCE_REMINDER
from bfcl_multiturn.recorder import Recorder


@dataclass
class TurnResult:
    """What one turn produced: the calls it made, and how it ended."""

    steps: list[list[str]]
    reply: str
    stop_reason: str
    model_steps: int
    #: Whether the turn had to be asked for its action format again.
    repaired: bool = False
    #: The code the turn executed, for the cave arm. Kept because a recording is
    #: a claim about this code, and a claim that falls short is worth reading.
    code: tuple[str, ...] = ()


def unexecuted_call(response, names: frozenset[str]) -> bool:
    """Whether a fenced turn tried to act in a form the runtime ignored.

    Not a wrong answer but a missed one: the code went to the user as text, so
    the agent waits on a result that never arrives and the conversation stalls.
    Only a turn that executed nothing qualifies, so a function named in a reply
    alongside real execution does not trigger it.
    """
    if response.code_snippets:
        return False
    text = response.content or ""
    if re.search(r"<\s*(?:tool_call|function|invoke|code)\b", text):
        return True
    if "```" in text:                       # a block the parser did not take
        return True
    return bool(names) and bool(re.search(rf"\b(?:{'|'.join(map(re.escape, sorted(names)))})\s*\(", text))


@dataclass
class CaveArm:
    """Python against the instances, in a persistent runtime."""

    model: Any
    methods: list[Callable]
    max_steps: int = 10
    name: str = field(default="cave", init=False)

    def __post_init__(self) -> None:
        self._recorder = Recorder()
        self.instances: dict[str, Any] = {}       # set by the runner, for the fidelity check
        runtime = IPythonRuntime(
            functions=[Function(self._recorder.wrap(method)) for method in self.methods])
        self._agent = CaveAgent(model=self.model, runtime=runtime,
                                instructions=CAVE, max_steps=self.max_steps)
        self._names = frozenset(method.__name__ for method in self.methods)

    async def turn(self, message: str) -> TurnResult:
        response = await self._agent.run(message)
        repaired = unexecuted_call(response, self._names)
        if repaired:
            # The provider gives the JSON arm a rejection and another attempt; a
            # fenced block has nothing equivalent, so ask once for the format.
            response = await self._agent.run(FENCE_REMINDER)
        return TurnResult(steps=self._recorder.take_turn(), reply=response.content or "",
                          stop_reason=response.stop_reason.value, model_steps=response.steps,
                          repaired=repaired, code=tuple(response.code_snippets or ()))


@dataclass
class Settings:
    """How a model is called, stated rather than left to a provider default."""

    model_id: str
    #: litellm needs the provider named; the gateways here speak the OpenAI API,
    #: so it is a parameter rather than something inferred from the id. `genai`
    #: is the provider in `gemini.py`, for a model whose thought signatures the
    #: OpenAI-compatible endpoint drops.
    provider: str = "openai"
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    #: Passed through to the request; reasoning is disabled explicitly, never
    #: assumed off, because the same model id reasons by default on some gateways.
    extra_body: dict = field(default_factory=lambda: {"thinking": {"type": "disabled"}})

    def request(self) -> dict:
        """The keyword arguments of one litellm call, provider included."""
        arguments = {"model": f"{self.provider}/{self.model_id}",
                     "temperature": self.temperature}
        if self.base_url:
            arguments["base_url"] = self.base_url
        if self.api_key:
            arguments["api_key"] = self.api_key
        if self.extra_body:
            arguments["extra_body"] = self.extra_body
        return arguments


@dataclass
class FunctionCallingArm:
    """JSON tool calls over the same methods, with no runtime between them."""

    settings: Settings
    methods: list[Callable]
    #: The benchmark's own JSON descriptions, so the tools are as it defines them.
    tool_documents: list[dict]
    max_steps: int = 10
    name: str = field(default="fc", init=False)

    def __post_init__(self) -> None:
        self._recorder = Recorder()
        self._by_name = {method.__name__: self._recorder.wrap(method) for method in self.methods}
        self._tools = list(self.tool_documents)      # already complete tool objects
        self._history: list[dict] = [{"role": "system", "content": FC}]

    async def turn(self, message: str) -> TurnResult:
        self._history.append({"role": "user", "content": message})
        reply, stop, steps = "", StopReason.MAX_STEPS.value, 0
        while steps < self.max_steps:
            steps += 1
            answer = await litellm.acompletion(messages=self._history, tools=self._tools,
                                               **self.settings.request())
            spoken = answer.choices[0].message
            self._history.append(spoken.model_dump(exclude_none=True))
            calls = spoken.tool_calls or []
            if not calls:                       # a turn ends when it stops calling
                reply, stop = spoken.content or "", StopReason.COMPLETED.value
                break
            for call in calls:
                self._history.append({"role": "tool", "tool_call_id": call.id,
                                      "content": self._dispatch(call.model_dump())})
            self._recorder.end_step()
        return TurnResult(steps=self._recorder.take_turn(), reply=reply,
                          stop_reason=stop, model_steps=steps)

    def _dispatch(self, call: dict) -> str:
        """Answer one tool call, and answer it even when it cannot be run.

        A turn whose history has an unanswered call cannot be sent again, so a
        bad name or bad arguments cost this step rather than the conversation.
        """
        name = call["function"]["name"]
        method = self._by_name.get(name)
        if method is None:
            return f"error: no tool named {name!r}"
        try:
            arguments = json.loads(call["function"]["arguments"] or "{}")
        except json.JSONDecodeError as error:
            return f"error: arguments were not JSON ({error})"
        try:
            return json.dumps(method(**arguments), default=repr)
        except Exception as error:                      # the tool's own refusal is data
            return f"error: {type(error).__name__}: {error}"


ARMS = {"cave": CaveArm, "fc": FunctionCallingArm}
