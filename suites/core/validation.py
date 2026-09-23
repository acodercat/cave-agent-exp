"""Function call validation logic for evaluating agent behavior.

This module also exposes NaN-safe numeric comparison helpers
(`is_finite_number`, `compare_numeric`) that custom validators should use
instead of hand-rolling `abs(a - b) > tol` — the hand-rolled form silently
passes NaN (`abs(nan - x) > tol` is False) and divides-by-zero on relative
tolerances. `compare_numeric` compares the **signed** difference, so values
whose sign carries meaning (returns, deltas, z-scores) fail when flipped.
"""

import math
from enum import Enum
from typing import List, Optional, NamedTuple
from core.types import ToolCall, ExpectedFunctionCall


try:
    import numpy as np
    _NUMPY_NUMERIC: tuple = (np.integer, np.floating)
except ImportError:
    _NUMPY_NUMERIC = ()


def is_finite_number(value) -> bool:
    """Return True iff `value` is a finite int/float (or numpy numeric).

    Rejects None, bool, NaN, +/-inf, strings, lists, and any non-numeric type.
    Use this as a NaN/None guard before any arithmetic comparison — without it,
    `abs(nan - x) > tol` is False, causing NaN to silently pass validation.
    """
    if value is None or isinstance(value, bool):
        return False
    if not isinstance(value, (int, float, *_NUMPY_NUMERIC)):
        return False
    return math.isfinite(float(value))


def compare_numeric(
    actual,
    expected,
    *,
    tolerance: Optional[float] = None,
    decimals: Optional[int] = None,
) -> bool:
    """Signed numeric equality within tolerance.

    Returns True iff `actual` is a finite number within tolerance of `expected`.
    Returns False (never raises) for None, NaN, +/-inf, bool, or non-numeric
    `actual` — so wrong-type and NaN agent outputs always fail validation.

    Use this in every validator instead of hand-rolling `abs(a - b) > tol`.
    Critically, this compares the **signed** difference: `+12` vs `-12` is a
    failure (the sign carries meaning for returns, deltas, z-scores, etc.).

    Specify exactly one of `tolerance` or `decimals`:
      - tolerance=0.1  -> absolute tolerance of +/-0.1
      - decimals=2     -> derives tolerance = 0.6 * 10^(-decimals) = 0.006,
                          i.e. the value must round to the same 2-dp number.
    For a relative tolerance (e.g. within 1%), pass
    `tolerance=abs(expected) * 0.01`.
    """
    if (tolerance is None) == (decimals is None):
        raise ValueError(
            "compare_numeric: pass exactly one of `tolerance=` or `decimals=`"
        )
    if tolerance is None:
        tolerance = 0.6 * (10 ** (-decimals))

    if not is_finite_number(expected):
        raise ValueError(
            f"compare_numeric: `expected` must be a finite number, got {expected!r}"
        )
    if not is_finite_number(actual):
        return False
    return abs(float(actual) - float(expected)) <= tolerance


class ErrorType(Enum):
    MISSING_FUNCTION = "missing_function"  # Expected function call is missing
    MISSING_ARGUMENT = "missing_argument"  # Expected argument is missing
    WRONG_ARGUMENT_TYPE = "wrong_argument_type"  # Wrong type of argument
    WRONG_ARGUMENT_VALUE = "wrong_argument_value"  # Wrong value of argument
    UNEXPECTED_ARGUMENT = "unexpected_argument"  # Unexpected argument
    MISSING_VARIABLE_READ = "missing_variable_read"  # Expected variable read is missing
    MISSING_VARIABLE_WRITE = "missing_variable_write"  # Expected variable write is missing

class ValidatorResult(NamedTuple):
    success: bool
    message: str
    # Distinguishes "agent never populated the required runtime variables"
    # (an infrastructure / refusal signal) from "agent computed values but
    # they're wrong" (a substantive failure). Defaults False for back-compat.
    variables_not_set: bool = False

