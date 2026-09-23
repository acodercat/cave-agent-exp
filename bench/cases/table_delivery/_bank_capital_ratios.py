"""Bank capital ratios, asked at six sizes.

Each bank in the scope from the FFIEC call report capital data dated
2024-12-31: its CET1 capital, its standardized risk-weighted assets, their
ratio, and its reported tier 1 leverage ratio. Alaska has 5 banks,
Massachusetts 102, Minnesota 241, Texas with Pennsylvania 505, Texas with
Illinois and Minnesota 972, and the whole country 4,543, which is every bank in
the source and so is labelled 5k.

A bank that elected the community bank leverage ratio reports no risk-weighted
assets, so its assets and its ratio are missing while its leverage ratio is not:
1,700 of the 4,543 banks, and one of Alaska's five. Dropping those banks, taking
the CET1 ratio the bank reported (rounded as filed) instead of the ratio of the
amounts, giving the CET1 ratio as a percentage, or giving the leverage ratio as a
decimal fraction, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


REPORT_DATE = "2024-12-31"


def load():
    capital = load_expansion_table("ffiec_call_reports_capital")
    return capital.loc[capital["report_date"].eq(REPORT_DATE)]


def build(capital, *, states=None, ratio_as_reported=False):
    rows = capital if states is None else capital.loc[capital["bank_state"].isin(states)]
    cet1 = rows["common_equity_tier1_capital_thousand_usd"]
    risk_weighted = rows["standardized_risk_weighted_assets_thousand_usd"]
    ratio = (
        rows["reported_standardized_cet1_ratio_pct"] / 100 if ratio_as_reported
        else cet1 / risk_weighted
    )
    return rows.assign(
        cet1_capital_thousand_usd=cet1,
        risk_weighted_assets_thousand_usd=risk_weighted,
        cet1_ratio=ratio,
        tier1_leverage_ratio_pct=rows["reported_tier1_leverage_ratio_pct"],
    )[["bank_id", "bank_name", "cet1_capital_thousand_usd",
       "risk_weighted_assets_thousand_usd", "cet1_ratio", "tier1_leverage_ratio_pct"]]


TASK = TableTask(
    name="bank_capital_ratios",
    title="Bank capital ratios",
    data_sources=("ffiec_call_reports_capital",),
    financial_domain="banking_credit",
    query=(
        "Put together a capital snapshot of the banks in {scope} from the FFIEC call report "
        "capital data for 2024-12-31. For each bank show its identifier and name, its CET1 "
        "capital, its standardized risk-weighted assets, CET1 over those assets, and the "
        "tier 1 leverage ratio as the bank reported it. Banks that elected the community "
        "bank leverage ratio framework report no risk-weighted assets: keep them in the "
        "table and leave the assets and the ratio missing rather than dropping them or "
        "writing zero."
    ),
    output="capital_table",
    row_noun="bank",
    key=("bank_id",),
    columns=(
        Column("bank_id", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("bank_name", CellKind.TEXT, "text, exactly as in the source"),
        Column("cet1_capital_thousand_usd", CellKind.INTEGER, "integer, thousand USD"),
        Column("risk_weighted_assets_thousand_usd", CellKind.INTEGER,
               "integer, thousand USD, missing where the bank reports none", nullable=True),
        Column("cet1_ratio", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals, missing where the assets are",
               decimals=10, nullable=True),
        Column("tier1_leverage_ratio_pct", CellKind.DECIMAL,
               "percent as reported, rounded to 4 decimals", decimals=4),
    ),
    sizes=(
        Size("10", "Alaska", 5, {"states": ("AK",)}),
        Size("100", "Massachusetts", 102, {"states": ("MA",)}),
        Size("250", "Minnesota", 241, {"states": ("MN",)}),
        Size("500", "Texas and Pennsylvania", 505, {"states": ("TX", "PA")}),
        Size("1k", "Texas, Illinois and Minnesota", 972, {"states": ("TX", "IL", "MN")}),
        Size("5k", "the United States and its territories", 4543, {}),
    ),
    load=load,
    build=build,
    near_misses={
        "CET1 ratio as a percentage": changing(cet1_ratio=lambda ratio: ratio * 100),
        "leverage ratio as a decimal fraction": changing(
            tier1_leverage_ratio_pct=lambda pct: pct / 100),
        "banks without risk-weighted assets left out": lambda rows: [
            row for row in rows if row["risk_weighted_assets_thousand_usd"] is not None
        ],
    },
    misreadings={
        "the reported CET1 ratio, rounded as filed, instead of the amounts' ratio": partial(
            build, ratio_as_reported=True),
    },
)
