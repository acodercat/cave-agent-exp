"""The largest bank branches by deposits, at six volumes.

The Summary of Deposits as of 2024-06-30 holds 76,727 branches. Every case ranks
all of them the same way — branch deposits, highest first, ties broken by branch
identifier — and differs only in how many of the ranked rows the question asks
for: 10, 100, 250, 500, 1,000 and 5,000. A smaller answer is the first rows of a
larger one.

Deposits are reported in thousands of dollars and the question keeps them that
way. The main-office indicator is a zero-padded flag the source writes as text,
so a channel that reads it as a number loses it.
"""

from functools import partial

import pandas as pd

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


REPORT_DATE = "2024-06-30"
DEPOSITS = "branch_deposits_thousand_usd"


def load():
    branches = load_expansion_table("fdic_sod")
    return branches.loc[branches["report_date"].eq(REPORT_DATE)]


def build(branches, *, rows, main_offices_only=False):
    scoped = branches.loc[branches["main_office_indicator"].eq("1")] if main_offices_only \
        else branches
    ranked = scoped.sort_values([DEPOSITS, "branch_id"], ascending=[False, True]).head(rows)
    return pd.DataFrame({
        "branch_id": ranked["branch_id"],
        "bank_name": ranked["bank_name"].astype("string"),
        "branch_state": ranked["branch_state"].astype("string"),
        "main_office_indicator": ranked["main_office_indicator"].astype("string"),
        "branch_deposits_thousand_usd": ranked[DEPOSITS],
    }).reset_index(drop=True)


def _size(label: str, rows: int) -> Size:
    return Size(label, f"the top {rows:,} of that ranking", rows, {"rows": rows})


TASK = TableTask(
    name="branch_top_deposits",
    title="The largest bank branches by deposits",
    data_sources=("fdic_sod",),
    financial_domain="banking_credit",
    family="table_control",
    sizes_vary="the sizes differ only in how many of the ranked rows are asked for",
    query=(
        "From the FDIC Summary of Deposits as of 2024-06-30, rank every branch by its "
        "deposits, highest first, breaking ties by branch identifier in ascending order. "
        "Deliver {scope}. Each row: the branch identifier, the bank's name as the Summary of "
        "Deposits spells it, the branch's state, its main-office indicator exactly as the "
        "source writes it, and its deposits in thousands of dollars as reported."
    ),
    output="branch_table",
    row_noun="branch",
    key=("branch_id",),
    columns=(
        Column("branch_id", CellKind.IDENTIFIER, "the branch identifier as given"),
        Column("bank_name", CellKind.TEXT, "the bank's name as the source spells it"),
        Column("branch_state", CellKind.TEXT, "the branch's state, two letters"),
        Column("main_office_indicator", CellKind.PADDED_IDENTIFIER,
               "the main-office flag exactly as the source writes it"),
        Column("branch_deposits_thousand_usd", CellKind.INTEGER,
               "branch deposits in thousands of dollars"),
    ),
    sizes=(
        _size("10", 10), _size("100", 100), _size("250", 250),
        _size("500", 500), _size("1k", 1000), _size("5k", 5000),
    ),
    load=load,
    build=build,
    near_misses={
        "deposits_in_dollars": changing(
            branch_deposits_thousand_usd=lambda deposits: deposits * 1000),
    },
    misreadings={"main_offices_only": partial(build, main_offices_only=True)},
)
