"""The most traded symbols of a day, delivered at six volumes.

FINRA's consolidated short sale volume file for 2024-12-31 holds 10,321 symbols.
Every case ranks all of them the same way — total volume, highest first, ties
broken by symbol — and differs only in how many of the ranked rows the question
asks for: 10, 100, 250, 500, 1,000 and 5,000. A smaller answer is the first rows
of a larger one, so what separates the cases is delivered volume alone.

The symbols are the trap that `cases/table_delivery/_short_volume_ratios.py`
documents: NA, NAN and TRUE are listed securities. The market codes are one text
cell such as B,Q,N. Short volume already includes the short-exempt shares, and
the question says so.
"""

from functools import partial

import pandas as pd

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


TRADE_DATE = "2024-12-31"
BY_TOTAL, BY_SHORT = "total_volume_shares", "short_volume_shares"


def load():
    volume = load_expansion_table("finra_short_volume")
    return volume.loc[volume["date"].eq(TRADE_DATE)]


def build(volume, *, rows, rank_by=BY_TOTAL):
    ranked = volume.sort_values([rank_by, "symbol"], ascending=[False, True]).head(rows)
    return pd.DataFrame({
        "symbol": ranked["symbol"],
        "market_codes": ranked["market_codes"],
        "short_volume": ranked["short_volume_shares"],
        "total_volume": ranked["total_volume_shares"],
        "short_share": ranked["short_volume_shares"] / ranked["total_volume_shares"],
    }).reset_index(drop=True)


def _size(label: str, rows: int) -> Size:
    return Size(label, f"the top {rows:,} of that ranking", rows, {"rows": rows})


TASK = TableTask(
    name="short_volume_top_symbols",
    title="The most traded symbols of 2024-12-31",
    data_sources=("finra_short_volume",),
    financial_domain="capital_markets",
    family="table_control",
    sizes_vary="the sizes differ only in how many of the ranked rows are asked for",
    query=(
        "From FINRA's consolidated short sale volume file for 2024-12-31, rank every symbol "
        "by total volume, highest first, breaking ties by symbol in alphabetical order. "
        "Deliver {scope}. Each row: the symbol exactly as listed, its market codes as the "
        "file gives them, in one cell, short volume, total volume, and short volume over "
        "total volume. In this file short volume already includes the short-exempt shares, "
        "so neither add them nor net them out."
    ),
    output="volume_table",
    row_noun="symbol",
    key=("symbol",),
    columns=(
        Column("symbol", CellKind.IDENTIFIER, "the symbol exactly as the file lists it"),
        Column("market_codes", CellKind.TEXT, "the market codes in one cell, as given"),
        Column("short_volume", CellKind.INTEGER, "short volume in shares"),
        Column("total_volume", CellKind.INTEGER, "total volume in shares"),
        Column("short_share", CellKind.DECIMAL, "short volume over total volume, 6 decimals",
               decimals=6),
    ),
    sizes=(
        _size("10", 10), _size("100", 100), _size("250", 250),
        _size("500", 500), _size("1k", 1000), _size("5k", 5000),
    ),
    load=load,
    build=build,
    near_misses={"share_as_percentage": changing(short_share=lambda share: share * 100)},
    misreadings={"ranked_by_short_volume": partial(build, rank_by=BY_SHORT)},
)
