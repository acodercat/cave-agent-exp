"""State house price changes, asked at six sizes.

The FHFA traditional all-transactions quarterly index for states, not seasonally
adjusted, with its change from the same quarter a year earlier. The scopes run
from ten quarters of California to every state and the District of Columbia over
the whole series from 1975Q1 (10,404 rows).

The change is computed within each state's own series, so its first four
quarters have none: 4 missing cells for one whole series and 204 for all 51. The
smaller scopes begin later and have no missing change, because the question asks
for the change computed from the full series. The quarter is text that reads as
a number. Taking the change from the previous quarter, computing it only within
the delivered window, giving it as a percentage, or writing the quarter as
2024-3, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


def load():
    hpi = load_expansion_table("fhfa_hpi")
    states = hpi.loc[
        hpi["hpi_type"].eq("traditional") & hpi["hpi_flavor"].eq("all-transactions")
        & hpi["frequency"].eq("quarterly") & hpi["level"].eq("State")
    ].sort_values(["place_id", "yr", "period"])
    return states.assign(quarter=states["yr"].astype(str) + "Q" + states["period"].astype(str))


def build(states, *, places=None, since="1975Q1", lag=4, cut_before_change=False):
    rows = states if places is None else states.loc[states["place_id"].isin(places)]
    in_window = rows["quarter"].ge(since)
    if cut_before_change:
        rows = rows.loc[in_window]
    change = rows.groupby("place_id")["index_nsa"].pct_change(lag, fill_method=None)
    rows = rows.assign(change=change)
    if not cut_before_change:
        rows = rows.loc[in_window]
    return rows.assign(state=rows["place_id"], hpi=rows["index_nsa"],
                       change_over_four_quarters=rows["change"])[
        ["state", "quarter", "hpi", "change_over_four_quarters"]]


TASK = TableTask(
    name="state_house_prices",
    title="State house price changes",
    data_sources=("fhfa_hpi",),
    financial_domain="household_housing",
    query=(
        "From the FHFA state house price index (traditional, all-transactions, quarterly, not "
        "seasonally adjusted), pull the rows for {scope}, through the latest quarter in the "
        "data, and deliver no other rows. Each row is one state and quarter: the state's "
        "postal code, the quarter written like 2024Q3, the index, and its change from the "
        "same quarter a year earlier. Work the change out on the full series before cutting "
        "it to the window, so the first quarters you deliver still have one; it is missing "
        "only where the series has no value a year earlier."
    ),
    output="index_table",
    row_noun="state and quarter",
    key=("state", "quarter"),
    columns=(
        Column("state", CellKind.IDENTIFIER, "two-letter postal code"),
        Column("quarter", CellKind.IDENTIFIER, "text such as 2024Q3"),
        Column("hpi", CellKind.DECIMAL, "index, rounded to 2 decimals", decimals=2),
        Column("change_over_four_quarters", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals, missing where the series has no "
               "value a year earlier", decimals=10, nullable=True),
    ),
    sizes=(
        Size("10", "California from 2023Q3", 10, {"places": ("CA",), "since": "2023Q3"}),
        Size("100", "California from 2001Q1", 100, {"places": ("CA",), "since": "2001Q1"}),
        Size("250", "California over its whole series", 204, {"places": ("CA",)}),
        Size("500", "California and Texas over their whole series", 408,
             {"places": ("CA", "TX")}),
        Size("1k", "California, Texas, Florida, New York and Illinois over their whole series",
             1020, {"places": ("CA", "TX", "FL", "NY", "IL")}),
        Size("10k", "every state and the District of Columbia over their whole series", 10404,
             {}),
    ),
    load=load,
    build=build,
    near_misses={
        "change as a percentage": changing(change_over_four_quarters=lambda change: change * 100),
        "quarter as year and number": changing(quarter=lambda quarter: quarter.replace("Q", "-")),
    },
    misreadings={
        "change from the previous quarter": partial(build, lag=1),
        "change computed only within the delivered window": partial(
            build, cut_before_change=True),
    },
)
