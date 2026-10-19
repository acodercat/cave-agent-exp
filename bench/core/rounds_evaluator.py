"""Running one rounds case: a chain of workers, and what the object was at each hop.

The fidelity study's machinery, at length (:mod:`core.fidelity_evaluator`): the
same four arms, the same object workers, the same budget, the same host-asked
question at the end. Between the producer and the consumer stand the revisers,
one per edit the chain makes, each handed the object, each handing it on.

What the host records at every hop, and why each is separate:

* ``carried`` — the object as the reviser bound it on arrival, against the
  object the worker before it had bound. This is the crossing and nothing else.
  It is ``None`` when the reviser bound nothing: not knowing is not a loss.
* ``edited`` — its output against its own rule applied to what it actually
  received. A reviser handed a stale object can still do its work correctly,
  and that is the signature of a stale path rather than a careless agent.
* ``applied`` — its output against the standard for that stage. The absolute
  reading, which an upstream mistake also fails.
* ``encoded`` — what it delivered against what it bound: the writing-out half
  alone, which is a format round trip in the file arm and the agent's own
  transcription in the text arms.
* where the object sits in the chain (:func:`core.rounds.align`), so an object
  that is an earlier version is told apart from one that is merely wrong.

A repeat is read from the run record, never from the object: a rule applied
twice may leave the object exactly as it was.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import json
from pathlib import Path
import re
import time
from typing import Any

from cave_agent import Variable
from cave_agent.agent import AgentResponse
from cave_agent.runtime import IPythonRuntime

from core.agents import FencedCodeAgent, ToolCallAgent
from core.errors import InfrastructureError
from core.evaluator import idle_timeout, raise_if_infrastructure
from core.fidelity import (
    HANDED_OBJECT_DESCRIPTION, INPUT_SLOT, RECEIVED, compare, from_jsonable, read_object,
)
from core.fidelity_evaluator import (
    _OBJECT_CHANNEL, PRODUCER, Budget, ObjectWorker, _frozen, _plain, retrieve, spent_over,
)
from core.orchestration import Arm, Medium, OrchestrationResult, describe_worker, worker_specs
from core.orchestration_evaluator import BuiltWorker
from core.paradigms import Delivery, table_paths
from core.pipeline_evaluator import PipelineSettings
from core.prompts import (
    describe_handed_object, handed_agent_instructions, object_delivery,
    orchestrator_instructions, reviser_turn, system_instructions,
)
from core.rounds import (
    CARRIED, CARRIED_DESCRIPTION, HANDED_REVISED_DESCRIPTION, Alignment, Hop, Revision, RoundsCase,
    align, judged,
)
from core.runtime_catalog import select_runtime_tables
from core.security import SECURITY_CHECKER
from core.transcripts import messages_of


class RoundsWorker(ObjectWorker):
    """An object worker that may also be asked to keep what it was handed.

    ``observed`` are variables the host reads from the runtime but the worker
    does not hand on. They are deliberately not part of the contract: the
    contract decides what the orchestrator's runtime registers a slot for in
    the cave arm, and what the snapshot looks for in a file or a reply, and an
    observation is none of those things.
    """

    observed: tuple[Variable, ...] = ()
    revision: Revision | None = None
    shared_output: str | None = None        # the one file every stage writes, in that arm
    medium: Medium = Medium.CAVE
    takes_input: bool = False
    parity: bool = False                    # the arm's Arm.parity

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # One entry per call of ``run``, finished or not, so that a worker run
        # twice can be judged on its first run as well as its last (``invocations``
        # in the run record); ``bound``, ``handed`` and ``delivered`` alone hold
        # only what each run got as far as leaving, and need not line up.
        self.attempts: list[dict[str, Any]] = []
        self.notes: list[str | None] = []

    async def run(self, query):
        attempt: dict[str, Any] = {}
        self.attempts.append(attempt)
        sizes = len(self.handed), len(self.bound), len(self.delivered), len(self.notes)
        try:
            return await super().run(query)
        finally:
            def new(items: list, before: int) -> Any:
                return items[before] if len(items) > before else None
            attempt.update(
                stamp=self.started[-1] if self.started else None,
                handed=new(self.handed, sizes[0]), bound=new(self.bound, sizes[1]),
                delivered=new(self.delivered, sizes[2]), note=new(self.notes, sizes[3]),
            )
            attempt["completed"] = attempt["delivered"] is not None

    def output_path(self, name: str) -> Path:
        return super().output_path(self.shared_output or name)

    def _turn(self, query: str) -> str:
        if self.observed:
            turn = reviser_turn(query, self.observed[0], self.contract)
        else:
            turn = super()._turn(query)
        if not (self.parity and self.takes_input):
            return turn
        note = self._host_reading(query)
        self.notes.append(note)
        return f"{turn}\n\n{note}"

    def _host_reading(self, query: str) -> str:
        """The parity arms' note: what the host reads off the input this worker received.

        One function for every medium, and always what actually reached the
        worker, never the object the agent before it left: the object in the
        input slot, the file the instruction names, the JSON the instruction
        holds. In the text arms that is the payload as written, so the note
        cannot restore what the writing lost.
        """
        if self.medium is Medium.CAVE:
            value = self.handed[-1] if self.handed else None
            source = f"the object in your runtime as `{INPUT_SLOT}`"
            found = value is not None
        elif self.medium is Medium.FILE:
            path, value = _named_file(query, self.kind)
            source = f"the file {path} named in your instruction" if path else \
                "no readable file named in your instruction"
            found = path is not None
        else:
            found, value = _instruction_json(query)
            source = "the JSON in your instruction" if found else \
                "no JSON object the host could read in your instruction"
        if not found:
            return f"Host reading of what you were handed: {source}."
        reading = describe_handed_object("", value).strip()
        return f"Host reading of what you were handed — {source}: {reading}"

    async def _snapshot(self, response: AgentResponse) -> dict[str, Any]:
        outputs = await super()._snapshot(response)
        if self.observed:
            self.bound[-1].update({
                variable.name: _frozen(await retrieve(self.runtime, variable.name))
                for variable in self.observed
            })
        return outputs

    first_hop: bool = True                  # handed the producer's object, not a revised one

    async def _describe_handed_input(self) -> None:
        variable = self.runtime._variables.get(INPUT_SLOT)
        if variable is None:
            return
        value = await retrieve(self.runtime, INPUT_SLOT)
        # Taken before the run, and copied: this is the host's own view of what
        # crossed, and nothing the agent does afterwards can rewrite it.
        self.handed.append(_frozen(value))
        description = HANDED_OBJECT_DESCRIPTION if self.first_hop else HANDED_REVISED_DESCRIPTION
        # In the parity arms the reading goes in the turn, worded the same in
        # every arm (``_host_reading``), and the slot keeps only what it is.
        variable.description = description if self.parity else \
            describe_handed_object(description, value)


def _named_file(query: str, kind) -> tuple[Path | None, Any]:
    """The first file of the object's kind the instruction names that the host can read."""
    for match in re.finditer(rf"[^\s'\"`(),]+\.{re.escape(kind.extension)}\b", query):
        path = Path(match.group(0))
        if path.is_file():
            try:
                return path, read_object(kind, path)
            except Exception:                       # noqa: BLE001 - a half-written file, say
                continue
    return None, None


