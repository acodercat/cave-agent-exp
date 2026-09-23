"""The largest flood claims of 2024, delivered at six volumes.

The NFIP snapshot holds 102,045 claims with a date of loss in 2024. Every case
ranks all of them the same way — net building and contents payment, highest
first, ties broken by claim record identifier — and differs only in how many of
the ranked rows the question asks for: 10, 100, 250, 500, 1,000 and 5,000. A
smaller answer is the first rows of a larger one, so what separates the cases is
delivered volume alone.

Giving the building share as a percentage changes the table at every size. The
three misreadings of scope and ranking — the claims opened in 2024 rather than
those whose loss fell in 2024, a ranking by the gross building payment, a net
payment read as including the increased-cost-of-compliance payment — change it
from 500 or 1,000 rows on: the largest claims of the year were opened that year,
are paid mostly on the building and carry no compliance payment, so over the
first rows those readings agree with the answer.
"""

from functools import partial

import pandas as pd

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


YEAR_START, YEAR_END = "2024-01-01", "2024-12-31"
NET_PAID, GROSS_BUILDING = "net_paid", "gross_building_payment_usd"
# What "the net payment on building and contents" covers: those two (the answer),
# or those two plus increased cost of compliance (a reading the question excludes).
PAID_COLUMNS = ["net_building_payment_usd", "net_contents_payment_usd"]
WITH_ICC = [*PAID_COLUMNS, "net_icc_payment_usd"]


def load():
    return load_expansion_table("fema_nfip")


def build(claims, *, rows, rank_by=NET_PAID, paid_columns=None, dated_by="date_of_loss"):
    in_year = claims.loc[claims[dated_by].between(YEAR_START, YEAR_END)]
    paid = in_year[paid_columns or PAID_COLUMNS].fillna(0).sum(axis=1)
    ranked = in_year.assign(**{NET_PAID: paid}).sort_values(
        [rank_by, "claim_record_id"], ascending=[False, True]).head(rows)
    return pd.DataFrame({
        "claim_record_id": ranked["claim_record_id"],
        "state_usps": ranked["state_usps"],
        "date_of_loss": ranked["date_of_loss"],
        "net_paid_usd": ranked[NET_PAID],
        # Every delivered claim was paid something: the 5,000th of 2024 was paid
        # $280,703.73, so this share is never taken of zero.
        "building_share": (ranked["net_building_payment_usd"].fillna(0)
                           / ranked[NET_PAID]),
    }).reset_index(drop=True)


def _size(label: str, rows: int) -> Size:
    return Size(label, f"the top {rows:,} of that ranking", rows, {"rows": rows})


TASK = TableTask(
    name="flood_claim_top_payments",
    title="The largest flood claims of 2024",
    data_sources=("fema_nfip",),
    financial_domain="insurance_disaster",
    family="table_control",
    sizes_vary="the sizes differ only in how many of the ranked rows are asked for",
    query=(
        "Take the NFIP flood claims with a date of loss in 2024 and rank them by the net "
        "payment on building and contents combined, highest first, breaking ties by claim "
        "record identifier in ascending order. Deliver {scope}. Each row: the claim record "
        "identifier, the state, the date of loss, that net payment, and the share of it paid "
        "on the building."
    ),
    output="claim_table",
    row_noun="claim",
    key=("claim_record_id",),
    columns=(
        Column("claim_record_id", CellKind.IDENTIFIER, "the claim record identifier"),
        Column("state_usps", CellKind.TEXT, "the two-letter state code"),
        Column("date_of_loss", CellKind.DATE, "the date of loss as an ISO YYYY-MM-DD string"),
        Column("net_paid_usd", CellKind.DECIMAL,
               "net building and contents payment in USD, 2 decimals", decimals=2),
        Column("building_share", CellKind.DECIMAL,
               "the building share of that payment, 4 decimals", decimals=4),
    ),
    sizes=(
        _size("10", 10), _size("100", 100), _size("250", 250),
        _size("500", 500), _size("1k", 1000), _size("5k", 5000),
    ),
    load=load,
    build=build,
    near_misses={"share_as_percentage": changing(building_share=lambda share: share * 100)},
    misreadings={
        "claims_opened_in_2024": partial(build, dated_by="open_date"),
        "ranked_by_gross_building": partial(build, rank_by=GROSS_BUILDING),
        "icc_payments_included": partial(build, paid_columns=WITH_ICC),
    },
)
