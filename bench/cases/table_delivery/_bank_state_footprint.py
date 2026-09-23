"""Bank footprints in an area, asked at six sizes.

Each bank with a branch in the scope: its branches and deposits there from the
Summary of Deposits as of 2024-06-30, against its total assets from the bank
financials of the same date. Alaska has 7 such banks, Michigan 103, Kansas 249,
Texas 476, Texas with Illinois and Missouri 1,078 and the whole country 4,548,
which is every bank in the source and so is labelled 5k.

Bank names carry ampersands, commas and full stops. One bank in the country has
branches but no financial report for the date; the question says it keeps its
row, with its assets and its ratio missing, so an inner join loses a row at the
largest size only. Names in capitals or deposits in USD also produce a different
table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


REPORT_DATE = "2024-06-30"


def load():
    branches = load_expansion_table("fdic_sod")
    financials = load_expansion_table("fdic_bankfind")
    return (
        branches.loc[branches["report_date"].eq(REPORT_DATE)],
        financials.loc[financials["REPDTE"].eq(REPORT_DATE)].set_index("CERT")["ASSET"],
    )


def build(source, *, states=None, how="left"):
    branches, assets = source
    rows = branches if states is None else branches.loc[branches["branch_state"].isin(states)]
    banks = rows.groupby("fdic_certificate", as_index=False).agg(
        bank_name=("bank_name", "first"),
        branches_in_area=("branch_id", "size"),
        deposits_in_area_thousand_usd=("branch_deposits_thousand_usd", "sum"),
    ).merge(
        assets.rename("total_assets_thousand_usd"), how=how,
        left_on="fdic_certificate", right_index=True,
    )
    return banks.assign(
        deposits_to_assets=(
            banks["deposits_in_area_thousand_usd"] / banks["total_assets_thousand_usd"]
        ),
    )


TASK = TableTask(
    name="bank_state_footprint",
    title="Bank footprints in an area",
    data_sources=("fdic_sod", "fdic_bankfind"),
    financial_domain="banking_credit",
    query=(
        "Prepare a regional bank coverage table for {scope}, comparing deposits at local "
        "branches with each bank's total assets. Use the FDIC Summary of Deposits as of "
        "2024-06-30 and the bank financials for the same date. One row per bank with at "
        "least one branch "
        "there: FDIC certificate number, the bank's name as the Summary of Deposits spells "
        "it, the number of its branches in the area and their combined deposits, its total "
        "assets, and those deposits divided by total assets. If a bank has no financial "
        "report for that date, keep the row and leave its assets and the ratio missing."
    ),
    output="bank_table",
    row_noun="bank",
    key=("fdic_certificate",),
    columns=(
        Column("fdic_certificate", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("bank_name", CellKind.TEXT, "text, exactly as in the Summary of Deposits"),
        Column("branches_in_area", CellKind.INTEGER, "integer"),
        Column("deposits_in_area_thousand_usd", CellKind.INTEGER, "integer, thousand USD"),
        Column("total_assets_thousand_usd", CellKind.INTEGER,
               "integer, thousand USD, missing where the bank has no financial report",
               nullable=True),
        Column("deposits_to_assets", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals, missing where total assets are",
               decimals=10, nullable=True),
    ),
    sizes=(
        Size("10", "Alaska", 7, {"states": ("AK",)}),
        Size("100", "Michigan", 103, {"states": ("MI",)}),
        Size("250", "Kansas", 249, {"states": ("KS",)}),
        Size("500", "Texas", 476, {"states": ("TX",)}),
        Size("1k", "Texas, Illinois and Missouri", 1078, {"states": ("TX", "IL", "MO")}),
        Size("5k", "the United States and its territories", 4548, {}),
    ),
    load=load,
    build=build,
    near_misses={
        "names in capitals": changing(bank_name=str.upper),
        "deposits in USD": changing(
            deposits_in_area_thousand_usd=lambda deposits: deposits * 1000),
    },
    misreadings={
        "banks without a financial report dropped by the join": partial(build, how="inner"),
    },
)
