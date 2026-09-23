"""Private offerings by industry, size 250: a table of 250 rows.

The question:

    Tabulate the Form D notices filed during 2024 whose industry group is Other
    Energy. For each notice: the accession number, the CIK, the entity name, the
    filing date, the total offering amount, the total amount sold, and the amount
    sold as a fraction of the offering. Many issuers declare an offering of
    indefinite size; treat that as no stated amount and leave the amount and the
    fraction missing, and leave the fraction missing for a stated amount of zero as
    well.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_private_offerings.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._private_offerings import TASK

variables, ground_truth, validate, validators = TASK.members("250")
