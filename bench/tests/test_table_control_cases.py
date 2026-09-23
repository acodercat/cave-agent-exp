"""Each delivery-control size is a prefix of the next, and rejects the wrong rankings."""

from copy import deepcopy

import pytest

from cases.table_control import tasks


@pytest.fixture(scope="module", params=tasks(), ids=lambda task: task.name)
def answers(request):
    """One task with its answer at every size, built from one load of its tables."""
    task = request.param
    source = task.load()
    return task, source, {size.label: task.expected_rows(size, source) for size in task.sizes}


def test_each_size_holds_the_rows_it_asks_for(answers):
    task, _, rows = answers
    assert {label: len(expected) for label, expected in rows.items()} == {
        size.label: size.rows for size in task.sizes
    }


def test_a_smaller_answer_is_the_start_of_a_larger_one(answers):
    """The intervention: the rows are the same rows, and only their number changes."""
    task, _, rows = answers
    largest = rows[task.sizes[-1].label]
    for size in task.sizes:
        assert rows[size.label] == largest[:size.rows], size.label


def test_key_columns_identify_a_row(answers):
    task, _, rows = answers
    for label, expected in rows.items():
        keys = [tuple(row[column] for column in task.key) for row in expected]
        assert len(set(keys)) == len(keys), label


def test_no_cell_is_missing_and_none_is_declared_nullable(answers):
    """A ranked top-N carries no gaps, so a nullable column would be a wrong claim."""
    task, _, rows = answers
    assert not [column.name for column in task.columns if column.nullable]
    for label, expected in rows.items():
        assert not [name for row in expected for name, value in row.items() if value is None], label


def test_every_size_accepts_its_own_answer(answers):
    task, _, rows = answers
    for label, expected in rows.items():
        assert task.check(deepcopy(expected), expected).success, label


def test_a_near_miss_is_rejected_at_every_size(answers):
    task, _, rows = answers
    for label, expected in rows.items():
        for name, rewrite in task.near_misses.items():
            assert not task.check(rewrite(deepcopy(expected)), expected).success, (label, name)


def _keyed(task, rows):
    """The rows as the validator sees them: by key, order ignored."""
    return {tuple(row[column] for column in task.key): row for row in rows}


def _misread_sizes(task, source, rows):
    """Per misreading, the sizes at which it delivers something else than the answer."""
    return {
        name: [
            size.label for size in task.sizes
            if _keyed(task, task.expected_rows(size, source, build=build))
            != _keyed(task, rows[size.label])
        ]
        for name, build in task.misreadings.items()
    }


def test_a_misreading_is_rejected_wherever_it_differs(answers):
    """A misreading of the scope or the ranking can agree over the first rows.

    The largest flood claims of 2024 were opened in 2024, are paid mostly on the
    building and carry no compliance payment, so those three misreadings deliver
    the answer itself at the smaller sizes. At those sizes what probes the answer
    is the near miss (every size) and the row count (the test below).
    """
    task, source, rows = answers
    differing = _misread_sizes(task, source, rows)
    for name, build in task.misreadings.items():
        for label in differing[name]:
            misread = task.expected_rows(task.size(label), source, build=build)
            assert not task.check(misread, rows[label]).success, (label, name)
        # A misreading that never shows would probe nothing.
        assert task.sizes[-1].label in differing[name], name


def test_the_answer_of_another_size_is_rejected(answers):
    """Delivering too few or too many rows of the right ranking is still wrong."""
    task, _, rows = answers
    expected = rows["250"]
    assert not task.check(deepcopy(rows["100"]), expected).success
    assert not task.check(deepcopy(rows["500"]), expected).success
