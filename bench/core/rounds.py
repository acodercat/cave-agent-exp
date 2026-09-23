"""Rounds: one object handed on several times, edited at every hop.

The fidelity study (:mod:`core.fidelity`) hands an object across one seam and
asks what arrives. It found that a table, an array or a fitted model crosses a
Parquet or joblib file as whole as it crosses a shared runtime: where the
object can be serialised and the host has chosen the format for it, writing it
down loses nothing. What that study cannot see is what a *second* crossing
costs, or a fourth, or an eighth.

Here the same object passes through a chain: a producer builds it, then each
reviser is handed it, makes one fixed edit, and hands it on; the consumer at
the end answers a question the host asks only then. Every arm of the fidelity
study is run again, so what differs is still only how the object crosses — and
now how many times. Three things can go wrong at a hop that cannot go wrong at
one: the object can arrive as an earlier version (a stale path, an older reply
quoted again), an edit can be skipped or made twice, and whatever a crossing
loses is carried into every crossing after it.

The host knows what the object should be after each edit, because every rule is
a Python function it can apply itself (:class:`Revision`). So a hop's record
separates what the crossing did from what the agent did: whether the object
arrived as the agent before it left it (``carried``), whether the rule was
applied correctly to whatever did arrive (``edited``), and whether the result
is still the object the chain should have produced (``applied``).

Two things this study deliberately does not measure. The revisers are asked to
bind what they were handed before changing anything, so the host has evidence
of the object as it arrived; that makes this a study of *versioned* handoff and
not of shared mutable state, where a downstream agent edits an object the
upstream one still holds. And a repeat is read from the run record, never from
the object: a rule applied twice may leave the object exactly as it was.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import copy
from dataclasses import dataclass, field
from typing import Any

from cave_agent import Variable
import pandas as pd

from core.fidelity import (
    KEEP_BOUND, RECEIVED, RECEIVED_DESCRIPTION, FidelityReport, ObjectTask, compare,
)
from core.pipeline import FollowUp


# What a reviser binds the object it was handed to, before it changes anything.
# It is the host's evidence of the crossing where the host has no view of its
# own — the text and file arms, where what arrived is whatever the agent
# rebuilt or loaded. In the cave arm the object is in the worker's runtime
# before the run, and the host reads it there instead: an agent that binds the
# object it was handed and then edits a part they share (a dict's ``copy`` is
# shallow) leaves that variable holding something that was never handed to
# anyone, and the crossing would read as a loss that never happened.
CARRIED = "handed_in"
CARRIED_DESCRIPTION = (
    "The object as you were handed it, before you change anything: the same type, dtypes "
    "and values. Bind it here and leave it alone — make your changes on a copy."
)
# What a reviser's own output is called in the description it reads.
AFTER_THIS_CHANGE = "The same object after the change this stage of the task asks for."
# What the consumer is told ``received`` holds, once a chain has edited the
# object. It deliberately does not repeat how the task described the object
# when it was built: the edits add columns and keys, and a consumer told the
# original description rebuilt the object to match it, dropping what the chain
# had added. What it is asked for is what reached it.
RECEIVED_AFTER_ROUNDS = (
    "The object you were handed, exactly as you hold it after loading or rebuilding it: the "
    "same type, dtypes and values, changed in nothing. It has been through {rounds} round{s} "
    "of changes since it was built, so it no longer matches how this task described it then — "
    "bind what reached you, not what that description says."
)
HANDED_REVISED_DESCRIPTION = "The object as the agent before you left it."


@dataclass(frozen=True)
class Revision:
    """One fixed edit an intermediate agent makes to the object it is handed.

    ``ask`` is the whole instruction, with the rows and values written into it,
    and it is part of the study's resume key: a reworded rule is a different
    experiment. ``apply`` is the same edit in Python, and must be pure — it is
    folded over the chain to give the host its standard for every stage, so an
    ``apply`` that edited its argument in place would quietly corrupt every
    standard after it. ``output`` is what this stage hands on under, and must
    differ from every other stage's: in the cave arm the orchestrator's runtime
    registers one slot per worker output, and a runtime refuses a name twice.
    """

    index: int                              # 1-based; the rule's text names it too
    name: str                               # for the record, never shown to a model
    ask: str
    apply: Callable[[Any], Any]
    output: str

    def applied_to(self, value: Any) -> Any:
        """The rule's result on a copy, so the caller's object is untouched."""
        return self.apply(copy.deepcopy(value))


@dataclass(frozen=True)
class RoundsCase:
    """One object, one chain of edits, as the orchestrated pipeline runs it."""

    task: ObjectTask
    revisions: tuple[Revision, ...]

    def __post_init__(self):
        names = [self.task.output, *(revision.output for revision in self.revisions)]
        if len(set(names)) != len(names):
            raise ValueError(f"{self.task.name}: two stages hand on under one name: {names}")
        if [revision.index for revision in self.revisions] != list(range(1, len(self.revisions) + 1)):
            raise ValueError(f"{self.task.name}: revisions are not numbered 1..k")

    @property
    def name(self) -> str:
        return f"{self.task.name}_d{self.depth}"

    @property
    def depth(self) -> int:
        """Crossings: producer → reviser_1 → … → consumer."""
        return len(self.revisions) + 1

    @property
    def agents(self) -> int:
        return len(self.revisions) + 2

    @property
    def roles(self) -> tuple[str, ...]:
        return ("producer", *("reviser",) * len(self.revisions), "consumer")

    @property
    def data_sources(self) -> tuple[str, ...]:
        return self.task.data_sources

    @property
    def follow_up(self) -> FollowUp:
        return self.task.follow_up

    @property
    def consumer_variables(self) -> list[Variable]:
        rounds = len(self.revisions)
        if not rounds:
            describe = self.task.describe.rstrip(".")
            described = RECEIVED_DESCRIPTION.format(describe=describe[0].lower() + describe[1:])
        else:
            described = RECEIVED_AFTER_ROUNDS.format(
                rounds=rounds, s="" if rounds == 1 else "s",
            )
        return [Variable(RECEIVED, None, described), *self.follow_up.variables]

    def output_variable(self, revision: Revision) -> Variable:
        return Variable(revision.output, None, f"{AFTER_THIS_CHANGE} {KEEP_BOUND}")

    def standards(self, tables: Mapping[str, pd.DataFrame]) -> list[Any]:
        """S_0 … S_K: what the object should be when it is built and after each edit."""
        objects = [self.task.build(tables)]
        for revision in self.revisions:
            objects.append(revision.applied_to(objects[-1]))
        return objects


def cases(task: ObjectTask, revisions: Sequence[Revision], depths: Sequence[int]) -> list[RoundsCase]:
    """The same chain at several depths, each a prefix of the longest.

    A prefix, so the depths of one object are comparable: what depth 8 does in
    its first three hops is exactly what depth 4 does.
    """
    built = []
    for depth in depths:
        if depth < 1 or depth > len(revisions) + 1:
            raise ValueError(f"{task.name}: depth {depth} needs {depth - 1} revisions")
        built.append(RoundsCase(task, tuple(revisions[: depth - 1])))
    return built


# ----- where an object sits in the chain ------------------------------------

@dataclass
class Alignment:
    """Which version of the object a value is, in the terms the chain gives.

    ``as_of`` is the standard it matches. Of a worker's output, ``k`` is right
    and ``k - 1`` means the edit never happened; of a reviser's input, ``k - 1``
    is what it should have been handed and anything smaller is an earlier
    version. ``matches_output_of`` asks the same of what the agents actually
    produced — when something upstream went wrong the real earlier versions
    match no standard at all — and ``edited_from`` is the signature of a stale
    read: not a version itself, but this stage's rule applied to an older one.
    """

    as_of: int | None = None
    matches_output_of: int | None = None
    edited_from: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"as_of": self.as_of, "matches_output_of": self.matches_output_of,
                "edited_from": self.edited_from}


def align(
    value: Any, standards: Sequence[Any], produced: Sequence[Any], *,
    revision: Revision | None = None, row_key: str | None = None, older_than: int | None = None,
) -> Alignment:
    """Place ``value`` among the standards and among what the agents produced.

    ``older_than`` is the stage whose product this value should have come from,
    so only what earlier stages produced counts as an *earlier* version: a value
    that matches the stage before is the ordinary case and says nothing. Where
    ``revision`` is given, a value that is no version itself is also checked
    against that rule applied to each earlier product — an agent that read a
    stale object and then did its own work correctly on it (``edited_from``),
    which is what a path or a quoted reply from an earlier hop looks like.
    """
    def same(one: Any, other: Any) -> bool:
        return other is not None and compare(one, other, row_key=row_key).intact

    earlier = produced if older_than is None else produced[:max(older_than, 0)]
    found = Alignment()
    found.as_of = next((j for j, standard in enumerate(standards) if same(value, standard)), None)
    found.matches_output_of = next((j for j, output in enumerate(earlier) if same(value, output)), None)
    if revision is not None and found.as_of is None and found.matches_output_of is None:
        found.edited_from = next(
            (j for j, output in enumerate(earlier) if same(value, _rule_on(revision, output))),
            None,
        )
    return found


def _rule_on(revision: Revision, value: Any) -> Any:
    """The rule on an earlier output, or nothing where it cannot take what an agent bound."""
    if value is None:
        return None
    try:
        return revision.applied_to(value)
    except Exception:                               # noqa: BLE001 - not the kind of object the rule edits
        return None


@dataclass
class Hop:
    """What one worker's run says about the crossing into it and the edit in it.

    ``held`` places the object the worker produced; ``arrived`` places the one
    it was handed. The two answer different questions — where the chain got to,
    and where this worker started from. A stale read shows in both: the input
    is an earlier version (``in_as_of``), and the output is this stage's rule
    applied to one (``edited_from``).
    """

    name: str
    carried: bool | None = None             # arrived as the agent before it left it
    edited: bool | None = None              # the rule, applied to what did arrive; None where
                                            # what arrived was not the kind of object the rule edits
    # Which worker's run came just before this worker's last run. The chain is
    # judged in its designed order; where the orchestrator went back to an
    # earlier worker, this says so, and that hop's ``carried`` is read against
    # the wrong predecessor.
    after: str | None = None
    applied: bool | None = None             # still the object the chain should hold
    encoded: bool | None = None             # what it delivered vs what it bound
    # The agent bound its input after editing it, so what it holds as "handed
    # in" is its own output: the crossing was not observed, and ``carried``
    # stays None rather than reading as a loss. Only ever set where the agent's
    # own variable is the evidence, which ``input_seen`` says.
    observed_late: bool = False
    input_seen: str | None = None           # "host" (the runtime slot) or "agent"
    lost: list[str] = field(default_factory=list)
    held: Alignment = field(default_factory=Alignment)
    arrived: Alignment = field(default_factory=Alignment)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "carried": self.carried, "edited": self.edited,
            "applied": self.applied, "encoded": self.encoded, "observed_late": self.observed_late,
            "input_seen": self.input_seen, "after": self.after, "lost": self.lost,
            "as_of": self.held.as_of,
            "edited_from": self.held.edited_from,
            "in_as_of": self.arrived.as_of,
            "matches_output_of": self.arrived.matches_output_of,
        }


def judged(
    report: FidelityReport | None,
) -> tuple[bool | None, list[str]]:
    """A report as the record keeps it: the verdict and the names it lost, never every property."""
    if report is None:
        return None, []
    return report.intact, report.lost
