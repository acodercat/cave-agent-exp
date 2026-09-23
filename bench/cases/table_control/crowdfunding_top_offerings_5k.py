"""The largest Regulation Crowdfunding offerings, size 5k: a table of 5,000 rows.

The question:

    From the SEC Regulation Crowdfunding (Form C) filings, take those that state a
    maximum offering amount and rank them by it, highest first, breaking ties by
    accession number in ascending order; a filing that states no maximum is left out
    rather than sorted last. Deliver the top 5,000 of that ranking. Each row: the
    accession number, the issuer's name as filed, the filing date, the submission
    type, and the maximum offering amount in dollars as filed.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_control/_crowdfunding_top_offerings.py; the sizes differ only in how
many of the ranked rows are asked for.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_control._crowdfunding_top_offerings import TASK

variables, ground_truth, validate, validators = TASK.members("5k")
