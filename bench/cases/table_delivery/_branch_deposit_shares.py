"""Branch deposits and county shares, asked at six sizes.

Each branch in the scope with its deposits and its share of the deposits of all
branches in its county, from the FDIC Summary of Deposits as of 2024-06-30. The
scopes run from one county (Russell County, Alabama: 10 branches) through
Alaska (113), Delaware (249), Utah (506) and Arizona (979) to California with
Texas (11,810).

Every scope is whole counties, so a branch's county share does not depend on how
many rows the case asks for. County codes in Alabama, Alaska, Arizona and
California begin with a zero and those in Texas do not, so the largest size
holds both. Taking each share of all the delivered deposits instead of the
county's, giving it as a percentage, or giving deposits in USD instead of
thousands, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


REPORT_DATE = "2024-06-30"


def load():
    branches = load_expansion_table("fdic_sod")
    return branches.loc[branches["report_date"].eq(REPORT_DATE)]


def build(branches, *, states=(), county_fips=None):
    rows = branches.loc[
        branches["branch_county_fips"].eq(county_fips) if county_fips
        else branches["branch_state"].isin(states)
    ]
    deposits = rows["branch_deposits_thousand_usd"]
    county_total = deposits.groupby(rows["branch_county_fips"]).transform("sum")
    return rows.assign(
        county_fips=rows["branch_county_fips"],
        deposits_thousand_usd=deposits,
        county_deposit_share=deposits / county_total,
    )[["branch_id", "county_fips", "deposits_thousand_usd", "county_deposit_share"]]


def build_with_shares_of_everything(branches, **scope):
    return build(branches, **scope).assign(
        county_deposit_share=lambda rows: (
            rows["deposits_thousand_usd"] / rows["deposits_thousand_usd"].sum()
        ),
    )


TASK = TableTask(
    name="branch_deposit_shares",
    title="Branch deposits and county shares",
    data_sources=("fdic_sod",),
    financial_domain="banking_credit",
    query=(
        "Prepare a branch-level table for a local deposit-share review of {scope}, using the "
        "FDIC Summary of Deposits as of 2024-06-30. Every branch located there gets a row "
        "with its branch identifier, the FIPS code of its county, its deposits, and its "
        "share of the deposits held by all the branches in that county."
    ),
    output="branch_table",
    row_noun="branch",
    key=("branch_id",),
    columns=(
        Column("branch_id", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("county_fips", CellKind.PADDED_IDENTIFIER,
               "five-character text, keeping leading zeros"),
        Column("deposits_thousand_usd", CellKind.INTEGER, "integer, thousand USD"),
        Column("county_deposit_share", CellKind.DECIMAL,
               "decimal fraction, rounded to 10 decimals", decimals=10),
    ),
    sizes=(
        Size("10", "Russell County, Alabama (county FIPS 01113)", 10, {"county_fips": "01113"}),
        Size("100", "Alaska", 113, {"states": ("AK",)}),
        Size("250", "Delaware", 249, {"states": ("DE",)}),
        Size("500", "Utah", 506, {"states": ("UT",)}),
        Size("1k", "Arizona", 979, {"states": ("AZ",)}),
        Size("10k", "California and Texas", 11810, {"states": ("CA", "TX")}),
    ),
    load=load,
    build=build,
    near_misses={
        "share as a percentage": changing(county_deposit_share=lambda share: share * 100),
        "deposits in USD": changing(deposits_thousand_usd=lambda deposits: deposits * 1000),
    },
    misreadings={
        "share of all the deposits rather than the county's": build_with_shares_of_everything,
    },
)
