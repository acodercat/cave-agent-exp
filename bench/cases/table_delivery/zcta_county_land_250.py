"""ZCTA land by county, size 250: a table of 250 rows.

The question:

    Apportion ZIP code tabulation areas to counties for Puerto Rico, using the 2020
    Census ZCTA-to-county relationship file. Every ZCTA-county part lying in those
    counties gets a row: the ZCTA, the county FIPS code, the county name, the land
    area of the part, and that area as a fraction of the ZCTA's total land area.
    Take the total over every county the ZCTA touches, including counties outside
    the area asked for.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_zcta_county_land.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._zcta_county_land import TASK

variables, ground_truth, validate, validators = TASK.members("250")
