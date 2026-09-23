"""Running one orchestrated case: one orchestrator, its worker agents, one verdict.

The host builds the workers — the pipeline's stages, under their own prompts
and runtimes — registers each agent object as a variable in the orchestrator's
runtime with a description saying how to use it, and runs the orchestrator once
with the task. From then on the host does nothing until the orchestrator stops:
which worker runs, on what, in what order, is decided in the code the
orchestrator writes.

Afterwards the host judges. Each worker's output is judged against the
reference, as the hosted study judges its stages, so the record says which
worker got it wrong; the verdict is the analyst's answers. How the orchestrator
directed its workers — which ran, in what order, how often — is read from each
worker's own record of being run, never from the orchestrator's account of
itself, and stands beside the verdict as diagnosis (:class:`OrchestrationResult`).
"""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import itertools
from pathlib import Path
from typing import Any, Iterator

from cave_agent import Variable
from cave_agent.agent import AgentResponse
from cave_agent.runtime import IPythonRuntime
import pandas as pd

from core.agents import FencedCodeAgent, ToolCallAgent
from core.errors import InfrastructureError
from core.evaluator import idle_timeout, raise_if_infrastructure
from core.orchestration import (
    INPUT_TABLE, Arm, Medium, OrchestrationResult, WorkerSpec, describe_worker, worker_specs,
)
from core.paradigms import (
    CODEBLOCK, CODEBLOCK_FILES, CODEBLOCK_VARIABLES, JSON_EXEC, Delivery, reply_outputs,
    table_paths,
)
from core.pipeline import PipelineCase
from core.pipeline_evaluator import HANDED_TABLE_DESCRIPTION, PipelineSettings, row_count
from core.prompts import (
    describe_handed_frame, handed_agent_instructions, orchestrator_instructions,
    system_instructions, turn_prompt,
)
from core.runtime_catalog import select_runtime_tables
from core.security import SECURITY_CHECKER
from core.transcripts import messages_of
from core.validation import as_records


# What each medium's workers are. The retriever reads the source tables under the
# paradigm, so it is the same agent as in the delivery study; a later worker is a
# handed agent, reading the table from where the medium puts it.
PRODUCER = {
    Medium.CAVE: CODEBLOCK_VARIABLES, Medium.TEXT: CODEBLOCK, Medium.JSON: JSON_EXEC,
    Medium.FILE: CODEBLOCK_FILES,
}
HANDED_CHANNEL = {
    Medium.CAVE: "object", Medium.TEXT: "instruction", Medium.JSON: "instruction",
    Medium.FILE: "instruction_file",
}


