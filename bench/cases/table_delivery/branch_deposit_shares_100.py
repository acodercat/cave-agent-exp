"""Branch deposits and county shares, size 100: a table of 113 rows.

The question:

    Prepare a branch-level table for a local deposit-share review of Alaska, using
    the FDIC Summary of Deposits as of 2024-06-30. Every branch located there gets a
    row with its branch identifier, the FIPS code of its county, its deposits, and
    its share of the deposits held by all the branches in that county.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_branch_deposit_shares.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._branch_deposit_shares import TASK

variables, ground_truth, validate, validators = TASK.members("100")
