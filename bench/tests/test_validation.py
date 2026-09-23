import numpy as np
import pandas as pd
import pytest
from cave_agent import Variable

from core.types import Turn
from core.validation import (
    ValidatorResult,
    as_records,
    boolean_equal,
    datetime_equal,
    numeric_equal,
    select_extreme_key,
    turn_validator,
    validate_ordered_outputs,
    validate_table,
)


def test_datetime_equal_accepts_equivalent_iso_representations():
    expected = "2025-03-20T22:36:42.000Z"
    assert datetime_equal("2025-03-20 22:36:42+00:00", expected)
    assert datetime_equal(pd.Timestamp("2025-03-20 18:36:42-04:00"), expected)
    assert not datetime_equal("2025-03-20T22:36:43Z", expected)
    assert not datetime_equal("not-a-timestamp", expected)


def test_boolean_equal_accepts_numpy_boolean_but_not_truthy_lookalikes():
    assert boolean_equal(np.bool_(False), False)
    assert boolean_equal(True, True)
    assert not boolean_equal("False", False)
    assert not boolean_equal(1, True)


def test_zero_decimal_numeric_outputs_are_exact():
    assert numeric_equal(323, 323.0, decimals=0)
    assert not numeric_equal(322.6, 323, decimals=0)
    assert numeric_equal(3.2344, 3.234, decimals=3)


def test_extreme_selection_uses_natural_key_tie_breaking():
    values = {"WMT": 5.0, "COST": 5.0, "AAPL": 4.0}
    assert select_extreme_key(values) == "COST"
    assert select_extreme_key({("2020-04", "A"): -2, ("2020-03", "Z"): -2}, largest=False) == (
        "2020-03", "Z"
    )


def test_ordered_validator_returns_structured_variable_diagnostics():
    variables = [Variable("count", None, "count"), Variable("ratio", None, "ratio")]
    verdict = validate_ordered_outputs(
        {"count": 3, "ratio": 1.25}, variables, (3, 1.5), [0, 2]
    )
    assert not verdict.success
    assert verdict.variable_results["count"]["correct"] is True
    assert verdict.variable_results["ratio"]["correct"] is False
    missing = validate_ordered_outputs(
        {"count": None, "ratio": 1.5}, variables, (3, 1.5), [0, 2]
    )
    assert missing.variables_not_set
    assert missing.variable_results["count"] == {
        "is_set": False, "correct": False, "message": "not set",
    }


def test_a_turn_validator_checks_the_resolved_scope_not_an_empty_one():
    """A short-form turn declares no stores; judging nothing must be impossible.

    The evaluator and the verification channel both resolve the scope before
    calling a validator. If either stopped doing so, this check would silently
    receive `{}` and report a pass on an unanswered turn.
    """
    seen = {}

    def check(outputs):
        seen.update(outputs)
        return ValidatorResult(bool(outputs), "checked")

    class Runtime:
        def retrieve(self, name):
            return {"a": 1, "b": 2}[name]

    resolved = Turn(query="q", validator="validate", stores=["a", "b"])
    verdict = turn_validator(check)("response", Runtime(), resolved)
    assert verdict.success and seen == {"a": 1, "b": 2}

    # An unresolved turn is the failure mode being guarded against.
    seen.clear()
    unresolved = turn_validator(check)("response", Runtime(), Turn(query="q"))
    assert not unresolved.success and seen == {}


TABLE = Variable("branch_table", None, "Store a table.")
EXPECTED_ROWS = [
    {"branch_id": "b1", "county_fips": "02020", "deposits": 10, "share": 0.25, "note": None},
    {"branch_id": "b2", "county_fips": "02090", "deposits": 30, "share": 0.75, "note": "x"},
]
TABLE_DECIMALS = {"branch_id": None, "county_fips": None, "deposits": 0, "share": 2, "note": None}


def _validate_rows(rows):
    return validate_table(TABLE, rows, EXPECTED_ROWS, key=("branch_id",), decimals=TABLE_DECIMALS)


