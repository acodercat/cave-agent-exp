"""Short sale volume ratios, size 10: a table of 6 rows.

The question:

    From FINRA's consolidated short sale volume file for 2024-12-31, report every
    symbol with a total volume of at least 100 million shares. Give the symbol
    exactly as listed, the market codes, short volume, total volume, short volume
    over total volume, and short-exempt volume over short volume. In this file short
    volume already includes the short-exempt shares, so neither add them nor net
    them out.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_short_volume_ratios.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._short_volume_ratios import TASK

variables, ground_truth, validate, validators = TASK.members("10")
