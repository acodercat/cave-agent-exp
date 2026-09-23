"""The hosted study: the host runs the pipeline's stages and moves each table itself.

Every stage is an ordinary turn, run by :func:`core.evaluator.evaluate_turn`, so
each gets the same protocol repair, loop-event bookkeeping and usage accounting
as a delivery-study run. What this module adds is the seam: after each stage it
takes what that agent left behind, records that something really crossed, and
starts the next one from it.

The first agent reads the source tables. No later agent can: its runtime holds
only the table it was handed and the outputs it must assign, and its prompt says
so, which is what stops an arm quietly recovering by recomputing the answer.

A pipeline of k agents crosses the channel k-1 times, and every crossing is the
same channel, so the run records each stage's own verdict as well as the
end-to-end one. What depth costs is the difference between them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Sequence

import pandas as pd
from cave_agent import Variable
from cave_agent.runtime import IPythonRuntime

from core.agents import FencedCodeAgent, SignallingFencedCodeAgent
from core.evaluator import RunSettings, TurnResult, evaluate_turn, idle_timeout
from core.pipeline import Carry, Channel, PipelineCase, Middle
from core.paradigms import Action, DataAccess, Delivery, Paradigm, table_paths
from core.prompts import (
    HANDED_REPLY, HANDED_TABLE, QUOTED_REPLY, describe_handed_frame,
    handed_agent_instructions, system_instructions,
)
from core.runtime_catalog import select_runtime_tables
from core.security import SECURITY_CHECKER
from core.transcripts import messages_of
from core.types import Turn
from core.validation import turn_validator


HANDED_TABLE_DESCRIPTION = (
    "The table the previous agent was asked to compute, exactly as it computed it."
)
HANDED_REPLY_DESCRIPTION = (
    "The previous agent's whole reply, as a string: the same text quoted in the question."
)

# How a handed agent's turn is run. A turn consults its paradigm's action, to
# word a repair nudge, and its delivery, to collect the outputs. The action is
# the same everywhere; the delivery is the channel's for a middle agent, which
# hands a table on, and variables for the last, which assigns its answers.
# Nothing reads the data-access axis, which here is the channel and has no
# member on that enum.
def _handed_paradigm(delivery: Delivery) -> Paradigm:
    return Paradigm(
        f"handed_{delivery.value}", DataAccess.REGISTERED, Action.FENCED_CODE, delivery,
    )


@dataclass(frozen=True)
class PipelineSettings:
    """How every stage of a pipeline runs. One study holds these fixed.

    Each stage gets the same step budget, in every arm and at every depth. A
    channel that makes an agent retype the table spends more of that budget doing
    so, and what it spends is part of what the study measures; a budget that
    differed between arms would make it something else.
    """

    step_budget: int = 14
    max_protocol_nudges: int = 1
    max_exec_output: int = 100000
    # The orchestrator's own budget, where a study has one: a chain of nine
    # workers needs more cells than a worker's turn, and the workers' budget is
    # what the fidelity study's workers had. ``None`` is the same as the workers'.
    orchestrator_step_budget: int | None = None

    @property
    def orchestrator_steps(self) -> int:
        return self.orchestrator_step_budget or self.step_budget

    def stage(self, paradigm: Paradigm) -> RunSettings:
        return RunSettings(
            max_protocol_nudges=self.max_protocol_nudges,
            total_step_budget=self.step_budget,
            injection="eager",
            paradigm=paradigm,
            max_exec_output=self.max_exec_output,
        )


@dataclass(frozen=True)
class Crossing:
    """What crossed to the next agent, and the record that it did.

    A channel supplies exactly one of the three carriers: ``variables``, which
    the next agent's runtime starts with; ``path``, which its prompt names; or
    ``preamble``, which its question is prefixed with.

    ``evidence`` is stored whether the run succeeded or not, so a stage that
    failed can be told apart from a stage that never handed anything over. That
    reading is the one that was missed when a paradigm scored zero for want of a
    sandbox binary.
    """

    delivered: bool
    variables: tuple[Variable, ...] = ()
    path: Path | None = None
    preamble: str = ""
    # The runtime the next agent works in, when the channel hands it the one the
    # last agent used instead of a fresh one.
    runtime: Any = None
    # What the next agent calls the table: the name its producer gave it where a
    # variable crosses, the study's own where none does.
    table: str = HANDED_TABLE
    evidence: dict[str, Any] = field(default_factory=dict)


def as_it_ended(turn: TurnResult) -> tuple[bool, str, dict]:
    """A turn's verdict, reply and outputs as the turn ended.

    ``TurnResult`` keeps the strict first pass in its own fields and a protocol
    repair beside it. The delivery study's headline reads the repair where one
    was attempted (``scripts.compare_paradigms``), and so must this family, or
    its first hop could not be read against that study's single hop. It matters
    twice over at a seam: a reply that crosses as text must be the reply the
    agent ended on, not the one that ran no code and was nudged.
    """
    repair = turn.protocol_repair
    if repair and repair.get("attempted"):
        return bool(repair["success"]), repair["response"], repair["outputs"]
    return turn.success, turn.response, turn.outputs


@dataclass
class StageRecord:
    """One agent of the pipeline: what it did, and what left it.

    Two verdicts, because they answer different questions. ``success`` is
    against the reference — is what this stage produced the right table, or the
    right answers, for the case? ``faithful`` is against what the stage actually
    received — did it do its own job on its own input? A stage can be unfaithful
    yet right by luck, and it can be faithful yet wrong because it was handed a
    wrong table. Only the second reading says where a pipeline went wrong.
    """

    role: str
    turn: TurnResult
    success: bool
    # Whether the stage did its own operation correctly on the table it was
    # actually handed. None for the first agent, whose input is the source data.
    faithful: bool | None = None
    # What this stage handed on. None for the last agent, which hands on nothing.
    crossing: dict[str, Any] | None = None
    delivered_rows: int | None = None
    # The agent's conversation, for the transcript written beside the result. A
    # transcript is how both of this study's environment faults were found —
    # read the tool's reply, not the model's call — so no stage goes without one.
    messages: list = field(default_factory=list)
    # The table this stage produced, kept only when its verdict against the
    # reference was wrong: a right table is the reference, which is on disk
    # already, while a wrong one is the only record of what went wrong and
    # cannot be recomputed without paying for the run again.
    wrong_table: Any = None
    # Whether this stage's code named a source table. None for the first agent,
    # whose job that is. For the rest it is a validity check, and it matters most
    # in the shared channel: an agent working in the runtime the one before it
    # used can reach whatever that one left, the loaded source tables included,
    # and an answer recomputed from those did not cross the channel at all.
    read_source: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        """The stage as it is stored.

        A stage that handed a table on keeps everything but that table: at the
        larger sizes it is thousands of rows and it is the same table in every
        arm that delivered one, and whether it was right, how much of it arrived
        and whether it crossed are all recorded beside it. The last stage hands
        on nothing and answers in three scalars, so its outputs are kept — they
        are what a failure has to be read from.
        """
        turn = asdict(self.turn)
        if self.crossing is not None:
            turn.pop("outputs", None)
            if not self.success and self.wrong_table is not None:
                turn["wrong_table"] = self.wrong_table
        return {
            "role": self.role,
            "success": self.success,
            "faithful": self.faithful,
            "read_source": self.read_source,
            "delivered_rows": self.delivered_rows,
            "crossing": self.crossing,
            "turn": turn,
        }


@dataclass
class PipelineResult:
    """One case run on one channel, end to end."""

    case: str
    channel: str
    agents: int
    stages: list[StageRecord] = field(default_factory=list)
    # The first stage whose output was not right against the reference. This is
    # a position in the pipeline, not a cause: a wrong table can be repaired by
    # a later stage that drops the bad rows, and a right one can be spoilt by a
    # later stage that was handed it whole. `first_unfaithful` is the cause.
    first_contract_failure: str | None = None
    # The first stage that did its own job wrong on what it actually received.
    first_unfaithful: str | None = None

    @property
    def success(self) -> bool:
        """The end-to-end verdict: the last agent answered, and answered right."""
        return len(self.stages) == self.agents and self.stages[-1].success

    def as_dict(self) -> dict[str, Any]:
        return {
            "case": self.case,
            "channel": self.channel,
            "agents": self.agents,
            "success": self.success,
            "first_contract_failure": self.first_contract_failure,
            "first_unfaithful": self.first_unfaithful,
            "stage_success": [stage.success for stage in self.stages],
            "stage_faithful": [stage.faithful for stage in self.stages],
            "stages": [stage.as_dict() for stage in self.stages],
        }


def _stage_module(variables, check) -> SimpleNamespace:
    """A case module's interface, for a stage whose question is built not written.

    ``evaluate_turn`` reads a case module for its output variables and for the
    validator a turn names. A pipeline stage has both, but they come from the task
    and the follow-up rather than from a file in ``cases/``, so they are handed
    over in the shape the evaluator already reads.
    """
    return SimpleNamespace(
        variables=list(variables),
        validators={"validate": turn_validator(check)},
    )


def _agent(
    model, runtime, instructions: str, settings: PipelineSettings, channel: Channel,
    outputs: Sequence[str] = (),
) -> FencedCodeAgent:
    """The stage's agent: the signalling one where the channel asks for it.

    ``outputs`` are the names this stage must assign, so the signalling agent
    knows what to watch for; the plain agent ignores them.
    """
    cls = SignallingFencedCodeAgent if channel.signals else FencedCodeAgent
    agent = cls(
        model=model,
        runtime=runtime,
        system_instructions=instructions,
        max_steps=settings.step_budget,
        max_exec_output=settings.max_exec_output,
        stream_idle_timeout=idle_timeout(model),
    )
    if channel.signals:
        agent.outputs = tuple(outputs)
    return agent


def _read_source(turn: TurnResult, source_paths: Sequence[str]) -> bool:
    """Whether the code this stage ran named one of the source tables' files."""
    code = "\n".join(turn.code_snippets or ())
    return any(path in code for path in source_paths)


