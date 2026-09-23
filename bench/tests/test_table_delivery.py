"""Table-delivery tasks are well formed and their written case files are current.

Local and deterministic: no model, no runtime tables.
"""

import importlib
import json

import pytest

from cases.table_delivery import task_and_size, tasks
from config import CASE_TAXONOMY_PATH
from core.runtime_catalog import select_runtime_tables
from core.table_delivery import CellKind, Column


SIZE_LABELS = ("10", "100", "250", "500", "1k")
LARGEST_LABELS = {"10k", "5k"}    # a source with fewer than ten thousand rows stops at 5k
TASKS = tasks()


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.name)
def test_a_task_is_asked_at_every_size_in_increasing_order(task):
    *labels, largest = (size.label for size in task.sizes)
    assert tuple(labels) == SIZE_LABELS and largest in LARGEST_LABELS
    rows = [size.rows for size in task.sizes]
    assert rows == sorted(rows) and len(set(rows)) == len(rows)


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.name)
def test_a_task_declares_its_key_and_reaches_its_tables(task):
    names = [column.name for column in task.columns]
    assert len(set(names)) == len(names) and set(task.key) <= set(names)
    assert not any(column.nullable for column in task.columns if column.name in task.key)
    assert "{scope}" in task.query
    assert select_runtime_tables(task.data_sources)
    # The comparison's cell accuracy divides by the non-key cells of at least one row.
    assert len(names) > len(task.key) and all(size.rows > 0 for size in task.sizes)


def test_a_task_names_a_financial_domain_the_taxonomy_defines():
    domains = json.loads(CASE_TAXONOMY_PATH.read_text())["financial_domains"]
    assert {task.financial_domain for task in TASKS} <= domains.keys()


def test_a_case_name_gives_back_its_task_and_size():
    for task in TASKS:
        for size in task.sizes:
            assert task_and_size(task.case_name(size)) == (task, size)


def test_a_task_module_opens_with_its_title_and_names_wrong_answers_to_reject():
    for task in TASKS:
        module = importlib.import_module(f"cases.table_delivery._{task.name}")
        assert module.__doc__.startswith(f"{task.title}, asked at six sizes."), task.name
        assert task.near_misses, task.name


def test_tasks_do_not_share_a_name_or_an_output_question():
    assert len({task.name for task in TASKS}) == len(TASKS)
    assert len({task.query for task in TASKS}) == len(TASKS)


def test_decimals_belong_to_decimal_columns_only():
    with pytest.raises(ValueError):
        Column("share", CellKind.DECIMAL, "a fraction")
    with pytest.raises(ValueError):
        Column("count", CellKind.INTEGER, "a count", decimals=0)
