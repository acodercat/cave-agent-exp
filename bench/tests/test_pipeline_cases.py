"""The last agent's question rejects the tables a broken crossing produces.

If it did not, every arm would pass and the study would be silent. So the check
here is not that a correct answer passes but that perturbing one — dropping a
row, halving the table, reading a zero-padded code as a number — stops it
passing. The perturbations are applied to the expected rows and the answers
recomputed from them, which is what a second agent handed that table would get.
"""

from copy import deepcopy

import pytest

from cases.pipeline import PIPELINE_SIZES
from cases.pipeline.follow_ups import FOLLOW_UPS
from cases.pipeline.stages import KEEP_LOWER_HALF
from core.pipeline import FollowUp
from core.table_delivery import CellKind


@pytest.fixture(scope="module", params=list(FOLLOW_UPS), ids=lambda pair: pair[0].name)
def task_answers(request):
    """One task, its follow-up, and the table its last agent answers from.

    The main study puts a narrower between the two, so what the last agent is
    handed is half of what the first one produced. That half is what these
    perturbations are applied to, because a question that separates on the whole
    table but not on the half would not separate in the study.
    """
    task, follow_up = request.param
    source = task.load()
    return task, follow_up, {
        label: KEEP_LOWER_HALF.select(task, task.expected_rows(task.size(label), source))
        for label in PIPELINE_SIZES
    }


def _verdict(follow_up: FollowUp, delivered: list[dict], expected: list[dict]):
    """The verdict on the answers a second agent would compute from ``delivered``."""
    outputs = dict(zip(follow_up.stores, follow_up.compute(delivered)))
    return follow_up.check(outputs, expected)



def test_the_right_answer_passes(task_answers):
    _, follow_up, rows = task_answers
    for label, expected in rows.items():
        assert _verdict(follow_up, deepcopy(expected), expected).success, label


def test_a_missing_output_is_not_a_wrong_one(task_answers):
    """A second agent that assigned nothing is refused, not scored as wrong."""
    _, follow_up, rows = task_answers
    verdict = follow_up.check({}, rows["250"])
    assert not verdict.success
    assert verdict.variables_not_set


def test_a_table_that_arrived_one_row_short_at_the_end_is_rejected(task_answers):
    """Truncation is the failure a channel with an output limit actually has.

    Only the tail: dropping an arbitrary row is not always visible, and which
    questions are blind to which rows is measured in
    ``test_the_rows_no_question_can_miss_are_the_ones_recorded`` rather than
    assumed away.
    """
    _, follow_up, rows = task_answers
    for label, expected in rows.items():
        assert not _verdict(follow_up, expected[:-1], expected).success, label


# How many rows each question cannot see the loss of, per size. Measured, not
# aspired to: a conditional count, a distinct count or a sum with zero terms can
# all be blind to one row. The study's channel failures are gross, so this is a
# recorded limit; it is pinned here so it cannot grow without being noticed.
BLIND_ROWS = {
    ("flood_claim_top_payments", "500"): 1,
    ("flood_claim_top_payments", "1k"): 7,
    ("county_sector_employment", "500"): 3,
    ("county_sector_employment", "1k"): 1,
    ("private_offerings", "250"): 7,
    ("private_offerings", "500"): 24,
    ("private_offerings", "1k"): 24,
}


def test_the_rows_no_question_can_miss_are_the_ones_recorded(task_answers):
    task, follow_up, rows = task_answers
    for label, expected in rows.items():
        full = follow_up.compute(expected)
        blind = sum(
            1 for index in range(len(expected))
            if follow_up.compute(expected[:index] + expected[index + 1:]) == full
        )
        assert blind == BLIND_ROWS.get((task.name, label), 0), (task.name, label, blind)


def test_a_table_that_arrived_half_length_is_rejected(task_answers):
    _, follow_up, rows = task_answers
    for label, expected in rows.items():
        if len(expected) < 2:
            continue
        assert not _verdict(follow_up, expected[: len(expected) // 2], expected).success, label


def test_no_answer_is_the_same_at_every_size(task_answers):
    """An answer the table never moves is dead weight in the verdict.

    It cannot show that a channel truncated, and three of the questions first
    written here had one: a state that led at every size, a month range a wider
    scope did not widen, a threshold one row in 251 crossed. The data was read
    again and the question changed, which is what this test is here to force.
    """
    _, follow_up, rows = task_answers
    answers = [follow_up.compute(expected) for expected in rows.values()]
    for index, answer in enumerate(follow_up.answers):
        assert len({values[index] for values in answers}) > 1, answer.name


def test_every_size_is_told_apart_from_every_other(task_answers):
    """A channel that delivered a different size's table cannot pass as this one."""
    _, follow_up, rows = task_answers
    answers = {label: tuple(follow_up.compute(expected)) for label, expected in rows.items()}
    assert len(set(answers.values())) == len(answers)


# The questions whose answer changes when a text-typed code is read as a number.
# A distinct count over such a column survives it — the same rows still fall into
# the same number of groups — so only a question that compares the code against
# its text notices, and exactly one does.
#
# It is worth being exact about what that one detects. `main_office_indicator`
# holds "0" and "1": single characters, with no leading zero to lose. What the
# question notices is `1 == "1"` being False, which is the cell's *type*, not the
# survival of an identifier's zeros. So this family has no measurement of
# leading-zero fidelity at all; it reads the text channel by whether the table
# crossed, and type fidelity is a limit to state rather than a result to report.
TYPE_SENSITIVE = {"branch_top_deposits"}


def test_a_text_code_read_as_a_number_is_caught_where_it_can_be(task_answers):
    task, follow_up, rows = task_answers
    padded = [
        column.name for column in task.columns
        if column.kind is CellKind.PADDED_IDENTIFIER
    ]
    if not padded:
        pytest.skip(f"{task.name} has no padded identifier")
    expected = rows["250"]
    as_numbers = [
        row | {
            name: int(row[name]) for name in padded
            if row[name] is not None and row[name].isdigit()
        }
        for row in expected
    ]
    caught = not _verdict(follow_up, as_numbers, expected).success
    assert caught == (task.name in TYPE_SENSITIVE), task.name


def test_the_first_stage_is_judged_by_the_task_s_own_validator(task_answers):
    """The delivered table is scored by the check the delivery study already uses.

    Which wrong tables that check rejects — a near miss, a misreading, a date
    delivered as a timestamp — is settled in ``tests/test_table_control_cases.py``
    and is not restated here. What matters to this family is that the first stage
    is not judged by some second, softer standard.
    """
    task, _, rows = task_answers
    for label, expected in rows.items():
        assert task.check(deepcopy(expected), expected).success, label
        assert not task.check(expected[:-1], expected).success, label


def test_the_middle_agent_s_answer_does_not_depend_on_the_order_it_received(task_answers):
    """The defect this rule replaced, checked against the real tables.

    ``validate_table`` matches rows on the key and ignores their order, and
    nineteen of the twenty-four first-stage questions never ask for an order. So
    the first agent's table can be judged correct in any order, and a middle-agent
    rule that read "the first half as they stand" scored a faithful agent as wrong
    whenever that order differed from the reference's.
    """
    task, _, rows = task_answers
    for label, handed in rows.items():
        # `rows` here is already what the middle agent hands on; rebuild its input.
        source = task.expected_rows(task.size(label))
        wanted = KEEP_LOWER_HALF.select(task, source)
        assert wanted == handed, label
        for order in (source[::-1], source[len(source) // 2:] + source[: len(source) // 2]):
            assert KEEP_LOWER_HALF.select(task, order) == wanted, label
