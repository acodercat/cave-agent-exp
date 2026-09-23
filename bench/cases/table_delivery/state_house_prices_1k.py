"""State house price changes, size 1k: a table of 1,020 rows.

The question:

    From the FHFA state house price index (traditional, all-transactions, quarterly,
    not seasonally adjusted), pull the rows for California, Texas, Florida, New York
    and Illinois over their whole series, through the latest quarter in the data,
    and deliver no other rows. Each row is one state and quarter: the state's postal
    code, the quarter written like 2024Q3, the index, and its change from the same
    quarter a year earlier. Work the change out on the full series before cutting it
    to the window, so the first quarters you deliver still have one; it is missing
    only where the series has no value a year earlier.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_state_house_prices.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._state_house_prices import TASK

variables, ground_truth, validate, validators = TASK.members("1k")
