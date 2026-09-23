"""A control: the pipeline study's ten-row table of plain types, expected intact in every arm."""

from __future__ import annotations

import pandas as pd

from cases.fidelity._sources import branches_on
from cases.table_control._branch_top_deposits import REPORT_DATE, TASK as BRANCH_TASK, build as rank
from core.fidelity import TEXT_COLUMNS, Degradation, ObjectKind, ObjectTask
from core.pipeline import Answer, FollowUp

ROWS = 10


def build(tables) -> pd.DataFrame:
    return rank(branches_on(tables, REPORT_DATE), rows=ROWS)


def total_deposits(table: pd.DataFrame) -> tuple:
    return (int(table["branch_deposits_thousand_usd"].sum()),)


TASK = ObjectTask(
    name="control_small_table",
    title=BRANCH_TASK.title,
    group="control",
    kind=ObjectKind.TABLE,
    data_sources=BRANCH_TASK.data_sources,
    ask=(
        BRANCH_TASK.query.format(scope=BRANCH_TASK.size("10").scope)
        + " Build it as a DataFrame with exactly the columns branch_id (as text), bank_name "
        "(as text), branch_state (as text), main_office_indicator (as text) and "
        "branch_deposits_thousand_usd (an integer column)."
        + " " + TEXT_COLUMNS
    ),
    output=BRANCH_TASK.output,
    describe=(
        "A DataFrame of the ten largest branches by deposits with columns branch_id, "
        "bank_name, branch_state and main_office_indicator (text) and "
        "branch_deposits_thousand_usd (an integer column)."
    ),
    build=build,
    follow_up=FollowUp(
        "What do the ten branches' deposits sum to, in thousands of dollars?",
        (Answer("total_deposits_thousand_usd", "the sum, a whole number", 0),),
        total_deposits,
    ),
    row_key="branch_id",
    degradations={
        "a row dropped": Degradation(lambda t: t.iloc[:-1], "rows"),
    },
)