class Worker:
    """What the host adds to an agent that the orchestrator runs as a worker.

    The agent is the pipeline's stage, unchanged; the orchestrator calls its
    ``run`` and, in the cave arm, its ``runtime``, exactly as the library's
    multi-agent example does. Around ``run`` the host does four things.

    *Each run is a fresh conversation.* ``CaveAgent.run`` appends to the
    agent's history and never clears it, so a worker run twice would still hold
    its first instruction — and, where tables travel as text, its first table.
    A retry would then be cheaper in the text arms than in the cave arm, where
    the object is in the runtime either way. The history is cleared before
    every run, as the orchestrator's prompt says; the runtime is not, as in the
    example. Every run's history is kept for the transcript.

    *The output contract rides with the instruction.* The orchestrator writes
    the instruction; the host appends the worker's output names and
    descriptions, as :func:`turn_prompt` does for every question in the suite,
    so a worker delivers under the name the study judges by.

    *A handed object is described.* Before a run, the runtime states the shape
    and dtypes of the table it holds under ``INPUT_TABLE``, as the hosted
    study's described arm does. Where no object is handed, nothing is
    registered under that name and this does nothing.

    *What the run produced is read at once.* Its outputs are snapshotted as
    records when it returns, because in the cave arm the object goes on to the
    next worker by reference and a downstream worker that mutates it in place
    would otherwise rewrite what this one is judged on. An outage — a model or
    runtime error the conversation did not cause, by the delivery study's rule
    — is recorded rather than raised here, since an exception inside the
    orchestrator's cell is only execution output to it; the host raises it once
    the orchestrator stops, and the driver retries the case.
    """

    # Set by the host once the worker is built: what it owes, how it delivers
    # it (and where, when it delivers files), and the clock its case's runs are
    # stamped on.
    contract: list[Variable] = []
    delivers: Delivery = Delivery.VARIABLES
    output_dir: Path | None = None
    clock: Iterator[int] = itertools.count()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.responses: list[AgentResponse] = []
        self.delivered: list[dict[str, Any]] = []
        self.histories: list[list[Any]] = []
        self.started: list[int] = []
        self.outage: InfrastructureError | None = None

    async def run(self, query):
        self.started.append(next(self.clock))
        self.messages = []
        await self._describe_handed_input()
        try:
            response = await super().run(self._turn(str(query)))
        finally:
            self.histories.append(list(self.messages))
        self.responses.append(response)
        try:
            raise_if_infrastructure(response, self)
        except InfrastructureError as error:
            self.outage = self.outage or error
        self.delivered.append(await self._snapshot(response))
        return response

    def _turn(self, query: str) -> str:
        """The instruction the orchestrator wrote, with the worker's output contract."""
        return turn_prompt(query, self.contract)

    @property
    def runs(self) -> int:
        return len(self.responses)

    def output_path(self, name: str) -> Path:
        """Where a worker that delivers files writes the output called ``name``."""
        return self.output_dir / f"{name}.parquet"

    @property
    def transcript(self) -> list[Any]:
        """Every run's messages, one after another; the system prompt opens each."""
        return [message for history in self.histories for message in history]

    async def _snapshot(self, response: AgentResponse) -> dict[str, Any]:
        outputs = {}
        for variable in self.contract:
            if self.delivers is Delivery.VARIABLES:
                value = await retrieve(self.runtime, variable.name)
            elif self.delivers is Delivery.FILES and self.output_path(variable.name).is_file():
                value = pd.read_parquet(self.output_path(variable.name))
            else:
                value = _reply_table(response.content, variable.name)
            outputs[variable.name] = as_records(value)
        return outputs

    async def _describe_handed_input(self) -> None:
        # The registry is the runtime's own; cave-agent 0.8.0 offers no call
        # that rewrites a description, and the version is pinned (core.agents).
        variable = self.runtime._variables.get(INPUT_TABLE)
        if variable is not None:
            variable.description = describe_handed_frame(
                HANDED_TABLE_DESCRIPTION, await retrieve(self.runtime, INPUT_TABLE),
            )


class FencedCodeWorker(Worker, FencedCodeAgent):
    pass


class ToolCallWorker(Worker, ToolCallAgent):
    pass


@dataclass
class BuiltWorker:
    """A worker as the host holds it: the spec the orchestrator reads, the agent, the judge."""

    spec: WorkerSpec
    agent: Worker
    # ("table", task, expected rows) or ("answers", follow_up, expected rows).
    judge: tuple

    @property
    def contract(self) -> list[Variable]:
        return self.agent.contract


def worker_class(medium: Medium) -> type[Worker]:
    return ToolCallWorker if medium is Medium.JSON else FencedCodeWorker


