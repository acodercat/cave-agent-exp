"""Effective exchange rates, size 500: a table of 504 rows.

The question:

    Line up the BIS broad nominal and real effective exchange rate indices for the
    United States, the euro area, Japan, the United Kingdom, Canada and Australia
    from 2019-01, month by month through the latest month available. One row per
    economy and month: the two-letter code, the economy's name (the file gives the
    two together, as in "US: United States"), the month, the nominal index, the real
    index, and real divided by nominal.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_effective_exchange_rates.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._effective_exchange_rates import TASK

variables, ground_truth, validate, validators = TASK.members("500")
