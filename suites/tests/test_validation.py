"""Tests for validation logic."""

import pytest
from core.validation import (
    ErrorType,
    ValidationError,
    ValidatorResult,
    validate_function_calls,
    validate_arguments,
    normalize_value,
    is_type_compatible,
    calculate_mismatch_cost,
    is_finite_number,
    compare_numeric,
)
from core.types import ToolCall, ExpectedFunctionCall, ExpectedArgument


class TestErrorType:
    """Tests for ErrorType enum."""

    def test_error_types_exist(self):
        assert ErrorType.MISSING_FUNCTION.value == "missing_function"
        assert ErrorType.MISSING_ARGUMENT.value == "missing_argument"
        assert ErrorType.WRONG_ARGUMENT_TYPE.value == "wrong_argument_type"
        assert ErrorType.WRONG_ARGUMENT_VALUE.value == "wrong_argument_value"
        assert ErrorType.UNEXPECTED_ARGUMENT.value == "unexpected_argument"
        assert ErrorType.MISSING_VARIABLE_READ.value == "missing_variable_read"
        assert ErrorType.MISSING_VARIABLE_WRITE.value == "missing_variable_write"


class TestValidatorResult:
    """Tests for ValidatorResult namedtuple."""

    def test_success_result(self):
        result = ValidatorResult(success=True, message="")
        assert result.success is True
        assert result.message == ""

    def test_failure_result(self):
        result = ValidatorResult(success=False, message="Validation failed")
        assert result.success is False
        assert result.message == "Validation failed"


class TestValidationError:
    """Tests for ValidationError namedtuple."""

    def test_basic_error(self):
        error = ValidationError(
            error_type=ErrorType.MISSING_FUNCTION,
            message="Function not found"
        )
        assert error.error_type == ErrorType.MISSING_FUNCTION
        assert error.message == "Function not found"
        assert error.call_index is None
        assert error.arg_name is None

    def test_error_with_details(self):
        error = ValidationError(
            error_type=ErrorType.WRONG_ARGUMENT_VALUE,
            message="Wrong value",
            call_index=0,
            arg_name="city"
        )
        assert error.call_index == 0
        assert error.arg_name == "city"


class TestNormalizeValue:
    """Tests for normalize_value function."""

    def test_none(self):
        assert normalize_value(None) == "None"

    def test_integer(self):
        assert normalize_value(42) == "42"

    def test_float_whole_number(self):
        assert normalize_value(42.0) == "42"
        assert normalize_value(2750.0) == "2750"

    def test_float_decimal(self):
        assert normalize_value(3.14) == "3.14"
        assert normalize_value(5.60) == "5.6"  # trailing zero removed

    def test_string(self):
        assert normalize_value("hello") == "hello"
        assert normalize_value("  hello  ") == "hello"  # trimmed

    def test_boolean(self):
        assert normalize_value(True) == "True"
        assert normalize_value(False) == "False"

    def test_list(self):
        result = normalize_value([1, 2, 3])
        assert result == "['1', '2', '3']"

    def test_list_mixed(self):
        result = normalize_value([1, "hello", 3.14])
        assert "1" in result
        assert "hello" in result
        assert "3.14" in result

    def test_dict(self):
        result = normalize_value({"a": 1, "b": 2})
        assert "'a': '1'" in result
        assert "'b': '2'" in result

    def test_nested_dict(self):
        data = {"outer": {"inner": 42}}
        result = normalize_value(data)
        assert "outer" in result
        assert "inner" in result
        assert "42" in result

    def test_complex_nested(self):
        data = {
            "prices": {
                "AAPL": {"price": 185.5, "change": 2.3}
            }
        }
        result = normalize_value(data)
        assert "AAPL" in result
        assert "185.5" in result


class TestIsTypeCompatible:
    """Tests for is_type_compatible function."""

    def test_exact_match(self):
        assert is_type_compatible(42, "int") is True
        assert is_type_compatible("hello", "str") is True
        assert is_type_compatible([1, 2], "list") is True
        assert is_type_compatible({"a": 1}, "dict") is True

    def test_numeric_interchangeable(self):
        assert is_type_compatible(42, "float") is True
        assert is_type_compatible(3.14, "int") is True

    def test_string_numeric(self):
        assert is_type_compatible("42", "int") is True
        assert is_type_compatible("3.14", "float") is True
        assert is_type_compatible("not_a_number", "int") is False

    def test_incompatible_types(self):
        assert is_type_compatible("hello", "int") is False
        assert is_type_compatible([1, 2], "str") is False
        assert is_type_compatible({"a": 1}, "list") is False