def row_count(table: Any) -> int | None:
    if isinstance(table, pd.DataFrame):
        return int(table.shape[0])
    return len(table) if isinstance(table, list) else None


def _next_runtime(crossing: Crossing, variables) -> IPythonRuntime:
    """The runtime the next agent works in.

    A channel that shares hands over the runtime itself, and the next agent's
    own outputs are registered into it: that is what sharing means, and it is
    why its prompt can describe what the agent before it left. Every other
    channel starts a fresh one, so nothing but the table crosses.
    """
    if crossing.runtime is not None:
        for variable in variables:
            if variable.value is None:
                crossing.runtime.inject_variable(variable)
        return crossing.runtime
    return IPythonRuntime(
        functions=[], variables=list(variables), types=[],
        security_checker=SECURITY_CHECKER,
    )


def _table_variable(task, name: str) -> Variable:
    """The output contract for a table this pipeline hands on, under a new name."""
    return Variable(name, None, task.variable.description)


async def _cross(
    channel: Channel, *, runtime, table_name: str, output_dir: Path | None, reply: str,
) -> Crossing:
    """Take what an agent left behind, and record that it was there.

    Which of the three it takes follows the channel's delivery axis rather than
    its name, because that axis is what the arms differ on.
    """
    if channel.producer.delivery is Delivery.VARIABLES:
        value = runtime.retrieve(table_name)
        table = await value if inspect.isawaitable(value) else value
        if table is None:
            return Crossing(False, evidence={"variable": table_name, "assigned": False})
        dtypes = table.dtypes.items() if isinstance(table, pd.DataFrame) else ()
        evidence = {
            "variable": table_name,
            "assigned": True,
            "type": type(table).__name__,
            "rows": row_count(table),
            "dtypes": {str(name): str(dtype) for name, dtype in dtypes},
        }
        if channel.carry is Carry.SHARE:
            # Nothing is moved: the next agent is handed the runtime itself, so
            # the record is that it is the same one and what it already holds.
            # The identity is the evidence: the same runtime object, so the
            # next agent's prompt is built from a namespace it did not receive.
            return Crossing(
                True, runtime=runtime, table=table_name,
                evidence=evidence | {"carried": "share", "runtime_id": id(runtime)},
            )
        # The object's identity travels with it. The next stage's runtime is
        # asked for the same name and the two ids are compared once it has run,
        # so the record shows an injection, not a copy — see `_confirm_inject`.
        described = channel.describes
        description = (
            describe_handed_frame(HANDED_TABLE_DESCRIPTION, table) if described
            else HANDED_TABLE_DESCRIPTION
        )
        return Crossing(
            True,
            variables=(Variable(table_name, table, description),),
            table=table_name,
            evidence=evidence | {"carried": channel.carry.value, "object_id": id(table),
                                 "described": described},
        )

    if channel.producer.delivery is Delivery.FILES:
        path = output_dir / f"{table_name}.parquet"
        if not path.is_file():
            return Crossing(False, evidence={"path": str(path), "written": False})
        content = path.read_bytes()
        return Crossing(
            True,
            path=path,
            evidence={
                "path": str(path),
                "written": True,
                "bytes": len(content),
                "sha256": sha256(content).hexdigest(),
            },
        )

    text = reply or ""
    # `quoted_in_prompt` is filled in once the next agent has run, from the
    # question it was actually asked — see `_confirm_crossing` — not assumed here.
    evidence = {
        "characters": len(text),
        "holds_json_block": "```json" in text,
        "carried": channel.carry.value,
    }
    # The bound arm quotes the very same text, and binds it too: the next
    # agent reads the same question and can also reach the reply from code.
    bound = (
        (Variable(HANDED_REPLY, text, HANDED_REPLY_DESCRIPTION),)
        if channel.carry is Carry.REPLY_BOUND else ()
    )
    return Crossing(
        bool(text.strip()),
        variables=bound,
        preamble=QUOTED_REPLY.format(reply=text),
        evidence=evidence,
    )


