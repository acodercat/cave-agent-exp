"""The control: ten rows of plain types, corrected round by round.

Nothing here is a type a format has trouble with — the fidelity study's own
control object, whose JSON round trip is exact. What it measures is the error
rate of handing an object on and editing it at all, so that what the harder
objects lose on top of this can be read as the object's difficulty rather than
the chain's length. It is not a guarantee: ten rows can still be dropped,
mistyped or handed on from the wrong round, and that is a result too.
"""

from __future__ import annotations

import pandas as pd

from cases.fidelity._control_small_table import TASK as BRANCHES
from core.fidelity import ObjectTask
from core.pipeline import Answer, FollowUp
from core.rounds import Revision

# The branch each round corrects, frozen because the ids are written into the rules.
CORRECTED = (
    "2024_628_544", "2024_7213_0", "2024_3511_0", "2024_3510_0", "2024_4297_1301",
    "2024_57450_0", "2024_33124_0",
)
DEPOSITS = "branch_deposits_thousand_usd"
FLAG = "main_office_indicator"


def _correct(table: pd.DataFrame, index: int) -> pd.DataFrame:
    table = table.copy()
    chosen = table["branch_id"].eq(CORRECTED[index - 1])
    table.loc[chosen, DEPOSITS] = table.loc[chosen, DEPOSITS] + index
    table.loc[chosen, FLAG] = f"R{index}"
    return table


def _ask(index: int) -> str:
    return (
        f"In the row whose branch_id is '{CORRECTED[index - 1]}', add {index} to "
        f"{DEPOSITS} and set {FLAG} to 'R{index}'. Leave every other row and column, and the "
        "column types, exactly as they are."
    )


REVISIONS = tuple(
    Revision(
        index=index, name=f"correct_{index}", ask=_ask(index),
        apply=(lambda table, index=index: _correct(table, index)),
        output=f"branch_table_{index}",
    )
    for index in range(1, len(CORRECTED) + 1)
)


def corrected(table: pd.DataFrame) -> tuple:
    return (int(table[DEPOSITS].sum()), int(table[FLAG].str.startswith("R").sum()))


TASK = ObjectTask(
    name="rounds_control_branches",
    title=BRANCHES.title,
    group="rounds",
    kind=BRANCHES.kind,
    data_sources=BRANCHES.data_sources,
    ask=BRANCHES.ask,
    output=BRANCHES.output,
    describe=BRANCHES.describe,
    build=BRANCHES.build,
    follow_up=FollowUp(
        "What do the ten branches' deposits sum to, in thousands of dollars, and how many of "
        f"them have a {FLAG} beginning with 'R'?",
        (
            Answer("total_deposits_thousand_usd", "the sum over the ten branches", 0),
            Answer("corrected_branches", f"how many rows have a {FLAG} starting with R", 0),
        ),
        corrected,
    ),
    row_key=BRANCHES.row_key,
)
