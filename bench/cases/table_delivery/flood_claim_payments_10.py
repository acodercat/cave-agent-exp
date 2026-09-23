"""Flood claim payments, size 10: a table of 10 rows.

The question:

    Prepare a loss run of the NFIP flood claims in the county with code 17161 (Rock
    Island County, Illinois) with a date of loss in 2024. Each claim's row needs the
    claim record identifier, the county code, the date of loss, the net payment on
    building and contents combined, and the gross building payment. Where no gross
    building payment is reported, keep the claim and leave that cell missing.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_flood_claim_payments.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._flood_claim_payments import TASK

variables, ground_truth, validate, validators = TASK.members("10")