async def _run_first(
    model, case: PipelineCase, channel: Channel, settings: PipelineSettings,
    expected: list[dict], output_dir: Path | None,
) -> tuple[TurnResult, IPythonRuntime, FencedCodeAgent, list[str]]:
    """Ask the first agent for the table, judged by the delivery study's validator."""
    task = case.task
    tables = select_runtime_tables(case.data_sources)
    paths = table_paths(tables, None)
    runtime = IPythonRuntime(
        functions=[],
        variables=[task.variable] if channel.producer.delivery is Delivery.VARIABLES else [],
        types=[],
        security_checker=SECURITY_CHECKER,
    )
    agent = _agent(
        model, runtime,
        system_instructions(
            "eager", paradigm=channel.producer, tables=tables,
            paths=paths, output_dir=output_dir,
        ),
        settings, channel, outputs=[task.output],
    )
    turn = await evaluate_turn(
        agent, runtime,
        _stage_module(
            [task.variable],
            lambda outputs: task.check(outputs.get(task.output), expected),
        ),
        case.name,
        Turn(query=case.producer_query(), validator="validate", stores=[task.output]),
        0, [task.output], [table.name for table in tables],
        settings.stage(channel.producer), output_dir,
    )
    return turn, runtime, agent, [str(path) for path in paths.values()]


