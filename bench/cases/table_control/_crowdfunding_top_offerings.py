"""The largest Regulation Crowdfunding offerings, at six volumes.

The Form C archive holds 30,074 filings made from 2019 through 2025, of which
23,092 state a maximum offering amount. Every case ranks those the same way —
maximum offering amount, highest first, ties broken by accession number — and
differs only in how many of the ranked rows the question asks for: 10, 100, 250,
500, 1,000 and 5,000. A smaller answer is the first rows of a larger one.

A filing that states no maximum is out of the ranking rather than sorted last,
and the question says so. Ranking by the stated offering amount instead of the
maximum gives a different table, and so does taking the amounts as dollars per
share of something rather than as filed.
"""

from functools import partial

import pandas as pd

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


MAXIMUM, OFFERED = "MAXIMUMOFFERINGAMOUNT", "OFFERINGAMOUNT"


def load():
    return load_expansion_table("sec_form_c")


def build(filings, *, rows, rank_by=MAXIMUM):
    stated = filings.loc[filings[rank_by].notna()]
    ranked = stated.sort_values(
        [rank_by, "ACCESSION_NUMBER"], ascending=[False, True]).head(rows)
    return pd.DataFrame({
        "accession_number": ranked["ACCESSION_NUMBER"],
        "issuer_name": ranked["NAMEOFISSUER"].astype("string"),
        "filing_date": ranked["FILING_DATE"],
        "submission_type": ranked["SUBMISSION_TYPE"].astype("string"),
        "maximum_offering_usd": ranked[MAXIMUM],
    }).reset_index(drop=True)


def _size(label: str, rows: int) -> Size:
    return Size(label, f"the top {rows:,} of that ranking", rows, {"rows": rows})


TASK = TableTask(
    name="crowdfunding_top_offerings",
    title="The largest Regulation Crowdfunding offerings",
    data_sources=("sec_form_c",),
    financial_domain="corporate_reporting",
    family="table_control",
    sizes_vary="the sizes differ only in how many of the ranked rows are asked for",
    query=(
        "From the SEC Regulation Crowdfunding (Form C) filings, take those that state a "
        "maximum offering amount and rank them by it, highest first, breaking ties by "
        "accession number in ascending order; a filing that states no maximum is left out "
        "rather than sorted last. Deliver {scope}. Each row: the accession number, the "
        "issuer's name as filed, the filing date, the submission type, and the maximum "
        "offering amount in dollars as filed."
    ),
    output="offering_table",
    row_noun="filing",
    key=("accession_number",),
    columns=(
        Column("accession_number", CellKind.IDENTIFIER, "the accession number as filed"),
        Column("issuer_name", CellKind.TEXT, "the issuer's name as filed"),
        Column("filing_date", CellKind.DATE, "the filing date as an ISO YYYY-MM-DD string"),
        Column("submission_type", CellKind.TEXT, "the submission type as filed"),
        Column("maximum_offering_usd", CellKind.DECIMAL,
               "the maximum offering amount in USD, 2 decimals", decimals=2),
    ),
    sizes=(
        _size("10", 10), _size("100", 100), _size("250", 250),
        _size("500", 500), _size("1k", 1000), _size("5k", 5000),
    ),
    load=load,
    build=build,
    near_misses={
        "amount_in_thousands": changing(maximum_offering_usd=lambda amount: amount / 1000),
    },
    misreadings={"ranked_by_stated_offering": partial(build, rank_by=OFFERED)},
)