class TestCalculateMismatchCost:
    """Tests for calculate_mismatch_cost function."""

    def test_no_expected_args(self):
        actual = ToolCall(function="func", arguments={"a": 1}, call_id="1")
        expected = ExpectedFunctionCall(name="func", arguments=[])
        cost = calculate_mismatch_cost(actual, expected)
        assert cost == 0.0

    def test_perfect_match(self):
        actual = ToolCall(function="func", arguments={"city": "London"}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="city", value="London", type="str")]
        )
        cost = calculate_mismatch_cost(actual, expected)
        assert cost == 0.0

    def test_missing_required_arg(self):
        actual = ToolCall(function="func", arguments={}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="city", required=True)]
        )
        cost = calculate_mismatch_cost(actual, expected)
        assert cost > 0

    def test_value_mismatch(self):
        actual = ToolCall(function="func", arguments={"city": "Paris"}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="city", value="London")]
        )
        cost = calculate_mismatch_cost(actual, expected)
        assert cost > 0


class TestValidateArguments:
    """Tests for validate_arguments function."""

    def test_no_expected_args(self):
        actual = ToolCall(function="func", arguments={"a": 1}, call_id="1")
        expected = ExpectedFunctionCall(name="func", arguments=[])
        errors = validate_arguments(actual, expected, 0, "func")
        assert len(errors) == 0

    def test_matching_args(self):
        actual = ToolCall(function="func", arguments={"city": "London"}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="city", value="London", type="str")]
        )
        errors = validate_arguments(actual, expected, 0, "func")
        assert len(errors) == 0

    def test_missing_required_arg(self):
        actual = ToolCall(function="func", arguments={}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="city", required=True)]
        )
        errors = validate_arguments(actual, expected, 0, "func")
        assert len(errors) == 1
        assert errors[0].error_type == ErrorType.MISSING_ARGUMENT

    def test_wrong_value(self):
        actual = ToolCall(function="func", arguments={"city": "Paris"}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="city", value="London")]
        )
        errors = validate_arguments(actual, expected, 0, "func")
        assert len(errors) == 1
        assert errors[0].error_type == ErrorType.WRONG_ARGUMENT_VALUE

    def test_wrong_type(self):
        actual = ToolCall(function="func", arguments={"count": "five"}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="count", type="int")]
        )
        errors = validate_arguments(actual, expected, 0, "func")
        assert len(errors) == 1
        assert errors[0].error_type == ErrorType.WRONG_ARGUMENT_TYPE

    def test_strict_args_unexpected(self):
        actual = ToolCall(function="func", arguments={"city": "London", "extra": "arg"}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="city", value="London")],
            strict_args=True
        )
        errors = validate_arguments(actual, expected, 0, "func")
        assert any(e.error_type == ErrorType.UNEXPECTED_ARGUMENT for e in errors)

    def test_non_strict_allows_extra(self):
        actual = ToolCall(function="func", arguments={"city": "London", "extra": "arg"}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="city", value="London")],
            strict_args=False
        )
        errors = validate_arguments(actual, expected, 0, "func")
        assert len(errors) == 0

    def test_optional_arg_missing(self):
        actual = ToolCall(function="func", arguments={}, call_id="1")
        expected = ExpectedFunctionCall(
            name="func",
            arguments=[ExpectedArgument(name="limit", required=False)]
        )
        errors = validate_arguments(actual, expected, 0, "func")
        assert len(errors) == 0