def _faithful_middle(case: PipelineCase, middle: Middle, received, produced) -> bool | None:
    """Did the middle agent apply its rule to the table it actually received?

    None when the question cannot be put: nothing was received, nothing was
    produced, or what was received is not a table the rule can be applied to.
    A text-channel upstream can hand on rows missing the key column, and the
    diagnostic must record that rather than abort the run over it.
    """
    if not isinstance(received, list) or produced is None:
        return None
    try:
        return case.task.check(produced, middle.select(case.task, received)).success
    except (KeyError, TypeError, ValueError):
        return None


def _faithful_last(case: PipelineCase, received, outputs: dict) -> bool | None:
    """Did the last agent answer correctly from the table it actually received?

    None when what it received is not a table the follow-up can be computed
    from; see `_faithful_middle`.
    """
    if not isinstance(received, list):
        return None
    try:
        return case.follow_up.check(outputs, received).success
    except (KeyError, TypeError, ValueError):
        return None


async def _run_middle(
    model, case: PipelineCase, channel: Channel, settings: PipelineSettings,
    middle: Middle, expected: list[dict], crossing: Crossing, index: int,
    output_dir: Path | None,
) -> tuple[TurnResult, IPythonRuntime, FencedCodeAgent]:
    """Ask a middle agent to hand the table on, judged as a delivered table."""
    delivery = channel.producer.delivery
    variable = _table_variable(case.task, middle.output)
    runtime = _next_runtime(
        crossing,
        ([variable] if delivery is Delivery.VARIABLES else []) + list(crossing.variables),
    )
    agent = _agent(
        model, runtime,
        handed_agent_instructions(
            channel.name, delivers=delivery, table=crossing.table,
            path=crossing.path, output_dir=output_dir,
        ),
        settings, channel, outputs=[middle.output],
    )
    turn = await evaluate_turn(
        agent, runtime,
        _stage_module(
            [variable],
            lambda outputs: case.task.check(outputs.get(middle.output), expected),
        ),
        case.name,
        Turn(
            query=crossing.preamble + middle.query(case.task),
            validator="validate",
            stores=[middle.output],
        ),
        index, [middle.output], [], settings.stage(_handed_paradigm(delivery)), output_dir,
    )
    return turn, runtime, agent


