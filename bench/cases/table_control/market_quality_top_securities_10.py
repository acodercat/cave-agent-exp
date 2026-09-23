"""The most traded securities of 2024-12-31, size 10: a table of 10 rows.

The question:

    From the SEC MIDAS security-and-exchange metrics for 2024-12-31, rank every
    security by traded volume, highest first, breaking ties by security type and
    then by ticker, both ascending. Deliver the top 10 of that ranking. Each row:
    the ticker, the security type as given, the number of trades, the traded volume
    in thousands of shares exactly as the file reports it, and hidden volume over
    traded volume.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_control/_market_quality_top_securities.py; the sizes differ only in how
many of the ranked rows are asked for.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_control._market_quality_top_securities import TASK

variables, ground_truth, validate, validators = TASK.members("10")
