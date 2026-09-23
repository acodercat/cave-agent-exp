"""Table-delivery cases: each ``_<task>.py`` defines a TASK, asked at several sizes.

The per-size case files beside them are written by ``scripts.build_cases`` from
those tasks; edit the task and rebuild, never a case file.
"""

from functools import cache

from cases import tasks_in
from core.table_delivery import Size, TableTask


@cache
def tasks() -> tuple[TableTask, ...]:
    """Every task in this family, by name."""
    return tasks_in("table_delivery")


def task_and_size(case_name: str) -> tuple[TableTask, Size]:
    """The task a case asks and the size it asks it at, from the case's name."""
    task_name, _, label = case_name.rpartition("_")
    task = next(task for task in tasks() if task.name == task_name)
    return task, task.size(label)