# Define a validation error structure
class ValidationError(NamedTuple):
    error_type: ErrorType
    message: str
    call_index: Optional[int] = None
    arg_name: Optional[str] = None

def validate_function_calls(
    actual_calls: List[ToolCall],
    expected_calls: List[ExpectedFunctionCall]
) -> List[ValidationError]:
    """Validate function calls against expected calls."""
    from collections import defaultdict

    errors = []

    # Group actual calls by function name
    actual_groups = defaultdict(list)
    for call in actual_calls:
        actual_groups[call.function].append(call)

    expected_groups = defaultdict(list)
    for i, expected in enumerate(expected_calls):
        expected_groups[expected.name].append((i, expected))

    # Validate each expected function
    for func_name, expected_list in expected_groups.items():
        actual_list = actual_groups.get(func_name, [])

        # Simple strategy: as long as actual count >= expected count
        required_count = sum(1 for _, exp in expected_list if exp.required)

        if len(actual_list) < required_count:
            errors.append(ValidationError(
                error_type=ErrorType.MISSING_FUNCTION,
                message=f"Function '{func_name}' called {len(actual_list)} times, expected at least {required_count}",
            ))
            continue

        # Try to match: find the most similar actual for each expected
        used_actual_indices = set()

        for exp_index, expected in expected_list:
            best_match_idx = None
            best_score = float('inf')

            # Find the best matching actual call
            for j, actual in enumerate(actual_list):
                if j in used_actual_indices:
                    continue

                score = calculate_mismatch_cost(actual, expected)
                if score < best_score:
                    best_score = score
                    best_match_idx = j

            if best_match_idx is not None:
                # Validate parameters
                used_actual_indices.add(best_match_idx)
                argument_errors = validate_arguments(actual_list[best_match_idx], expected, exp_index, func_name)
                errors.extend(argument_errors)
            elif expected.required:
                errors.append(ValidationError(
                    error_type=ErrorType.MISSING_FUNCTION,
                    message=f"No suitable match found for required function call: {func_name}",
                    call_index=exp_index
                ))
    
    return errors

def calculate_mismatch_cost(actual: ToolCall, expected: ExpectedFunctionCall) -> float:
    """Calculate the mismatch cost between actual and expected arguments"""
    expected_args = expected.arguments
    if not expected_args:
        return 0.0

    total_cost = 0.0
    total_weight = 0.0

    for expected_arg in expected_args:
        expected_name = expected_arg.name
        weight = 1.0

        if expected_name not in actual.arguments:
            if expected_arg.required:
                total_cost += 1.0  # Fixed cost for missing required parameters
            total_weight += weight
            continue

        actual_value = actual.arguments[expected_name]

        # Value matching check
        if expected_arg.value is not None:
            if normalize_value(actual_value) != normalize_value(expected_arg.value):
                total_cost += 0.5  # Value mismatch cost
            total_weight += 1.0

        # Type matching check
        if expected_arg.type is not None:
            if not is_type_compatible(actual_value, expected_arg.type):
                total_cost += 0.3  # Type mismatch cost
            total_weight += 0.5

    return total_cost / max(total_weight, 1.0)

def normalize_value(value):
    """Normalize value for comparison, handle type conversion and nested structures"""
    
    # Handle None
    if value is None:
        return "None"
    
    # Handle numeric values
    if isinstance(value, (int, float)):
        # Convert both int and float to the same representation
        if isinstance(value, float):
            # Check if it's a whole number
            if value == int(value):
                return str(int(value))  # 2750.0 -> "2750"
            else:
                return f"{value:g}"     # Remove trailing zeros: 5.60 -> "5.6"
        else:
            return str(value)           # int -> str
    
    # Handle strings
    if isinstance(value, str):
        return value.strip()
    
    # Handle lists - recursively normalize each element
    if isinstance(value, list):
        normalized_list = [normalize_value(item) for item in value]
        return str(normalized_list)
    
    # Handle dictionaries - recursively normalize keys and values
    if isinstance(value, dict):
        # Sort keys to ensure consistent ordering
        normalized_dict = {}
        for k in sorted(value.keys()):
            # Normalize both key and value
            normalized_key = normalize_value(k) if not isinstance(k, str) else k
            normalized_value = normalize_value(value[k])
            normalized_dict[normalized_key] = normalized_value
        return str(normalized_dict)
    
    # Handle other types (bool, etc.)
    return str(value)

