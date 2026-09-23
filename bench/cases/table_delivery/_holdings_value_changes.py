"""13F holdings value changes, asked at six sizes.

The securities whose total 13F reported value moved most, in absolute terms,
between the report periods 2025-06-30 and 2025-09-30, among the 29,469 CUSIPs
reported in both. None of the six cut-offs (10 to 10,000) falls on a tie.

Values reach the trillions of dollars, about one CUSIP in eight begins with a
zero (3 of the top 10, 1,237 of the top 10,000), and 26 of the top 10,000 had an
earlier value of zero, which leaves their relative change missing. Ranking by
the signed change, dividing by the later value, reversing the sign of the
change, or giving the relative change as a percentage, produces a different
table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


EARLIER, LATER = "2025-06-30", "2025-09-30"


def load():
    holdings = load_expansion_table("sec_13f_holdings")
    periods = {
        period: holdings.loc[holdings["period_of_report"].eq(period)].set_index("cusip")
        for period in (EARLIER, LATER)
    }
    both = periods[EARLIER][["value_usd_total"]].join(
        periods[LATER][["value_usd_total", "issuer_name"]],
        how="inner", lsuffix="_earlier", rsuffix="_later",
    )
    return both.reset_index()


def build(both, *, top, rank=abs, relative_to="value_usd_total_earlier"):
    earlier, later = both["value_usd_total_earlier"], both["value_usd_total_later"]
    change = later - earlier
    rows = both.assign(
        value_q2_usd=earlier, value_q3_usd=later, value_change_usd=change,
        relative_change=(change / both[relative_to]).where(earlier.ne(0)),
    )
    rows = rows.loc[rank(change).sort_values(ascending=False).index[:top]]
    return rows[["cusip", "issuer_name", "value_q2_usd", "value_q3_usd", "value_change_usd",
                 "relative_change"]]


TASK = TableTask(
    name="holdings_value_changes",
    title="13F holdings value changes",
    data_sources=("sec_13f_holdings",),
    financial_domain="investment_funds",
    query=(
        "Between the 2025-06-30 and 2025-09-30 report periods, which securities saw the "
        "largest swing in total 13F reported value? Use the holdings aggregated by CUSIP, "
        "keep only securities reported in both periods, and deliver the top {scope} by "
        "absolute change. Each row: the CUSIP, the issuer name as reported for 2025-09-30, "
        "the value in each period, the change (later minus earlier), and the change relative "
        "to the earlier value, left missing where the earlier value is zero."
    ),
    output="security_table",
    row_noun="security",
    key=("cusip",),
    columns=(
        Column("cusip", CellKind.PADDED_IDENTIFIER, "nine-character text, keeping leading zeros"),
        Column("issuer_name", CellKind.TEXT, "text, exactly as reported for 2025-09-30"),
        Column("value_q2_usd", CellKind.INTEGER, "integer, USD, 2025-06-30"),
        Column("value_q3_usd", CellKind.INTEGER, "integer, USD, 2025-09-30"),
        Column("value_change_usd", CellKind.INTEGER,
               "integer, the later value minus the earlier value"),
        Column("relative_change", CellKind.DECIMAL,
               "the change as a decimal fraction of the earlier value, rounded to 10 decimals, "
               "missing where the earlier value is zero", decimals=10, nullable=True),
    ),
    sizes=tuple(
        Size(label, f"{top:,}", top, {"top": top})
        for label, top in (("10", 10), ("100", 100), ("250", 250), ("500", 500),
                           ("1k", 1000), ("10k", 10000))
    ),
    load=load,
    build=build,
    near_misses={
        "change with its sign reversed": changing(value_change_usd=lambda change: -change),
        "relative change as a percentage": changing(relative_change=lambda change: change * 100),
    },
    misreadings={
        "the largest increases rather than the largest moves": partial(build, rank=lambda c: c),
        "change relative to the later value": partial(
            build, relative_to="value_usd_total_later"),
    },
)
