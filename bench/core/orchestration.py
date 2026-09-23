"""Multi-agent coordination as cave-agent's ``examples/multi_agent.py`` does it.

The hosted study (:mod:`core.pipeline_evaluator`) has the host run the pipeline
and move each table itself; it measures how a table crosses a seam. It does not
measure coordination, because no agent coordinates anything — the host does.

Here the host runs one agent, the orchestrator, and steps back. The workers are
``CaveAgent`` objects registered as variables in the orchestrator's runtime, as
the library's own example registers its ``cleaner`` and ``analyzer``, and each
variable's description says how to use the worker. The orchestrator is asked to
get the task done by directing them. Whether it runs the right worker, on the
right data, in the right order, and carries each worker's result to the next, is
the orchestrator's to get right in code it writes — that is the coordination
being measured. The host judges only what comes out at the end, and records what
the orchestrator did along the way.

The workers are the pipeline's stages: the retriever that computes a table, the
narrower that keeps half of it, the analyst that answers from it. Each has its
own runtime, its own prompt and its own outputs; each is judged as before, so a
run says which worker was wrong and whether the orchestrator's directing was.

What varies is the **medium** — how the orchestrator and a worker exchange
state — and the arm is the whole of how the worker is exposed:

* ``cave`` — the orchestrator reaches the worker's runtime, as in the example:
  ``worker.runtime.update_variable(name, table)`` to hand a table in,
  ``await worker.run(instruction)`` to run it, and
  ``await worker.runtime.retrieve(name)`` to take the table it made — the
  object itself, never serialized. The worker delivers by assigning a variable.
* ``text`` — the worker is the same object, but its runtime is not the
  orchestrator's to reach: the only entry is ``await worker.run(instruction)``,
  and what comes back is the worker's reply as text. A table travels in that
  text and in the instruction the orchestrator writes for the next worker. The
  worker delivers by writing its table into its reply. This is the
  message-passing pattern of frameworks in which agents talk.
* ``json`` — as ``text``, with workers that act through JSON function calls
  rather than fenced code. With ``text`` it makes the text-centric pipeline in
  both of its action formats, which is what the paper's claim is about.
* ``file`` — the worker's runtime is again not the orchestrator's to reach, but
  a table does not travel as text: a worker writes its table to a Parquet file
  whose path its description states, and the orchestrator names that path in
  the next worker's instruction. State crosses by reference to a file instead
  of by reference to an object, which is the contrast with ``cave``.

The orchestrator in every arm is the same fenced-code agent with the same
instructions; the arms differ in what the worker variables' descriptions say the
orchestrator can do, and that is the medium.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from core.fidelity import RECEIVED, FidelityCase
from core.pipeline import PipelineCase
from core.rounds import RoundsCase


class Medium(Enum):
    """How the orchestrator and a worker exchange state."""

    CAVE = "cave"     # the worker's runtime: update_variable in, retrieve out
    TEXT = "text"     # the worker's reply, fenced-code worker
    JSON = "json"     # the worker's reply, function-calling worker
    FILE = "file"     # a Parquet file the worker writes; its path goes in the next instruction


@dataclass(frozen=True)
class Arm:
    name: str
    medium: Medium
    # Every worker writes to one path instead of its own. Only the rounds study
    # (core.rounds) reads this: it is the file medium's other protocol, where
    # the object is one artifact that each stage overwrites, so there is no
    # version for an orchestrator to name and none for it to name wrongly.
    shared_path: bool = False

    @property
    def reaches_runtime(self) -> bool:
        return self.medium is Medium.CAVE


ARMS = {arm.name: arm for arm in (
    Arm("cave", Medium.CAVE), Arm("text", Medium.TEXT), Arm("json", Medium.JSON),
    Arm("file", Medium.FILE), Arm("file_shared", Medium.FILE, shared_path=True),
)}


# What a worker calls the table it is handed, in the arm where a table is handed
# to it as an object. The orchestrator writes it into the worker's runtime under
# this name, and the worker's prompt names it.
INPUT_TABLE = "delivered_table"


@dataclass(frozen=True)
class WorkerSpec:
    """One worker as the orchestrator is told about it.

    ``name`` is the variable the orchestrator finds it under; ``role`` is the
    stage it plays; ``outputs`` are the names of what it produces — one table
    for the retriever and each middle, the answers for the analyst.
    ``takes_input`` is whether a table is handed to it: the retriever computes
    from the source data and takes none. The description the orchestrator reads
    is built per arm by :func:`describe_worker`.
    """

    name: str
    role: str
    purpose: str
    outputs: tuple[str, ...]
    takes_input: bool = True

    @property
    def answers(self) -> bool:
        """Whether its outputs are answers rather than a table or an object."""
        return self.role in ("analyst", "consumer")

    @property
    def table(self) -> str:
        """The name of the one table a non-analyst worker produces."""
        (name,) = self.outputs
        return name


def worker_specs(case: PipelineCase | FidelityCase | RoundsCase) -> list[WorkerSpec]:
    """The workers a case needs.

    Listed in the order the task naturally runs them, but the orchestrator is
    told what each is for and not in what order to run them: that is its job.
    A fidelity case (core.fidelity) has two: the producer that builds the
    object, and the consumer that is handed it and answers about it. A rounds
    case (core.rounds) has a reviser between them for every edit its chain
    makes, each named by its place in the chain.
    """
    task = case.task
    if isinstance(case, RoundsCase):
        return [
            WorkerSpec(
                "producer", "producer",
                f"builds the object the task asks for from the source data ({task.title.lower()})",
                (task.output,), takes_input=False,
            ),
            *(
                WorkerSpec(
                    f"reviser_{revision.index}", "reviser",
                    f"given the object, does this to it: {revision.ask}", (revision.output,),
                )
                for revision in case.revisions
            ),
            WorkerSpec(
                "consumer", "consumer",
                "given the object, answers the question the task asks about it",
                (RECEIVED, *case.follow_up.stores),
            ),
        ]
    if isinstance(case, FidelityCase):
        return [
            WorkerSpec(
                "producer", "producer",
                f"builds the object the task asks for from the source data ({task.title.lower()})",
                (task.output,), takes_input=False,
            ),
            WorkerSpec(
                "consumer", "consumer",
                "given the object, answers the question the task asks about it",
                (RECEIVED, *case.follow_up.stores),
            ),
        ]
    specs = [WorkerSpec(
        "retriever", "retriever",
        f"computes the table the task asks for from the source data ({task.title.lower()})",
        (task.output,), takes_input=False,
    )]
    # A middle worker's purpose is its own rule, as its stage asks it, and its
    # name is unique: a depth pipeline holds several relays.
    for index, middle in enumerate(case.middles):
        name = middle.role if len(case.middles) == 1 else f"{middle.role}_{index + 1}"
        specs.append(WorkerSpec(
            name, middle.role, f"given a table, does this to it: {middle.query(task)}",
            (middle.output,),
        ))
    specs.append(WorkerSpec(
        "analyst", "analyst",
        "given the final table, answers the question the task asks about it",
        tuple(case.follow_up.stores),
    ))
    return specs


def describe_worker(
    spec: WorkerSpec, arm: Arm, output_path: Path | None = None, *,
    input_slot: str = INPUT_TABLE, noun: str = "table",
) -> str:
    """The description of a worker variable, in the terms of the arm's medium.

    Modelled on the library's example, which tells the orchestrator in the
    variable's description exactly what to call:

        Cleaner agent: call cleaner.runtime.update_variable('data', value) to set
        input, await cleaner.run('instruction') to execute, await
        cleaner.runtime.retrieve('cleaned_data') to get output

    In the cave arm the description says the same of this worker. In the text
    and json arms the worker's runtime is not the orchestrator's to reach, and
    the description says so: the only call is ``run``, and what comes back is
    the reply. In the file arm the description states where the worker writes
    its table (``output_path``), as the cave arm states the name to retrieve.
    All are true statements about the medium, not instructions favouring one.

    ``input_slot`` is the name the worker is handed its input under, and
    ``noun`` what that input is called: a table in the pipeline cases, an
    object in the fidelity cases, where what crosses need not be a table.
    """
    head = f"{spec.role.capitalize()} agent: {spec.purpose}."
    handle, file_noun = ("table", "Parquet file") if noun == "table" else ("obj", "file")
    if arm.reaches_runtime:
        take = " and ".join(f"await {spec.name}.runtime.retrieve('{name}')" for name in spec.outputs)
        # A live orchestrator, told the example's wording, awaited update_variable
        # too and crashed on the None it returns, 39 times in 35 runs; the
        # description now says which of the three calls is awaited.
        give = (
            f"call {spec.name}.runtime.update_variable('{input_slot}', {handle}) — a plain "
            f"call, not awaited — to hand it its input {noun}, then "
            if spec.takes_input else ""
        )
        return (
            f"{head} Use it from code: {give}await {spec.name}.run('instruction') to run it, "
            f"then {take} to get what it made."
        )
    if arm.medium is Medium.FILE:
        made = (
            "result.content is its reply as text, and its answers are in that reply"
            if spec.answers else
            f"it writes the {noun} it made to the {file_noun} '{output_path}'"
        )
        # The text arms' sentence, with the path in place of the table. An earlier
        # wording — "name in the instruction the path" — had a live orchestrator
        # send the path as the whole instruction, and a worker told nothing else
        # copied its table through unchanged.
        given = (
            "It cannot reach your runtime: everything it needs must be in the "
            f"instruction you send, including the path of the {file_noun} it is to read."
            if spec.takes_input else
            "It reads the source data itself."
        )
        return (
            f"{head} Use it from code: result = await {spec.name}.run('instruction') runs it; "
            f"{made}. {given}"
        )
    made = (
        "its answers are in that reply" if spec.answers
        else f"the {noun} it made is in that reply, in its final ```json block"
    )
    given = (
        "It cannot reach your runtime or any file: everything it needs must be in the "
        f"instruction you send, including any {noun}, written out in full."
        if spec.takes_input else
        "It reads the source data itself."
    )
    return (
        f"{head} Use it from code: result = await {spec.name}.run('instruction') runs it, "
        f"and result.content is its reply as text; {made}. {given}"
    )


@dataclass
class OrchestrationResult:
    """One case run under one arm, with what the orchestrator did recorded.

    ``success`` is the analyst's answers against the reference: the same
    verdict the pipeline family's last stage gets, so the two studies' end-to-end
    numbers mean the same thing. How the orchestrator directed its workers is
    recorded beside it, as diagnosis, and not folded into the verdict. It was,
    in a first draft — success required every worker to have run exactly once
    — and that punished an arm twice for one failure: a worker that misread a
    quoted table is likelier to be run again, so an arm whose tables travel as
    text would have lost once for the wrong answer and once for the retry. The
    diagnostic fields say what happened; the verdict says whether the answer
    was right.
    """

    case: str
    arm: str
    orchestrator: dict[str, Any]
    workers: list[dict[str, Any]] = field(default_factory=list)
    # The verdict: the analyst's answers against the reference.
    success: bool = False
    # Which worker ran, in the order the runs happened, from each worker's own
    # record of being run — not from the orchestrator's account of itself.
    ran: list[str] = field(default_factory=list)
    # Whether the run went as the task naturally does: each worker once, in
    # the order the parts of the task come; and where it did not, which
    # workers ran more than once and which never.
    ran_as_designed: bool = False
    repeated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    # When the answer was wrong, the first worker whose output was: a wrong
    # worker upstream is the failure, not the analyst that answered from it.
    failure: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "case": self.case, "arm": self.arm, "success": self.success,
            "ran": self.ran, "ran_as_designed": self.ran_as_designed,
            "repeated": self.repeated, "skipped": self.skipped,
            "failure": self.failure, "orchestrator": self.orchestrator,
            "workers": self.workers,
        }
