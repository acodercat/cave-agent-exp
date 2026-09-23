"""The multi-agent pipeline: its cases, its stages, and the channels between them.

The delivery study (:mod:`core.table_delivery`) measures what it costs to get a
table out of a runtime and into the host. The pipeline asks the same question of
the seam between two agents: the first is asked for a table, the last is asked
something that can only be answered from every row of it, and a middle agent
narrows it on the way. Two studies run it. The **hosted** study
(:mod:`core.pipeline_evaluator`) has the host run the stages in order and move
each table across itself, and varies the channel it moves it on. The
**orchestrated** study (:mod:`core.orchestration`) hands the same stages to an
orchestrator agent as workers and lets it direct them; there the arm is the
medium the orchestrator reaches a worker through. This module holds what both
share: the cases, the stages, and the channels.

What it varies is the channel: how an agent's table reaches the next one. Five
arms, and they make three contrasts rather than one.

* ``object`` — the agent assigns the table to a runtime variable, and the host
  injects that same object into the next agent's own runtime.
* ``object_described`` — the same injection, and the runtime also states the
  object's shape and column dtypes in the variable's description, which it can
  read off the object it holds.
* ``object_signalled`` — described as above, and each agent is told, once every
  output it was asked for is assigned, that nothing further needs to run.
* ``file`` — the agent writes Parquet, and the next one is told the path.
* ``text`` — the agent's reply is the message the next one reads.
* ``text_bound`` — the same reply, quoted in the same message, and also bound
  as a string variable in the next agent's runtime, so code can parse it.
* ``shared`` — the agents run in one runtime, so the host moves nothing: what
  one registered, the next one's prompt already describes.

``object``, ``file`` and ``text`` differ on the delivery axis alone — all three
read their data from files and run fenced code — so a difference between them is
a difference between channels and not between paradigms. ``object`` and
``shared`` are produced identically and differ only in whether the host moves
anything, which is the contrast the library's own documented pattern and a
published blackboard system sit on either side of. ``text`` and ``text_bound``
are produced identically and the next agent is told the same thing about the
table; they differ only in whether the text it was told about is reachable
from code. That last contrast is what answers the objection that a text
channel is only expensive because the model was made to retype the table.
``tests/test_pipeline.py`` pins all three. What a handed agent is told differs in one sentence and one worked
first step, which live with every other prompt in :mod:`core.prompts`.

What it asks is a :class:`PipelineCase`: a delivery task at one of its sizes, zero
or more :class:`Middle` agents that are handed the table and hand one on, and a
:class:`FollowUp` that the last agent answers from whatever reached it. Every
seam uses the same channel, so a pipeline of k agents crosses it k-1 times and
the study can ask what depth alone costs. The cases are in
:mod:`cases.pipeline`. They are not registered in
``benchmarks.json`` and cannot be run by ``scripts.run``: a pipeline is two agents
and two runtimes, which the single-agent evaluator has no shape for.
``scripts.run_pipeline`` runs them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Sequence

from cave_agent import Variable

from core.paradigms import CODEBLOCK, CODEBLOCK_FILES, CODEBLOCK_VARIABLES, Paradigm
from core.table_delivery import Size, TableTask
from core.validation import ValidatorResult, validate_ordered_outputs


# ----- what the study varies --------------------------------------------------

class Carry(Enum):
    """What the host does with an agent's table before the next agent runs."""

    INJECT = "inject"        # put the object into the next agent's own runtime
    INJECT_DESCRIBED = "inject_described"  # the same, and say what the object holds
    INJECT_SIGNALLED = "inject_signalled"  # described, and told when its outputs are assigned
    SHARE = "share"          # nothing: the next agent runs in the same runtime
    PATH = "path"            # name the Parquet file the agent wrote
    REPLY = "reply"          # quote the agent's whole reply
    REPLY_BOUND = "reply_bound"  # quote it, and bind the same text as a variable


@dataclass(frozen=True)
class Channel:
    """One way for a table to cross between two agents.

    ``producer`` is the paradigm every agent of the pipeline delivers under, and
    ``carry`` is what the host does between them. Two channels can share a
    producer and differ in the carry — that is ``object`` against ``shared`` —
    which is how the study separates the crossing from the moving.

    The text a handed agent reads is keyed by ``name`` in :mod:`core.prompts`.
    """

    name: str
    producer: Paradigm
    carry: Carry

    @property
    def shares_runtime(self) -> bool:
        return self.carry is Carry.SHARE

    @property
    def describes(self) -> bool:
        return self.carry in (Carry.INJECT_DESCRIBED, Carry.INJECT_SIGNALLED)

    @property
    def signals(self) -> bool:
        return self.carry is Carry.INJECT_SIGNALLED


OBJECT = Channel("object", CODEBLOCK_VARIABLES, Carry.INJECT)
OBJECT_DESCRIBED = Channel("object_described", CODEBLOCK_VARIABLES, Carry.INJECT_DESCRIBED)
OBJECT_SIGNALLED = Channel("object_signalled", CODEBLOCK_VARIABLES, Carry.INJECT_SIGNALLED)
SHARED = Channel("shared", CODEBLOCK_VARIABLES, Carry.SHARE)
FILE = Channel("file", CODEBLOCK_FILES, Carry.PATH)
TEXT = Channel("text", CODEBLOCK, Carry.REPLY)
TEXT_BOUND = Channel("text_bound", CODEBLOCK, Carry.REPLY_BOUND)

