"""Treasury securities outstanding, asked at six sizes.

Marketable Treasury securities at month-end from the Monthly Statement of the
Public Debt: each security's issued and outstanding amounts and its share of
its class. On 2024-12-31 there are 8 floating rate notes, 102 bonds, 243 notes
and 456 securities in all; two month-ends hold 908 rows and the 22 from
2023-03-31 hold 9,826.

The source lists a security once per issue and reopening and states the amount
outstanding on exactly one of those lines, so a security is an aggregation of
its lines; the subtotal and total lines are left out, and the question says so.
Bills and floating rate notes state no interest rate; their yield column holds a
discount yield or, for a floating rate note, the spread, and taking it as the
rate is a misreading the question rules out. Amounts are in millions
with four decimals. Taking the share of everything outstanding rather than of
the class, giving amounts in USD, or giving the share as a percentage, produces
a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


END = "2024-12-31"


def load():
    lines = load_expansion_table("treasury_marketable_securities")
    cusip = lines["security_identifier_or_total_label"]
    # The rest of the table is subtotal and total lines.
    return lines.loc[cusip.str.fullmatch(r"[0-9A-Z]{9}", na=False) & lines["record_date"].le(END)]


def build(lines, *, since=END, classes=None, share_of="class", rate_from_yield=False):
    rows = lines.loc[lines["record_date"].ge(since)]
    if classes is not None:
        rows = rows.loc[rows["security_class"].isin(classes)]
    if rate_from_yield:
        rows = rows.assign(interest_rate_pct=rows["interest_rate_pct"].fillna(rows["yield_pct"]))
    securities = rows.groupby(
        ["record_date", "security_identifier_or_total_label"], as_index=False,
    ).agg(
        security_class=("security_class", "first"),
        maturity_date=("maturity_date", "first"),
        interest_rate_pct=("interest_rate_pct", "first"),
        issues=("issued_million_usd", "size"),
        issued_million_usd=("issued_million_usd", "sum"),
        outstanding_million_usd=("outstanding_million_usd", "sum"),
    )
    total_by = ["record_date", "security_class"] if share_of == "class" else ["record_date"]
    total = securities.groupby(total_by)["outstanding_million_usd"].transform("sum")
    return securities.assign(
        cusip=securities["security_identifier_or_total_label"],
        share_of_class_outstanding=securities["outstanding_million_usd"] / total,
    )[["record_date", "cusip", "security_class", "maturity_date", "interest_rate_pct", "issues",
       "issued_million_usd", "outstanding_million_usd", "share_of_class_outstanding"]]


TASK = TableTask(
    name="treasury_securities_outstanding",
    title="Treasury securities outstanding",
    data_sources=("treasury_marketable_securities",),
    financial_domain="public_finance",
    query=(
        "Reconstruct from the Monthly Statement of the Public Debt detail of marketable "
        "securities what was outstanding, security by security, for {scope}, and deliver no "
        "other securities. The statement prints one line per issue and reopening and states "
        "the amount outstanding on only one of them, so roll the lines up to the CUSIP "
        "within each record date, and ignore the subtotal and total lines. Per record date "
        "and CUSIP: the security class, the maturity date, the interest rate, the number of "
        "lines rolled up, the amount issued, the amount outstanding, and that outstanding "
        "amount as a share of all the delivered securities of the same class on that record "
        "date. Use the source's stated interest-rate field, leaving it missing where "
        "unstated; do not substitute the yield field, including the discount yield of a "
        "bill or the spread of a floating rate note."
    ),
    output="security_table",
    row_noun="record date and security",
    key=("record_date", "cusip"),
    columns=(
        Column("record_date", CellKind.DATE, "text, ISO YYYY-MM-DD"),
        Column("cusip", CellKind.IDENTIFIER, "nine-character text"),
        Column("security_class", CellKind.TEXT, "text, exactly as in the source"),
        Column("maturity_date", CellKind.DATE, "text, ISO YYYY-MM-DD"),
        Column("interest_rate_pct", CellKind.DECIMAL,
               "percent, rounded to 3 decimals, missing where the source states none",
               decimals=3, nullable=True),
        Column("issues", CellKind.INTEGER, "integer, the security's lines on that record date"),
        Column("issued_million_usd", CellKind.DECIMAL,
               "million USD, rounded to 4 decimals", decimals=4),
        Column("outstanding_million_usd", CellKind.DECIMAL,
               "million USD, rounded to 4 decimals", decimals=4),
        Column("share_of_class_outstanding", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals", decimals=10),
    ),
    sizes=(
        Size("10", "the floating rate notes on 2024-12-31", 8,
             {"classes": ("Floating Rate Notes",)}),
        Size("100", "the bonds on 2024-12-31", 102, {"classes": ("Bonds",)}),
        Size("250", "the notes on 2024-12-31", 243, {"classes": ("Notes",)}),
        Size("500", "every security on 2024-12-31", 456, {}),
        Size("1k", "every security on 2024-11-30 and 2024-12-31", 908, {"since": "2024-11-30"}),
        Size("10k", "every security on each month-end from 2023-03-31 through 2024-12-31", 9826,
             {"since": "2023-03-31"}),
    ),
    load=load,
    build=build,
    near_misses={
        "amounts in USD": changing(
            issued_million_usd=lambda amount: amount * 1_000_000,
            outstanding_million_usd=lambda amount: amount * 1_000_000),
        "share as a percentage": changing(share_of_class_outstanding=lambda share: share * 100),
    },
    misreadings={
        "share of everything outstanding rather than of the class": partial(
            build, share_of="everything"),
        "the yield or spread taken as the rate of a bill or floating rate note": partial(
            build, rate_from_yield=True),
    },
)
