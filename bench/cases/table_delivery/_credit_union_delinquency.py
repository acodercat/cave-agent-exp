"""Credit union delinquency, asked at six sizes.

Each credit union in the scope from the NCUA call reports dated 2024-12-31: its
loans, its loans two or more months delinquent, and their ratio. Alaska has 9,
Virginia 98, California 251, Texas with Wisconsin 503, Texas with Pennsylvania
and New York 970, and the whole country 4,550, which is every credit union in
the source and so is labelled 5k.

Ten credit unions in the country hold no loans, which leaves their ratio
missing, not zero. Names carry apostrophes, ampersands and hyphens. Giving the
ratio as a percentage, a missing ratio as zero, or the names in title case,
produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


REPORT_DATE = "2024-12-31"


def load():
    reports = load_expansion_table("ncua_call_reports")
    return reports.loc[reports["report_date"].eq(REPORT_DATE)]


def build(reports, *, states=None):
    rows = reports if states is None else reports.loc[reports["state"].isin(states)]
    loans = rows["total_loans_and_leases_usd"]
    delinquent = rows["delinquent_loans_two_plus_months_usd"]
    return rows.assign(
        loans_usd=loans, delinquent_loans_usd=delinquent,
        delinquency_ratio=(delinquent / loans).where(loans.ne(0)),
    )[["credit_union_number", "credit_union_name", "loans_usd", "delinquent_loans_usd",
       "delinquency_ratio"]]


TASK = TableTask(
    name="credit_union_delinquency",
    title="Credit union delinquency",
    data_sources=("ncua_call_reports",),
    financial_domain="banking_credit",
    query=(
        "How delinquent are the loan books of the credit unions in {scope}? From the NCUA "
        "call reports dated 2024-12-31, list every credit union there with its charter "
        "number, its name, total loans and leases, loans two or more months delinquent, and "
        "the delinquent amount as a fraction of total loans. A credit union with no loans "
        "has no ratio; leave it missing."
    ),
    output="credit_union_table",
    row_noun="credit union",
    key=("credit_union_number",),
    columns=(
        Column("credit_union_number", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("credit_union_name", CellKind.TEXT, "text, exactly as in the source"),
        Column("loans_usd", CellKind.INTEGER, "integer, USD"),
        Column("delinquent_loans_usd", CellKind.INTEGER, "integer, USD"),
        Column("delinquency_ratio", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals, missing where total loans are zero",
               decimals=10, nullable=True),
    ),
    sizes=(
        Size("10", "Alaska", 9, {"states": ("AK",)}),
        Size("100", "Virginia", 98, {"states": ("VA",)}),
        Size("250", "California", 251, {"states": ("CA",)}),
        Size("500", "Texas and Wisconsin", 503, {"states": ("TX", "WI")}),
        Size("1k", "Texas, Pennsylvania and New York", 970, {"states": ("TX", "PA", "NY")}),
        Size("5k", "the United States and its territories", 4550, {}),
    ),
    load=load,
    build=build,
    near_misses={
        "ratio as a percentage": changing(delinquency_ratio=lambda ratio: ratio * 100),
        "names in title case": changing(credit_union_name=str.title),
        "a missing ratio given as zero": lambda rows: [
            row | {"delinquency_ratio": row["delinquency_ratio"] or 0.0} for row in rows
        ],
    },
)
