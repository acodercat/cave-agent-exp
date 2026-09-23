"""Market growth and drawdown, size 250: a table of 252 rows.

The question:

    Build the series behind a growth-of-a-dollar chart for the US market from
    2024-01-01 through 2024-12-31, out of the Fama-French daily factors. For every
    trading day give the market's total return in percent (the excess return plus
    the risk-free rate), the value of the dollar at that day's close with the first
    day's return already in it, and the drawdown from the highest close so far in
    the window.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_market_growth_drawdown.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._market_growth_drawdown import TASK

variables, ground_truth, validate, validators = TASK.members("250")