def is_type_compatible(actual_value, expected_type: str) -> bool:
    """
    Check if actual value's type is compatible with expected type.

    Handles common compatible type pairs:
    - int/float are interchangeable for numeric comparisons
    - str containing a number is compatible with int/float
    """
    actual_type = type(actual_value).__name__

    # Exact match
    if actual_type == expected_type:
        return True

    # Numeric types are interchangeable
    numeric_types = {'int', 'float'}
    if actual_type in numeric_types and expected_type in numeric_types:
        return True

    # String containing a number is compatible with numeric types
    if actual_type == 'str' and expected_type in numeric_types:
        try:
            float(actual_value)
            return True
        except (ValueError, TypeError):
            pass

    return False

def validate_arguments(actual: ToolCall,
                     expected: ExpectedFunctionCall,
                     call_index: int,
                     function_name: str) -> List[ValidationError]:
    """
    Validate arguments of a function call with smarter handling of renamed parameters.

    Args:
        actual: Actual function call record
        expected: Expected function call
        call_index: Index of this call
    """
    # Skip if no arguments are expected
    if not expected.arguments:
        return []
    actual_args = actual.arguments
    expected_args = expected.arguments
    errors = []

    # Keep track of matched actual arguments
    matched_actual_args = set()

    # First check all expected arguments
    for expected_arg in expected_args:
        expected_name = expected_arg.name

        is_required = expected_arg.required
        if is_required and expected_name not in actual_args:
            errors.append(ValidationError(
                error_type=ErrorType.MISSING_ARGUMENT,
                message=f"Call {function_name}(call_index={call_index}): Expected parameter '{expected_name}' not found in actual arguments",
                call_index=call_index,
                arg_name=expected_name
            ))
            continue

        if expected_name in actual_args:
            # Found a matching named parameter
            actual_value = actual_args[expected_name]
            matched_actual_args.add(expected_name)

            # Validate value if specified
            if expected_arg.value is not None:
                expected_value = expected_arg.value
                if normalize_value(actual_value) != normalize_value(expected_value):
                    errors.append(ValidationError(
                        error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                        message=f"Call {function_name}(call_index={call_index}): Expected value '{expected_value}', got '{actual_value}'",
                        call_index=call_index,
                        arg_name=expected_name
                    ))

            # Validate type if specified
            if expected_arg.type is not None:
                if actual_value is None:
                    continue
                if not is_type_compatible(actual_value, expected_arg.type):
                    actual_type = type(actual_value).__name__
                    errors.append(ValidationError(
                        error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                        message=f"Call {function_name}(call_index={call_index}): Expected type '{expected_arg.type}', got '{actual_type}'",
                        call_index=call_index,
                        arg_name=expected_name
                    ))

    # Only check for unexpected arguments if strict_args is enabled
    if expected.strict_args:
        if expected_args:  # If there are expected arguments, check if there are any unexpected actual arguments
            for actual_arg_name in actual_args:
                if actual_arg_name not in matched_actual_args:
                    errors.append(ValidationError(
                        error_type=ErrorType.UNEXPECTED_ARGUMENT,
                        message=f"Call {function_name}(call_index={call_index}): Unexpected argument '{actual_arg_name}' not in expected arguments",
                        call_index=call_index,
                        arg_name=actual_arg_name
                    ))
        else:  # If there are no expected arguments, actual should also have no arguments
            if actual_args:
                unexpected_args = list(actual_args.keys())
                errors.append(ValidationError(
                    error_type=ErrorType.UNEXPECTED_ARGUMENT,
                    message=f"Call {function_name}(call_index={call_index}): Expected no arguments, but got: {unexpected_args}",
                    call_index=call_index
                ))
    
    return errors