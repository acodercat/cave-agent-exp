"""CaveAgent as a tau2-bench agent.

tau2 expects an agent that answers one message at a time, and scores it on the
tool calls that message carries. CaveAgent instead runs a whole loop per turn,
calling tools itself as it writes and executes Python. Three things bridge that:

1. The tools CaveAgent gets are bound to a shadow copy of the environment's
   database, so its own execution does not double every write that tau2 will
   apply when it replays the calls. The copy is refreshed at every turn: tau2
   applies a task's initial state only after the agent is built, and in telecom
   the user side writes into the agent database mid-conversation.
2. Each of those tools is wrapped so the calls it makes are recorded in order.
3. A turn that made calls is reported to tau2 as a tool-calls-only message, and
   the text CaveAgent actually said is held back and returned on the next turn —
   tau2 rejects a message carrying both.
"""

import asyncio
import functools
import inspect
import re
from enum import Enum
from typing import Any, Callable, Iterable, Optional, get_args

from cave_agent import (
    AgentResponse,
    CaveAgent,
    FunctionRule,
    LiteLLMModel,
    SecurityChecker,
    StopReason,
    TokenUsage,
)
from cave_agent.runtime import Function, IPythonRuntime, Type
from loguru import logger
from pydantic import BaseModel
from tau2.agent.base import ValidAgentInputMessage
from tau2.agent.llm_agent import LLMAgent
from tau2.config import DEFAULT_MAX_RETRIES
from tau2.data_model.message import AssistantMessage, Message, ToolCall, UserMessage
from tau2.environment.tool import Tool
from tau2.registry import registry

from tau2_cave.prompts import AGENT_INSTRUCTIONS, FENCE_REMINDER

AGENT_NAME = "cave_agent"

# Model calls CaveAgent may make within one customer turn. A turn needs a few —
# look something up, act on it, reply — and a long one is typically re-reading
# state that cannot change until the customer acts, which they can do only
# after it replies. cave-agent's own default.
MAX_STEPS_PER_TURN = 10

# input() would block forever inside the runtime; the customer replies next turn.
_SECURITY_CHECKER = SecurityChecker([
    FunctionRule(
        {"input"},
        "Don't call input(). Ask the customer in your reply; they answer on the next turn.",
    )
])


# Markup a model wraps around code it means to run: its own tool-calling tokens,
# an invented tag, or a fence without the language. A well-formed ```python block
# is absent on purpose — for this arm that block is what runs.
_FENCED_CALL_MARKUP = r"<\s*python\s*>|<code_block>|<[｜|]\s*\w*DSML|```(?!python)"


def _unexecuted_call_pattern(
    tool_names: Iterable[str], markup: str = _FENCED_CALL_MARKUP,
) -> re.Pattern:
    """What marks a reply as code the runtime never ran.

    Listing markup alone does not hold: each model reaches for its own —
    <python>, <code>, <tool_call>, DSML tokens — and every new one slips past,
    as <code> did for deepseek-v4-flash and <tool_call> for qwen3.8-flash. A
    call to one of the agent's own tools in a turn that executed nothing is the
    same failure whatever wraps it. The markup stays as a second signal, for
    code that calls no tool.
    """
    calls = "|".join(re.escape(name) for name in sorted(tool_names))
    return re.compile(rf"{markup}|\b(?:{calls})\s*\(" if calls else markup)


def _looks_like_an_unexecuted_call(response: AgentResponse, pattern: re.Pattern) -> bool:
    """Whether a turn tried to run code in a form the runtime ignored.

    Such a turn is not a wrong answer but a missed one: the code went to the
    customer as text, so the agent is waiting on results that never come, and
    the conversation loops until the step budget ends it. Only a turn that ran
    nothing qualifies, so a function name in a reply alongside real execution
    cannot trigger it.
    """
    return not response.code_snippets and bool(pattern.search(response.content or ""))


class CaveAgentState(BaseModel):
    """What has to survive between tau2 turns.

    CaveAgent keeps its own history, so the only state here is the reply held
    back while tau2 replays a turn's tool calls.
    """

    turn_count: int = 0
    pending_reply: Optional[str] = None


