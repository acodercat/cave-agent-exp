from typing import List, Dict, Tuple, Set, Union, Any, get_origin, get_args, Optional, NamedTuple
from enum import Enum
import typing

class ErrorType(Enum):
    MISSING_FUNCTION = "missing_function"  # Expected function call is missing
    MISSING_ARGUMENT = "missing_argument"  # Expected argument is missing
    WRONG_ARGUMENT_TYPE = "wrong_argument_type"  # Wrong type of argument
    WRONG_ARGUMENT_VALUE = "wrong_argument_value"  # Wrong value of argument

# Define a validation error structure
class ValidationError(NamedTuple):
    error_type: ErrorType
    message: str
    call_index: Optional[int] = None
    arg_name: Optional[str] = None

def _get_type_name(type_obj: type) -> str:
    # This function is used to convert a type object (e.g., int, List[float]) into a string that can be parsed by eval().
    # It prioritizes standard typing module string representations.
    if hasattr(type_obj, '__origin__') and type_obj.__origin__ is not None:
        # For typing generics like List[float], Dict[str, int]
        return str(type_obj).replace('typing.', '')
    elif hasattr(type_obj, '__name__'):
        # For built-in types like int, str, float, bool
        return type_obj.__name__
    elif type_obj is type(None): # Specific handling for NoneType
        return 'None'
    else:
        # Fallback for other types, attempting to clean if it's already a <class 'X'> string repr
        s_type_obj = str(type_obj)
        if s_type_obj.startswith("<class '") and s_type_obj.endswith("'>"):
            return s_type_obj[8:-2] # Remove "<class '" and "'>"
        return s_type_obj.replace('typing.', '')


def restore_type(type_str: str) -> Any:
    # --- Enhanced Pre-processing for incoming type_str ---
    # This handles cases where type_str might come in as "<class 'int'>" or "NoneType" etc.
    cleaned_type_str = type_str
    if cleaned_type_str.startswith("<class '") and cleaned_type_str.endswith("'>"):
        cleaned_type_str = cleaned_type_str[8:-2] # Remove "<class '" and "'>"
    
    # Specific mapping for common built-in types that might be represented differently
    type_name_map = {
        'NoneType': 'None',
        'int': 'int',
        'float': 'float',
        'str': 'str',
        'bool': 'bool',
        'list': 'List', # Map built-in list to typing.List if used as generic base
        'dict': 'Dict', # Map built-in dict to typing.Dict if used as generic base
        'tuple': 'Tuple',
        'set': 'Set'
    }
    cleaned_type_str_lower = cleaned_type_str.lower() # For case-insensitive matching if needed

    # Try mapping if it's a direct built-in type name after cleaning
    if cleaned_type_str in type_name_map:
        cleaned_type_str = type_name_map[cleaned_type_str]
    elif cleaned_type_str_lower in type_name_map: # Handle lower case e.g. "int" -> "Int"
        cleaned_type_str = type_name_map[cleaned_type_str_lower]
        
    # If it's a complex typing hint like 'List[float]', it remains as is for eval
    # If it's a simple type like 'int', it also remains as is
    final_type_str_to_eval = cleaned_type_str

    safe_globals = {
        'List': list,
        'Dict': dict,
        'Tuple': tuple,
        'Set': set,
        'Union': Union,
        'Any': Any,
        'int': int, 'float': float, 'str': str, 'bool': bool, 'None': type(None) # Make sure NoneType is covered by 'None' in safe_globals
    }
    try:
        # Use final_type_str_to_eval for evaluation
        return eval(final_type_str_to_eval, safe_globals)
    except (NameError, TypeError, SyntaxError) as e:
        # If it still fails, the type string is genuinely invalid or unresolvable
        raise ValueError(f"Invalid type string: {type_str} (Cleaned to: '{final_type_str_to_eval}'). Details: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error while restoring type: {type_str} (Cleaned to: '{final_type_str_to_eval}'). Details: {e}") from e

# The rest of the functions (_compare_single_value_deep, validate_argument) are the same as the previous version.
# They will call the updated restore_type.

def actual_in_expected_pattern(actual_value: Any, expected_pattern: List[Any]) -> bool:
    """
    Check if the actual value is in the expected pattern list.
    """
    if actual_value in expected_pattern:
        return True
    else:
        for pattern_item in expected_pattern:
            if isinstance(pattern_item, str) and isinstance(actual_value, str):
                if pattern_item.lower() == actual_value.lower():
                    return True
    return False

