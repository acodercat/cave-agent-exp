"""Reading a run's file: which of its tasks count, and how the rest are treated.

A task that raised is not evidence about a paradigm -- the gateway refused it or
dropped the connection, which says nothing about how the agent reasoned -- so it
is left out and, on a rerun, attempted again.

A task whose record does not account for the state the agent reached (see
:mod:`fidelity`) is treated differently, and deliberately not symmetrically. Only
the cave arm can produce one: the function-calling arm dispatches each call to one
wrapped method, so its record is complete by construction. Dropping such a task
would therefore remove tasks from one arm only -- and in the one real case so far
it was a task that arm had failed, so dropping it raised that arm's score by half
a point. An exclusion that can only help one side is not an exclusion to make on
a judgement call.

So it is kept and counted as a failure. What the agent actually achieved is
unknown, and the arm whose recording fell short is the one that has to carry the
doubt. The id is reported either way, so a reader can see how many there were.

Defined here rather than in each of the runner, the estimator and the comparison,
so the three cannot drift apart on what they are counting.
"""

from __future__ import annotations

import json
from pathlib import Path


def is_evidence(row: dict) -> bool:
    """Whether a task's row counts towards a paradigm's rate.

    A task whose record fell short counts -- as a failure, see the module
    docstring -- so only an errored task is excluded.
    """
    return row.get("error") is None


def counts_as_solved(row: dict) -> bool:
    """Whether a counted task is credited to the paradigm.

    A task the benchmark scored correct on a record that does not account for the
    state is not credited: the verdict is about a trajectory that is not the one
    the agent took.
    """
    return bool(row["valid"]) and not row.get("unrecorded_change")


def read(path: Path) -> dict:
    """A run's file, as written."""
    return json.loads(path.read_text())


def scored(payload: dict) -> list[dict]:
    """The rows of a run that count, in the order the file holds them."""
    return [row for row in payload["tasks"] if is_evidence(row)]


def solved(payload: dict) -> int:
    """How many of them are credited."""
    return sum(counts_as_solved(row) for row in scored(payload))


def set_aside(payload: dict) -> dict[str, list[str]]:
    """What a report has to say out loud: the excluded, and the discredited."""
    errored = [row["id"] for row in payload["tasks"] if row.get("error") is not None]
    unaccounted = [row["id"] for row in payload["tasks"]
                   if row.get("error") is None and row.get("unrecorded_change")]
    return {"errored": errored, "unaccounted": unaccounted}
