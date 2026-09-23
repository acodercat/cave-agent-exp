"""SBA lending by state and industry, asked at six sizes.

SBA 7(a) loans approved in fiscal 2024, grouped by project state and NAICS
code: the loans, the gross approval, the guaranteed share and the average
initial interest rate weighted by gross approval. Guam has 9 such groups, West
Virginia 102, Connecticut 248, Texas 516, Texas with New York 1,049 and the
whole country 12,994.

The source has no loan identifier, which is why the task groups. One loan states
no rate and carries no weight in its group's average; every group has a loan
that does. Industry descriptions are long free text with commas and brackets.
Taking a plain average of the rates, keeping the loan without a rate in the
weights, giving the guaranteed share as a percentage, or putting the descriptions
in capitals, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


FISCAL_YEAR = 2024


def load():
    loans = load_expansion_table("sba_7a")
    return loans.loc[loans["ApprovalFY"].eq(FISCAL_YEAR)]


def build(loans, *, states=None, weighted=True, unstated_rates_count=False):
    rows = loans if states is None else loans.loc[loans["ProjectState"].isin(states)]
    # A loan that states no rate carries no weight in its group's average.
    stated = rows["InitialInterestRate"].notna() | unstated_rates_count
    weight = (rows["GrossApproval"] if weighted else 1.0) * stated
    groups = rows.assign(
        weight=weight, weighted_rate=rows["InitialInterestRate"].fillna(0) * weight,
    ).groupby(["ProjectState", "NaicsCode"], as_index=False).agg(
        naics_description=("NaicsDescription", "first"),
        loans=("GrossApproval", "size"),
        gross_approval_usd=("GrossApproval", "sum"),
        guaranteed=("SBAGuaranteedApproval", "sum"),
        weight=("weight", "sum"),
        weighted_rate=("weighted_rate", "sum"),
    )
    return groups.assign(
        project_state=groups["ProjectState"], naics_code=groups["NaicsCode"],
        guaranteed_share=groups["guaranteed"] / groups["gross_approval_usd"],
        average_interest_rate_pct=groups["weighted_rate"] / groups["weight"],
    )[["project_state", "naics_code", "naics_description", "loans", "gross_approval_usd",
       "guaranteed_share", "average_interest_rate_pct"]]


TASK = TableTask(
    name="sba_industry_lending",
    title="SBA lending by state and industry",
    data_sources=("sba_7a",),
    financial_domain="banking_credit",
    query=(
        "Summarise the SBA 7(a) lending approved in fiscal year 2024 for projects in "
        "{scope}, by project state and NAICS industry. For every state-industry pair with at "
        "least one loan, report the state, the NAICS code with its description, the number "
        "of loans, total gross approval, the share of that total guaranteed by the SBA, and "
        "the average initial interest rate weighted by gross approval, leaving a loan that "
        "states no rate out of both the weighted sum and its total weight."
    ),
    output="lending_table",
    row_noun="state and industry",
    key=("project_state", "naics_code"),
    columns=(
        Column("project_state", CellKind.IDENTIFIER, "two-letter postal code"),
        Column("naics_code", CellKind.IDENTIFIER, "six-digit text, exactly as in the source"),
        Column("naics_description", CellKind.TEXT, "text, exactly as in the source"),
        Column("loans", CellKind.INTEGER, "integer"),
        Column("gross_approval_usd", CellKind.DECIMAL, "USD, rounded to 2 decimals", decimals=2),
        Column("guaranteed_share", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals", decimals=10),
        Column("average_interest_rate_pct", CellKind.DECIMAL,
               "percent, rounded to 6 decimals", decimals=6),
    ),
    sizes=(
        Size("10", "Guam", 9, {"states": ("GU",)}),
        Size("100", "West Virginia", 102, {"states": ("WV",)}),
        Size("250", "Connecticut", 248, {"states": ("CT",)}),
        Size("500", "Texas", 516, {"states": ("TX",)}),
        Size("1k", "Texas and New York", 1049, {"states": ("TX", "NY")}),
        Size("10k", "the United States and its territories", 12994, {}),
    ),
    load=load,
    build=build,
    near_misses={
        "guaranteed share as a percentage": changing(guaranteed_share=lambda share: share * 100),
        "descriptions in capitals": changing(naics_description=str.upper),
    },
    misreadings={
        "a plain average of the interest rates": partial(build, weighted=False),
        "loans without a stated rate kept in the weights": partial(
            build, unstated_rates_count=True),
    },
)