def _instruction_json(query: str) -> tuple[bool, Any]:
    """The JSON value an instruction carries: its last fenced block, else its longest one."""
    for block in reversed(re.findall(r"```(?:json)?\s*\n(.*?)```", query, re.DOTALL)):
        try:
            return True, json.loads(block)
        except ValueError:
            continue
    decoder, best = json.JSONDecoder(), None
    for start, char in enumerate(query):
        if char not in "{[":
            continue
        try:
            value, end = decoder.raw_decode(query, start)
        except ValueError:
            continue
        if best is None or end - start > best[0]:
            best = (end - start, value)
    return (True, best[1]) if best else (False, None)


class FencedCodeRoundsWorker(RoundsWorker, FencedCodeAgent):
    pass


class ToolCallRoundsWorker(RoundsWorker, ToolCallAgent):
    pass


@dataclass
class RoundsResult(OrchestrationResult):
    """One chain run under one arm, hop by hop.

    ``success`` is the consumer's object against the standard for the last
    stage — end to end, as the fidelity study's is. ``hops`` holds each
    worker's crossing and edit; ``chain`` is the version each worker's output
    turned out to be, which reads as a trace: ``[0, 1, 2, 3]`` is a chain that
    went as designed, ``[0, 1, 1, 3]`` a skipped edit, ``[0, 1, None, …]`` a
    crossing that lost the object.
    """

    depth: int = 0
    hops: list[dict[str, Any]] = field(default_factory=list)
    chain: list[int | None] = field(default_factory=list)
    planned_hops: int = 0
    tokens: int = 0
    elapsed_s: float = 0.0
    host_observations: int = 0
    budget_exceeded: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            **super().as_dict(), "depth": self.depth, "hops": self.hops, "chain": self.chain,
            "planned_hops": self.planned_hops, "tokens": self.tokens,
            "elapsed_s": round(self.elapsed_s, 1), "host_observations": self.host_observations,
            "budget_exceeded": self.budget_exceeded,
        }


