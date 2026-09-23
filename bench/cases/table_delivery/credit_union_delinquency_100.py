"""Credit union delinquency, size 100: a table of 98 rows.

The question:

    How delinquent are the loan books of the credit unions in Virginia? From the
    NCUA call reports dated 2024-12-31, list every credit union there with its
    charter number, its name, total loans and leases, loans two or more months
    delinquent, and the delinquent amount as a fraction of total loans. A credit
    union with no loans has no ratio; leave it missing.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_credit_union_delinquency.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._credit_union_delinquency import TASK

variables, ground_truth, validate, validators = TASK.members("100")
