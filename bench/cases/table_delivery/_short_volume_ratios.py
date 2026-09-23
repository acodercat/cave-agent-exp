"""Short sale volume ratios, asked at six sizes.

FINRA consolidated short sale volume for 2024-12-31, for the symbols whose total
volume was at least a threshold: 100 million shares (6 symbols), 10 million
(98), 5 million (208), 2 million (440) and 1 million (836). The largest scope is
every symbol (10,321).

The symbols are the trap: NA, NAN and TRUE are listed securities, and preferred
shares and warrants carry lower case and slashes. The market codes are one text
cell such as B,Q,N. The source's short volume already includes the short-exempt
volume, and the question says so; netting it out or adding it again, giving the
ratio as a percentage, or splitting the market codes into a list, produces a
different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


TRADE_DATE = "2024-12-31"


def load():
    volume = load_expansion_table("finra_short_volume")
    return volume.loc[volume["date"].eq(TRADE_DATE)]


# How the short-exempt shares enter short volume: as the file counts them, already
# inside it (0), or as a reader who takes them out (-1) or adds them again (+1).
EXEMPT_INSIDE, EXEMPT_TAKEN_OUT, EXEMPT_ADDED_AGAIN = 0, -1, 1


def build(volume, *, at_least_shares=0, exempt=EXEMPT_INSIDE):
    rows = volume.loc[volume["total_volume_shares"].ge(at_least_shares)]
    short = rows["short_volume_shares"] + exempt * rows["short_exempt_volume_shares"]
    return rows.assign(
        short_volume_shares=short,
        short_volume_ratio=short / rows["total_volume_shares"],
        exempt_share_of_short=rows["short_exempt_volume_shares"] / short,
    )[["symbol", "market_codes", "short_volume_shares", "total_volume_shares",
       "short_volume_ratio", "exempt_share_of_short"]]


TASK = TableTask(
    name="short_volume_ratios",
    title="Short sale volume ratios",
    data_sources=("finra_short_volume",),
    financial_domain="capital_markets",
    query=(
        "From FINRA's consolidated short sale volume file for 2024-12-31, report {scope}. "
        "Give the symbol exactly as listed, the market codes, short volume, total volume, "
        "short volume over total volume, and short-exempt volume over short volume. In this "
        "file short volume already includes the short-exempt shares, so neither add them nor "
        "net them out."
    ),
    output="volume_table",
    row_noun="symbol",
    key=("symbol",),
    columns=(
        Column("symbol", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("market_codes", CellKind.TEXT, "text, exactly as in the source, such as B,Q,N"),
        Column("short_volume_shares", CellKind.INTEGER, "integer, shares"),
        Column("total_volume_shares", CellKind.INTEGER, "integer, shares"),
        Column("short_volume_ratio", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals", decimals=10),
        Column("exempt_share_of_short", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals", decimals=10),
    ),
    sizes=(
        Size("10", "every symbol with a total volume of at least 100 million shares", 6,
             {"at_least_shares": 100_000_000}),
        Size("100", "every symbol with a total volume of at least 10 million shares", 98,
             {"at_least_shares": 10_000_000}),
        Size("250", "every symbol with a total volume of at least 5 million shares", 208,
             {"at_least_shares": 5_000_000}),
        Size("500", "every symbol with a total volume of at least 2 million shares", 440,
             {"at_least_shares": 2_000_000}),
        Size("1k", "every symbol with a total volume of at least 1 million shares", 836,
             {"at_least_shares": 1_000_000}),
        Size("10k", "every symbol", 10321, {}),
    ),
    load=load,
    build=build,
    near_misses={
        "ratio as a percentage": changing(short_volume_ratio=lambda ratio: ratio * 100),
        "market codes as a list": changing(market_codes=lambda codes: codes.split(",")),
    },
    misreadings={
        "short volume net of the exempt volume": partial(build, exempt=EXEMPT_TAKEN_OUT),
        "the exempt volume added to short volume again": partial(
            build, exempt=EXEMPT_ADDED_AGAIN),
    },
)