def _build_workers(
    model, case: RoundsCase, arm: Arm, settings: PipelineSettings, workdir: Path, budget: Budget,
) -> list[BuiltWorker]:
    """The producer, one reviser per edit, and the consumer, under the arm's medium.

    Each worker keeps its own object bound under its output's name in every arm
    (``KEEP_BOUND``), so the host reads what it made before anything crosses;
    each reviser also binds what it was handed. In the file arm every worker
    writes into its own directory, so the chain leaves one file per stage and
    an instruction naming an earlier one is a stale path and not a race.
    """
    producer = PRODUCER[arm.medium]
    clock = itertools.count()
    tables = select_runtime_tables(case.data_sources)
    paths = table_paths(tables, None)
    kind = case.task.kind
    by_name = {f"reviser_{revision.index}": revision for revision in case.revisions}
    built = []
    for spec in worker_specs(case):
        revision = by_name.get(spec.name)
        is_consumer = spec.role == "consumer"
        delivers = Delivery.VARIABLES if is_consumer else producer.delivery
        if revision is not None:
            contract = [case.output_variable(revision)]
        elif is_consumer:
            contract = case.consumer_variables
        else:
            contract = [case.task.variable]
        observed = (Variable(CARRIED, None, CARRIED_DESCRIPTION),) if revision is not None else ()
        registered = [*contract, *observed]
        if spec.takes_input and arm.reaches_runtime:
            registered.append(Variable(INPUT_SLOT, None, HANDED_OBJECT_DESCRIPTION))
        output_dir = None
        if delivers is Delivery.FILES:
            output_dir = workdir / ("shared" if arm.shared_path else spec.name)
            output_dir.mkdir(parents=True, exist_ok=True)
        worker_type = ToolCallRoundsWorker if arm.medium is Medium.JSON else FencedCodeRoundsWorker
        name = case.task.output if arm.shared_path else contract[0].name
        path = output_dir / f"{name}.{kind.extension}" if output_dir else None
        delivery = object_delivery(delivers, path=path, writer=f"`{kind.writer}`")
        if revision is None and not is_consumer:
            instructions = system_instructions(
                "eager", paradigm=producer, tables=tables, paths=paths, output_dir=output_dir,
                delivery=delivery,
            )
        else:
            instructions = handed_agent_instructions(
                _OBJECT_CHANNEL[arm.medium], delivers=delivers, table=INPUT_SLOT,
                action=producer.action, loader=kind.loader, extension=kind.extension,
                delivery=None if is_consumer else delivery,
            )
        runtime = IPythonRuntime(
            functions=[], variables=registered, types=[], security_checker=SECURITY_CHECKER,
        )
        agent = worker_type(
            model=model, runtime=runtime, system_instructions=instructions,
            max_steps=settings.step_budget, max_exec_output=settings.max_exec_output,
            stream_idle_timeout=idle_timeout(model),
        )
        agent.contract, agent.delivers, agent.clock = contract, delivers, clock
        agent.output_dir, agent.kind, agent.budget = output_dir, kind, budget
        agent.observed, agent.revision = observed, revision
        agent.shared_output = case.task.output if arm.shared_path else None
        agent.medium, agent.takes_input, agent.parity = arm.medium, spec.takes_input, arm.parity
        agent.first_hop = revision.index == 1 if revision is not None else not case.revisions
        if is_consumer:
            agent.question = case.follow_up.query
        budget.agents.append(agent)
        built.append(BuiltWorker(spec, agent, (spec.role,)))
    return built


