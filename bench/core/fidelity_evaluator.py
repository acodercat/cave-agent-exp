"""Running one fidelity case: producer, consumer, and what arrived.

The orchestrated study's machinery, unchanged (:mod:`core.orchestration_evaluator`):
the host builds the workers, registers them in the orchestrator's runtime with
a description saying how to use them, runs the orchestrator once and steps
back. Two things differ.

*What the producer makes need not be a table.* Its output is judged, where the
host can take it as an object (the cave and file arms), by the fidelity
comparator rather than the table validator; in the text arms it is a JSON block
in a reply, which is not an object, and the producer is not judged — what it
lost shows up in what the consumer received, and the record says so.

*The consumer's first output is the object it holds.* Its contract begins with
``received``, and the host reads that from the consumer's runtime in every arm
— never from a reply. It is compared twice: with the object the producer had
bound in its own runtime before anything crossed (``carried``: what the
crossing kept), and with the true object (``final``). The producer's bound
object is itself compared with the truth (``built``), so a producer that built
the wrong thing is told apart from a crossing that lost it. Beside these the
host stores the two format floors, the same comparator on the true object after
a JSON and a file round trip with no model in between.

*The question is the host's.* The orchestrator is told to build the object and
hand it to the consumer, not what the consumer will be asked; the host puts the
question in the consumer's turn. Told the question, an orchestrator answered
it upstream, or handed on only the rows it would take.

Every case runs under a token budget across all its agents: a worker asked to
run once the budget is spent raises instead, the orchestrator sees the error
as any other, and the run is recorded as failed. The agents are not told the
budget, so an enforced cap and one applied afterwards decide the same runs;
enforcing it only stops paying for a run already lost.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import itertools
from pathlib import Path
from typing import Any

from cave_agent import Variable
from cave_agent.agent import AgentResponse
from cave_agent.runtime import IPythonRuntime

from core.agents import FencedCodeAgent, ToolCallAgent
from core.errors import InfrastructureError
from core.evaluator import idle_timeout, raise_if_infrastructure
from core.fidelity import (
    HANDED_OBJECT_DESCRIPTION, INPUT_SLOT, RECEIVED, FidelityCase, FidelityReport, compare,
    format_floors, read_object,
)
from core.orchestration import Arm, Medium, OrchestrationResult, describe_worker, worker_specs
from core.orchestration_evaluator import PRODUCER, BuiltWorker, Worker, retrieve, spent_over
from core.paradigms import Delivery, reply_outputs, table_paths
from core.pipeline_evaluator import PipelineSettings
from core.prompts import (
    consumer_turn, describe_handed_object, handed_agent_instructions, object_delivery,
    orchestrator_instructions, system_instructions,
)
from core.runtime_catalog import select_runtime_tables
from core.security import SECURITY_CHECKER
from core.transcripts import messages_of


# Tokens one case may spend over all its agents, on the suite's own estimate
# (core.agents counts it for every call, whoever the provider is).
TOKEN_BUDGET = 500_000


class BudgetExceeded(Exception):
    """Raised to the orchestrator by a worker it runs after the case's budget is spent."""


class Budget:
    """One case's token budget, shared by every agent in it."""

    def __init__(self, limit: int | None = None):
        self.limit = TOKEN_BUDGET if limit is None else limit
        self.agents: list[Any] = []

    @property
    def spent(self) -> int:
        return sum(
            agent.spent["estimated_prompt_tokens"] + agent.spent["estimated_completion_tokens"]
            for agent in self.agents
        )

    @property
    def exceeded(self) -> bool:
        return self.spent > self.limit


class ObjectWorker(Worker):
    """A worker whose output, or input, is an object of any kind.

    As :class:`Worker`, except that what it delivers is read as the object
    itself rather than as rows, a handed object is described by what it is,
    the file it writes carries its kind's extension, and a run past the
    case's budget raises.
    """

    kind = None                 # ObjectKind of what this case's producer builds
    budget: Budget = Budget()
    question: str | None = None # the host's question, put to the consumer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # What each run left bound in the runtime under its contract's names,
        # whatever the arm's delivery rule: the object before it crosses.
        self.bound: list[dict[str, Any]] = []
        # What the host itself saw in the input slot before each run, where
        # there is one: the arms that hand an object through the runtime.
        # Filled by the host, never by the agent, and per worker — a list on the
        # class would be one list for every worker in the study.
        self.handed: list[Any] = []

    def _turn(self, query: str) -> str:
        if self.question is None:
            return super()._turn(query)
        return consumer_turn(query, self.question, self.contract)

    async def run(self, query):
        if self.budget.exceeded:
            self.started.append(next(self.clock))
            raise BudgetExceeded(
                f"the case's token budget of {self.budget.limit} is spent; no worker runs again"
            )
        return await super().run(query)

    def output_path(self, name: str) -> Path:
        return self.output_dir / f"{name}.{self.kind.extension}"

    async def _snapshot(self, response: AgentResponse) -> dict[str, Any]:
        """What the run delivered, copied: in the cave arm the object goes on by reference."""
        outputs = {}
        for variable in self.contract:
            if self.delivers is Delivery.VARIABLES:
                value = await retrieve(self.runtime, variable.name)
            elif self.delivers is Delivery.FILES and self.output_path(variable.name).is_file():
                value = read_object(self.kind, self.output_path(variable.name))
            else:
                value = _reply_object(response.content, variable.name)
            outputs[variable.name] = _frozen(value)
        self.bound.append({
            variable.name: _frozen(await retrieve(self.runtime, variable.name))
            for variable in self.contract
        })
        return outputs

    async def _describe_handed_input(self) -> None:
        variable = self.runtime._variables.get(INPUT_SLOT)
        if variable is None:
            return
        value = await retrieve(self.runtime, INPUT_SLOT)
        self.handed.append(_frozen(value))
        variable.description = describe_handed_object(HANDED_OBJECT_DESCRIPTION, value)


