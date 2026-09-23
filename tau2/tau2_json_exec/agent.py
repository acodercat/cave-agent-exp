"""The capability-matched JSON baseline: a tool call, over the same persistent runtime.

Reviewer R3's third comment is that the paper's JSON baseline "differs in several
respects at once. It removes code execution as well as the injection/retrieval
mechanism," and asks for one that keeps them:

    A stronger baseline could use JSON function calls while retaining the same
    persistent backend and access to equivalent operations. For example, the
    baseline could call a Python execution tool…

That is this arm. The model is offered exactly one JSON function,
``execute_python``; the domain's tools still reach it as Python functions
injected into the same ``IPythonRuntime``, described the same way. So persistent
state and native injection are held fixed, and what changes is how an action
crosses the boundary: a serialized call instead of a fenced block.

Everything the comparison holds fixed is inherited from :class:`Tau2CaveAgent`
rather than rewritten — the shadow database and its per-turn resync, the call
recorder, the injected functions and types, tau2's retry budget, the per-turn
step budget, the pending-reply split, the trace and token accounting. Only the
four seams that describe the action are overridden.
"""

from typing import Optional

from loguru import logger
from tau2.data_model.message import AssistantMessage
from tau2.registry import registry

from tau2_cave.agent import CaveAgentState, Tau2CaveAgent
from tau2_json_exec.prompts import (
    AGENT_INSTRUCTIONS, TOOL_CALL_MARKUP, TOOL_CALL_SYSTEM_INSTRUCTIONS, TOOL_REMINDER,
)
from tau2_json_exec.tool_call_agent import ToolCallAgent

AGENT_NAME = "json_exec_agent"

# What a turn says when the model answered with a bare call and no prose. tau2
# rejects an assistant message that is neither text nor calls, and this arm meets
# that case often: a fenced reply usually carries prose around its block, a tool
# call need not. Counted in the trace so its frequency stays auditable.
EMPTY_TURN_REPLY = "One moment."


class Tau2JsonExecAgent(Tau2CaveAgent):
    """Tau2CaveAgent with the action format flipped to an ``execute_python`` call."""

    _AGENT_CLASS = ToolCallAgent
    _INSTRUCTIONS = AGENT_INSTRUCTIONS
    _CALL_MARKUP = TOOL_CALL_MARKUP
    _CORRECTION = TOOL_REMINDER

    def _agent_kwargs(self) -> dict:
        """Read the runtime rules as this action performs them.

        cave-agent's own system instructions tell the model to write its code in
        a fenced block. The fenced arm relies on that default and is right to;
        here it would describe the one form that does not run, so this arm passes
        the same instructions with those sentences rewritten (see
        ``tau2_json_exec.prompts``).
        """
        return {"system_instructions": TOOL_CALL_SYSTEM_INSTRUCTIONS}

    def __init__(self, *args, **kwargs):
        # Counted from before the first turn, so a trace can report it from turn one.
        self._empty_replies = 0
        super().__init__(*args, **kwargs)

    def _release_pending_reply(
        self, state: CaveAgentState
    ) -> tuple[AssistantMessage, CaveAgentState]:
        """Hand back the held reply, standing in for one the model never wrote.

        A turn that ended in a bare call with no prose leaves nothing to say, and
        an assistant message that is neither text nor calls fails tau2's own
        validation. The filler keeps the conversation going, and the count rides
        on the message itself: how often one arm had to speak for the model is a
        measured asymmetry between the arms, not a hidden one.
        """
        stood_in = not (state.pending_reply or "").strip()
        if stood_in:
            state.pending_reply = EMPTY_TURN_REPLY
            self._empty_replies += 1
            logger.debug("A turn ended in a bare call; released a filler reply")
        message, state = super()._release_pending_reply(state)
        message.raw_data = {"stood_in_for_an_empty_reply": stood_in,
                            "empty_replies": self._empty_replies}
        return message, state

    def _turn_trace(self, attempts: list) -> dict:
        """The shared trace, plus how many replies this arm has stood in for."""
        return super()._turn_trace(attempts) | {"empty_replies": self._empty_replies}


def register() -> None:
    """Make the agent available to tau2 as `json_exec_agent`."""
    if AGENT_NAME in registry.get_info().agents:
        return
    registry.register_agent(Tau2JsonExecAgent, AGENT_NAME)
    logger.info(f"Registered {AGENT_NAME} with tau2")
