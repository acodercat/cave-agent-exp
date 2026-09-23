"""Effective exchange rates, asked at six sizes.

The BIS broad nominal and real effective exchange rate indices side by side, by
economy and month, with the real index divided by the nominal. The source holds
one row per type of index, so the answer is a reshape from long to wide. The
scopes run from ten months of the United States to all 64 economies from
2019-01 (5,376 rows), which is all the source holds and so is labelled 5k.

The source labels an economy "US: United States", and the answer separates the
code from the name; the month is text that reads as a date; and one name,
Türkiye, is not ASCII. Dividing the nominal index by the real, giving the month
as a full date, or reducing names to ASCII, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


LARGE_ECONOMIES = ("US", "XM", "JP", "GB", "CA", "AU", "CH", "CN", "IN", "BR", "MX", "KR")


def load():
    rates = load_expansion_table("bis_effective_exchange_rates").set_axis(
        ["type", "basket", "area", "month", "value"], axis=1)
    wide = rates.pivot(index=["area", "month"], columns="type", values="value").reset_index()
    area = wide["area"].str.split(": ", n=1, expand=True)
    return wide.assign(
        area_code=area[0], area_name=area[1],
        nominal_index=wide["N: Nominal"], real_index=wide["R: Real"],
    )


def build(rates, *, areas=None, since="2019-01", inverted=False):
    rows = rates.loc[rates["month"].ge(since)]
    if areas is not None:
        rows = rows.loc[rows["area_code"].isin(areas)]
    real_to_nominal = rows["real_index"] / rows["nominal_index"]
    return rows.assign(
        real_to_nominal=1 / real_to_nominal if inverted else real_to_nominal,
    )[["area_code", "month", "area_name", "nominal_index", "real_index", "real_to_nominal"]]


TASK = TableTask(
    name="effective_exchange_rates",
    title="Effective exchange rates",
    data_sources=("bis_effective_exchange_rates",),
    financial_domain="macro_rates_fx_trade",
    query=(
        "Line up the BIS broad nominal and real effective exchange rate indices for {scope}, "
        "month by month through the latest month available. One row per economy and month: "
        "the two-letter code, the economy's name (the file gives the two together, as in "
        "\"US: United States\"), the month, the nominal index, the real index, and real "
        "divided by nominal."
    ),
    output="rate_table",
    row_noun="economy and month",
    key=("area_code", "month"),
    columns=(
        Column("area_code", CellKind.IDENTIFIER, "two-letter code as in the source"),
        Column("month", CellKind.DATE, "text, YYYY-MM"),
        Column("area_name", CellKind.TEXT, "the name that follows the code in the source"),
        Column("nominal_index", CellKind.DECIMAL, "rounded to 2 decimals", decimals=2),
        Column("real_index", CellKind.DECIMAL, "rounded to 2 decimals", decimals=2),
        Column("real_to_nominal", CellKind.DECIMAL, "rounded to 10 decimals", decimals=10),
    ),
    sizes=(
        Size("10", "the United States from 2025-03", 10, {"areas": ("US",), "since": "2025-03"}),
        Size("100", "the United States from 2019-01", 84, {"areas": ("US",)}),
        Size("250", "the United States, the euro area and Japan from 2019-01", 252,
             {"areas": LARGE_ECONOMIES[:3]}),
        Size("500", "the United States, the euro area, Japan, the United Kingdom, Canada and "
                    "Australia from 2019-01", 504, {"areas": LARGE_ECONOMIES[:6]}),
        Size("1k", "the United States, the euro area, Japan, the United Kingdom, Canada, "
                   "Australia, Switzerland, China, India, Brazil, Mexico and Korea from 2019-01",
             1008, {"areas": LARGE_ECONOMIES}),
        Size("5k", "every economy from 2019-01", 5376, {}),
    ),
    load=load,
    build=build,
    near_misses={
        "month as a full date": changing(month=lambda month: f"{month}-01"),
        "names reduced to ASCII": changing(
            area_name=lambda name: name.encode("ascii", "ignore").decode()),
    },
    misreadings={
        "the nominal index divided by the real index": partial(build, inverted=True),
    },
)
