"""County employment by sector, size 10k: a table of 12,461 rows.

The question:

    Break down private employment in Texas, Georgia, Virginia and Kentucky by county
    and NAICS sector, from the 2024 QCEW annual averages. Skip the unknown-or-
    undefined areas, whose codes end in 999. Each county-sector row should carry the
    county code, the sector code, establishments, average employment, average annual
    pay, and the sector's share of all private employment in its county. Take that
    county total from the county's own private-ownership row, not from a sum of the
    sector rows, which leaves the suppressed sectors out. BLS suppresses some cells,
    and the file shows zeros there under disclosure code N; those are not zeros, so
    leave employment, pay and the share missing for them, and leave the share
    missing too where the county total is suppressed.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_county_sector_employment.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._county_sector_employment import TASK

variables, ground_truth, validate, validators = TASK.members("10k")
