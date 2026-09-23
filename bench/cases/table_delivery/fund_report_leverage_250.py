"""Fund liabilities against assets, size 250: a table of 278 rows.

The question:

    Screen the N-PORT reports with the report date 2024-12-31 for balance-sheet
    leverage, covering every fund whose net assets were at least 10 billion USD. Go
    report by report, since a fund that amended has more than one: the accession
    number, the registrant's CIK and name, the series name if the report gives one,
    total assets, net assets, and total liabilities over total assets.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_fund_report_leverage.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._fund_report_leverage import TASK

variables, ground_truth, validate, validators = TASK.members("250")