def _changed(index, **cells):
    rows = [dict(row) for row in EXPECTED_ROWS]
    rows[index].update(cells)
    return rows


def test_a_table_is_matched_by_key_whatever_the_row_order():
    verdict = _validate_rows(list(reversed(EXPECTED_ROWS)))
    assert verdict.success
    assert verdict.variable_results["branch_table"]["table"]["rows_delivered"] == 2


def test_cell_errors_are_counted_over_the_rows_that_matched():
    rows = _changed(0, share=0.9) + [{**EXPECTED_ROWS[0], "branch_id": "b9"}]
    table = _validate_rows(rows).variable_results["branch_table"]["table"]
    assert (table["rows_delivered"], table["rows_matched"]) == (3, 2)
    assert table["cell_errors"]["share"] == 1


def test_an_undelivered_table_is_an_unset_output():
    verdict = _validate_rows(None)
    assert not verdict.success and verdict.variables_not_set


@pytest.mark.parametrize("rows, column", [
    (_changed(0, county_fips="2020"), "county_fips"),    # the leading zero is part of the id
    (_changed(0, county_fips=2020), "county_fips"),      # a number is not an identifier
    (_changed(0, deposits=11), "deposits"),              # integers are exact
    (_changed(0, share=0.26), "share"),                  # one unit of the last decimal
    (_changed(0, note=0), "note"),                       # missing is not zero
    (_changed(1, note=None), "note"),                    # a value is not missing
])
def test_a_wrong_cell_fails_and_is_counted_under_its_column(rows, column):
    verdict = _validate_rows(rows)
    assert not verdict.success and not verdict.variables_not_set
    errors = verdict.variable_results["branch_table"]["table"]["cell_errors"]
    assert errors[column] == 1 and sum(errors.values()) == 1


def test_display_rounding_within_the_declared_decimals_passes():
    assert _validate_rows(_changed(0, share=0.2504)).success


@pytest.mark.parametrize("rows, field", [
    (EXPECTED_ROWS[:1], "rows_missing"),
    (EXPECTED_ROWS + [{**EXPECTED_ROWS[0], "branch_id": "b3"}], "rows_unexpected"),
    (EXPECTED_ROWS + EXPECTED_ROWS[:1], "rows_repeated"),
])
def test_missing_unexpected_and_repeated_rows_fail(rows, field):
    verdict = _validate_rows(rows)
    assert not verdict.success
    assert verdict.variable_results["branch_table"]["table"][field] == 1


def test_a_left_out_column_is_not_a_missing_value():
    rows = [{key: value for key, value in row.items() if key != "note"} for row in EXPECTED_ROWS]
    verdict = _validate_rows(rows)
    table = verdict.variable_results["branch_table"]["table"]
    assert not verdict.success
    assert table["columns_absent"]["note"] == 2 and table["cell_errors"]["note"] == 0


def test_an_undeclared_column_fails_the_table():
    rows = [row | {"branch_name": "Main"} for row in EXPECTED_ROWS]
    verdict = _validate_rows(rows)
    assert not verdict.success
    assert verdict.variable_results["branch_table"]["table"]["columns_unexpected"] == {
        "branch_name": 2,
    }


@pytest.mark.parametrize("missing", [float("nan"), np.nan, pd.NA, None])
def test_every_spelling_of_missing_is_missing_in_rows_as_in_a_frame(missing):
    rows = [dict(row) for row in EXPECTED_ROWS]
    rows[0]["note"] = missing
    assert _validate_rows(as_records(rows)).success
    frame = pd.DataFrame(rows)
    assert _validate_rows(as_records(frame)).success


def test_rows_can_be_matched_on_several_columns():
    expected = [{"county": "02020", "sector": "31-33", "jobs": 5},
                {"county": "02020", "sector": "44-45", "jobs": 7}]
    decimals = {"county": None, "sector": None, "jobs": 0}
    key = ("county", "sector")
    assert validate_table(TABLE, expected[::-1], expected, key=key, decimals=decimals).success
    renamed = [expected[0], {**expected[1], "sector": "44"}]
    verdict = validate_table(TABLE, renamed, expected, key=key, decimals=decimals)
    table = verdict.variable_results["branch_table"]["table"]
    assert (table["rows_missing"], table["rows_unexpected"]) == (1, 1)


