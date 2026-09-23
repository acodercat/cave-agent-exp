"""Market growth and drawdown, asked at six sizes.

The market's daily total return, the growth of a dollar and the drawdown from
the running peak, from the Fama-French daily factors over a window that ends on
2024-12-31 and begins between 2024-12-16 (11 trading days) and 1985-01-01
(10,080).

Each row depends on every row before it; returns carry signs, and the drawdown
sits at or just below zero for much of a window. The drawdown is asked to fewer
decimals than the growth it is derived from, so that computing it from the
rounded growth, which a pilot run did, gives the same cell. Leaving out the risk-free rate,
starting the growth after the first day, giving the drawdown as a positive
depth, or giving the return as a decimal fraction, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_ken_french_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


END = "2024-12-31"


def load():
    return load_ken_french_table("daily_factors")


def build(factors, *, start, add_risk_free=True):
    rows = factors.loc[factors["date"].between(start, END)].sort_values("date")
    market_return = rows["mkt_rf_pct"] + (rows["rf_pct"] if add_risk_free else 0)
    growth = (1 + market_return / 100).cumprod()
    return rows.assign(
        market_return_pct=market_return,
        growth_of_dollar=growth,
        drawdown=growth / growth.cummax() - 1,
    )[["date", "market_return_pct", "growth_of_dollar", "drawdown"]]


TASK = TableTask(
    name="market_growth_drawdown",
    title="Market growth and drawdown",
    data_sources=("ken_french_daily_factors",),
    financial_domain="capital_markets",
    query=(
        "Build the series behind a growth-of-a-dollar chart for the US market from {scope} "
        "through 2024-12-31, out of the Fama-French daily factors. For every trading day "
        "give the market's total return in percent (the excess return plus the risk-free "
        "rate), the value of the dollar at that day's close with the first day's return "
        "already in it, and the drawdown from the highest close so far in the window."
    ),
    output="daily_table",
    row_noun="trading day",
    key=("date",),
    columns=(
        Column("date", CellKind.DATE, "text, ISO YYYY-MM-DD"),
        Column("market_return_pct", CellKind.DECIMAL,
               "percent, rounded to 4 decimals", decimals=4),
        Column("growth_of_dollar", CellKind.DECIMAL,
               "value of the dollar at the day's close, the first day's return included, "
               "rounded to 8 decimals", decimals=8),
        Column("drawdown", CellKind.DECIMAL,
               "growth divided by its running peak, minus one: a decimal fraction at or below "
               "zero, rounded to 6 decimals", decimals=6),
    ),
    sizes=(
        Size("10", "2024-12-16", 11, {"start": "2024-12-16"}),
        Size("100", "2024-08-08", 101, {"start": "2024-08-08"}),
        Size("250", "2024-01-01", 252, {"start": "2024-01-01"}),
        Size("500", "2023-01-01", 502, {"start": "2023-01-01"}),
        Size("1k", "2021-01-01", 1005, {"start": "2021-01-01"}),
        Size("10k", "1985-01-01", 10080, {"start": "1985-01-01"}),
    ),
    load=load,
    build=build,
    near_misses={
        "drawdown as a positive depth": changing(drawdown=lambda drawdown: -drawdown),
        "return as a decimal fraction": changing(market_return_pct=lambda pct: pct / 100),
        "growth that leaves out the first day": lambda rows: [
            row | {"growth_of_dollar": round(
                row["growth_of_dollar"] / rows[0]["growth_of_dollar"], 8)}
            for row in rows
        ],
    },
    misreadings={
        "the excess return without the risk-free rate": partial(build, add_risk_free=False),
    },
)