def _compare_single_value_deep(actual: Any, expected_pattern: Any, current_expected_type_str: str, param_path: str, call_index: int, function_name: str) -> Union[bool, ValidationError]:
    try:
        full_expected_type = restore_type(current_expected_type_str)
        origin_type = get_origin(full_expected_type)
        args_types = get_args(full_expected_type)

        if origin_type is None or origin_type is Union or origin_type is Any:
            if isinstance(expected_pattern, list) and not isinstance(actual, list):
                # if actual not in expected_pattern:
                if actual_in_expected_pattern(actual, expected_pattern) == False:
                    return ValidationError(
                        error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                        message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Actual value '{actual}' not in expected value list '{expected_pattern}'.",
                        call_index=call_index,
                        arg_name=param_path
                    )
                return True
            else:
                if actual != expected_pattern:
                    if isinstance(expected_pattern, str) and isinstance(actual, str):
                        if expected_pattern.lower() == actual.lower():
                            return True
                        else:
                            return ValidationError(
                                error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                                message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Expected value '{expected_pattern}', got '{actual}'.",
                                call_index=call_index,
                                arg_name=param_path
                            )
                    else:
                        return ValidationError(
                            error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                            message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Expected value '{expected_pattern}', got '{actual}'.",
                            call_index=call_index,
                            arg_name=param_path
                        )
                return True

        if origin_type is dict:
            if not isinstance(actual, dict):
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Expected dictionary, got non-dictionary type '{type(actual).__name__}'.",
                    call_index=call_index,
                    arg_name=param_path
                )
            if not (actual.keys() <= expected_pattern.keys() and expected_pattern.keys() <= actual.keys()):
                 return ValidationError(
                     error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                     message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Dictionary key sets do not match. Expected keys: {list(expected_pattern.keys())}, Actual keys: {list(actual.keys())}.",
                     call_index=call_index,
                     arg_name=param_path
                 )
            
            if len(args_types) != 2:
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Dict type hint incomplete, requires key and value types.",
                    call_index=call_index,
                    arg_name=param_path
                )
            expected_value_type_obj = args_types[1]

            for key in expected_pattern:
                if key not in actual:
                    return ValidationError(
                        error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                        message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}.{key}': Dictionary field is missing.",
                        call_index=call_index,
                        arg_name=f"{param_path}.{key}"
                    )
                
                if isinstance(expected_pattern[key], list) and not isinstance(actual[key], list):
                    # if actual[key] not in expected_pattern[key]:
                    if actual_in_expected_pattern(actual[key], expected_pattern[key]) == False:
                        return ValidationError(
                            error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                            message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}.{key}': Actual value '{actual[key]}' not in expected value list '{expected_pattern[key]}'.",
                            call_index=call_index,
                            arg_name=f"{param_path}.{key}"
                        )
                    continue

                next_expected_type_str = _get_type_name(expected_value_type_obj)
                comparison_result = _compare_single_value_deep(actual[key], expected_pattern[key], next_expected_type_str, f"{param_path}.{key}", call_index, function_name)
                if not comparison_result:
                    return comparison_result
            return True

        elif origin_type is list:
            if not isinstance(actual, list):
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Expected list, got non-list type '{type(actual).__name__}'.",
                    call_index=call_index,
                    arg_name=param_path
                )
            if len(actual) != len(expected_pattern):
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': List lengths do not match. Expected length: {len(expected_pattern)}, Actual length: {len(actual)}.",
                    call_index=call_index,
                    arg_name=param_path
                )

            if len(args_types) != 1:
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': List type hint incomplete, requires element type.",
                    call_index=call_index,
                    arg_name=param_path
                )
            expected_item_type_obj = args_types[0]

            for i in range(len(actual)):
                next_expected_type_str = _get_type_name(expected_item_type_obj)
                comparison_result = _compare_single_value_deep(actual[i], expected_pattern[i], next_expected_type_str, f"{param_path}[{i}]", call_index, function_name)
                if not comparison_result:
                    return comparison_result
            return True

        elif origin_type is tuple:
            # Accept both tuple and list since JSON arrays become Python lists
            if not isinstance(actual, (tuple, list)):
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Expected tuple, got non-tuple type '{type(actual).__name__}'.",
                    call_index=call_index,
                    arg_name=param_path
                )
            if len(actual) != len(expected_pattern):
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Tuple lengths do not match. Expected length: {len(expected_pattern)}, Actual length: {len(actual)}.",
                    call_index=call_index,
                    arg_name=param_path
                )

            expected_types_for_elements = [_get_type_name(t) for t in args_types] if args_types else []
            while len(expected_types_for_elements) < len(actual):
                expected_types_for_elements.append('Any')

            for i in range(len(actual)):
                next_expected_type_str = expected_types_for_elements[i]
                comparison_result = _compare_single_value_deep(actual[i], expected_pattern[i], next_expected_type_str, f"{param_path}[{i}]", call_index, function_name)
                if not comparison_result:
                    return comparison_result
            return True

        elif origin_type is set:
            # Accept both set and list since JSON arrays become Python lists
            if not isinstance(actual, (set, list)):
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Expected set, got non-set type '{type(actual).__name__}'.",
                    call_index=call_index,
                    arg_name=param_path
                )
            # Convert to sets for comparison
            actual_set = set(actual) if isinstance(actual, list) else actual
            expected_set = set(expected_pattern) if isinstance(expected_pattern, list) else expected_pattern
            if actual_set != expected_set:
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Sets are not equal. Expected: '{expected_set}', Actual: '{actual_set}'.",
                    call_index=call_index,
                    arg_name=param_path
                )
            return True
        
        else:
            if actual != expected_pattern:
                if isinstance(expected_pattern, str) and isinstance(actual, str):
                    if expected_pattern.lower() == actual.lower():
                        return True
                    else:
                        return ValidationError(
                            error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                            message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Expected value '{expected_pattern}', got '{actual}'.",
                            call_index=call_index,
                            arg_name=param_path
                        )
                return ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_VALUE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Expected value '{expected_pattern}', got '{actual}'.",
                    call_index=call_index,
                    arg_name=param_path
                )
            return True

    except (ValueError, RuntimeError) as e:
        return ValidationError(
            error_type=ErrorType.WRONG_ARGUMENT_VALUE,
            message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': Value validation failed due to type parsing exception. Details: {e}",
            call_index=call_index,
            arg_name=param_path
        )
    except Exception as e:
        import traceback
        return ValidationError(
            error_type=ErrorType.WRONG_ARGUMENT_VALUE,
            message=f"Call {function_name}(call_index={call_index}), Arg '{param_path}': An unexpected error occurred during recursive value validation. Details: {e}\n{traceback.format_exc()}",
            call_index=call_index,
            arg_name=param_path
        )


