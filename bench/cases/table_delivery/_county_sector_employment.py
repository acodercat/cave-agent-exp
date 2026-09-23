"""County employment by sector, asked at six sizes.

Private employment by county and NAICS sector from the 2024 QCEW annual
averages, each sector set against its county's private total, which is another
row of the same table. The unknown-or-undefined areas whose code ends in 999 are
left out, and the question says so.

BLS withholds some figures: the source marks those rows with disclosure code N
and carries zeros in them, and a withheld figure is missing, not zero. That is 2
of the District of Columbia's 19 rows, 11 of Rhode Island's 99, 398 of Montana's
1,033 and 4,173 of the 12,461 in the largest scope. Sector codes such as 31-33
and 44-45 are text that reads as arithmetic or a date. Delivering the source's
zeros, taking the county total as the sum of the sector rows (which leaves the
suppressed sectors out of it), cutting a sector range to its first code, or
giving the share as a percentage, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


YEAR = 2024


def load():
    qcew = load_expansion_table("bls_qcew")
    qcew = qcew.loc[qcew["year"].eq(YEAR) & ~qcew["area_fips"].str.endswith("999")]
    sectors = qcew.loc[qcew["aggregation_level"].eq("county_naics_sector")]
    totals = qcew.loc[
        qcew["aggregation_level"].eq("county_by_ownership")
        & qcew["ownership_scope"].eq("private")
    ]
    return sectors, totals


def build(source, *, states, withheld_as_zero=False, total_from_sectors=False):
    sectors, totals = source
    rows = sectors.loc[sectors["state_fips"].isin(states)]
    disclosed = rows["disclosure_code"].ne("N").fillna(True) | withheld_as_zero
    if total_from_sectors:
        county_total = rows.groupby("area_fips")["annual_avg_employment"].sum()
    else:
        county_total = totals.set_index("area_fips")["annual_avg_employment"].where(
            totals.set_index("area_fips")["disclosure_code"].ne("N").fillna(True)
        )
    employment = rows["annual_avg_employment"].where(disclosed)
    return rows.assign(
        establishments=rows["annual_avg_establishments"],
        employment=employment,
        average_annual_pay_usd=rows["average_annual_pay_usd"].where(disclosed),
        employment_share=employment / rows["area_fips"].map(county_total),
    )[["area_fips", "industry_code", "establishments", "employment", "average_annual_pay_usd",
       "employment_share"]]


TASK = TableTask(
    name="county_sector_employment",
    title="County employment by sector",
    data_sources=("bls_qcew",),
    financial_domain="macro_rates_fx_trade",
    query=(
        "Break down private employment in {scope} by county and NAICS sector, from the 2024 "
        "QCEW annual averages. Skip the unknown-or-undefined areas, whose codes end in 999. "
        "Each county-sector row should carry the county code, the sector code, "
        "establishments, average employment, average annual pay, and the sector's share of "
        "all private employment in its county. Take that county total from the county's own "
        "private-ownership row, not from a sum of the sector rows, which leaves the "
        "suppressed sectors out. BLS suppresses some cells, and the file shows zeros there "
        "under disclosure code N; those are not zeros, so leave employment, pay and the share "
        "missing for them, and leave the share missing too where the county total is "
        "suppressed."
    ),
    output="sector_table",
    row_noun="county and sector",
    key=("area_fips", "industry_code"),
    columns=(
        Column("area_fips", CellKind.PADDED_IDENTIFIER, "five-character county code"),
        Column("industry_code", CellKind.IDENTIFIER,
               "NAICS sector code as text, exactly as in the source, for example 31-33"),
        Column("establishments", CellKind.INTEGER, "integer"),
        Column("employment", CellKind.INTEGER,
               "integer, missing where withheld", nullable=True),
        Column("average_annual_pay_usd", CellKind.INTEGER,
               "integer, USD, missing where withheld", nullable=True),
        Column("employment_share", CellKind.DECIMAL,
               "employment as a decimal fraction of the county's total private employment, "
               "rounded to 10 decimals, missing where either figure is withheld",
               decimals=10, nullable=True),
    ),
    sizes=(
        Size("10", "the District of Columbia", 19, {"states": ("11",)}),
        Size("100", "Rhode Island", 99, {"states": ("44",)}),
        Size("250", "Massachusetts", 278, {"states": ("25",)}),
        Size("500", "Maryland", 468, {"states": ("24",)}),
        Size("1k", "Montana", 1033, {"states": ("30",)}),
        Size("10k", "Texas, Georgia, Virginia and Kentucky", 12461,
             {"states": ("48", "13", "51", "21")}),
    ),
    load=load,
    build=build,
    near_misses={
        "share as a percentage": changing(employment_share=lambda share: share * 100),
        "a sector range cut to its first code": changing(
            industry_code=lambda code: code.split("-")[0]),
    },
    misreadings={
        "withheld figures delivered as the zeros the source carries": partial(
            build, withheld_as_zero=True),
        "the county total taken as the sum of its sector rows": partial(
            build, total_from_sectors=True),
    },
)
