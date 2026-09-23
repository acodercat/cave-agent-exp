"""Pension plan net income, asked at six sizes.

Form 5500 filings for form year 2023 of plans that began the year with at least
a threshold of participants: 1,000,000 (8 filings), 150,000 (109), 80,000 (263),
45,000 (531), 25,000 (1,111) and 3,000 (9,416), with net income as a fraction of
the beginning net assets.

A plan can file more than once, so a row is a filing. Filing identifiers are
thirty characters long, one employer number in sixteen begins with a zero, plan
names carry brackets and commas, and net income is signed. At the largest size
16 filings report no beginning assets, 17 no net income, and 92 have no ratio,
most because the plan began the year with none. Dividing by the ending assets,
giving a loss as a positive amount, or giving the ratio as a percentage,
produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


FORM_YEAR = 2023


def load():
    plans = load_expansion_table("dol_form5500_financials")
    return plans.loc[plans["form_year"].eq(FORM_YEAR)]


def build(plans, *, at_least_participants, base="net_assets_beginning_usd"):
    rows = plans.loc[plans["participants_beginning_count"].ge(at_least_participants)]
    return rows.assign(
        participants=rows["participants_beginning_count"],
        net_income_to_beginning_assets=(
            rows["net_income_usd"] / rows[base]
        ).where(rows["net_assets_beginning_usd"].ne(0)),
    )[["filing_id", "sponsor_ein", "plan_name", "participants", "net_assets_beginning_usd",
       "net_income_usd", "net_income_to_beginning_assets"]]


TASK = TableTask(
    name="pension_plan_returns",
    title="Pension plan net income",
    data_sources=("dol_form5500_financials",),
    financial_domain="household_housing",
    query=(
        "Among the Form 5500 plan financials for form year 2023, take the plans that began "
        "the year with at least {scope} participants and set their net income against their "
        "opening net assets. A plan may have filed more than once, so work filing by filing: "
        "the filing identifier, the sponsor's EIN, the plan name, participants at the "
        "beginning of the year, beginning net assets, net income (a loss is negative), and "
        "net income divided by beginning net assets. Leave the ratio missing where either "
        "figure is missing or the plan began with no assets."
    ),
    output="plan_table",
    row_noun="filing",
    key=("filing_id",),
    columns=(
        Column("filing_id", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("sponsor_ein", CellKind.PADDED_IDENTIFIER,
               "nine-character text, keeping leading zeros"),
        Column("plan_name", CellKind.TEXT, "text, exactly as in the source"),
        Column("participants", CellKind.INTEGER, "integer"),
        Column("net_assets_beginning_usd", CellKind.INTEGER,
               "integer, USD, missing where the filing reports none", nullable=True),
        Column("net_income_usd", CellKind.INTEGER,
               "integer, USD, negative for a loss, missing where the filing reports none",
               nullable=True),
        Column("net_income_to_beginning_assets", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals, missing where either figure is "
               "missing or the beginning net assets are zero", decimals=10, nullable=True),
    ),
    sizes=(
        Size("10", "1,000,000", 8, {"at_least_participants": 1_000_000}),
        Size("100", "150,000", 109, {"at_least_participants": 150_000}),
        Size("250", "80,000", 263, {"at_least_participants": 80_000}),
        Size("500", "45,000", 531, {"at_least_participants": 45_000}),
        Size("1k", "25,000", 1111, {"at_least_participants": 25_000}),
        Size("10k", "3,000", 9416, {"at_least_participants": 3_000}),
    ),
    load=load,
    build=build,
    near_misses={
        "ratio as a percentage": changing(
            net_income_to_beginning_assets=lambda ratio: ratio * 100),
        "losses given as positive amounts": changing(net_income_usd=abs),
    },
    misreadings={
        "net income over the ending net assets": partial(build, base="net_assets_ending_usd"),
    },
)
