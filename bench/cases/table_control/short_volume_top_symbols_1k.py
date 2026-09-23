"""The most traded symbols of 2024-12-31, size 1k: a table of 1,000 rows.

The question:

    From FINRA's consolidated short sale volume file for 2024-12-31, rank every
    symbol by total volume, highest first, breaking ties by symbol in alphabetical
    order. Deliver the top 1,000 of that ranking. Each row: the symbol exactly as
    listed, its market codes as the file gives them, in one cell, short volume,
    total volume, and short volume over total volume. In this file short volume
    already includes the short-exempt shares, so neither add them nor net them out.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_control/_short_volume_top_symbols.py; the sizes differ only in how many
of the ranked rows are asked for.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_control._short_volume_top_symbols import TASK

variables, ground_truth, validate, validators = TASK.members("1k")
