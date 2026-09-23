"""The largest flood claims of 2024, size 1k: a table of 1,000 rows.

The question:

    Take the NFIP flood claims with a date of loss in 2024 and rank them by the net
    payment on building and contents combined, highest first, breaking ties by claim
    record identifier in ascending order. Deliver the top 1,000 of that ranking.
    Each row: the claim record identifier, the state, the date of loss, that net
    payment, and the share of it paid on the building.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_control/_flood_claim_top_payments.py; the sizes differ only in how many
of the ranked rows are asked for.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_control._flood_claim_top_payments import TASK

variables, ground_truth, validate, validators = TASK.members("1k")