def _applied(revision: Revision, value: Any) -> Any:
    """The rule on what an agent bound, or nothing where the rule cannot take it."""
    try:
        return revision.applied_to(value)
    except Exception:                               # noqa: BLE001 - a list where a table was due, say
        return None


def orchestrator_task(case: RoundsCase) -> str:
    """The chain, in order, with no worker named.

    The second sentence is what makes a stale path the orchestrator's mistake
    rather than the task's silence: it says, once and for every arm, that each
    part works on what the part before it produced.
    """
    steps = [f"First, build this object: {case.task.ask}"]
    steps += [
        f"Next, to the object as the part before this one left it: {revision.ask}"
        for revision in case.revisions
    ]
    steps.append(
        "Finally, hand the object as it stands after the last of those changes, whole, to the "
        "consumer and run it: the consumer will be asked a question about the object, and its "
        "answer is what counts."
    )
    return (
        "The task has these parts, in this order. Each part works on the object the part before "
        "it produced, not on the object as it was first built, and not on a copy made earlier."
        "\n\n" + "\n\n".join(steps)
    )


@dataclass
class _Judge:
    """The host's standards and what the agents actually produced, as the chain grows."""

    case: RoundsCase
    arm: Arm
    standards: list[Any]
    produced: list[Any] = field(default_factory=list)
    observations: int = 0

    def _as_delivered(self, delivered: Any, like: Any) -> Any:
        """What a careful reader rebuilds from what crossed, with nothing but the payload.

        In the text arms what a worker hands on is a JSON payload; comparing it
        with the object as an object would only ever say that a reply is not a
        DataFrame. It is rebuilt the way the study's JSON floor rebuilds it, so
        ``encoded`` reads the same question in every arm: did the values and the
        shape survive being written out.
        """
        if delivered is None or self.arm.medium not in (Medium.TEXT, Medium.JSON):
            return delivered
        try:
            return from_jsonable(delivered, like)
        except Exception:                           # noqa: BLE001 - the payload is the agent's
            # A payload that cannot be read back as the object it should be is
            # itself the finding; the comparator says so from the raw payload,
            # and the host does not fall over on it.
            return delivered

    @property
    def row_key(self) -> str | None:
        return self.case.task.row_key

    def _compare(self, value: Any, against: Any):
        self.observations += 1
        return None if against is None else compare(value, against, row_key=self.row_key)

    def hop(self, worker: BuiltWorker, index: int) -> Hop:
        """One worker's crossing and edit; ``index`` is its place in the chain, 0 for the producer."""
        agent = worker.agent
        hop = self._judged(
            worker, index,
            bound=agent.bound[-1] if agent.bound else {},
            delivered=agent.delivered[-1] if agent.delivered else {},
            seen=agent.handed[-1] if getattr(agent, "handed", None) else None,
            previous=self.produced[index - 1] if index else None,
        )
        self.produced.append(_output_of(worker, agent.bound[-1] if agent.bound else {}))
        return hop

    def invocations(self, workers: list[BuiltWorker]) -> list[list[dict[str, Any]]]:
        """Every run of every worker, each judged on its own, after the chain is judged.

        ``hop`` judges a worker's last run against the last output of the worker
        before it, which is what the chain ended with. Here each run is judged
        against the output the worker before it had last left when that run
        began, so a worker run twice is read on its first run too: the first-run
        reading is what crossed before anyone tried again. The host's count of
        observations is the chain's, and is left as it was.
        """
        counted = self.observations
        out = []
        for index, worker in enumerate(workers):
            before = workers[index - 1].agent.attempts if index else []
            rows = []
            for attempt in worker.agent.attempts:
                record = {"stamp": attempt["stamp"], "completed": attempt["completed"]}
                if attempt["note"] is not None:
                    record["note"] = attempt["note"]
                if attempt["completed"]:
                    left = [a for a in before if a["completed"] and a["stamp"] < attempt["stamp"]]
                    previous = _output_of(workers[index - 1], left[-1]["bound"]) if left else None
                    record.update(self._judged(
                        worker, index, bound=attempt["bound"] or {},
                        delivered=attempt["delivered"] or {}, seen=attempt["handed"],
                        previous=previous,
                    ).as_dict())
                rows.append(record)
            out.append(rows)
        self.observations = counted
        return out

    def _judged(
        self, worker: BuiltWorker, index: int, *, bound: dict[str, Any],
        delivered: dict[str, Any], seen: Any, previous: Any,
    ) -> Hop:
        """One run's crossing and edit, from what it bound and delivered and what came before it."""
        agent = worker.agent
        name = worker.spec.name
        revision = getattr(agent, "revision", None)
        output_name = RECEIVED if worker.spec.role == "consumer" else agent.contract[0].name
        output = bound.get(output_name)
        hop = Hop(name=name)
        if revision is not None or worker.spec.role == "consumer":
            # The host's own view of the input where it has one (the object was
            # in the worker's runtime before it ran), else what the agent bound.
            handed = seen if seen is not None else (
                bound.get(CARRIED) if revision is not None else output
            )
            hop.input_seen = None if handed is None else ("host" if seen is not None else "agent")
            if handed is not None:
                hop.carried, _ = judged(self._compare(handed, previous))
                hop.arrived = align(
                    handed, self.standards, self.produced, row_key=self.row_key,
                    older_than=index - 1,
                )
                if revision is not None:
                    # Where what arrived is not the kind of object the rule
                    # edits, the edit cannot be judged; the loss is upstream's
                    # and ``applied`` carries it.
                    edited_handed = _applied(revision, handed)
                    hop.edited = None if edited_handed is None else \
                        judged(self._compare(output, edited_handed))[0]
                    # Its "handed in" is its own output, and that output is the
                    # right edit of what came before: it edited first and bound
                    # after, so the crossing was not observed. (An object handed
                    # on unchanged also equals its input, but is not the edit.)
                    from_previous = _applied(revision, previous)
                    if hop.input_seen == "agent" and output is not None and from_previous is not None \
                            and self._compare(handed, output).intact \
                            and self._compare(output, from_previous).intact:
                        hop.observed_late, hop.carried, hop.edited = True, None, None
        stage = min(index, len(self.standards) - 1)
        hop.applied, hop.lost = judged(self._compare(output, self.standards[stage]))
        hop.held = Alignment(as_of=stage) if hop.applied else align(
            output, self.standards, self.produced, revision=revision, row_key=self.row_key,
            older_than=index - 1,
        )
        if worker.spec.role != "consumer":
            hop.encoded, _ = judged(
                self._compare(self._as_delivered(delivered.get(output_name), output), output),
            )
        return hop


