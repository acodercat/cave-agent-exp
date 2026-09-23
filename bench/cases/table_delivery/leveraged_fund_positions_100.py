"""Leveraged fund futures positions, size 100: a table of 125 rows.

The question:

    Track how leveraged funds were positioned in financial futures, using the CFTC
    Traders in Financial Futures futures-only reports: every contract from
    2024-12-24 through 2024-12-31. For each contract and report date give the
    contract market code, the report date, the market and exchange name, open
    interest, the leveraged funds' net position (long minus short, so negative when
    net short), and that net position over open interest.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_leveraged_fund_positions.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._leveraged_fund_positions import TASK

variables, ground_truth, validate, validators = TASK.members("100")