def _build_workers(
    model, case: PipelineCase, arm: Arm, settings: PipelineSettings, workdir: Path,
) -> list[BuiltWorker]:
    """The case's workers: the pipeline's stages under the arm's medium.

    Every worker has its own runtime and its own prompt. A worker that delivers
    as variables has its output registered, so its runtime names what it is to
    assign; the analyst always does, in every arm, so the answers are read the
    same way everywhere. In the cave arm a worker handed a table has
    ``INPUT_TABLE`` registered empty for the orchestrator to fill with
    ``update_variable``, which is the library's own way of handing a worker its
    input; in the text arms nothing is registered, since a table can only reach
    the worker inside the instruction. In the file arm each worker that hands
    a table on has its own directory under ``workdir`` to write it into.
    """
    producer = PRODUCER[arm.medium]
    clock = itertools.count()
    tables = select_runtime_tables(case.data_sources)
    paths = table_paths(tables, None)
    expected_tables = case.expected_tables(case.expected_rows())
    specs = worker_specs(case)
    built = []
    for index, spec in enumerate(specs):
        is_first, is_last = index == 0, index == len(specs) - 1
        delivers = Delivery.VARIABLES if is_last else producer.delivery
        # What the worker owes: the analyst its answers, every other worker the
        # task's table under this worker's name. Registered in its runtime only
        # where it delivers by assigning; read to it beside the question always.
        contract = case.follow_up.variables if is_last else \
            [Variable(spec.table, None, case.task.variable.description)]
        registered = list(contract) if delivers is Delivery.VARIABLES else []
        if spec.takes_input and arm.reaches_runtime:
            # Registered empty and untyped. An upstream worker may deliver its
            # table as a DataFrame or as a list of row dicts — the contract
            # allows both and the judge reads both — and a typed slot would
            # refuse one of them at update_variable and make the orchestrator
            # convert it, a task the medium does not set.
            registered.append(Variable(INPUT_TABLE, None, HANDED_TABLE_DESCRIPTION))
        output_dir = None
        if delivers is Delivery.FILES:
            output_dir = workdir / spec.name
            output_dir.mkdir(parents=True, exist_ok=True)
        if is_first:
            instructions = system_instructions(
                "eager", paradigm=producer, tables=tables, paths=paths, output_dir=output_dir,
            )
        else:
            instructions = handed_agent_instructions(
                HANDED_CHANNEL[arm.medium], delivers=delivers, table=INPUT_TABLE,
                output_dir=output_dir, action=producer.action,
            )
        runtime = IPythonRuntime(
            functions=[], variables=registered, types=[], security_checker=SECURITY_CHECKER,
        )
        agent = worker_class(arm.medium)(
            model=model, runtime=runtime, system_instructions=instructions,
            max_steps=settings.step_budget, max_exec_output=settings.max_exec_output,
            stream_idle_timeout=idle_timeout(model),
        )
        agent.contract, agent.delivers, agent.clock = contract, delivers, clock
        agent.output_dir = output_dir
        judge = ("answers", case.follow_up, expected_tables[-1]) if is_last \
            else ("table", case.task, expected_tables[index])
        built.append(BuiltWorker(spec, agent, judge))
    return built


async def retrieve(runtime, name: str):
    value = runtime.retrieve(name)
    return await value if inspect.isawaitable(value) else value


def _reply_table(reply: str, name: str):
    """The table in a reply's final ```json block.

    Under the name the study gives it when the worker used that name, else the
    one table the block holds. The orchestrator wrote the worker's instruction,
    and the name it chose for the output is not what the study measures.
    """
    delivered = reply_outputs(reply)
    if name in delivered:
        return delivered[name]
    tables = [value for value in delivered.values() if isinstance(value, list)]
    return tables[0] if len(tables) == 1 else None


def _judge(worker: BuiltWorker) -> dict[str, Any]:
    """This worker's output against the reference, as it stood when its last run returned."""
    kind, checker, expected = worker.judge
    delivered = worker.agent.delivered[-1] if worker.agent.delivered else {}
    if kind == "answers":
        verdict = checker.check(delivered, expected)
        return {"success": bool(verdict.success), "message": verdict.message, "outputs": delivered}
    rows = delivered.get(worker.spec.table)
    verdict = checker.check(rows, expected)
    return {"success": bool(verdict.success), "message": verdict.message, "rows": row_count(rows)}