class TestValidateFunctionCalls:
    """Tests for validate_function_calls function."""

    def test_empty_calls(self):
        errors = validate_function_calls([], [])
        assert len(errors) == 0

    def test_matching_calls(self):
        actual = [ToolCall(function="get_weather", arguments={"city": "London"}, call_id="1")]
        expected = [ExpectedFunctionCall(
            name="get_weather",
            arguments=[ExpectedArgument(name="city", value="London")]
        )]
        errors = validate_function_calls(actual, expected)
        assert len(errors) == 0

    def test_missing_required_function(self):
        actual = []
        expected = [ExpectedFunctionCall(name="get_weather", required=True)]
        errors = validate_function_calls(actual, expected)
        assert len(errors) == 1
        assert errors[0].error_type == ErrorType.MISSING_FUNCTION

    def test_extra_actual_call_ok(self):
        actual = [
            ToolCall(function="get_weather", arguments={}, call_id="1"),
            ToolCall(function="get_time", arguments={}, call_id="2"),
        ]
        expected = [ExpectedFunctionCall(name="get_weather")]
        errors = validate_function_calls(actual, expected)
        # Extra calls are OK - we only check expected ones
        assert len(errors) == 0

    def test_multiple_same_function(self):
        actual = [
            ToolCall(function="send_message", arguments={"to": "Alice"}, call_id="1"),
            ToolCall(function="send_message", arguments={"to": "Bob"}, call_id="2"),
        ]
        expected = [
            ExpectedFunctionCall(
                name="send_message",
                arguments=[ExpectedArgument(name="to", value="Alice")]
            ),
            ExpectedFunctionCall(
                name="send_message",
                arguments=[ExpectedArgument(name="to", value="Bob")]
            ),
        ]
        errors = validate_function_calls(actual, expected)
        assert len(errors) == 0

    def test_not_enough_calls(self):
        actual = [
            ToolCall(function="send_message", arguments={"to": "Alice"}, call_id="1"),
        ]
        expected = [
            ExpectedFunctionCall(name="send_message", required=True),
            ExpectedFunctionCall(name="send_message", required=True),
        ]
        errors = validate_function_calls(actual, expected)
        assert any(e.error_type == ErrorType.MISSING_FUNCTION for e in errors)

    def test_complex_scenario(self):
        """Test a realistic scenario with multiple functions and arguments."""
        actual = [
            ToolCall(
                function="get_stock_prices",
                arguments={"symbols": ["AAPL", "GOOGL"]},
                call_id="1"
            ),
            ToolCall(
                function="calculate_portfolio_value",
                arguments={"holdings": {"AAPL": 100, "GOOGL": 50}},
                call_id="2"
            ),
        ]
        expected = [
            ExpectedFunctionCall(
                name="get_stock_prices",
                arguments=[ExpectedArgument(name="symbols", value=["AAPL", "GOOGL"], type="list")]
            ),
            ExpectedFunctionCall(
                name="calculate_portfolio_value",
                arguments=[ExpectedArgument(name="holdings", value={"AAPL": 100, "GOOGL": 50}, type="dict")]
            ),
        ]
        errors = validate_function_calls(actual, expected)
        assert len(errors) == 0

    def test_numeric_value_normalization(self):
        """Test that numeric values are normalized correctly."""
        actual = [
            ToolCall(
                function="set_temperature",
                arguments={"temp": 72.0},  # float
                call_id="1"
            ),
        ]
        expected = [
            ExpectedFunctionCall(
                name="set_temperature",
                arguments=[ExpectedArgument(name="temp", value=72)]  # int
            ),
        ]
        errors = validate_function_calls(actual, expected)
        # 72.0 should match 72 due to normalization
        assert len(errors) == 0


class TestIsFiniteNumber:
    """Tests for is_finite_number guard."""

    def test_accepts_int_and_float(self):
        assert is_finite_number(3) is True
        assert is_finite_number(3.14) is True
        assert is_finite_number(-0.0) is True

    def test_rejects_bool(self):
        # bool is an int subclass but must not count as numeric
        assert is_finite_number(True) is False
        assert is_finite_number(False) is False

    def test_rejects_none_nan_inf(self):
        assert is_finite_number(None) is False
        assert is_finite_number(float("nan")) is False
        assert is_finite_number(float("inf")) is False
        assert is_finite_number(float("-inf")) is False

    def test_rejects_non_numeric(self):
        assert is_finite_number("3") is False
        assert is_finite_number([1]) is False


class TestCompareNumeric:
    """Tests for compare_numeric signed/NaN-safe comparison."""

    def test_within_absolute_tolerance(self):
        assert compare_numeric(72.0, 72, tolerance=0.0) is True
        assert compare_numeric(72.05, 72, tolerance=0.1) is True
        assert compare_numeric(72.2, 72, tolerance=0.1) is False

    def test_signed_difference(self):
        # +12 vs -12 must fail — sign carries meaning
        assert compare_numeric(12, -12, tolerance=0.1) is False

    def test_decimals_mode(self):
        assert compare_numeric(2.7505, 2.75, decimals=2) is True
        assert compare_numeric(2.76, 2.75, decimals=2) is False

    def test_nan_none_nonnumeric_actual_fail(self):
        assert compare_numeric(float("nan"), 1.0, tolerance=0.1) is False
        assert compare_numeric(None, 1.0, tolerance=0.1) is False
        assert compare_numeric("1.0", 1.0, tolerance=0.1) is False
        assert compare_numeric(True, 1.0, tolerance=0.1) is False

    def test_requires_exactly_one_of_tolerance_decimals(self):
        with pytest.raises(ValueError):
            compare_numeric(1, 1)
        with pytest.raises(ValueError):
            compare_numeric(1, 1, tolerance=0.1, decimals=2)

    def test_expected_must_be_finite(self):
        with pytest.raises(ValueError):
            compare_numeric(1.0, float("nan"), tolerance=0.1)


class TestValidatorResultVariablesNotSet:
    """ValidatorResult gained a variables_not_set field (default False)."""

    def test_default_false_backcompat(self):
        r = ValidatorResult(True, "")
        assert r.variables_not_set is False
        r2 = ValidatorResult(False, "wrong value")
        assert r2.variables_not_set is False

    def test_explicit_flag(self):
        r = ValidatorResult(False, "not populated", variables_not_set=True)
        assert r.variables_not_set is True
