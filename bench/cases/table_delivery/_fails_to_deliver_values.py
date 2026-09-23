"""Fails to deliver by value, asked at six sizes.

Fails to deliver on the settlement date 2024-12-31, valued at the reported
price, for the securities whose fails were worth at least a threshold: 20
million USD (7 securities), 2 million (153), 1 million (305), 500,000 (555) and
200,000 (1,013). The largest scope is every security with fails on the date
(5,535), which is all the source holds and so is labelled 5k.

One CUSIP in eight begins with a zero and some contain letters. 64 securities
have no reported price and so no value; they cannot meet a threshold, and appear
at the largest size only, where they keep their rows. Dropping them, or giving
the value in thousands, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


SETTLEMENT_DATE = "2024-12-31"


def load():
    fails = load_expansion_table("sec_ftd")
    return fails.loc[fails["settlement_date"].eq(SETTLEMENT_DATE)]


def build(fails, *, at_least_usd=None):
    value = fails["quantity_fails"] * fails["price"]
    rows = fails.assign(fails_value_usd=value)
    if at_least_usd is not None:
        rows = rows.loc[value.ge(at_least_usd).fillna(False)]
    return rows[["cusip", "symbol", "description", "quantity_fails", "price", "fails_value_usd"]]


TASK = TableTask(
    name="fails_to_deliver_values",
    title="Fails to deliver by value",
    data_sources=("sec_ftd",),
    financial_domain="capital_markets",
    query=(
        "Value the fails to deliver for the settlement date 2024-12-31 from the SEC "
        "fails-to-deliver file, and report {scope}. For each one: CUSIP, symbol, "
        "description, quantity of fails, price, and the dollar value of the fails, taken as "
        "quantity times price. Where the file states no price, leave both price and "
        "estimated value missing rather than guessing. A security with no price cannot clear "
        "a value threshold, so it belongs in the table only where no threshold is asked for."
    ),
    output="fails_table",
    row_noun="security",
    key=("cusip",),
    columns=(
        Column("cusip", CellKind.PADDED_IDENTIFIER, "nine-character text, keeping leading zeros"),
        Column("symbol", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("description", CellKind.TEXT, "text, exactly as in the source"),
        Column("quantity_fails", CellKind.INTEGER, "integer, shares"),
        Column("price", CellKind.DECIMAL,
               "USD, rounded to 2 decimals, missing where the source reports none",
               decimals=2, nullable=True),
        Column("fails_value_usd", CellKind.DECIMAL,
               "USD, rounded to 2 decimals, missing where the price is", decimals=2,
               nullable=True),
    ),
    sizes=(
        Size("10", "every security whose fails were worth at least 20 million USD", 7,
             {"at_least_usd": 20_000_000}),
        Size("100", "every security whose fails were worth at least 2 million USD", 153,
             {"at_least_usd": 2_000_000}),
        Size("250", "every security whose fails were worth at least 1 million USD", 305,
             {"at_least_usd": 1_000_000}),
        Size("500", "every security whose fails were worth at least 500,000 USD", 555,
             {"at_least_usd": 500_000}),
        Size("1k", "every security whose fails were worth at least 200,000 USD", 1013,
             {"at_least_usd": 200_000}),
        Size("5k", "every security with fails on that date", 5535, {}),
    ),
    load=load,
    build=build,
    near_misses={
        "fails without a price left out": lambda rows: [
            row for row in rows if row["price"] is not None
        ],
        "value in thousands of USD": changing(fails_value_usd=lambda value: value / 1000),
    },
)
