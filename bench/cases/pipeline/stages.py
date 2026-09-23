"""The agents between the first and the last, and what they are asked.

Two rules, and both are deliberately easy. A middle agent is in the pipeline to
add a crossing, not to add a second thing that could go wrong: if its own work
were hard, a deeper pipeline would fail more often for a reason that is not the
channel, and the study could not say which. So each is something the agent reads
straight off the table it was handed, and the host can state exactly which rows
it should hand on.

Both rules refer only to what the question fixes. In particular neither refers to
the order the rows arrived in: ``core.validation.validate_table`` matches rows on
the task's key and **ignores their order**, so the first agent's table can be
judged correct in any order, and nineteen of the twenty-four questions never ask
for one. A rule saying "the first half of the rows as they stand" therefore had no
single right answer — it scored a faithful middle agent as wrong whenever the
first agent's order differed from the reference's. What every task does fix is its
key, which is unique and never missing, so the key is what the rules sort by.

``keep_lower_half`` hands on the half that sorts first by key. It is the middle
agent of the main study: a funnel that carries part of the work forward, with one
right answer whatever order it received.

``relay`` keeps everything. It is the instrument of the depth probe: repeating it
lengthens the pipeline without changing what any stage carries, so the only thing
varying between a pipeline of three agents and one of five is how many times the
table crossed. A relay is not a claim about how anyone builds an agent pipeline;
it is how the payload is held constant while depth is not.
"""

from __future__ import annotations

from core.pipeline import Middle
from core.table_delivery import TableTask


def _key_phrase(task: TableTask) -> str:
    """How a question names the columns it is to be sorted by."""
    columns = [f"`{column}`" for column in task.key]
    if len(columns) == 1:
        return columns[0]
    return ", ".join(columns[:-1]) + " and then " + columns[-1]


def _sorted_by_key(task: TableTask, rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: tuple(str(row[column]) for column in task.key))


def _ask_lower_half(task: TableTask) -> str:
    return (
        f"Sort this table by {_key_phrase(task)}, comparing the values as text, and "
        "hand on the half that sorts first. If the number of rows is odd, hand on the "
        "smaller half. Keep every column exactly as you received it, in that sorted "
        "order: no new columns, no rounding, no other change."
    )


def _lower_half(task: TableTask, rows: list[dict]) -> list[dict]:
    ordered = _sorted_by_key(task, rows)
    return ordered[: len(ordered) // 2]


KEEP_LOWER_HALF = Middle(
    role="narrower",
    ask=_ask_lower_half,
    select=_lower_half,
    output="shortlisted_table",
)

RELAY = Middle(
    role="relay",
    ask=lambda task: (
        "Hand this table on exactly as you received it: every row, every column, "
        "every value unchanged. Do not drop anything, add anything or round anything."
    ),
    select=lambda task, rows: list(rows),
    output="relayed_table",
)
