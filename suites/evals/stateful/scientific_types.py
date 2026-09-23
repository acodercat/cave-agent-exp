"""
Scientific Types - Stateful Benchmark

Tests: pandas DataFrame, numpy ndarray, pandas Series.
"""

from typing import List
import pandas as pd
import numpy as np
from cave_agent import Variable, IPythonRuntime
from core.validation import ValidatorResult
from core.types import Turn, ToolCall


# ============================================================================
# INITIAL STATE
# ============================================================================

# Main DataFrame for various operations
df = pd.DataFrame({
    "category": ["Electronics", "Electronics", "Clothing", "Clothing", "Food"],
    "product": ["Phone", "Laptop", "Shirt", "Pants", "Apple"],
    "price": [500.0, 1200.0, 50.0, 80.0, 10.0],
    "quantity": [10, 5, 20, 15, 100]
})

# Second DataFrame for merge operations
df2 = pd.DataFrame({
    "product": ["Phone", "Laptop", "Shirt"],
    "supplier": ["SupA", "SupB", "SupA"]
})

# DataFrame with missing values for fillna/dropna operations
df_missing = pd.DataFrame({
    "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
    "age": [25.0, np.nan, 35.0, np.nan, 28.0],
    "score": [85.0, 90.0, np.nan, 78.0, np.nan]
})

# DataFrame for pivot operations
df_sales = pd.DataFrame({
    "region": ["North", "North", "South", "South", "East", "East"],
    "quarter": ["Q1", "Q2", "Q1", "Q2", "Q1", "Q2"],
    "sales": [100, 150, 200, 180, 120, 140]
})

# Second array for operations
array2 = np.array([1, 2, 3, 4, 5, 6, 7, 8])

# Matrix for dot product
matrix2 = np.array([
    [1, 0],
    [0, 1],
    [1, 1]
])

# Main array for matrix operations
matrix = np.array([
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
])

# Second array for operations
array = np.array([10, 25, 5, 30, 15, 8, 22, 3])

# Main Series
series = pd.Series([85, 92, 78, 95, 88], index=["a", "b", "c", "d", "e"], name="scores")

# Result variables (reused across conversations)
result_df = None
result_array = None
result_value = 0.0


# ============================================================================
# VALIDATORS - DataFrame Operations
# ============================================================================

