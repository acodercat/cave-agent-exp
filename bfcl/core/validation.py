from enum import Enum
from typing import List, Dict, Any, Optional, NamedTuple
from core.agent import AgentToolCall
# from agent import AgentToolCall
from core.complex_value_validation import validate_argument as complex_validate_argument
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

def validate_function_calls(actual_calls: List[AgentToolCall],
                          expected_calls: List[Dict[str, Any]]) -> List[ValidationError]:
    """
    Validate that actual function calls match expected calls.
    
    Args:
        actual_calls: List of actual function calls from the tracker
        expected_calls: List of expected function calls from ground_truths.json
        
    Returns:
        List of validation errors with structured type information
    """
    errors = []

    if len(actual_calls) < len(expected_calls):
        errors.append(ValidationError(
            error_type=ErrorType.MISSING_FUNCTION,
            message=f"Expected {len(expected_calls)} function calls, but got {len(actual_calls)}",
        ))
    # elif len(actual_calls) > len(expected_calls):
    #     actual_calls = actual_calls[:len(expected_calls)]
        
    # Create a copy of actual_calls to mark matches
    remaining_actual_calls = list(actual_calls)

    # For each expected call, try to find a matching actual call
    for i, expected in enumerate(expected_calls):
        expected_name = expected["name"]
        is_required = expected.get("required", True)  # Default to True if not specified
        
        # Find a matching function call by name
        match_found = False
        match_index = []
        
        for j, actual in enumerate(remaining_actual_calls):
            if actual.function == expected_name:
                match_found = True
                match_index.append(j)
                # break
        
        if not match_found:
            # Only report missing functions that are required
            if is_required:
                errors.append(ValidationError(
                    error_type=ErrorType.MISSING_FUNCTION,
                    message=f"Missing required function call: {expected_name}",
                    call_index=i
                ))
            continue
        
        argument_errors = []
        right_status = False
        # delete_index = []
        delete_index = None
        for index in match_index:
            # Validate arguments of the matching call
            actual_call = remaining_actual_calls[index]
            e = validate_arguments(actual_call, expected, i, expected_name+str(i))
            if e == []:
                # delete_index.append(index)
                delete_index = index
                right_status = True
                break
            else:
                argument_errors.extend(e)

        # Just for BFCL, we dont check if there are any extra calls in actual_calls        
        if right_status == False:
                errors.extend(argument_errors)
        
        # delete_index.sort(reverse=True)
        # for index in delete_index:
        #     remaining_actual_calls.pop(index)
        if delete_index is not None:
            remaining_actual_calls.pop(delete_index)

    return errors

# def calculate_mismatch_cost(actual: AgentToolCall, expected: Dict[str, Any]) -> float:
#     """Calculate the mismatch cost between actual and expected arguments"""
#     expected_args = expected.get("arguments", [])
#     if not expected_args:
#         return 0.0
    
#     total_cost = 0.0
#     total_weight = 0.0
    
#     for expected_arg in expected_args:
#         if "name" not in expected_arg:
#             continue
            
#         expected_name = expected_arg["name"]
#         weight = 1.0
        
#         if expected_name not in actual.arguments:
#             if expected_arg.get("required", True):
#                 total_cost += 1.0  # Fixed cost for missing required parameters
#             total_weight += weight
#             continue
        
#         actual_value = actual.arguments[expected_name]
        
#         # Value matching check
#         if "value" in expected_arg:
#             if normalize_value(actual_value) != normalize_value(expected_arg["value"]):
#                 total_cost += 0.5  # Value mismatch cost    
#             total_weight += 1.0
        
#         # Type matching check  
#         if "type" in expected_arg:
#             if not is_type_compatible(actual_value, expected_arg["type"]):
#                 total_cost += 0.3  # Type mismatch cost
#             total_weight += 0.5
    
#     return total_cost / max(total_weight, 1.0)

# def normalize_value(value):
#     """Normalize value for comparison, handle type conversion and nested structures"""
    
#     # Handle None
#     if value is None:
#         return "None"
    
#     # Handle numeric values
#     if isinstance(value, (int, float)):
#         # Convert both int and float to the same representation
#         if isinstance(value, float):
#             # Check if it's a whole number
#             if value == int(value):
#                 return str(int(value))  # 2750.0 -> "2750"
#             else:
#                 return f"{value:g}"     # Remove trailing zeros: 5.60 -> "5.6"
#         else:
#             return str(value)           # int -> str
    