class FencedCodeObjectWorker(ObjectWorker, FencedCodeAgent):
    pass


class ToolCallObjectWorker(ObjectWorker, ToolCallAgent):
    pass


def _frozen(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except Exception:                               # noqa: BLE001 - a live handle, say
        return value


def _reply_object(reply: str, name: str) -> Any:
    """What a reply's final ```json block delivered under ``name``, or its one non-scalar value."""
    delivered = reply_outputs(reply)
    if name in delivered:
        return delivered[name]
    objects = [value for value in delivered.values() if isinstance(value, (list, dict))]
    return objects[0] if len(objects) == 1 else None


@dataclass
class FidelityResult(OrchestrationResult):
    """An orchestrated run whose verdict is whether the object arrived intact.

    ``success`` is the consumer's ``received`` against the true object: every
    property the comparator checks. The light question's verdict is in the
    consumer's record as ``answered``; the format floors are stored with the
    run so a table can be made from the runs alone.
    """

    floors: dict[str, Any] = field(default_factory=dict)
    tokens: int = 0
    budget_exceeded: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            **super().as_dict(), "floors": self.floors, "tokens": self.tokens,
            "budget_exceeded": self.budget_exceeded,
        }


def _build_workers(
    model, case: FidelityCase, arm: Arm, settings: PipelineSettings, workdir: Path,
    budget: Budget,
) -> list[BuiltWorker]:
    """The producer and the consumer under the arm's medium.

    As the orchestrated study builds its workers, with the producer's delivery
    rule the object one and the consumer's input slot ``INPUT_SLOT``. Every
    worker's outputs are registered in its runtime in every arm: the consumer
    delivers as variables, and the producer keeps its object bound beside
    delivering it, so both are read the same way everywhere.
    """
    producer = PRODUCER[arm.medium]
    clock = itertools.count()
    tables = select_runtime_tables(case.data_sources)
    paths = table_paths(tables, None)
    kind = case.task.kind
    built = []
    for spec in worker_specs(case):
        is_producer = not spec.takes_input
        delivers = producer.delivery if is_producer else Delivery.VARIABLES
        contract = [case.task.variable] if is_producer else case.consumer_variables
        # Registered in every arm: the producer keeps its object bound under
        # the output's name whatever its delivery rule, and the host reads it
        # there before it crosses; the consumer always delivers as variables.
        registered = list(contract)
        if not is_producer and arm.reaches_runtime:
            registered.append(Variable(INPUT_SLOT, None, HANDED_OBJECT_DESCRIPTION))
        output_dir = None
        if delivers is Delivery.FILES:
            output_dir = workdir / spec.name
            output_dir.mkdir(parents=True, exist_ok=True)
        worker_type = ToolCallObjectWorker if arm.medium is Medium.JSON else FencedCodeObjectWorker
        if is_producer:
            path = output_dir / f"{spec.table}.{kind.extension}" if output_dir else None
            instructions = system_instructions(
                "eager", paradigm=producer, tables=tables, paths=paths, output_dir=output_dir,
                delivery=object_delivery(delivers, path=path, writer=f"`{kind.writer}`"),
            )
        else:
            instructions = handed_agent_instructions(
                _OBJECT_CHANNEL[arm.medium], delivers=delivers, table=INPUT_SLOT, action=producer.action,
                loader=kind.loader, extension=kind.extension,
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
        if not is_producer:
            agent.question = case.follow_up.query
        budget.agents.append(agent)
        built.append(BuiltWorker(spec, agent, ("producer" if is_producer else "consumer",)))
    return built


# The consumer's channel by medium: the object channels of core.prompts. In the
# cave arm the object is in its runtime, as a table would be.
_OBJECT_CHANNEL = {
    Medium.CAVE: "object_any", Medium.TEXT: "instruction_object", Medium.JSON: "instruction_object",
    Medium.FILE: "instruction_file_object",
}


def _judge(
    worker: BuiltWorker, case: FidelityCase, truth: Any, probes, produced: Any,
) -> dict[str, Any]:
    """The worker's last run in the comparator's terms.

    The producer: ``built``, its bound object against the truth. The consumer:
    ``carried``, its ``received`` against what the producer had bound (the
    crossing alone), ``final``, the same against the truth, and ``answered``.
    ``success`` is ``built`` for the one and ``final`` for the other; where the
    producer bound nothing, ``carried`` cannot be judged and is ``None``.
    """
    (role,) = worker.judge
    against = dict(probes=probes, row_key=case.task.row_key)
    delivered = worker.agent.delivered[-1] if worker.agent.delivered else {}
    if role == "producer":
        report = compare(produced, truth, **against)
        return {
            "success": report.intact, "message": _message(report), "fidelity": report.as_dict(),
            "bound": produced is not None,
        }
    received = delivered.get(RECEIVED)
    final = compare(received, truth, **against)
    carried = compare(received, produced, **against) if produced is not None else None
    answers = {name: value for name, value in delivered.items() if name != RECEIVED}
    answered = case.follow_up.check(_plain(answers), truth)
    return {
        "success": final.intact, "message": _message(final), "fidelity": final.as_dict(),
        "carried": None if carried is None else carried.intact,
        "carried_report": None if carried is None else carried.as_dict(),
        # Not the same failure as a lost property: the object may have arrived
        # whole and been bound under another name, or not bound at all.
        "received_bound": received is not None,
        "answered": bool(answered.success), "answer_message": answered.message,
        "outputs": _plain(answers),
    }


def _plain(outputs: dict[str, Any]) -> dict[str, Any]:
    """The answers as JSON-storable values; a number stays a number."""
    return {
        name: value.item() if hasattr(value, "item") else value
        for name, value in outputs.items()
    }


def _message(report: FidelityReport) -> str:
    return "intact" if report.intact else "lost: " + ", ".join(report.lost)


def orchestrator_task(case: FidelityCase) -> str:
    """What the orchestrator is asked: the object, and that the consumer is to be given it.

    The question the consumer will answer is not here; the host asks it.
    """
    return (
        "The task has two parts, in this order.\n\n"
        f"First, build this object: {case.task.ask}\n\n"
        "Then hand that object, whole, to the consumer and run it: the consumer will be "
        "asked a question about the object, and its answer is what counts."
    )


async def run_fidelity(
    model, case: FidelityCase, arm: Arm, settings: PipelineSettings, workdir: Path,
) -> FidelityResult:
    """Build the workers, hand them to the orchestrator, run it once, compare."""
    tables = {table.name: table.loader() for table in select_runtime_tables(case.data_sources)}
    truth, probes = case.truth(tables), case.probes(tables)
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
        system_instructions=orchestrator_instructions(answerer="consumer"),
        max_steps=settings.step_budget, max_exec_output=settings.max_exec_output,
        stream_idle_timeout=idle_timeout(model),
    )
    budget.agents.append(orchestrator)
    response = await orchestrator.run(orchestrator_task(case))
    raise_if_infrastructure(response, orchestrator)
    for worker in workers:
        if worker.agent.outage is not None:
            raise InfrastructureError(f"{worker.spec.name}: {worker.agent.outage}")

    result = FidelityResult(
        case=case.name, arm=arm.name,
        orchestrator={
            **spent_over(orchestrator, [response]), "response": response.content,
            "code_snippets": response.code_snippets,
            "messages": messages_of(orchestrator) or [],
        },
        floors={name: report.as_dict() for name, report in
                format_floors(case.task.kind, truth, probes=probes, row_key=case.task.row_key).items()},
        tokens=budget.spent, budget_exceeded=budget.exceeded,
    )
    runs = sorted((stamp, worker.spec.name) for worker in workers for stamp in worker.agent.started)
    result.ran = [name for _, name in runs]
    result.ran_as_designed = result.ran == [worker.spec.name for worker in workers]
    result.repeated = [worker.spec.name for worker in workers if worker.agent.runs > 1]
    result.skipped = [worker.spec.name for worker in workers if worker.agent.runs == 0]
    producer = workers[0].agent
    produced = producer.bound[-1].get(case.task.output) if producer.bound else None
    for worker in workers:
        result.workers.append({
            "name": worker.spec.name, "runs": worker.agent.runs,
            **spent_over(worker.agent, worker.agent.responses),
            **_judge(worker, case, truth, probes, produced),
            "messages": worker.agent.transcript,
        })
    result.success = bool(result.workers[-1]["success"]) and not result.budget_exceeded
    if not result.success:
        result.failure = "budget" if result.budget_exceeded else next(
            (record["name"] for record in result.workers if record["success"] is False), None,
        )
    return result


def _describe(worker: BuiltWorker, arm: Arm) -> str:
    writes = worker.agent.delivers is Delivery.FILES
    path = worker.agent.output_path(worker.spec.table) if writes else None
    return describe_worker(worker.spec, arm, path, input_slot=INPUT_SLOT, noun="object")


def _output_slots(workers: list[BuiltWorker], arm: Arm) -> list[Variable]:
    """As the orchestrated study's: one slot per worker output, in the arm that retrieves."""
    if not arm.reaches_runtime:
        return []
    return [
        Variable(output.name, None, f"What the {worker.spec.role} agent produces. {output.description}")
        for worker in workers for output in worker.contract
    ]
