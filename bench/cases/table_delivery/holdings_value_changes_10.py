"""13F holdings value changes, size 10: a table of 10 rows.

The question:

    Between the 2025-06-30 and 2025-09-30 report periods, which securities saw the
    largest swing in total 13F reported value? Use the holdings aggregated by CUSIP,
    keep only securities reported in both periods, and deliver the top 10 by
    absolute change. Each row: the CUSIP, the issuer name as reported for
    2025-09-30, the value in each period, the change (later minus earlier), and the
    change relative to the earlier value, left missing where the earlier value is
    zero.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_holdings_value_changes.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._holdings_value_changes import TASK

variables, ground_truth, validate, validators = TASK.members("10")