def _output_of(worker: BuiltWorker, bound: dict[str, Any]) -> Any:
    """What a worker made, as one of its runs left it bound."""
    name = RECEIVED if worker.spec.role == "consumer" else worker.agent.contract[0].name
    return bound.get(name)


async def run_rounds(
    model, case: RoundsCase, arm: Arm, settings: PipelineSettings, workdir: Path,
) -> RoundsResult:
    """Build the chain, hand it to the orchestrator, run it once, judge every hop."""
    tables = {table.name: table.loader() for table in select_runtime_tables(case.data_sources)}
    standards = case.standards(tables)
    budget = Budget()
    workers = _build_workers(model, case, arm, settings, workdir, budget)
    orchestrator_runtime = IPythonRuntime(
        functions=[],
        variables=[
            Variable(worker.spec.name, worker.agent, _describe(worker, arm))
            for worker in workers
        ] + _output_slots(workers, arm),
        types=[],
        security_checker=SECURITY_CHECKER,
    )
    orchestrator = FencedCodeAgent(
        model=model, runtime=orchestrator_runtime,
        system_instructions=orchestrator_instructions(answerer="consumer", may_inspect=arm.parity),
        max_steps=settings.orchestrator_steps, max_exec_output=settings.max_exec_output,
        stream_idle_timeout=idle_timeout(model),
    )
    budget.agents.append(orchestrator)
    started = time.monotonic()
    response = await orchestrator.run(orchestrator_task(case))
    elapsed = time.monotonic() - started
    raise_if_infrastructure(response, orchestrator)
    for worker in workers:
        if worker.agent.outage is not None:
            raise InfrastructureError(f"{worker.spec.name}: {worker.agent.outage}")

    result = RoundsResult(
        case=case.name, arm=arm.name, depth=case.depth, planned_hops=case.depth,
        orchestrator={
            **spent_over(orchestrator, [response]), "response": response.content,
            "code_snippets": response.code_snippets,
            "messages": messages_of(orchestrator) or [],
        },
        tokens=budget.spent, elapsed_s=elapsed, budget_exceeded=budget.exceeded,
    )
    runs = sorted((stamp, worker.spec.name) for worker in workers for stamp in worker.agent.started)
    result.ran = [name for _, name in runs]
    result.ran_as_designed = result.ran == [worker.spec.name for worker in workers]
    result.repeated = [worker.spec.name for worker in workers if worker.agent.runs > 1]
    result.skipped = [worker.spec.name for worker in workers if worker.agent.runs == 0]

    judge = _Judge(case, arm, standards)
    order = sorted((stamp, worker.spec.name) for worker in workers for stamp in worker.agent.started)
    hops = [judge.hop(worker, index) for index, worker in enumerate(workers)]
    invocations = judge.invocations(workers)
    for index, worker in enumerate(workers):
        hop = hops[index]
        if worker.agent.started:
            last = max(worker.agent.started)
            before = [name for stamp, name in order if stamp < last]
            hop.after = before[-1] if before else None
        record = {
            "name": worker.spec.name, "role": worker.spec.role, "runs": worker.agent.runs,
            **spent_over(worker.agent, worker.agent.responses), **hop.as_dict(),
            "invocations": invocations[index], "messages": worker.agent.transcript,
        }
        if worker.spec.role == "consumer":
            bound = worker.agent.delivered[-1] if worker.agent.delivered else {}
            answers = {name: value for name, value in bound.items() if name != RECEIVED}
            answered = case.follow_up.check(_plain(answers), standards[-1])
            record.update({
                "received_bound": bound.get(RECEIVED) is not None,
                "answered": bool(answered.success), "answer_message": answered.message,
                "outputs": _plain(answers),
            })
        record["success"] = hop.applied
        result.workers.append(record)
        result.hops.append(hop.as_dict())
    result.chain = [hop["as_of"] for hop in result.hops]
    result.host_observations = judge.observations
    result.success = bool(result.workers[-1]["success"]) and not result.budget_exceeded
    if not result.success:
        result.failure = "budget" if result.budget_exceeded else next(
            (record["name"] for record in result.workers if record["success"] is False), None,
        )
    return result


def _describe(worker: BuiltWorker, arm: Arm) -> str:
    writes = worker.agent.delivers is Delivery.FILES
    path = worker.agent.output_path(worker.agent.contract[0].name) if writes else None
    return describe_worker(worker.spec, arm, path, input_slot=INPUT_SLOT, noun="object")


def _output_slots(workers: list[BuiltWorker], arm: Arm) -> list[Variable]:
    """One slot per worker output in the arm that retrieves objects; observations get none."""
    if not arm.reaches_runtime:
        return []
    # The output's own description reaches the worker in its turn in every arm;
    # the parity arm does not also give it to this orchestrator alone.
    return [
        Variable(
            output.name, None,
            f"What the {worker.spec.role} agent produces."
            + ("" if arm.parity else f" {output.description}"),
        )
        for worker in workers for output in worker.agent.contract
    ]