def test_a_key_cell_that_is_not_a_scalar_fails_without_raising():
    verdict = _validate_rows(_changed(0, branch_id=["b1"]))
    assert not verdict.success
    assert verdict.variable_results["branch_table"]["table"]["rows_unexpected"] == 1


def test_something_that_is_not_a_table_fails_without_raising():
    assert not _validate_rows("b1,b2").success
    assert not _validate_rows([1, 2]).success


class TestTableRecords:
    def test_a_table_becomes_plain_rows_whatever_delivered_it(self):
        frame = pd.DataFrame({
            "county_fips": pd.array(["02020", "02090"], dtype="string"),
            "count": pd.array([4, None], dtype="Int64"),
            "share": [np.float64(0.25), np.nan],
        })
        assert as_records(frame) == [
            {"county_fips": "02020", "count": 4, "share": 0.25},
            {"county_fips": "02090", "count": None, "share": None},
        ]

    def test_values_are_plain_python_so_the_run_file_can_store_them(self):
        (row,) = as_records(pd.DataFrame({"n": np.array([7], dtype="int64")}))
        assert type(row["n"]) is int

    def test_anything_else_passes_through(self):
        assert as_records(3.5) == 3.5
        assert as_records(None) is None


def test_whole_numbers_are_compared_exactly_beyond_float_precision():
    assert not numeric_equal(2**53 + 1, 2**53, decimals=0)
    assert numeric_equal(2**53, float(2**53), decimals=0)
    assert numeric_equal(5, 5.0, decimals=0)
    assert not numeric_equal(5, 5.5, decimals=0)


def test_a_number_delivered_as_text_is_that_number():
    """A text channel can only encode a number as text; see core.validation.as_number."""
    assert numeric_equal("5761924.64", 5761924.64, decimals=2)
    assert numeric_equal(" 12 ", 12, decimals=0)
    assert numeric_equal(str(2**53 + 1), 2**53 + 1, decimals=0)
    assert not numeric_equal(str(2**53 + 1), 2**53, decimals=0)


def test_text_that_is_not_plainly_a_number_is_not_one():
    for delivered in ("5,761,924.64", "$5761924.64", "99%", "", "nan", "1e", None, True, [5]):
        assert not numeric_equal(delivered, 5761924.64, decimals=2), delivered


NUMBERED_ROWS = [
    {"branch_id": "17", "county_fips": "02020", "deposits": 10, "share": 0.25, "note": None},
    {"branch_id": "18", "county_fips": "02090", "deposits": 30, "share": 0.75, "note": "x"},
]


def _numbered(rows):
    return validate_table(TABLE, rows, NUMBERED_ROWS, key=("branch_id",), decimals=TABLE_DECIMALS)


def test_an_identifier_delivered_as_an_integer_keeps_its_digits():
    """Including in the key column, where the rows are matched."""
    assert _numbered([row | {"branch_id": int(row["branch_id"])} for row in NUMBERED_ROWS]).success


def test_a_padded_identifier_delivered_as_an_integer_has_lost_its_zeros():
    verdict = _numbered([row | {"county_fips": int(row["county_fips"])} for row in NUMBERED_ROWS])
    assert not verdict.success
    assert verdict.variable_results["branch_table"]["table"]["cell_errors"]["county_fips"] == 2


def test_a_padded_key_delivered_as_an_integer_matches_no_row():
    padded = [row | {"branch_id": f"0{row['branch_id']}"} for row in NUMBERED_ROWS]
    delivered = [row | {"branch_id": int(row["branch_id"])} for row in padded]
    verdict = validate_table(TABLE, delivered, padded, key=("branch_id",), decimals=TABLE_DECIMALS)
    assert not verdict.success
    assert verdict.variable_results["branch_table"]["table"]["rows_missing"] == 2
