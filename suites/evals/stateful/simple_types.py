"""
Simple Types - Stateful Benchmark

Tests: int, float, str, bool, list, dict operations across turns.
"""

from typing import List
from cave_agent import Variable, IPythonRuntime
from core.validation import ValidatorResult
from core.types import Turn, ToolCall


# ============================================================================
# INITIAL STATE - One variable per type
# ============================================================================

number = 10          # int
value = 19.99        # float
text = "Hello"       # str
flag = False         # bool
items = [1, 2, 3]    # list
data = {"name": "Alice", "age": 25, "scores": {"math": 85, "english": 90}}  # dict


# ============================================================================
# VALIDATORS - Integer
# ============================================================================

def validate_int_add(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("number")
    return ValidatorResult(val == 25, f"number = {val}, expected 25")

def validate_int_multiply(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("number")
    return ValidatorResult(val == 75, f"number = {val}, expected 75")

def validate_int_modulo(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("number")
    return ValidatorResult(val == 5, f"number = {val}, expected 5")


def validate_int_abs(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("number")
    return ValidatorResult(val == 25, f"number = {val}, expected 25")

def validate_int_floor_div(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("number")
    return ValidatorResult(val == 6, f"number = {val}, expected 6")

def validate_int_power(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("number")
    return ValidatorResult(val == 36, f"number = {val}, expected 36")


# ============================================================================
# VALIDATORS - Float
# ============================================================================

def validate_float_add(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("value")
    return ValidatorResult(abs(val - 22.49) < 0.01, f"value = {val}, expected 22.49")

def validate_float_discount(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("value")
    return ValidatorResult(abs(val - 17.992) < 0.01, f"value = {val}, expected 17.992")

def validate_float_round(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("value")
    return ValidatorResult(val == 17.99, f"value = {val}, expected 17.99")


def validate_float_c_to_f(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("value")
    expected = 36.5 * 9/5 + 32  # 97.7
    return ValidatorResult(abs(val - expected) < 0.1, f"value = {val}, expected {expected:.1f}")

def validate_float_add_temp(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("value")
    return ValidatorResult(abs(val - 100.0) < 0.1, f"value = {val}, expected 100.0")

def validate_float_f_to_c(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("value")
    expected = (100 - 32) * 5/9  # 37.78
    return ValidatorResult(abs(val - expected) < 0.1, f"value = {val}, expected {expected:.2f}")


# ============================================================================
# VALIDATORS - String
# ============================================================================

def validate_str_append(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("text")
    return ValidatorResult(val == "Hello World", f"text = '{val}'")

def validate_str_upper(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("text")
    return ValidatorResult(val == "HELLO WORLD", f"text = '{val}'")

def validate_str_replace(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("text")
    return ValidatorResult(val == "HELLO PYTHON", f"text = '{val}'")


def validate_str_split(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("text")
    return ValidatorResult(val == "a | b | c", f"text = '{val}'")

def validate_str_sort(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("text")
    return ValidatorResult(val == "a | b | c", f"text = '{val}'")

def validate_str_reverse(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("text")
    return ValidatorResult(val == "c | b | a", f"text = '{val}'")


# ============================================================================
# VALIDATORS - Bool
# ============================================================================

def validate_bool_toggle(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("flag")
    return ValidatorResult(val == True, f"flag = {val}, expected True")

def validate_bool_and(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("flag")
    return ValidatorResult(val == True, f"flag = {val}, expected True")

def validate_bool_toggle2(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("flag")
    return ValidatorResult(val == False, f"flag = {val}, expected False")


def validate_bool_or(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("flag")
    return ValidatorResult(val == True, f"flag = {val}, expected True")

def validate_bool_and_false(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("flag")
    return ValidatorResult(val == False, f"flag = {val}, expected False")

def validate_bool_not(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("flag")
    return ValidatorResult(val == True, f"flag = {val}, expected True")


# ============================================================================
# VALIDATORS - List
# ============================================================================

def validate_list_append(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("items")
    return ValidatorResult(val == [1, 2, 3, 4, 5, 6], f"items = {val}")

def validate_list_remove(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("items")
    return ValidatorResult(val == [2, 3, 4, 5, 6], f"items = {val}")

def validate_list_reverse(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("items")
    return ValidatorResult(val == [6, 5, 4, 3, 2], f"items = {val}")


def validate_list_sort(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("items")
    return ValidatorResult(val == [1, 2, 3, 5, 8], f"items = {val}")

def validate_list_sort_desc(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("items")
    return ValidatorResult(val == [8, 5, 3, 2, 1], f"items = {val}")

def validate_list_double(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("items")
    return ValidatorResult(val == [16, 10, 6, 4, 2], f"items = {val}")


# ============================================================================
# VALIDATORS - Dict
# ============================================================================

def validate_dict_add(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("data")
    ok = val.get("city") == "NYC"
    return ValidatorResult(ok, f"data['city'] = {val.get('city')}")

def validate_dict_update(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("data")
    ok = val.get("age") == 26
    return ValidatorResult(ok, f"data['age'] = {val.get('age')}")

def validate_dict_remove(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("data")
    ok = "city" not in val
    return ValidatorResult(ok, f"'city' in data = {'city' in val}")


def validate_dict_nested_update(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("data")
    ok = val.get("scores", {}).get("math") == 90
    return ValidatorResult(ok, f"data['scores']['math'] = {val.get('scores', {}).get('math')}")

def validate_dict_nested_add(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("data")
    ok = val.get("scores", {}).get("science") == 88
    return ValidatorResult(ok, f"data['scores']['science'] = {val.get('scores', {}).get('science')}")

def validate_dict_increment(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    val = runtime.retrieve("data")
    scores = val.get("scores", {})
    ok = scores.get("math") == 95 and scores.get("english") == 95 and scores.get("science") == 93
    return ValidatorResult(ok, f"scores = {scores}")


# ============================================================================
# EXPORTS
# ============================================================================

tools = []

variables = [
    Variable("number", number, "An integer (initial: 10)."),
    Variable("value", value, "A float (initial: 19.99)."),
    Variable("text", text, "A string (initial: 'Hello')."),
    Variable("flag", flag, "A boolean (initial: False)."),
    Variable("items", items, "A list (initial: [1, 2, 3])."),
    Variable("data", data, "A dict (initial: {'name': 'Alice', 'age': 25, 'scores': {'math': 85, 'english': 90}})."),
]

validators = {
    # Integer
    "validate_int_add": validate_int_add,
    "validate_int_multiply": validate_int_multiply,
    "validate_int_modulo": validate_int_modulo,
    "validate_int_abs": validate_int_abs,
    "validate_int_floor_div": validate_int_floor_div,
    "validate_int_power": validate_int_power,
    # Float
    "validate_float_add": validate_float_add,
    "validate_float_discount": validate_float_discount,
    "validate_float_round": validate_float_round,
    "validate_float_c_to_f": validate_float_c_to_f,
    "validate_float_add_temp": validate_float_add_temp,
    "validate_float_f_to_c": validate_float_f_to_c,
    # String
    "validate_str_append": validate_str_append,
    "validate_str_upper": validate_str_upper,
    "validate_str_replace": validate_str_replace,
    "validate_str_split": validate_str_split,
    "validate_str_sort": validate_str_sort,
    "validate_str_reverse": validate_str_reverse,
    # Bool
    "validate_bool_toggle": validate_bool_toggle,
    "validate_bool_and": validate_bool_and,
    "validate_bool_toggle2": validate_bool_toggle2,
    "validate_bool_or": validate_bool_or,
    "validate_bool_and_false": validate_bool_and_false,
    "validate_bool_not": validate_bool_not,
    # List
    "validate_list_append": validate_list_append,
    "validate_list_remove": validate_list_remove,
    "validate_list_reverse": validate_list_reverse,
    "validate_list_sort": validate_list_sort,
    "validate_list_sort_desc": validate_list_sort_desc,
    "validate_list_double": validate_list_double,
    # Dict
    "validate_dict_add": validate_dict_add,
    "validate_dict_update": validate_dict_update,
    "validate_dict_remove": validate_dict_remove,
    "validate_dict_nested_update": validate_dict_nested_update,
    "validate_dict_nested_add": validate_dict_nested_add,
    "validate_dict_increment": validate_dict_increment,
}