CHANNELS = {
    channel.name: channel
    for channel in (OBJECT, OBJECT_DESCRIBED, OBJECT_SIGNALLED, SHARED, FILE, TEXT, TEXT_BOUND)
}
# The arms that differ on the producer's delivery alone, so a difference between
# them cannot be a difference between paradigms.
DELIVERY_ARMS = ("object", "file", "text")
# The pair produced identically, differing only in whether the host moves it.
CARRY_ARMS = ("object", "shared")
# The pair whose next agent reads the same text, differing only in whether that
# text is also reachable from its code.
ADDRESS_ARMS = ("text", "text_bound")
# The pair injected identically, differing only in whether the runtime tells the
# next agent what the object it holds looks like. A runtime that holds a
# DataFrame can read its shape and dtypes at no cost; the file and text arms
# oblige the model to look for itself, and it turned out that an agent handed a
# ready object without that description often did not look, and compared a
# text column to a number.
DESCRIBE_ARMS = ("object", "object_described")
# The pair injected and described identically, differing only in whether each
# agent is told, once every output it was asked for is assigned, that it is.
# Writing a file is a visible act of delivery; an assignment is not, and an
# agent left to infer that it had delivered was seen to spend its remaining
# steps re-typing the variable's name.
SIGNAL_ARMS = ("object_described", "object_signalled")



# ----- what the study asks ----------------------------------------------------

@dataclass(frozen=True)
class Answer:
    """One value the second agent is asked for.

    ``decimals`` pins how closely a number must match; ``None`` asks for exact
    equality, which is what a label is compared by, and ``0`` is the whole-number
    comparison counts and sums of integer columns use.
    """

    name: str
    description: str
    decimals: int | None = None

    @property
    def variable(self) -> Variable:
        return Variable(self.name, None, self.description)


@dataclass(frozen=True)
class FollowUp:
    """The question the second agent answers from the table it was handed.

    ``compute`` takes the expected rows of the first agent's table — the correct
    one — and returns the answers in the order ``answers`` declares them. So the
    second agent's verdict is end-to-end: it is right only if the table it was
    handed was right and it read every row of it.
    """

    query: str
    answers: tuple[Answer, ...]
    compute: Callable[[list[dict]], tuple]

    @property
    def variables(self) -> list[Variable]:
        return [answer.variable for answer in self.answers]

    @property
    def stores(self) -> list[str]:
        return [answer.name for answer in self.answers]

    def check(self, outputs: dict, expected_rows: list[dict]) -> ValidatorResult:
        return validate_ordered_outputs(
            outputs,
            self.variables,
            list(self.compute(expected_rows)),
            [answer.decimals for answer in self.answers],
        )


@dataclass(frozen=True)
class Middle:
    """An agent between the first and the last: handed a table, hands one on.

    ``select`` is what it should hand on, given the task and the rows it was
    handed, so the host can say what each stage's table ought to be without
    running the pipeline. It takes the task because a rule may only refer to
    something the question fixes — the task's key orders every row of it, while
    the order the rows happen to arrive in does not: ``validate_table`` matches
    rows on the key and **ignores their order**, so a table can be judged correct
    in any order and a rule about "the first half as they stand" has no single
    right answer. ``ask`` renders the rule for that task, naming the key.

    The rules the study uses are deliberately simple, because the middle agent is
    there to add a crossing, not a second thing that could go wrong. A stage
    whose work were hard would make a deeper pipeline fail for a reason that is
    not the channel.
    """

    role: str
    ask: Callable[[TableTask], str]
    select: Callable[[TableTask, list[dict]], list[dict]]
    output: str

    def query(self, task: TableTask) -> str:
        return self.ask(task)


@dataclass(frozen=True)
class PipelineCase:
    """One delivery question, at one size, crossed by a pipeline of agents."""

    task: TableTask
    size: Size
    follow_up: FollowUp
    middles: tuple[Middle, ...] = ()

    @property
    def name(self) -> str:
        return f"{self.task.name}_{self.size.label}"

    @property
    def agents(self) -> int:
        """How many agents the pipeline holds, the first and the last included."""
        return len(self.middles) + 2

    @property
    def roles(self) -> tuple[str, ...]:
        return ("retriever", *(middle.role for middle in self.middles), "analyst")

    def expected_tables(self, rows: list[dict]) -> list[list[dict]]:
        """What each agent should hand on: the first agent's table, then each middle's."""
        tables = [rows]
        for middle in self.middles:
            tables.append(middle.select(self.task, tables[-1]))
        return tables

    @property
    def data_sources(self) -> tuple[str, ...]:
        return self.task.data_sources

    def producer_query(self) -> str:
        return self.task.query.format(scope=self.size.scope)

    def expected_rows(self) -> list[dict]:
        return self.task.expected_rows(self.size)


def cases_by_name(cases: Sequence[PipelineCase]) -> dict[str, PipelineCase]:
    """The cases keyed by name, refusing a duplicate rather than dropping one."""
    by_name: dict[str, PipelineCase] = {}
    for case in cases:
        if case.name in by_name:
            raise ValueError(f"two pipeline cases are both named {case.name!r}")
        by_name[case.name] = case
    return by_name
