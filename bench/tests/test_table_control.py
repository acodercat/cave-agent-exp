"""The delivery-control tasks: same computation at every size, only more rows asked for."""

import pytest

from cases.table_control import task_and_size, tasks
from core.runtime_catalog import select_runtime_tables
from core.table_delivery import CellKind


SIZE_LABELS = ("10", "100", "250", "500", "1k", "5k")
TASKS = tasks()


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.name)
def test_a_task_is_asked_at_every_size_and_belongs_to_this_family(task):
    assert tuple(size.label for size in task.sizes) == SIZE_LABELS
    assert [size.rows for size in task.sizes] == [10, 100, 250, 500, 1000, 5000]
    assert task.family == "table_control"


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.name)
def test_only_the_row_count_changes_between_sizes(task):
    """Every size runs the same computation over the same rows: `rows` is the only parameter."""
    assert {name for size in task.sizes for name in size.params} == {"rows"}
    assert all(size.params["rows"] == size.rows for size in task.sizes)
    scopes = {size.scope for size in task.sizes}
    assert len(scopes) == len(task.sizes)


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.name)
def test_a_task_declares_its_key_and_reaches_its_tables(task):
    names = [column.name for column in task.columns]
    assert names[0] == task.key[0] and len(set(names)) == len(names)
    assert select_runtime_tables(task.data_sources)
    assert all(column.decimals is not None for column in task.columns
               if column.kind is CellKind.DECIMAL)


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.name)
def test_a_task_probes_the_wrong_answers_it_expects(task):
    assert task.near_misses and task.misreadings


def test_a_case_name_resolves_to_its_task_and_size():
    task, size = task_and_size("flood_claim_top_payments_1k")
    assert task.name == "flood_claim_top_payments" and size.rows == 1000