async def _run_last(
    model, case: PipelineCase, channel: Channel, settings: PipelineSettings,
    expected: list[dict], crossing: Crossing, index: int,
) -> tuple[TurnResult, IPythonRuntime, FencedCodeAgent]:
    """Ask the last agent the follow-up, from the handed table and nothing else."""
    follow_up = case.follow_up
    runtime = _next_runtime(crossing, follow_up.variables + list(crossing.variables))
    agent = _agent(
        model, runtime,
        handed_agent_instructions(
            channel.name, delivers=Delivery.VARIABLES, table=crossing.table,
            path=crossing.path,
        ),
        settings, channel, outputs=follow_up.stores,
    )
    turn = await evaluate_turn(
        agent, runtime,
        _stage_module(follow_up.variables, lambda outputs: follow_up.check(outputs, expected)),
        case.name,
        Turn(
            query=crossing.preamble + follow_up.query,
            validator="validate",
            stores=follow_up.stores,
        ),
        index, follow_up.stores, [], settings.stage(_handed_paradigm(Delivery.VARIABLES)), None,
    )
    return turn, runtime, agent


async def _confirm_crossing(
    crossing: Crossing, evidence: dict[str, Any], next_turn: TurnResult, next_runtime,
) -> None:
    """Fill in the parts of a crossing's record that only the next stage can show.

    A record that says "quoted" or "injected" because the host meant to is not
    evidence. What is: the next agent's question containing the reply, and the
    next agent's runtime holding the very object the producer made.
    """
    if crossing.preamble:
        evidence["quoted_in_prompt"] = crossing.preamble in next_turn.query
    if evidence.get("carried") == Carry.REPLY_BOUND.value and crossing.variables:
        value = next_runtime.retrieve(HANDED_REPLY)
        held = await value if inspect.isawaitable(value) else value
        evidence["same_reply_bound_in_next_runtime"] = held == crossing.variables[0].value
    if "object_id" in evidence and crossing.variables:
        value = next_runtime.retrieve(crossing.table)
        held = await value if inspect.isawaitable(value) else value
        evidence["same_object_in_next_runtime"] = id(held) == evidence["object_id"]


