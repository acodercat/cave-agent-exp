"""Flood claim payments, asked at six sizes.

Each NFIP claim with a 2024 date of loss in the scope, with its net payment for
building and contents together and its gross building payment. The gross
building payment is not reported for 3 of the 10 claims in Rock Island County,
11 of 97 in Michigan, 13 of 258 in New Hampshire, 37 of 589 in Pennsylvania, 79
of 928 in New York and 776 of the 10,917 in Louisiana, North Carolina and Texas.

A claim without a gross building payment keeps its row and the cell is missing,
not zero. Dropping those claims, counting the net payment for the building
alone, or giving the date of loss with a time part, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


def load():
    claims = load_expansion_table("fema_nfip")
    return claims.loc[claims["date_of_loss"].str.startswith("2024")]


def build(claims, *, states=(), county_code=None):
    rows = claims.loc[
        claims["county_code"].eq(county_code) if county_code
        else claims["state_usps"].isin(states)
    ]
    return rows.assign(
        net_total_payment_usd=rows["net_building_payment_usd"] + rows["net_contents_payment_usd"],
    )[["claim_record_id", "county_code", "date_of_loss", "net_total_payment_usd",
       "gross_building_payment_usd"]]


def build_without_contents(claims, **scope):
    return build(claims, **scope).assign(
        net_total_payment_usd=lambda rows: claims.loc[rows.index, "net_building_payment_usd"],
    )


TASK = TableTask(
    name="flood_claim_payments",
    title="Flood claim payments",
    data_sources=("fema_nfip",),
    financial_domain="insurance_disaster",
    query=(
        "Prepare a loss run of the NFIP flood claims in {scope} with a date of loss in 2024. "
        "Each claim's row needs the claim record identifier, the county code, the date of "
        "loss, the net payment on building and contents combined, and the gross building "
        "payment. Where no gross building payment is reported, keep the claim and leave that "
        "cell missing."
    ),
    output="claim_table",
    row_noun="claim",
    key=("claim_record_id",),
    columns=(
        Column("claim_record_id", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("county_code", CellKind.PADDED_IDENTIFIER, "five-character text"),
        Column("date_of_loss", CellKind.DATE, "text, ISO YYYY-MM-DD"),
        Column("net_total_payment_usd", CellKind.DECIMAL,
               "net building payment plus net contents payment, USD, rounded to 2 decimals",
               decimals=2),
        Column("gross_building_payment_usd", CellKind.DECIMAL,
               "USD, rounded to 2 decimals, missing where the source reports none",
               decimals=2, nullable=True),
    ),
    sizes=(
        Size("10", "the county with code 17161 (Rock Island County, Illinois)", 10,
             {"county_code": "17161"}),
        Size("100", "Michigan", 97, {"states": ("MI",)}),
        Size("250", "New Hampshire", 258, {"states": ("NH",)}),
        Size("500", "Pennsylvania", 589, {"states": ("PA",)}),
        Size("1k", "New York", 928, {"states": ("NY",)}),
        Size("10k", "Louisiana, North Carolina and Texas", 10917, {"states": ("LA", "NC", "TX")}),
    ),
    load=load,
    build=build,
    near_misses={
        "date with a time part": changing(date_of_loss=lambda date: f"{date}T00:00:00"),
        "claims without a gross building payment left out": lambda rows: [
            row for row in rows if row["gross_building_payment_usd"] is not None
        ],
    },
    misreadings={
        "net payment for the building alone": build_without_contents,
    },
)
