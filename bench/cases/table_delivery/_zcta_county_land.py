"""ZCTA land by county, asked at six sizes.

Each part of a ZIP code tabulation area that lies in a county of the scope, from
the 2020 Census relationship file, with its land area and that area as a
fraction of the ZCTA's total land. The scopes run from Guam (7 parts) through
Hawaii (97), Puerto Rico (250), Massachusetts (565) and Alabama (979) to Texas
with Pennsylvania, New York, Illinois and New Mexico (9,803).

A ZCTA on a state line has parts in counties the scope leaves out, and they
still count in its total; the question says so. ZCTAs in Puerto Rico and
Massachusetts and county codes in Alabama begin with zeros, areas are large
integers, and county names in Puerto Rico and New Mexico carry letters outside
ASCII. Taking the total over the delivered counties only, reducing names to
ASCII, or giving the area in square kilometres, produces a different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

from functools import partial

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


def load():
    return load_expansion_table("census_zcta_county_relationships")


def build(parts, *, states, total_within_scope=False):
    in_scope = parts["GEOID_COUNTY_20"].str[:2].isin(states)
    basis = parts.loc[in_scope] if total_within_scope else parts
    zcta_land = basis.groupby("GEOID_ZCTA5_20")["AREALAND_PART"].sum()
    rows = parts.loc[in_scope]
    return rows.assign(
        zcta=rows["GEOID_ZCTA5_20"], county_fips=rows["GEOID_COUNTY_20"],
        county_name=rows["NAMELSAD_COUNTY_20"], land_area_sq_m=rows["AREALAND_PART"],
        share_of_zcta_land=rows["AREALAND_PART"] / rows["GEOID_ZCTA5_20"].map(zcta_land),
    )[["zcta", "county_fips", "county_name", "land_area_sq_m", "share_of_zcta_land"]]


TASK = TableTask(
    name="zcta_county_land",
    title="ZCTA land by county",
    data_sources=("census_zcta_county_relationships",),
    financial_domain="household_housing",
    query=(
        "Apportion ZIP code tabulation areas to counties for {scope}, using the 2020 Census "
        "ZCTA-to-county relationship file. Every ZCTA-county part lying in those counties "
        "gets a row: the ZCTA, the county FIPS code, the county name, the land area of the "
        "part, and that area as a fraction of the ZCTA's total land area. Take the total "
        "over every county the ZCTA touches, including counties outside the area asked for."
    ),
    output="part_table",
    row_noun="ZCTA and county",
    key=("zcta", "county_fips"),
    columns=(
        Column("zcta", CellKind.PADDED_IDENTIFIER, "five-character text, keeping leading zeros"),
        Column("county_fips", CellKind.PADDED_IDENTIFIER,
               "five-character text, keeping leading zeros"),
        Column("county_name", CellKind.TEXT, "text, exactly as in the source"),
        Column("land_area_sq_m", CellKind.INTEGER, "integer, square metres"),
        Column("share_of_zcta_land", CellKind.DECIMAL,
               "decimal fraction rounded to 10 decimals", decimals=10),
    ),
    sizes=(
        Size("10", "Guam", 7, {"states": ("66",)}),
        Size("100", "Hawaii", 97, {"states": ("15",)}),
        Size("250", "Puerto Rico", 250, {"states": ("72",)}),
        Size("500", "Massachusetts", 565, {"states": ("25",)}),
        Size("1k", "Alabama", 979, {"states": ("01",)}),
        Size("10k", "Texas, Pennsylvania, New York, Illinois and New Mexico", 9803,
             {"states": ("48", "42", "36", "17", "35")}),
    ),
    load=load,
    build=build,
    near_misses={
        "county names reduced to ASCII": changing(
            county_name=lambda name: name.encode("ascii", "ignore").decode()),
        "area in square kilometres": changing(land_area_sq_m=lambda area: area // 1_000_000),
    },
    misreadings={
        "the total taken over the delivered counties only": partial(
            build, total_within_scope=True),
    },
)
