"""Storm event damages, size 10: a table of 28 rows.

The question:

    Compile the 2024 storm record for the District of Columbia from the NOAA storm
    events data, taking events by the date they began. For each event: its
    identifier, the event type, the county or forecast zone name, the beginning
    timestamp as the source writes it, the duration in hours, and the reported
    property damage and crop damage. Damage is often not reported; leave those cells
    missing rather than zero.

The columns, the arithmetic and the wrong answers the validator must reject are in
cases/table_delivery/_storm_event_damages.py; the sizes differ in scope only.

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

from cases.table_delivery._storm_event_damages import TASK

variables, ground_truth, validate, validators = TASK.members("10")
