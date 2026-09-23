"""Bank footprints in an area, size 500: a table of 476 rows.

The question:

    Prepare a regional bank coverage table for Texas, comparing deposits at local
    branches with each bank's total assets. Use the FDIC Summary of Deposits as of
    2024-06-30 and the bank financials for the same date. One row per bank with at
    least one branch there: FDIC certificate number, the bank's name as the Summary
    of Deposits spells it, the number of its branches in the area and their combined
    deposits, its total assets, and those deposits divided by total assets. If a
    bank has no financial report for that date, keep the row and leave its assets
    and the ratio missing.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_bank_state_footprint.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._bank_state_footprint import TASK

variables, ground_truth, validate, validators = TASK.members("500")
