"""Delivery-control cases: each ``_<task>.py`` defines a TASK, asked at several sizes.

Every size of a task here runs the same computation over the same rows, and the
question differs only in how many of the ranked rows it asks the agent to
deliver. A size's answer is a prefix of the next size's, which a test holds, so a
difference between sizes is a difference in delivered volume and nothing else.
The per-size case files beside them are written by ``scripts.build_cases``.
"""

from functools import cache

from cases import tasks_in
from core.table_delivery import Size, TableTask


@cache
def tasks() -> tuple[TableTask, ...]:
    """Every task in this family, by name."""
    return tasks_in("table_control")


def task_and_size(case_name: str) -> tuple[TableTask, Size]:
    """The task a case asks and the size it asks it at, from the case's name."""
    task_name, _, label = case_name.rpartition("_")
    task = next(task for task in tasks() if task.name == task_name)
    return task, task.size(label)
