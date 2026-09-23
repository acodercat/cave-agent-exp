"""SBA lending by state and industry, size 500: a table of 516 rows.

The question:

    Summarise the SBA 7(a) lending approved in fiscal year 2024 for projects in
    Texas, by project state and NAICS industry. For every state-industry pair with
    at least one loan, report the state, the NAICS code with its description, the
    number of loans, total gross approval, the share of that total guaranteed by the
    SBA, and the average initial interest rate weighted by gross approval, leaving a
    loan that states no rate out of both the weighted sum and its total weight.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_sba_industry_lending.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._sba_industry_lending import TASK

variables, ground_truth, validate, validators = TASK.members("500")
