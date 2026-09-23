from collections.abc import Hashable
from dataclasses import dataclass
import math
from numbers import Integral, Real
from typing import Any

import pandas as pd
import numpy as np


@dataclass
class ValidatorResult:
    success: bool
    message: str
    variables_not_set: bool = False
    variable_results: dict[str, dict[str, Any]] | None = None


def turn_validator(check):
    """Adapt an outputs-only check to the turn validator contract.

    A turn validator is called as `(response, runtime, turn)`, which is what a
    case needs when it must inspect the runtime itself. Most cases only compare
    the values the turn asked the agent to store, so they write that comparison
    against a plain dict and wrap it here; the retrieval and the turn's `stores`
    list stay in one place instead of being repeated per case.

    `response` is deliberately not forwarded: a validator must not read prose to
    decide whether a number is right (CASE_DESIGN_STANDARD P2). A case that
    genuinely needs the response or the live runtime registers its own
    three-argument callable in `validators` instead of calling this.
    """
    def validate_turn(response, runtime, turn):
        names = turn.stores if turn and turn.stores else []
        return check({name: runtime.retrieve(name) for name in names})

    return validate_turn


def finite_number(value) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, Real)
        and math.isfinite(float(value))
    )


def _whole(value) -> bool:
    return isinstance(value, Integral) or (isinstance(value, float) and value.is_integer())


def as_number(value):
    """A delivered cell read as a number, or None when it does not hold one.

    A channel that delivers through text can only encode a number as text, and
    the host reads a delivered cell against the output contract, so "5761924.64"
    is that number and not a formatting failure. Only plain numeric text counts:
    no thousands separators, no currency, no percent. An integer is parsed as an
    integer, so text for 2**53 + 1 keeps the exactness float would lose.
    """
    if finite_number(value):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    try:
        return int(text)
    except ValueError:
        pass
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def numeric_equal(actual, expected, *, decimals: int) -> bool:
    actual, expected = as_number(actual), as_number(expected)
    if actual is None or expected is None:
        return False
    if decimals < 0:
        raise ValueError("decimals must be non-negative")
    if decimals == 0:
        # Counts and other zero-decimal outputs are deterministic in the frozen
        # data, so there is no tolerance. Whole numbers are compared as integers:
        # through float, 2**53 + 1 and 2**53 are the same number.
        if _whole(actual) and _whole(expected):
            return int(actual) == int(expected)
        return float(actual) == float(expected)
    return abs(float(actual) - float(expected)) <= 0.6 * 10 ** (-decimals)


def datetime_equal(actual, expected) -> bool:
    """Compare timestamp-like values by instant rather than ISO formatting."""
    if actual is None or expected is None or isinstance(actual, bool):
        return False
    try:
        actual_timestamp = pd.to_datetime(actual, utc=True)
        expected_timestamp = pd.to_datetime(expected, utc=True)
    except (TypeError, ValueError, OverflowError):
        return False
    if pd.isna(actual_timestamp) or pd.isna(expected_timestamp):
        return False
    return bool(actual_timestamp == expected_timestamp)


def boolean_equal(actual, expected: bool) -> bool:
    """Accept Python and NumPy booleans without accepting truthy strings/ints."""
    return isinstance(actual, (bool, np.bool_)) and bool(actual) is expected


def select_extreme_key(values: dict, *, largest: bool = True):
    """Select an extremum, breaking a tie by the key itself.

    The tie is broken by ``min`` over the keys as they are, so a question built
    on this must state the rule in those terms. For text keys that is
    alphabetical order; for keys that are text but read as numbers — an FDIC
    certificate, a NAICS code — "9" sorts after "10", so a question promising
    "the lower number" would not be answered by this. Say "the one that sorts
    first" instead, or key the mapping by something already numeric.
    """
    if not values:
        raise ValueError("cannot select an extremum from an empty mapping")
    extreme = (max if largest else min)(values.values())
    tied = [key for key, value in values.items() if value == extreme]
    return min(tied)


def validate_ordered_outputs(
    outputs: dict,
    variables,
    expected,
    decimals: list[int | None],
) -> ValidatorResult:
    """Validate a case's ordered scalar outputs with pinned numeric precision.

    ``None`` means exact equality. Numeric slots reject booleans, NaN and strings.
    The helper deliberately does not coerce dates or labels; cases needing semantic
    timestamp or alias handling should keep a case-specific validator.
    """
    if not (len(variables) == len(expected) == len(decimals)):
        raise ValueError("variables, expected values and decimals must have equal length")
    errors = []
    variable_results = {}
    missing = False
    for variable, target, places in zip(variables, expected, decimals):
        actual = outputs.get(variable.name)
        if actual is None:
            missing = True
            variable_results[variable.name] = {
                "is_set": False, "correct": False, "message": "not set",
            }
            continue
        matches = actual == target if places is None else numeric_equal(
            actual, target, decimals=places
        )
        if isinstance(matches, np.bool_):
            matches = bool(matches)
        if not matches:
            formatted = repr(target) if places is None else f"{target:.{places}f}"
            message = f"{variable.name}={actual!r}, expected {formatted}"
            errors.append(message)
        else:
            message = "correct"
        variable_results[variable.name] = {
            "is_set": True, "correct": bool(matches), "message": message,
        }
    message = "required output not set" if missing else "; ".join(errors) or "correct"
    return ValidatorResult(
        not missing and not errors,
        message,
        missing,
        variable_results,
    )


