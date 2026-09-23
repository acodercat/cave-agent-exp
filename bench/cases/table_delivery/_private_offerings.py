"""Private offerings by industry, asked at six sizes.

SEC Form D notices filed in 2024, by industry group: the offering, the amount
sold, and the amount sold as a fraction of the offering. Electric Utilities has
10 notices, Commercial Banking 119, Other Energy 250, Oil and Gas 553, Other
Health Care 1,009, and Other with Other Technology and Other Real Estate 11,004.

Accession numbers and CIKs are zero-padded text. The source writes an offering
of no stated amount as the word Indefinite in a column of numbers: 1,209 of the
11,004 notices, whose offering and share are missing; nine more state an
offering of zero and have no share. Delivering the word, giving a stated zero as
missing, dropping the zeros from a CIK, or giving the share as a percentage,
produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

import pandas as pd

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


def load():
    notices = load_expansion_table("sec_form_d")
    return notices.loc[notices["FILING_DATE"].between("2024-01-01", "2024-12-31")]


def build(notices, *, industries):
    rows = notices.loc[notices["INDUSTRYGROUPTYPE"].isin(industries)]
    offering = pd.to_numeric(rows["TOTALOFFERINGAMOUNT"], errors="coerce")
    return rows.assign(
        accession_number=rows["ACCESSIONNUMBER"], cik=rows["CIK"],
        entity_name=rows["ENTITYNAME"], filing_date=rows["FILING_DATE"],
        total_offering_usd=offering, amount_sold_usd=rows["TOTALAMOUNTSOLD"],
        sold_share=(rows["TOTALAMOUNTSOLD"] / offering).where(offering.gt(0)),
    )[["accession_number", "cik", "entity_name", "filing_date", "total_offering_usd",
       "amount_sold_usd", "sold_share"]]


TASK = TableTask(
    name="private_offerings",
    title="Private offerings by industry",
    data_sources=("sec_form_d",),
    financial_domain="corporate_reporting",
    query=(
        "Tabulate the Form D notices filed during 2024 whose industry group is {scope}. For "
        "each notice: the accession number, the CIK, the entity name, the filing date, the "
        "total offering amount, the total amount sold, and the amount sold as a fraction of "
        "the offering. Many issuers declare an offering of indefinite size; treat that as no "
        "stated amount and leave the amount and the fraction missing, and leave the fraction "
        "missing for a stated amount of zero as well."
    ),
    output="offering_table",
    row_noun="notice",
    key=("accession_number",),
    columns=(
        Column("accession_number", CellKind.PADDED_IDENTIFIER,
               "text, exactly as in the source, such as 0001234567-24-000012"),
        Column("cik", CellKind.PADDED_IDENTIFIER, "ten-character text, keeping leading zeros"),
        Column("entity_name", CellKind.TEXT, "text, exactly as in the source"),
        Column("filing_date", CellKind.DATE, "text, ISO YYYY-MM-DD"),
        Column("total_offering_usd", CellKind.INTEGER,
               "integer, USD, missing where the offering is of an indefinite amount",
               nullable=True),
        Column("amount_sold_usd", CellKind.INTEGER, "integer, USD"),
        Column("sold_share", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals, missing where the total offering "
               "amount is indefinite or zero", decimals=10, nullable=True),
    ),
    sizes=(
        Size("10", "Electric Utilities", 10, {"industries": ("Electric Utilities",)}),
        Size("100", "Commercial Banking", 119, {"industries": ("Commercial Banking",)}),
        Size("250", "Other Energy", 250, {"industries": ("Other Energy",)}),
        Size("500", "Oil and Gas", 553, {"industries": ("Oil and Gas",)}),
        Size("1k", "Other Health Care", 1009, {"industries": ("Other Health Care",)}),
        Size("10k", "Other, Other Technology or Other Real Estate", 11004,
             {"industries": ("Other", "Other Technology", "Other Real Estate")}),
    ),
    load=load,
    build=build,
    near_misses={
        "an indefinite offering given as the word": lambda rows: [
            row | {"total_offering_usd": "Indefinite"} if row["total_offering_usd"] is None
            else row
            for row in rows
        ],
        "a stated offering of zero given as missing": lambda rows: [
            row | {"total_offering_usd": None} if row["total_offering_usd"] == 0 else row
            for row in rows
        ],
        "CIK without its leading zeros": changing(cik=lambda cik: cik.lstrip("0")),
        "share as a percentage": changing(sold_share=lambda share: share * 100),
    },
)
