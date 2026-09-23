"""Treasury securities outstanding, size 10: a table of 8 rows.

The question:

    Reconstruct from the Monthly Statement of the Public Debt detail of marketable
    securities what was outstanding, security by security, for the floating rate
    notes on 2024-12-31, and deliver no other securities. The statement prints one
    line per issue and reopening and states the amount outstanding on only one of
    them, so roll the lines up to the CUSIP within each record date, and ignore the
    subtotal and total lines. Per record date and CUSIP: the security class, the
    maturity date, the interest rate, the number of lines rolled up, the amount
    issued, the amount outstanding, and that outstanding amount as a share of all
    the delivered securities of the same class on that record date. Use the source's
    stated interest-rate field, leaving it missing where unstated; do not substitute
    the yield field, including the discount yield of a bill or the spread of a
    floating rate note.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_treasury_securities_outstanding.py; the sizes differ in scope
only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._treasury_securities_outstanding import TASK

variables, ground_truth, validate, validators = TASK.members("10")