def _stage_dir(workdir: Path, channel: Channel, index: int) -> Path | None:
    """Where a stage writes its table, for the channel that hands one over as a file.

    A directory per stage, so a later stage cannot read an earlier stage's file
    by name and quietly skip the crossing it was given.
    """
    if channel.producer.delivery is not Delivery.FILES:
        return None
    path = workdir / f"stage{index}"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def run_hosted(
    model, case: PipelineCase, channel: Channel, settings: PipelineSettings, workdir: Path,
) -> PipelineResult:
    """Run every stage of one case on one channel, and judge the last."""
    tables = case.expected_tables(case.expected_rows())
    result = PipelineResult(case=case.name, channel=channel.name, agents=case.agents)

    output_dir = _stage_dir(workdir, channel, 0)
    turn, runtime, agent, source_paths = await _run_first(
        model, case, channel, settings, tables[0], output_dir,
    )
    handed = case.task.output
    received = None            # what the stage now recorded was itself handed
    previous_middle = None

    for index, middle in enumerate(case.middles + (None,), start=1):
        success, reply, outputs = as_it_ended(turn)
        produced = outputs.get(handed)
        crossing = await _cross(
            channel, runtime=runtime, table_name=handed, output_dir=output_dir, reply=reply,
        )
        result.stages.append(StageRecord(
            role=case.roles[index - 1], turn=turn, success=success,
            faithful=None if previous_middle is None
            else _faithful_middle(case, previous_middle, received, produced),
            crossing=crossing.evidence, delivered_rows=row_count(produced),
            messages=messages_of(agent) or [],
            wrong_table=None if success else produced,
            read_source=None if previous_middle is None else _read_source(turn, source_paths),
        ))
        received = produced
        previous_middle = middle
        if not crossing.delivered:
            result.first_contract_failure = f"{case.roles[index - 1]}_handed_nothing_on"
            result.first_unfaithful = result.first_contract_failure
            return result

        if middle is None:
            last, last_runtime, last_agent = await _run_last(
                model, case, channel, settings, tables[-1], crossing, index,
            )
            await _confirm_crossing(crossing, result.stages[-1].crossing, last, last_runtime)
            last_ok, _, last_outputs = as_it_ended(last)
            result.stages.append(StageRecord(
                role=case.roles[index], turn=last, success=last_ok,
                faithful=_faithful_last(case, received, last_outputs),
                messages=messages_of(last_agent) or [],
                read_source=_read_source(last, source_paths),
            ))
            break

        output_dir = _stage_dir(workdir, channel, index)
        turn, runtime, agent = await _run_middle(
            model, case, channel, settings, middle, tables[index], crossing, index, output_dir,
        )
        await _confirm_crossing(crossing, result.stages[-1].crossing, turn, runtime)
        handed = middle.output

    if not result.success:
        failed = next((stage for stage in result.stages if not stage.success), None)
        result.first_contract_failure = failed.role if failed else None
        # The cause is the first stage that did its own job wrong on what it was
        # actually given. A first agent's table being wrong is not enough: a
        # later stage may have dropped the bad rows, in which case the wrong
        # answer came from further down. The first agent is the cause only when
        # every later stage was faithful and the answer is still wrong — then
        # the wrong table is the only thing left to blame.
        culprit = next((stage for stage in result.stages[1:] if stage.faithful is False), None)
        if culprit is not None:
            result.first_unfaithful = culprit.role
        elif result.stages and not result.stages[0].success:
            result.first_unfaithful = result.stages[0].role
    return result
