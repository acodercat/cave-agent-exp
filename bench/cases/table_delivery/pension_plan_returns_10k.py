"""Pension plan net income, size 10k: a table of 9,416 rows.

The question:

    Among the Form 5500 plan financials for form year 2023, take the plans that
    began the year with at least 3,000 participants and set their net income against
    their opening net assets. A plan may have filed more than once, so work filing
    by filing: the filing identifier, the sponsor's EIN, the plan name, participants
    at the beginning of the year, beginning net assets, net income (a loss is
    negative), and net income divided by beginning net assets. Leave the ratio
    missing where either figure is missing or the plan began with no assets.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_pension_plan_returns.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._pension_plan_returns import TASK

variables, ground_truth, validate, validators = TASK.members("10k")