def spent_over(agent, responses: list[AgentResponse]) -> dict[str, Any]:
    """What an agent spent over all its runs, in the suite's counters.

    ``agent.spent`` (core.agents) counts provider-reported and estimated tokens
    side by side for every call, so an arm whose calls the provider counted and
    one whose calls were estimated are compared on the same estimate, as the
    delivery study compares them. The response totals alone would mix the two.
    """
    return {
        "steps": sum(response.steps for response in responses),
        "stop_reasons": [response.stop_reason.value for response in responses],
        "spent": dict(agent.spent),
    }


def _output_slots(workers: list[BuiltWorker], arm: Arm) -> list[Variable]:
    """Where the orchestrator keeps what it retrieves, in the arm that retrieves objects.

    The example registers ``cleaned_data`` and ``insights`` in the orchestrator's
    runtime beside the agents, one slot per worker output; so does this. Each
    slot carries the output's own description — the table's columns, or what an
    answer is — so the orchestrator knows what each worker is to produce and can
    instruct it in those terms. In the text arms nothing is retrieved, a
    worker's product being in its reply, so there is nothing to make a slot for.
    """
    if not arm.reaches_runtime:
        return []
    return [
        Variable(output.name, None, f"What the {worker.spec.role} agent produces. {output.description}")
        for worker in workers for output in worker.contract
    ]


def _describe(worker: BuiltWorker, arm: Arm) -> str:
    """The worker's description, naming the file it writes where it writes one."""
    writes_table = worker.agent.delivers is Delivery.FILES
    path = worker.agent.output_path(worker.spec.table) if writes_table else None
    return describe_worker(worker.spec, arm, path)


def orchestrator_task(case: PipelineCase) -> str:
    """What the orchestrator is asked: the table, the narrowing, the question.

    The same three things the hosted study asks its three stages, in one text
    with no worker named, so the orchestrator has to match them to workers.
    """
    steps = [f"First, compute this table: {case.producer_query()}"]
    steps += [f"Next, from the table so far: {middle.query(case.task)}" for middle in case.middles]
    steps.append(f"Finally, about the table that is left: {case.follow_up.query}")
    return "The task has these parts, in this order.\n\n" + "\n\n".join(steps)


async def run_orchestration(
    model, case: PipelineCase, arm: Arm, settings: PipelineSettings, workdir: Path,
) -> OrchestrationResult:
    """Build the workers, hand them to the orchestrator, run it once, judge."""
    workers = _build_workers(model, case, arm, settings, workdir)
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
        system_instructions=orchestrator_instructions(),
        max_steps=settings.step_budget, max_exec_output=settings.max_exec_output,
        stream_idle_timeout=idle_timeout(model),
    )
    response = await orchestrator.run(orchestrator_task(case))
    raise_if_infrastructure(response, orchestrator)
    for worker in workers:
        if worker.agent.outage is not None:
            raise InfrastructureError(f"{worker.spec.name}: {worker.agent.outage}")

    result = OrchestrationResult(
        case=case.name, arm=arm.name,
        orchestrator={
            **spent_over(orchestrator, [response]), "response": response.content,
            "code_snippets": response.code_snippets,
            "messages": messages_of(orchestrator) or [],
        },
    )
    # Which worker ran when, from the workers themselves: every run stamped on
    # one clock, read back in stamp order.
    runs = sorted((stamp, worker.spec.name) for worker in workers for stamp in worker.agent.started)
    result.ran = [name for _, name in runs]
    result.ran_as_designed = result.ran == [worker.spec.name for worker in workers]
    result.repeated = [worker.spec.name for worker in workers if worker.agent.runs > 1]
    result.skipped = [worker.spec.name for worker in workers if worker.agent.runs == 0]

    for worker in workers:
        result.workers.append({
            "name": worker.spec.name, "runs": worker.agent.runs,
            **spent_over(worker.agent, worker.agent.responses), **_judge(worker),
            "messages": worker.agent.transcript,
        })
    result.success = bool(result.workers[-1]["success"])
    if not result.success:
        result.failure = next(
            (record["name"] for record in result.workers if not record["success"]), None,
        )
    return result