#     # Handle strings
#     if isinstance(value, str):
#         return value.strip()
    
#     # Handle lists - recursively normalize each element
#     if isinstance(value, list):
#         normalized_list = [normalize_value(item) for item in value]
#         return str(normalized_list)
    
#     # Handle dictionaries - recursively normalize keys and values
#     if isinstance(value, dict):
#         # Sort keys to ensure consistent ordering
#         normalized_dict = {}
#         for k in sorted(value.keys()):
#             # Normalize both key and value
#             normalized_key = normalize_value(k) if not isinstance(k, str) else k
#             normalized_value = normalize_value(value[k])
#             normalized_dict[normalized_key] = normalized_value
#         return str(normalized_dict)
    
#     # Handle other types (bool, etc.)
#     return str(value)

# def is_type_compatible(actual_value, expected_type):
#     """More lenient type checking"""
#     actual_type = type(actual_value).__name__
#     if actual_type == expected_type:
#         return True
    
#     return False

def validate_arguments(actual: AgentToolCall,
                     expected: Dict[str, Any],
                     call_index: int,
                     function_name: str) -> List[ValidationError]:
    """
    Validate arguments of a function call with smarter handling of renamed parameters.
    
    Args:
        actual: Actual function call record
        expected: Expected function call
        call_index: Index of this call
    """
    actual_args = actual.arguments
    expected_args = expected.get("arguments", [])
    errors = []
    
    # Keep track of matched arguments on both sides
    matched_actual_args = set()
    matched_expected_args = set()
    
    # First check all expected arguments
    for arg_index, expected_arg in enumerate(expected_args):
        if "name" not in expected_arg:
            errors.append(ValidationError(
                error_type=ErrorType.MISSING_ARGUMENT,
                message=f"Call {function_name}(call_index={call_index}), Arg {arg_index+1}: Expected argument is missing required 'name' field",
                call_index=call_index
            ))
            continue
        
        expected_name = expected_arg["name"]

        is_required = expected_arg.get("required", True)  # Default to True if not specified
        if is_required and expected_name not in actual_args:
            errors.append(ValidationError(
                error_type=ErrorType.MISSING_ARGUMENT,
                message=f"Call {function_name}(call_index={call_index}): Expected parameter '{expected_name}' not found in actual arguments",
                call_index=call_index,
                arg_name=expected_name
            ))
            continue
        if is_required is False:
            continue
        
        if expected_name in actual_args:
            # Found a matching named parameter
            actual_value = actual_args[expected_name]
            matched_actual_args.add(expected_name)
            matched_expected_args.add(expected_name)

            if "value" in expected_arg and "type" in expected_arg:
                expected_value = expected_arg["value"]
                expected_type = expected_arg["type"]
                if isinstance(actual_value,str) and "^" in actual_value:
                    actual_value = actual_value.replace("^", "**")
                status,error = complex_validate_argument(actual_value, expected_arg, call_index, function_name)
                if status == False:
                    errors.append(error)
    
    return errors



if __name__ == "__main__":
    # actual_calls = [
    #     AgentToolCall(function="check_seat_availability", arguments={"flight_id": "LH797", "seat_class": "premium_economy"},call_id=0),
    #     AgentToolCall(function="check_seat_availability", arguments={"flight_id": "LH797"},call_id=1),
    # ]
    # expected_calls = [{"name": "check_seat_availability", "arguments": [{"name": "flight_id", "value": "LH797", "type": "str"}, {"name": "seat_class", "value": "premium_economy", "type": "str"}]}]
    # print(validate_function_calls(actual_calls, expected_calls))

    actual_calls = [AgentToolCall(function="weather_get_by_coordinates_date", arguments={"coordinates": [46.603354,1.888334], "date": "2019-12-13"}, call_id=0)]
    expected_calls = [{'name': 'weather_get_by_coordinates_date', 'arguments': [{'name': 'coordinates', 'value': [[46.603354,1.888334]], 'type': 'Tuple[float]', 'required': True}, {'name': 'date', 'value': '2019-12-13', 'type': 'str', 'required': True}]}]
    errors = validate_function_calls(actual_calls=actual_calls, expected_calls=expected_calls)
    print(errors)