def validate_df_add_column(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    d = runtime.retrieve("df")
    if "total" not in d.columns:
        return ValidatorResult(False, "Column 'total' not found")
    expected = [5000.0, 6000.0, 1000.0, 1200.0, 1000.0]
    actual = d["total"].tolist()
    ok = actual == expected
    return ValidatorResult(ok, f"total = {actual}")

def validate_df_filter(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    d = runtime.retrieve("df")
    ok = len(d) == 3 and all(t > 1000 for t in d["total"].tolist())
    return ValidatorResult(ok, f"df has {len(d)} rows with total > 1000")

def validate_df_sort(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    d = runtime.retrieve("df")
    totals = d["total"].tolist()
    ok = totals == sorted(totals, reverse=True)
    return ValidatorResult(ok, f"totals = {totals}")


# ============================================================================
# VALIDATORS - DataFrame Groupby
# ============================================================================

def validate_df_groupby(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_df")
    if r is None:
        return ValidatorResult(False, "result_df is None")
    # Electronics: 1700, Clothing: 130, Food: 10
    if isinstance(r, pd.Series):
        r = r.to_dict()
    elif isinstance(r, pd.DataFrame):
        r = r.set_index("category")["price"].to_dict() if "category" in r.columns else r.to_dict()
    expected = {"Electronics": 1700.0, "Clothing": 130.0, "Food": 10.0}
    ok = r == expected or (isinstance(r, dict) and all(abs(r.get(k, 0) - v) < 0.01 for k, v in expected.items()))
    return ValidatorResult(ok, f"grouped = {r}")

def validate_df_groupby_count(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Number of categories: 3
    ok = r == 3
    return ValidatorResult(ok, f"category count = {r}, expected 3")

def validate_df_groupby_max(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Max total price: Electronics = 1700
    ok = abs(r - 1700.0) < 0.01
    return ValidatorResult(ok, f"max = {r}, expected 1700.0")


# ============================================================================
# VALIDATORS - DataFrame Merge
# ============================================================================

def validate_df_merge(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_df")
    if r is None:
        return ValidatorResult(False, "result_df is None")
    ok = len(r) == 3 and "supplier" in r.columns
    return ValidatorResult(ok, f"merged has {len(r)} rows, columns: {r.columns.tolist()}")

def validate_df_merge_filter(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_df")
    if r is None:
        return ValidatorResult(False, "result_df is None")
    # Filter supplier == 'SupA': Phone, Shirt
    ok = len(r) == 2 and set(r["product"].tolist()) == {"Phone", "Shirt"}
    return ValidatorResult(ok, f"filtered to {r['product'].tolist()}")

def validate_df_merge_sum(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Sum of prices for SupA: 500 + 50 = 550
    ok = abs(r - 550.0) < 0.01
    return ValidatorResult(ok, f"sum = {r}, expected 550.0")


# ============================================================================
# VALIDATORS - ndarray Operations
# ============================================================================

def validate_array_multiply(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    m = runtime.retrieve("matrix")
    expected = np.array([[2, 4, 6], [8, 10, 12], [14, 16, 18]])
    ok = bool(np.array_equal(m, expected))
    return ValidatorResult(ok, f"matrix[0] = {m[0].tolist()}")

def validate_array_add(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    m = runtime.retrieve("matrix")
    expected = np.array([[12, 14, 16], [18, 20, 22], [24, 26, 28]])
    ok = bool(np.array_equal(m, expected))
    return ValidatorResult(ok, f"matrix[0] = {m[0].tolist()}")

def validate_array_transpose(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    m = runtime.retrieve("matrix")
    expected = np.array([[12, 18, 24], [14, 20, 26], [16, 22, 28]])
    ok = bool(np.array_equal(m, expected))
    return ValidatorResult(ok, f"matrix shape = {m.shape}")


# ============================================================================
# VALIDATORS - ndarray Reshape
# ============================================================================

def validate_array_reshape(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    ok = r.shape == (2, 4)
    return ValidatorResult(ok, f"shape = {r.shape}, expected (2, 4)")

def validate_array_sum_axis(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Sum along axis 1: [10+25+5+30, 15+8+22+3] = [70, 48]
    expected = np.array([70, 48])
    ok = bool(np.array_equal(r, expected))
    return ValidatorResult(ok, f"row sums = {r.tolist()}")

def validate_array_total(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Total: 70 + 48 = 118
    ok = r == 118
    return ValidatorResult(ok, f"total = {r}, expected 118")


# ============================================================================
# VALIDATORS - ndarray Boolean
# ============================================================================

def validate_array_bool_filter(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    expected = np.array([25, 30, 15, 22])
    ok = bool(np.array_equal(r, expected))
    return ValidatorResult(ok, f"filtered = {r.tolist()}")

def validate_array_bool_replace(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    a = runtime.retrieve("array")
    # 10 < 10 is False, so 10 stays. Values < 10 are 5, 8, 3 which become 0
    expected = np.array([10, 25, 0, 30, 15, 0, 22, 0])
    ok = bool(np.array_equal(a, expected))
    return ValidatorResult(ok, f"array = {a.tolist()}")

def validate_array_bool_mean(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Mean of non-zero: (10+25+30+15+22)/5 = 20.4
    ok = abs(r - 20.4) < 0.01
    return ValidatorResult(ok, f"mean = {r}, expected 20.4")


# ============================================================================
# VALIDATORS - Series Operations
# ============================================================================

def validate_series_add(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("series")
    expected = [90, 97, 83, 100, 93]
    ok = s.tolist() == expected
    return ValidatorResult(ok, f"series = {s.tolist()}")

def validate_series_clip(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("series")
    ok = bool(s.max() <= 100 and s.min() >= 80)
    return ValidatorResult(ok, f"min={s.min()}, max={s.max()}")

def validate_series_mean(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    s = runtime.retrieve("series")
    expected = s.mean()
    ok = abs(r - expected) < 0.01
    return ValidatorResult(ok, f"mean = {r}")


# ============================================================================
# VALIDATORS - Series Index
# ============================================================================

def validate_series_select(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Select b, c, d from original: 92, 78, 95
    if hasattr(r, 'tolist'):
        r = r.tolist()
    ok = list(r) == [92, 78, 95]
    return ValidatorResult(ok, f"selected = {list(r)}")

def validate_series_multiply(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("series")
    # b, c, d doubled: a=85, b=184, c=156, d=190, e=88
    expected = {"a": 85, "b": 184, "c": 156, "d": 190, "e": 88}
    ok = s.to_dict() == expected
    return ValidatorResult(ok, f"series = {s.to_dict()}")

def validate_series_sum(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Sum: 85 + 184 + 156 + 190 + 88 = 703
    ok = r == 703
    return ValidatorResult(ok, f"sum = {r}, expected 703")


# ============================================================================
# VALIDATORS - Series Boolean
# ============================================================================

def validate_series_bool_filter(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Values > 90 from original: 92, 95
    if hasattr(r, 'tolist'):
        r = r.tolist()
    ok = sorted(r) == [92, 95]
    return ValidatorResult(ok, f"filtered = {list(r)}")

def validate_series_bool_count(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Count > 90: 2
    ok = r == 2
    return ValidatorResult(ok, f"count = {r}, expected 2")

def validate_series_max(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    ok = r == 95
    return ValidatorResult(ok, f"max = {r}, expected 95")


# ============================================================================
# VALIDATORS - DataFrame Missing Values
# ============================================================================

def validate_df_fillna(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    d = runtime.retrieve("df_missing")
    # Check no NaN in age column after filling with 30
    ok = bool(not d["age"].isna().any() and d["age"].tolist() == [25.0, 30.0, 35.0, 30.0, 28.0])
    return ValidatorResult(ok, f"age = {d['age'].tolist()}")

def validate_df_dropna(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_df")
    if r is None:
        return ValidatorResult(False, "result_df is None")
    # After fillna on age: Alice, Bob, Diana have complete data (Charlie, Eve have NaN score)
    ok = bool(len(r) == 3 and not r.isna().any().any())
    return ValidatorResult(ok, f"rows without NaN = {len(r)}")

def validate_df_apply(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    d = runtime.retrieve("df_missing")
    # score doubled where not NaN
    ok = bool(d.loc[0, "score"] == 170.0 and d.loc[1, "score"] == 180.0)
    return ValidatorResult(ok, f"scores = {d['score'].tolist()}")


# ============================================================================
# VALIDATORS - DataFrame Pivot
# ============================================================================

def validate_df_pivot(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_df")
    if r is None:
        return ValidatorResult(False, "result_df is None")
    # Pivot: rows=region, columns=quarter, values=sales
    ok = bool(r.shape == (3, 2) or (hasattr(r, 'columns') and 'Q1' in r.columns.tolist()))
    return ValidatorResult(ok, f"pivot shape = {r.shape}")

def validate_df_pivot_sum(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Sum all sales: 100+150+200+180+120+140 = 890
    ok = r == 890
    return ValidatorResult(ok, f"total sales = {r}, expected 890")

def validate_df_pivot_max_region(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Max region total: South = 200+180 = 380
    ok = r == 380
    return ValidatorResult(ok, f"max region = {r}, expected 380")


# ============================================================================
# VALIDATORS - ndarray Advanced
# ============================================================================

def validate_array_concat(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Concatenate array and array2
    expected = np.array([10, 25, 5, 30, 15, 8, 22, 3, 1, 2, 3, 4, 5, 6, 7, 8])
    ok = bool(np.array_equal(r, expected))
    return ValidatorResult(ok, f"length = {len(r)}, expected 16")

def validate_array_slice(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Slice first 4 elements from result_array
    expected = np.array([10, 25, 5, 30])
    ok = bool(np.array_equal(r, expected))
    return ValidatorResult(ok, f"sliced = {r.tolist()}")

def validate_array_reverse(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Reverse the sliced array
    expected = np.array([30, 5, 25, 10])
    ok = bool(np.array_equal(r, expected))
    return ValidatorResult(ok, f"reversed = {r.tolist()}")


def validate_array_dot(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # matrix (3x3) @ matrix2 (3x2) = (3x2)
    m = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    m2 = np.array([[1, 0], [0, 1], [1, 1]])
    expected = m @ m2
    ok = bool(np.array_equal(r, expected))
    return ValidatorResult(ok, f"shape = {r.shape}, expected (3, 2)")

def validate_array_dot_sum(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Sum of dot product result
    m = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    m2 = np.array([[1, 0], [0, 1], [1, 1]])
    expected = int((m @ m2).sum())
    ok = r == expected
    return ValidatorResult(ok, f"sum = {r}, expected {expected}")

def validate_array_dot_max(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_value")
    # Max of dot product result
    m = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    m2 = np.array([[1, 0], [0, 1], [1, 1]])
    expected = int((m @ m2).max())
    ok = r == expected
    return ValidatorResult(ok, f"max = {r}, expected {expected}")


# ============================================================================
# VALIDATORS - Series Advanced
# ============================================================================

def validate_series_cumsum(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Cumsum of original series [85, 92, 78, 95, 88]
    expected = [85, 177, 255, 350, 438]
    if hasattr(r, 'tolist'):
        r = r.tolist()
    ok = list(r) == expected
    return ValidatorResult(ok, f"cumsum = {list(r)}")

def validate_series_diff(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Diff of original series (excluding first NaN)
    expected = [7, -14, 17, -7]  # 92-85, 78-92, 95-78, 88-95
    if hasattr(r, 'tolist'):
        r = r.tolist()
    # Handle NaN in first position
    actual = [x for x in r if not (isinstance(x, float) and np.isnan(x))]
    ok = actual == expected
    return ValidatorResult(ok, f"diff = {actual}")

def validate_series_rank(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_array")
    if r is None:
        return ValidatorResult(False, "result_array is None")
    # Rank of original series [85, 92, 78, 95, 88]: [2, 4, 1, 5, 3]
    expected = [2.0, 4.0, 1.0, 5.0, 3.0]
    if hasattr(r, 'tolist'):
        r = r.tolist()
    ok = list(r) == expected
    return ValidatorResult(ok, f"rank = {list(r)}")


# ============================================================================
# EXPORTS
# ============================================================================

tools = []

variables = [
    # Data variables
    Variable("df", df, "DataFrame with columns: category, product, price, quantity."),
    Variable("df2", df2, "DataFrame with columns: product, supplier."),
    Variable("df_missing", df_missing, "DataFrame with columns: name, age (has NaN), score (has NaN)."),
    Variable("df_sales", df_sales, "DataFrame with columns: region, quarter, sales."),
    Variable("matrix", matrix, "3x3 numpy array: [[1,2,3],[4,5,6],[7,8,9]]."),
    Variable("matrix2", matrix2, "3x2 numpy array: [[1,0],[0,1],[1,1]]."),
    Variable("array", array, "1D numpy array: [10, 25, 5, 30, 15, 8, 22, 3]."),
    Variable("array2", array2, "1D numpy array: [1, 2, 3, 4, 5, 6, 7, 8]."),
    Variable("series", series, "Series with index a-e, values [85, 92, 78, 95, 88]."),
    # Result variables
    Variable("result_df", result_df, "Store DataFrame results here."),
    Variable("result_array", result_array, "Store array/Series results here."),
    Variable("result_value", result_value, "Store numeric results here (float)."),
]

validators = {
    # DataFrame ops
    "validate_df_add_column": validate_df_add_column,
    "validate_df_filter": validate_df_filter,
    "validate_df_sort": validate_df_sort,
    # DataFrame groupby
    "validate_df_groupby": validate_df_groupby,
    "validate_df_groupby_count": validate_df_groupby_count,
    "validate_df_groupby_max": validate_df_groupby_max,
    # DataFrame merge
    "validate_df_merge": validate_df_merge,
    "validate_df_merge_filter": validate_df_merge_filter,
    "validate_df_merge_sum": validate_df_merge_sum,
    # DataFrame missing values
    "validate_df_fillna": validate_df_fillna,
    "validate_df_dropna": validate_df_dropna,
    "validate_df_apply": validate_df_apply,
    # DataFrame pivot
    "validate_df_pivot": validate_df_pivot,
    "validate_df_pivot_sum": validate_df_pivot_sum,
    "validate_df_pivot_max_region": validate_df_pivot_max_region,
    # ndarray ops
    "validate_array_multiply": validate_array_multiply,
    "validate_array_add": validate_array_add,
    "validate_array_transpose": validate_array_transpose,
    # ndarray reshape
    "validate_array_reshape": validate_array_reshape,
    "validate_array_sum_axis": validate_array_sum_axis,
    "validate_array_total": validate_array_total,
    # ndarray boolean
    "validate_array_bool_filter": validate_array_bool_filter,
    "validate_array_bool_replace": validate_array_bool_replace,
    "validate_array_bool_mean": validate_array_bool_mean,
    # ndarray advanced
    "validate_array_concat": validate_array_concat,
    "validate_array_slice": validate_array_slice,
    "validate_array_reverse": validate_array_reverse,
    "validate_array_dot": validate_array_dot,
    "validate_array_dot_sum": validate_array_dot_sum,
    "validate_array_dot_max": validate_array_dot_max,
    # Series ops
    "validate_series_add": validate_series_add,
    "validate_series_clip": validate_series_clip,
    "validate_series_mean": validate_series_mean,
    # Series index
    "validate_series_select": validate_series_select,
    "validate_series_multiply": validate_series_multiply,
    "validate_series_sum": validate_series_sum,
    # Series boolean
    "validate_series_bool_filter": validate_series_bool_filter,
    "validate_series_bool_count": validate_series_bool_count,
    "validate_series_max": validate_series_max,
    # Series advanced
    "validate_series_cumsum": validate_series_cumsum,
    "validate_series_diff": validate_series_diff,
    "validate_series_rank": validate_series_rank,
}