class ToolCallRecorder:
    """Records the calls CaveAgent makes, in the order it makes them."""

    def __init__(self) -> None:
        self._calls: list[ToolCall] = []

    def wrap(self, func: Callable) -> Callable:
        """Return `func` with call recording; signature and docstring are kept.

        CaveAgent describes tools to the model from exactly those two things, so
        the wrapper must be transparent to `inspect`.
        """
        signature = inspect.signature(func)

        @functools.wraps(func)
        def recorded(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            self._calls.append(ToolCall(
                id=f"call_{len(self._calls)}",
                name=func.__name__,
                arguments=_as_json(dict(bound.arguments)),
                requestor="assistant",
            ))
            return func(*args, **kwargs)

        return recorded

    def take(self) -> list[ToolCall]:
        """Hand over the calls recorded so far and start a fresh turn."""
        calls, self._calls = self._calls, []
        return calls


def _as_json(value: Any) -> Any:
    """Make tool arguments serializable: tau2 stores them in the result file.

    Domain tools take pydantic models (a Passenger, a FlightInfo), which json
    cannot encode on its own.
    """
    if isinstance(value, BaseModel):   # not hasattr: the class has model_dump too
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _as_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    logger.debug(f"Tool argument of type {type(value).__name__} serialized with str()")
    return str(value)


def _count_usage_sources(agent: CaveAgent) -> Callable[[], dict[str, int]]:
    """Count, per model call, whether the provider reported usage or it was estimated.

    Both paradigms read cave-agent's own accounting, which estimates a call the
    provider says nothing about. It says nothing more often for a fenced reply,
    which is read only to its first closed code block — before the usage chunk
    arrives — than for a tool call, read to its end. So the two arms' token
    figures can come from different sources, and a comparison of them has to say
    how often. Wrapping the method rather than overriding it keeps the count
    identical for every arm, and keeps the vendored loop a faithful copy.
    """
    counts = {"reported": 0, "estimated": 0}
    finalize = agent._finalize_turn_usage

    @functools.wraps(finalize)
    def counted(turn, stream, wire, output):
        reported = getattr(stream, "usage", None)
        counts["reported" if reported and reported.total_tokens else "estimated"] += 1
        return finalize(turn, stream, wire, output)

    agent._finalize_turn_usage = counted
    return lambda: dict(counts)


def _trace(attempts: list[AgentResponse]) -> dict:
    """What CaveAgent did this turn, to store on the message tau2 keeps.

    A turn is usually one attempt; a format correction makes it two, and both
    cost tokens and time. The last attempt decides how the turn ended. The code
    it ran is the part a result file cannot otherwise show: tau2 records the
    tool calls, not the Python that produced them.
    """
    return {
        "stop_reason": attempts[-1].stop_reason.name,
        "steps": sum(a.steps for a in attempts),
        "elapsed": sum(a.elapsed for a in attempts),
        "usage": _total_usage(attempts).to_dict(),
        "code_snippets": [code for a in attempts for code in a.code_snippets],
        "format_corrections": len(attempts) - 1,
    }


def _total_usage(attempts: list[AgentResponse]) -> TokenUsage:
    return sum((a.usage for a in attempts[1:]), attempts[0].usage)


def _tau2_usage(usage: TokenUsage) -> dict:
    """Token usage in the shape tau2 stores on a message.

    The FC baseline's messages carry it there, so tau2's own accounting —
    get_token_usage and the run summaries built on it — reads both paradigms
    from the same field.
    """
    return {"completion_tokens": usage.completion_tokens, "prompt_tokens": usage.prompt_tokens}


def _live_toolkit(tools: list[Tool]) -> Any:
    """The toolkit tau2 scores against.

    Every tau2 tool is a bound method of one toolkit, so the toolkit — and the
    database behind it — is reachable from any of them.
    """
    if not tools:
        raise ValueError("A tau2 domain must provide at least one tool")
    return tools[0]._func.__self__


def _shadow_toolkit(live: Any) -> Any:
    """A second toolkit of the same kind, over a copy of the live database."""
    return type(live)(db=live.db.model_copy(deep=True))


def _data_types(db: type[BaseModel]) -> list[type]:
    """The models and enums a domain's database is built from.

    Tools return these objects, but their signatures do not always say which:
    telecom's get_details_by_id is annotated Dict[str, Any] and returns a Line,
    a Bill or a Plan. Described to the model, they give it the field names it
    otherwise guesses — `bill.total_amount_due` for `total_due` — at the cost of
    an error and another step each time. The FC baseline reads the same objects
    as JSON, keys included, so this closes a gap rather than opening one.
    """
    found: list[type] = []

    def visit(annotation: Any) -> None:
        for argument in get_args(annotation):   # list[Line], Optional[Plan], ...
            visit(argument)
        if not isinstance(annotation, type) or annotation in found:
            return
        if issubclass(annotation, Enum):
            found.append(annotation)
        elif issubclass(annotation, BaseModel):
            found.append(annotation)
            for field in annotation.model_fields.values():
                visit(field.annotation)

    for field in db.model_fields.values():
        visit(field.annotation)
    return found


class Tau2CaveAgent(LLMAgent):
    """Runs a tau2 domain with CaveAgent.

    Subclasses tau2's own LLM agent rather than LocalAgent directly: `run_task`
    picks how to construct an agent by walking `issubclass` over the agent types
    it knows, and only the LLMAgent branch matches this constructor. Everything
    that decides behaviour — the state, the messages, the tool calls — is
    overridden below; what is inherited is the plumbing tau2 expects.

    The two class attributes below are the only seam an arm that differs in its
    action format needs (`tau2_json_exec`): the loop class, and the instructions
    naming that action. Everything a paradigm comparison has to hold fixed — the
    shadow database and its per-turn resync, the recorder, the injected
    functions and types, the retry and step budgets — is written once, here.
    """

    # The CaveAgent loop this arm runs, the instructions that name its action, the
    # markup that means "code that never ran" for that action, and the correction
    # sent when it happens.
    _AGENT_CLASS = CaveAgent
    _INSTRUCTIONS = AGENT_INSTRUCTIONS
    _CALL_MARKUP = _FENCED_CALL_MARKUP
    _CORRECTION = FENCE_REMINDER

    def __init__(
        self,
        tools: list[Tool],
        domain_policy: str,
        llm: str,
        llm_args: Optional[dict] = None,
    ):
        """Build the agent for one task.

        Args:
            tools: The environment's tools, already initialized for this task
            domain_policy: The domain policy the agent has to follow
            llm: Model id, passed to litellm
            llm_args: api_key, base_url, temperature, ... plus `max_steps` and
                `max_exec_output` for CaveAgent itself
        """
        super().__init__(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args)
        llm_args = dict(self.llm_args)  # the parent deep-copied it, so popping here is safe
        max_steps = llm_args.pop("max_steps", MAX_STEPS_PER_TURN)
        max_exec_output = llm_args.pop("max_exec_output", 10_000)

        self._live = _live_toolkit(tools)
        self._shadow = _shadow_toolkit(self._live)
        self._unexecuted_call = _unexecuted_call_pattern(
            self._shadow.get_tools(), self._CALL_MARKUP)
        self._recorder = ToolCallRecorder()
        functions = [
            Function(self._recorder.wrap(tool._func))
            for tool in self._shadow.get_tools().values()
        ]
        types = [Type(data_type) for data_type in _data_types(type(self._live.db))]
        self._agent = self._AGENT_CLASS(
            # The same retry budget tau2 hands its own agent, so a gateway
            # hiccup does not end a sweep for one paradigm and not the other.
            model=LiteLLMModel(model_id=llm, num_retries=DEFAULT_MAX_RETRIES, **llm_args),
            runtime=IPythonRuntime(
                functions=functions, types=types, security_checker=_SECURITY_CHECKER,
            ),
            instructions=self._INSTRUCTIONS.format(domain_policy=domain_policy),
            max_steps=max_steps,
            max_exec_output=max_exec_output,
            **self._agent_kwargs(),
        )
        self._usage_sources = _count_usage_sources(self._agent)
        logger.info(
            f"{type(self._agent).__name__} ready with {len(functions)} tools "
            "on a shadow database"
        )

    def _turn_trace(self, attempts: list[AgentResponse]) -> dict:
        """What this turn did, for the message tau2 keeps. An arm may add to it."""
        return _trace(attempts) | {"usage_sources": self._usage_sources()}

    def _agent_kwargs(self) -> dict:
        """What this arm passes to its loop beyond the shared arguments.

        Empty here: the fenced arm reads cave-agent's own system instructions,
        which describe a code block, and that is the right description of it.
        """
        return {}

    def _sync_shadow(self) -> None:
        """Point the shadow toolkit at a fresh copy of the live database.

        Once per turn rather than once per task. tau2's orchestrator applies the
        task's initial state (a line over its data cap, roaming switched off)
        after the agent is constructed, so a copy taken then shows the pristine
        domain; and the telecom environment lets the user side write into the
        agent database (a bill the customer pays), so a copy taken later drifts
        as the conversation goes. Tools are bound methods reading `self.db`, so
        swapping the attribute is all it takes.
        """
        self._shadow.db = self._live.db.model_copy(deep=True)

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> CaveAgentState:
        """Start a task. CaveAgent carries its own history, so there is none to seed."""
        return CaveAgentState()

    @property
    def system_prompt(self) -> str:
        """The prompt the model actually sees, which CaveAgent builds itself.

        tau2 reads this when seeding an agent's history; CaveAgent keeps its own,
        so nothing here depends on it, but it stays answerable for logs.
        """
        return self._agent.build_system_prompt()

    def generate_next_message(
        self, message: ValidAgentInputMessage, state: CaveAgentState
    ) -> tuple[AssistantMessage, CaveAgentState]:
        """Answer one tau2 turn.

        A turn where CaveAgent called tools takes two messages: the calls, so
        tau2 can replay and score them, then the reply it held back.
        """
        if not isinstance(message, UserMessage):
            return self._release_pending_reply(state)

        self._sync_shadow()
        attempts = [asyncio.run(self._agent.run(message.content))]
        if _looks_like_an_unexecuted_call(attempts[0], self._unexecuted_call):
            logger.warning("A reply carried code the runtime did not parse; asking for the fence")
            attempts.append(asyncio.run(self._agent.run(self._CORRECTION)))
        response = attempts[-1]

        if response.stop_reason in (StopReason.MODEL_ERROR, StopReason.RUNTIME_ERROR):
            # Raising lets tau2 record an infrastructure failure. Returning an
            # apology instead would be scored as if the agent had answered.
            raise RuntimeError(
                f"CaveAgent stopped on {response.stop_reason.name}: {response.content}"
            )

        state.turn_count += 1
        logger.info(
            f"Turn {state.turn_count}: {response.stop_reason.name} in {response.steps} steps"
        )

        # Usage goes on the message that stands for this turn's model calls; the
        # reply released after tau2's replay made none.
        accounting = {
            "raw_data": self._turn_trace(attempts),
            "usage": _tau2_usage(_total_usage(attempts)),
        }
        tool_calls = self._recorder.take()
        if not tool_calls:
            message = AssistantMessage(role="assistant", content=response.content, **accounting)
            return message, state

        state.pending_reply = response.content
        message = AssistantMessage(role="assistant", tool_calls=tool_calls, **accounting)
        return message, state

    def _release_pending_reply(
        self, state: CaveAgentState
    ) -> tuple[AssistantMessage, CaveAgentState]:
        """Return the reply held back while tau2 replayed this turn's tool calls."""
        reply, state.pending_reply = state.pending_reply, None
        if reply is None:
            # tau2 only sends tool results for calls we reported, so this means
            # the two sides disagree about the turn rather than a quiet edge case.
            raise RuntimeError("tau2 returned tool results for a turn that reported no tool calls")
        return AssistantMessage(role="assistant", content=reply), state


def register() -> None:
    """Make the agent available to tau2 as `cave_agent`."""
    if AGENT_NAME in registry.get_info().agents:
        return
    registry.register_agent(Tau2CaveAgent, AGENT_NAME)
    logger.info(f"Registered {AGENT_NAME} with tau2")
