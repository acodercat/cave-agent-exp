"""Every table-delivery case accepts its own answer and rejects the near misses."""

from copy import deepcopy

import pytest

from cases.table_delivery import tasks
from core.table_delivery import CellKind


@pytest.fixture(scope="module", params=tasks(), ids=lambda task: task.name)
def answers(request):
    """One task with its answer at every size, built from one load of its tables."""
    task = request.param
    source = task.load()
    return task, source, {size.label: task.expected_rows(size, source) for size in task.sizes}


def test_each_size_holds_the_rows_it_declares(answers):
    task, _, rows = answers
    assert {size.label: len(rows[size.label]) for size in task.sizes} == {
        size.label: size.rows for size in task.sizes
    }


def test_key_columns_identify_a_row(answers):
    task, _, rows = answers
    for label, expected in rows.items():
        keys = [tuple(row[column] for column in task.key) for row in expected]
        assert len(set(keys)) == len(keys), label


def test_every_size_accepts_its_own_answer(answers):
    task, _, rows = answers
    for label, expected in rows.items():
        assert task.check(deepcopy(expected), expected).success, label


def test_an_integer_delivered_as_a_float_is_the_same_number(answers):
    """pandas holds an integer column with a missing cell as floats."""
    task, _, rows = answers
    expected = rows["100"]
    integers = [column.name for column in task.columns if column.kind is CellKind.INTEGER]
    as_floats = [
        row | {name: float(row[name]) for name in integers if row[name] is not None}
        for row in expected
    ]
    assert task.check(as_floats, expected).success


def test_nullable_is_declared_where_cells_are_missing_and_only_there(answers):
    task, _, rows = answers
    largest = rows[task.sizes[-1].label]
    for column in task.columns:
        has_missing = any(row[column.name] is None for row in largest)
        assert has_missing == column.nullable, column.name


def _generic_near_misses(task, rows):
    """Wrong answers any table invites: a lost row, and each column slightly off."""
    yield "one row left out", rows[1:]
    yield "one row repeated", rows + rows[:1]
    for column in task.columns:
        present = [i for i, row in enumerate(rows) if row[column.name] is not None]
        if present:
            index = present[0]
            value = rows[index][column.name]
            changed = deepcopy(rows)
            if column.kind is CellKind.DECIMAL:
                changed[index][column.name] = value + 10 ** -column.decimals
            elif column.kind is CellKind.INTEGER:
                changed[index][column.name] = value + 1
            else:
                changed[index][column.name] = value + " "
            yield f"{column.name} off in one row", changed
        if any(row[column.name] is None for row in rows):
            filled = [row | {column.name: 0 if row[column.name] is None else row[column.name]}
                      for row in rows]
            yield f"{column.name} missing given as zero", filled
        if column.kind is CellKind.PADDED_IDENTIFIER and present:
            values = [row[column.name] for row in rows]
            if any(value.startswith("0") for value in values):
                yield f"{column.name} without leading zeros", [
                    row | {column.name: row[column.name].lstrip("0")} for row in rows
                ]
            # Only where a leading zero makes it lossy. The scoring contract
            # reads an integer as its digits (core.validation._exact_text), so
            # for a code that never starts with a zero, int() round-trips to the
            # same identifier — that is the same answer in another encoding, not
            # a near miss, and the contract accepts it on purpose so that a
            # paradigm delivering through JSON text is not marked wrong for what
            # the serialisation did. Where a zero does lead, int() strips it and
            # the check must still refuse, which the case above covers as well.
            if any(value.startswith("0") for value in values):
                yield f"{column.name} as numbers", [
                    row | {column.name: int(value)} if value.isdigit() else row
                    for row, value in zip(rows, values)
                ]


def test_near_misses_are_rejected_at_every_size_where_they_differ(answers):
    """A wrong answer can coincide with the right one at some sizes: a share of
    all the deposits is the county's share when the scope is one county. So each
    is checked at every size, rejected wherever it differs, and must differ at
    one size at least, or it tests nothing."""
    task, source, rows = answers
    differs_somewhere = set()
    for size in task.sizes:
        expected = rows[size.label]
        near_misses = dict(_generic_near_misses(task, expected))
        near_misses |= {
            label: change(deepcopy(expected)) for label, change in task.near_misses.items()
        }
        near_misses |= {
            label: task.expected_rows(size, source, build=build)
            for label, build in task.misreadings.items()
        }
        for label, wrong in near_misses.items():
            if wrong == expected:
                continue
            differs_somewhere.add(label)
            assert not task.check(wrong, expected).success, (size.label, label)
    declared = set(task.near_misses) | set(task.misreadings)
    assert declared <= differs_somewhere, declared - differs_somewhere


def test_a_written_case_module_exposes_the_case_contract():
    from cases.table_delivery import branch_deposit_shares_10 as case

    (expected,) = case.ground_truth()
    names = [variable.name for variable in case.variables]
    assert case.validate(dict(zip(names, [expected]))).success
    assert set(case.validators) == {"validate"}


def test_a_drawdown_computed_from_the_delivered_growth_is_accepted():
    """A column derived from another delivered column must survive that column's rounding."""
    from cases.table_delivery._market_growth_drawdown import TASK

    source = TASK.load()
    for size in TASK.sizes:
        expected = TASK.expected_rows(size, source)
        peak, recomputed = 0.0, []
        for row in expected:
            peak = max(peak, row["growth_of_dollar"])
            recomputed.append(row | {"drawdown": row["growth_of_dollar"] / peak - 1})
        assert TASK.check(recomputed, expected).success, size.label
