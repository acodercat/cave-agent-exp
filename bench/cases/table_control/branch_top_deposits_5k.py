"""The largest bank branches by deposits, size 5k: a table of 5,000 rows.

The question:

    From the FDIC Summary of Deposits as of 2024-06-30, rank every branch by its
    deposits, highest first, breaking ties by branch identifier in ascending order.
    Deliver the top 5,000 of that ranking. Each row: the branch identifier, the
    bank's name as the Summary of Deposits spells it, the branch's state, its main-
    office indicator exactly as the source writes it, and its deposits in thousands
    of dollars as reported.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_control/_branch_top_deposits.py; the sizes differ only in how many of
the ranked rows are asked for.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_control._branch_top_deposits import TASK

variables, ground_truth, validate, validators = TASK.members("5k")
