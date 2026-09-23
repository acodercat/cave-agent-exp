"""The most traded securities of a day by SEC market-quality metrics, at six volumes.

The MIDAS security-and-exchange file holds 7,649 securities for 2024-12-31,
3,803 stocks and 3,846 ETFs. Every case ranks all of them the same way — traded
volume, highest first, ties broken by security type and then ticker — and differs
only in how many of the ranked rows the question asks for: 10, 100, 250, 500,
1,000 and 5,000. A smaller answer is the first rows of a larger one.

Volumes are reported in thousands of shares and the question keeps them that
way, so a reader who multiplies by a thousand delivers a different table. Ranking
by trades rather than by volume does too, from 100 rows on.
"""

from functools import partial

import pandas as pd

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


TRADE_DATE = "2024-12-31"
BY_VOLUME, BY_TRADES = "trade_volume_thousands", "trades"


def load():
    metrics = load_expansion_table("sec_midas_security_exchange")
    return metrics.loc[metrics["date"].eq(TRADE_DATE)]


def build(metrics, *, rows, rank_by=BY_VOLUME):
    ranked = metrics.sort_values(
        [rank_by, "security_type", "ticker"], ascending=[False, True, True]).head(rows)
    return pd.DataFrame({
        "ticker": ranked["ticker"],
        "security_type": ranked["security_type"],
        "trades": ranked["trades"],
        "trade_volume_thousands": ranked[BY_VOLUME],
        "hidden_volume_share": ranked["hidden_volume_thousands"] / ranked[BY_VOLUME],
    }).reset_index(drop=True)


def _size(label: str, rows: int) -> Size:
    return Size(label, f"the top {rows:,} of that ranking", rows, {"rows": rows})


TASK = TableTask(
    name="market_quality_top_securities",
    title="The most traded securities of 2024-12-31",
    data_sources=("sec_midas_security_exchange",),
    financial_domain="capital_markets",
    family="table_control",
    sizes_vary="the sizes differ only in how many of the ranked rows are asked for",
    query=(
        "From the SEC MIDAS security-and-exchange metrics for 2024-12-31, rank every security "
        "by traded volume, highest first, breaking ties by security type and then by ticker, "
        "both ascending. Deliver {scope}. Each row: the ticker, the security type as given, "
        "the number of trades, the traded volume in thousands of shares exactly as the file "
        "reports it, and hidden volume over traded volume."
    ),
    output="market_quality_table",
    row_noun="security",
    key=("ticker", "security_type"),
    columns=(
        Column("ticker", CellKind.IDENTIFIER, "the ticker as the file gives it"),
        Column("security_type", CellKind.TEXT, "the security type as the file gives it"),
        Column("trades", CellKind.INTEGER, "the number of trades"),
        Column("trade_volume_thousands", CellKind.DECIMAL,
               "traded volume in thousands of shares, 3 decimals", decimals=3),
        Column("hidden_volume_share", CellKind.DECIMAL,
               "hidden volume over traded volume, 6 decimals", decimals=6),
    ),
    sizes=(
        _size("10", 10), _size("100", 100), _size("250", 250),
        _size("500", 500), _size("1k", 1000), _size("5k", 5000),
    ),
    load=load,
    build=build,
    near_misses={"volume_in_shares": changing(trade_volume_thousands=lambda volume: volume * 1000)},
    misreadings={"ranked_by_trades": partial(build, rank_by=BY_TRADES)},
)