def validate_argument(actual_value: Any, expected_arg: Dict[str, Any], call_index: int, function_name: str) -> Union[Tuple[bool, str], Tuple[bool, ValidationError]]:
    expected_name = expected_arg.get("name", "unknown_param")
    expected_type_str = expected_arg["type"]
    expected_value = expected_arg["value"]

    # --- Type Validation ---
    try:
        full_expected_type = restore_type(expected_type_str)
        
        origin_type = get_origin(full_expected_type)
        args_types = get_args(full_expected_type)

        if origin_type is Union:
            if type(actual_value).__name__=="int" and expected_type_str == "float":
                return True, "Success" 
            if not isinstance(actual_value, full_expected_type):
                return False, ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Expected type '{expected_type_str}', got '{type(actual_value).__name__}'.",
                    call_index=call_index,
                    arg_name=expected_name
                )
        elif origin_type:
            if type(actual_value).__name__=="int" and expected_type_str == "float":
                return True, "Success" 
            if not isinstance(actual_value, origin_type) and not isinstance(actual_value, list):
                return False, ValidationError(
                    error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                    message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Expected container type '{expected_type_str}' (base type: '{origin_type.__name__}'), got '{type(actual_value).__name__}'.",
                    call_index=call_index,
                    arg_name=expected_name
                )

            if origin_type is list:
                if len(args_types) == 0:
                    pass  # No element type specified, skip element type validation
                elif all(isinstance(item, int) for item in actual_value) and _get_type_name(args_types[0]) == "float":
                    return True, "Success"
                else:
                    if not all(isinstance(item, args_types[0]) for item in actual_value):
                        for item in actual_value:
                            if not isinstance(item, args_types[0]):
                                return False, ValidationError(
                                    error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                                    message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': List inner element type mismatch. Expected inner element type: '{_get_type_name(args_types[0])}'.got '{type(item).__name__}'.",
                                    call_index=call_index,
                                    arg_name=expected_name
                                )
            elif origin_type is dict:
                if len(args_types) != 2:
                    return False, ValidationError(
                        error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                        message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Dict type hint incomplete, requires key and value types.",
                        call_index=call_index,
                        arg_name=expected_name
                    )
                expected_key_type = args_types[0]
                expected_value_type = args_types[1]
                for k, v in actual_value.items():
                    if not isinstance(k, expected_key_type) or not isinstance(v, expected_value_type):
                        return False, ValidationError(
                            error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                            message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Dict key-value type mismatch. Expected key type: '{_get_type_name(expected_key_type)}', Expected value type: '{_get_type_name(expected_value_type)}'.",
                            call_index=call_index,
                            arg_name=expected_name
                        )

            elif origin_type is tuple:
                # Accept both tuple and list since JSON arrays become Python lists
                if not isinstance(actual_value, (tuple, list)):
                    return False, ValidationError(
                        error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                        message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Expected tuple or list, got '{type(actual_value).__name__}'.",
                        call_index=call_index,
                        arg_name=expected_name
                    )
                # Handle variable-length tuple: Tuple[T, ...] or Tuple[T] (single type = homogeneous)
                if actual_value is not None and len(args_types) > 0 and (args_types[-1] is Ellipsis or len(args_types) == 1):
                    expected_item_type = args_types[0]
                    if all(isinstance(item, int) for item in actual_value) and _get_type_name(expected_item_type) == "float":
                        pass
                    else:
                        if not all(isinstance(item, expected_item_type) for item in actual_value):
                            return False, ValidationError(
                                error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                                message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Tuple inner element type mismatch. Expected inner element type: '{_get_type_name(expected_item_type)}'.",
                                call_index=call_index,
                                arg_name=expected_name
                            )
                else:
                    if len(actual_value) != len(args_types):
                        return False, ValidationError(
                            error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                            message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Tuple length mismatch. Expected length: {len(args_types)}, Actual length: {len(actual_value)}.",
                            call_index=call_index,
                            arg_name=expected_name
                        )
                    for i, item in enumerate(actual_value):
                        if not isinstance(item, args_types[i]):
                            return False, ValidationError(
                                error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                                message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Tuple element at index {i} type mismatch. Expected type: '{_get_type_name(args_types[i])}'.",
                                call_index=call_index,
                                arg_name=expected_name
                            )
            elif origin_type is set:
                # Accept both set and list since JSON arrays become Python lists
                if not isinstance(actual_value, (set, list)):
                    return False, ValidationError(
                        error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                        message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Expected set or list, got '{type(actual_value).__name__}'.",
                        call_index=call_index,
                        arg_name=expected_name
                    )
                if len(args_types) > 0:
                    if all(isinstance(item, int) for item in actual_value) and _get_type_name(args_types[0]) == "float":
                        pass
                    else:
                        if not all(isinstance(item, args_types[0]) for item in actual_value):
                            return False, ValidationError(
                                error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                                message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Set inner element type mismatch. Expected inner element type: '{_get_type_name(args_types[0])}'.",
                                call_index=call_index,
                                arg_name=expected_name
                            )
        else:
            if not isinstance(actual_value, full_expected_type):
                if type(actual_value).__name__ == "int" and expected_type_str == "float":
                    return True, "Success"
                else:
                    return False, ValidationError(
                        error_type=ErrorType.WRONG_ARGUMENT_TYPE,
                        message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Expected type '{expected_type_str}', got '{type(actual_value).__name__}'.",
                        call_index=call_index,
                        arg_name=expected_name
                    )

    except ValueError as e:
        return False, ValidationError(
            error_type=ErrorType.WRONG_ARGUMENT_TYPE,
            message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Expected type definition is invalid. Details: {e}",
            call_index=call_index,
            arg_name=expected_name
        )
    except Exception as e:
        if "typing.Any" in str(e):
            return True, "Success"
        return False, ValidationError(
            error_type=ErrorType.WRONG_ARGUMENT_TYPE,
            message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': An unexpected error occurred during type validation. Details: {e}",
            call_index=call_index,
            arg_name=expected_name
        )

    # --- Value Validation ---
    if isinstance(expected_value, list):
        for pattern_item in expected_value:
            if isinstance(pattern_item, str) and isinstance(actual_value, str):
                if pattern_item.lower() == actual_value.lower():
                    return True, "Success"
            comparison_result = _compare_single_value_deep(actual_value, pattern_item, expected_type_str, expected_name, call_index, function_name)
            if isinstance(comparison_result, bool) and comparison_result:
                return True, "Success"
            elif isinstance(comparison_result, ValidationError):
                continue
        return False, ValidationError(
            error_type=ErrorType.WRONG_ARGUMENT_VALUE,
            message=f"Call {function_name}(call_index={call_index}), Arg '{expected_name}': Actual value: '{actual_value}' not found in any matching item in expected value list '{expected_value}'.",
            call_index=call_index,
            arg_name=expected_name
        )
    else:
        comparison_result = _compare_single_value_deep(actual_value, expected_value, expected_type_str, expected_name, call_index, function_name)
        if isinstance(comparison_result, bool) and comparison_result:
            return True, "Success"
        elif isinstance(comparison_result, ValidationError):
            return False, comparison_result

    return True, "Success"