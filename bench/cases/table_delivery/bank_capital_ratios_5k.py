"""Bank capital ratios, size 5k: a table of 4,543 rows.

The question:

    Put together a capital snapshot of the banks in the United States and its
    territories from the FFIEC call report capital data for 2024-12-31. For each
    bank show its identifier and name, its CET1 capital, its standardized risk-
    weighted assets, CET1 over those assets, and the tier 1 leverage ratio as the
    bank reported it. Banks that elected the community bank leverage ratio framework
    report no risk-weighted assets: keep them in the table and leave the assets and
    the ratio missing rather than dropping them or writing zero.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_bank_capital_ratios.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._bank_capital_ratios import TASK

variables, ground_truth, validate, validators = TASK.members("5k")