def _plain(value: Any) -> Any:
    """A cell as a plain Python value, with every spelling of missing as None."""
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _is_rows(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(row, dict) for row in value)


def as_records(value: Any) -> Any:
    """A table as a list of plain row dicts; anything else unchanged.

    One stored form for a table, whichever channel delivered it, so validators
    and the replayed verification read the same thing from all of them. Rows
    delivered as rows are normalised exactly as a DataFrame's are: a NaN, a
    pandas NA or a NaT is a missing cell whether it arrived in a DataFrame, in
    a list the agent built, or as the NaN token Python's JSON reader accepts.
    """
    if isinstance(value, pd.DataFrame):
        rows = value.astype(object).to_dict("records")
    elif _is_rows(value):
        rows = value
    else:
        return value
    return [{str(column): _plain(cell) for column, cell in row.items()} for row in rows]


def _cell_matches(actual, expected, decimals: int | None) -> bool:
    if expected is None:
        return actual is None
    if decimals is not None:
        return numeric_equal(actual, expected, decimals=decimals)
    # Exact cells are identifiers and labels, read as the text the column
    # declares: a JSON integer for an identifier is that identifier's digits.
    # What a channel loses still shows, because the digits must match: 2020 has
    # lost the zero "02020" carries, and 2020.0 is not a set of digits at all.
    if isinstance(expected, str):
        return _exact_text(actual) == expected
    return type(actual) is type(expected) and actual == expected


def _exact_text(value):
    """A cell of an exact column as the text it declares, or None.

    An integer is its digits, which is how a JSON channel can encode an
    identifier; a float is not a set of digits, and neither is anything else.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, Integral) and not isinstance(value, bool):
        return str(int(value))
    return None


def validate_table(
    variable, actual, expected: list[dict], *, key: tuple[str, ...],
    decimals: dict[str, int | None],
) -> ValidatorResult:
    """Validate a delivered table against the expected rows, cell by cell.

    ``actual`` is the table as stored: a list of row dicts (see
    :func:`as_records`). ``decimals`` names every column the table has, each
    compared exactly when its entry is None and to that many decimals otherwise.

    The delivered table must have exactly those columns: a row that leaves one
    out, or carries one more, fails the table, and a cell left out is not the
    same as a cell given as missing. Rows are matched on the ``key`` columns and
    their order is ignored; a missing, unexpected or repeated key fails the
    table. A cell expected missing must be missing.

    The counts go into ``variable_results`` so a study can report where a
    delivery channel loses rows, columns and cells, not only whether it failed.
    Cell errors are counted over the delivered rows that matched an expected
    row, ``rows_matched``, which is the denominator of a cell error rate.
    """
    name = variable.name
    if actual is None:
        return ValidatorResult(False, "required output not set", True, {
            name: {"is_set": False, "correct": False, "message": "not set"},
        })

    def failed(message: str, table: dict | None = None) -> ValidatorResult:
        item = {"is_set": True, "correct": False, "message": message}
        return ValidatorResult(False, message, False, {name: item | {"table": table or {}}})

    if not isinstance(actual, list) or not all(isinstance(row, dict) for row in actual):
        return failed(f"{name} is not a table of rows")
    def key_of(row: dict) -> tuple:
        # Both sides are keyed the same way, so a key read per the contract
        # matches — an identifier delivered as a JSON integer is its digits —
        # while one a channel changed does not, and "02020" stays apart from
        # 2020. A list or an object matches no expected key, and must not stop
        # the comparison.
        cells = (row.get(column) for column in key)
        return tuple(
            _exact_text(cell) or (cell if isinstance(cell, Hashable) else repr(cell))
            for cell in cells
        )

    columns = set(decimals)
    keys = [key_of(row) for row in actual]
    wanted = {key_of(row): row for row in expected}
    table = {
        "rows_expected": len(expected), "rows_delivered": len(actual),
        "rows_missing": len(wanted.keys() - set(keys)),
        "rows_unexpected": len(set(keys) - wanted.keys()),
        "rows_repeated": len(keys) - len(set(keys)),
        "rows_matched": sum(key in wanted for key in keys),
        # Rows that leave a declared column out, and rows that add an undeclared one.
        "columns_absent": {
            column: sum(column not in row for row in actual) for column in sorted(columns)
        },
        "columns_unexpected": {
            column: sum(column in row for row in actual)
            for column in sorted({name for row in actual for name in row} - columns)
        },
    }
    cell_errors = {column: 0 for column in decimals if column not in key}
    for row in actual:
        target = wanted.get(key_of(row))
        for column in cell_errors if target else ():
            # A column the row leaves out is counted under columns_absent, once.
            if column in row and not _cell_matches(row[column], target[column], decimals[column]):
                cell_errors[column] += 1
    table["cell_errors"] = cell_errors
    problems = [f"{count} {label}" for label, count in (
        ("rows missing", table["rows_missing"]), ("rows unexpected", table["rows_unexpected"]),
        ("rows repeated", table["rows_repeated"]),
        *((f"rows without column {column}", count)
          for column, count in table["columns_absent"].items()),
        *((f"rows with undeclared column {column}", count)
          for column, count in table["columns_unexpected"].items()),
        *((f"wrong cells in {column}", count) for column, count in cell_errors.items()),
    ) if count]
    if problems:
        return failed(f"{name}: " + ", ".join(problems), table)
    return ValidatorResult(True, "correct", False, {
        name: {"is_set": True, "correct": True, "message": "correct", "table": table},
    })
