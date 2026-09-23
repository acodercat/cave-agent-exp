"""Fails to deliver by value, size 1k: a table of 1,013 rows.

The question:

    Value the fails to deliver for the settlement date 2024-12-31 from the SEC
    fails-to-deliver file, and report every security whose fails were worth at least
    200,000 USD. For each one: CUSIP, symbol, description, quantity of fails, price,
    and the dollar value of the fails, taken as quantity times price. Where the file
    states no price, leave both price and estimated value missing rather than
    guessing. A security with no price cannot clear a value threshold, so it belongs
    in the table only where no threshold is asked for.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_fails_to_deliver_values.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._fails_to_deliver_values import TASK

variables, ground_truth, validate, validators = TASK.members("1k")
