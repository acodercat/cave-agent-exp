"""Fund liabilities against assets, asked at six sizes.

Each N-PORT report with the report date 2024-12-31 of a fund whose net assets
were at least a threshold: 200 billion USD (10 reports), 30 billion (92), 10
billion (278), 5 billion (495) and 2 billion (1,027), with total liabilities as a
fraction of total assets. The largest scope is every report for the date
(6,600), which is all the source holds and so is labelled 5k.

A row is a report, identified by its accession number, since an amended report
is a second row for the same series. Accession numbers and CIKs are zero-padded
text, amounts carry cents, registrant and series names are free text, and 39 of
the 6,600 reports name no series, which leaves that cell missing. Screening the
funds on total assets instead of net assets, dividing liabilities by net assets,
giving the ratio as a percentage, or dropping the zeros from a CIK, produces a
different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


REPORT_DATE = "2024-12-31"


def load():
    reports = load_expansion_table("sec_nport")
    return reports.loc[reports["report_date"].eq(REPORT_DATE)]


def build(reports, *, at_least_usd=None, base="total_assets_usd", screened_on="net_assets_usd"):
    rows = reports if at_least_usd is None else reports.loc[
        reports[screened_on].ge(at_least_usd)]
    return rows.assign(
        liabilities_to_assets=rows["total_liabilities_usd"] / rows[base],
    )[["accession", "cik", "registrant_name", "series_name", "total_assets_usd",
       "net_assets_usd", "liabilities_to_assets"]]


TASK = TableTask(
    name="fund_report_leverage",
    title="Fund liabilities against assets",
    data_sources=("sec_nport",),
    financial_domain="investment_funds",
    query=(
        "Screen the N-PORT reports with the report date 2024-12-31 for balance-sheet "
        "leverage, covering {scope}. Go report by report, since a fund that amended has more "
        "than one: the accession number, the registrant's CIK and name, the series name if "
        "the report gives one, total assets, net assets, and total liabilities over total "
        "assets."
    ),
    output="report_table",
    row_noun="report",
    key=("accession",),
    columns=(
        Column("accession", CellKind.PADDED_IDENTIFIER,
               "text, exactly as in the source, such as 0001234567-25-000012"),
        Column("cik", CellKind.PADDED_IDENTIFIER, "ten-character text, keeping leading zeros"),
        Column("registrant_name", CellKind.TEXT, "text, exactly as in the source"),
        Column("series_name", CellKind.TEXT,
               "text, exactly as in the source, missing where the report names no series",
               nullable=True),
        Column("total_assets_usd", CellKind.DECIMAL, "USD, rounded to 2 decimals", decimals=2),
        Column("net_assets_usd", CellKind.DECIMAL, "USD, rounded to 2 decimals", decimals=2),
        Column("liabilities_to_assets", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals", decimals=10),
    ),
    sizes=(
        *(Size(label, f"every fund whose net assets were at least {billions} billion USD",
               rows, {"at_least_usd": billions * 1_000_000_000})
          for label, billions, rows in (("10", 200, 10), ("100", 30, 92), ("250", 10, 278),
                                        ("500", 5, 495), ("1k", 2, 1027))),
        Size("5k", "every fund", 6600, {}),
    ),
    load=load,
    build=build,
    near_misses={
        "ratio as a percentage": changing(liabilities_to_assets=lambda ratio: ratio * 100),
        "CIK without its leading zeros": changing(cik=lambda cik: cik.lstrip("0")),
    },
    misreadings={
        "liabilities over net assets": partial(build, base="net_assets_usd"),
        "funds screened on total assets rather than net assets": partial(
            build, screened_on="total_assets_usd"),
    },
)
