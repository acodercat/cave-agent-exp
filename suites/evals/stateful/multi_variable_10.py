"""
Multi-Variable (10) - Stateful Benchmark

Tests: Managing 10 variables of diverse types modified in each turn.
"""

from typing import List
from cave_agent import Variable, IPythonRuntime
from core.validation import ValidatorResult
from core.types import Turn, ToolCall


# ============================================================================
# INITIAL STATE - 10 variables with diverse types
# ============================================================================

# Strings
product_name = ""
category = ""

# Integers
quantity = 0
stock_count = 0

# Floats
price = 0.0
discount_rate = 0.0

# Booleans
in_stock = False
is_featured = False

# Collections
reviews = []
metadata = {}


# ============================================================================
# VALIDATORS
# ============================================================================

# Validation Strategy:
# - Lists (reviews): Exact order comparison. Reviews are chronologically ordered,
#   so order matters. The expected list reflects the sequence of additions.
# - Dicts (metadata): Exact key-value comparison. The agent must include exactly
#   the specified keys with correct values. Extra keys or missing keys fail.
# - Floats: Compared with 0.01 tolerance to handle floating-point precision.


def _compare_values(actual, expected, tolerance=0.01):
    """Recursively compare values with float tolerance."""
    if isinstance(expected, float):
        if not isinstance(actual, (int, float)):
            return False
        return abs(actual - expected) <= tolerance
    elif isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(_compare_values(actual[k], expected[k], tolerance) for k in expected)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(_compare_values(a, e, tolerance) for a, e in zip(actual, expected))
    elif isinstance(expected, tuple):
        # Tuple means "one of these values is acceptable"
        return actual in expected
    else:
        return actual == expected


def _validate_state(runtime: IPythonRuntime, expected: dict) -> list:
    """Helper to validate runtime state against expected values."""
    errors = []
    for key, exp_val in expected.items():
        val = runtime.retrieve(key)
        if not _compare_values(val, exp_val):
            errors.append(f"{key}={val} (expected {exp_val})")
    return errors


def validate_product_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Laptop",
        "category": "Electronics",
        "quantity": 50,
        "stock_count": 100,
        "price": 999.99,
        "discount_rate": 0.1,
        "in_stock": True,
        "is_featured": True,
        "reviews": [5, 4, 5],
        "metadata": {"brand": "TechCo", "year": 2024}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Product initialized")

def validate_product_sale(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Laptop",
        "category": "Electronics",
        "quantity": 45,
        "stock_count": 95,
        "price": 899.99,
        "discount_rate": 0.1,
        "in_stock": True,
        "is_featured": True,
        "reviews": [5, 4, 5, 4],
        "metadata": {"brand": "TechCo", "year": 2024, "sold": 5}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Sale processed")

def validate_product_update(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Laptop Pro",
        "category": "Premium Electronics",
        "quantity": 45,
        "stock_count": 95,
        "price": 1079.99,
        "discount_rate": 0.2,
        "in_stock": True,
        "is_featured": False,
        "reviews": [5, 4, 5, 4],
        "metadata": {"brand": "TechCo", "year": 2024, "sold": 5, "upgraded": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Product updated")


def validate_inventory_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Phone",
        "category": "Mobile",
        "quantity": 200,
        "stock_count": 500,
        "price": 599.0,
        "discount_rate": 0.0,
        "in_stock": True,
        "is_featured": False,
        "reviews": [],
        "metadata": {"color": "black"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Inventory initialized")

def validate_inventory_restock(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Phone",
        "category": "Mobile",
        "quantity": 400,
        "stock_count": 700,
        "price": 599.0,
        "discount_rate": 0.0,
        "in_stock": True,
        "is_featured": True,
        "reviews": [5],
        "metadata": {"color": "black", "restocked": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Restocked")

def validate_inventory_clearance(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Phone [CLEARANCE]",
        "category": "Mobile",
        "quantity": 0,
        "stock_count": 0,
        "price": 299.5,
        "discount_rate": 0.5,
        "in_stock": False,
        "is_featured": False,
        "reviews": [5],
        "metadata": {"color": "black", "restocked": True, "clearance": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Clearance applied")


# Book store validators
def validate_book_new(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Python Mastery",
        "category": "Programming Books",
        "quantity": 25,
        "stock_count": 50,
        "price": 49.99,
        "discount_rate": 0.0,
        "in_stock": True,
        "is_featured": True,
        "reviews": [5, 5, 4],
        "metadata": {"author": "Jane Smith", "pages": 450, "ISBN": "978-1234567890"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Book added")

def validate_book_bestseller(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Python Mastery - Bestseller Edition",
        "category": "Bestsellers",
        "quantity": 10,
        "stock_count": 35,
        "price": 54.99,
        "discount_rate": 0.15,
        "in_stock": True,
        "is_featured": True,
        "reviews": [5, 5, 4, 5, 5],
        "metadata": {"author": "Jane Smith", "pages": 450, "ISBN": "978-1234567890", "bestseller_rank": 1}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Bestseller status applied")

def validate_book_reprint(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Python Mastery - 2nd Edition",
        "category": "Bestsellers",
        "quantity": 110,
        "stock_count": 135,
        "price": 59.99,
        "discount_rate": 0.1,
        "in_stock": True,
        "is_featured": False,
        "reviews": [5, 5, 4, 5, 5],
        "metadata": {"author": "Jane Smith", "pages": 500, "ISBN": "978-1234567891", "bestseller_rank": 1, "edition": 2}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Reprint completed")


# Fashion retail validators
def validate_fashion_launch(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Summer Dress",
        "category": "Women's Apparel",
        "quantity": 75,
        "stock_count": 150,
        "price": 89.99,
        "discount_rate": 0.0,
        "in_stock": True,
        "is_featured": True,
        "reviews": [],
        "metadata": {"size": "M", "color": "blue", "material": "cotton"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Fashion item launched")

def validate_fashion_popular(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Summer Dress",
        "category": "Women's Apparel",
        "quantity": 25,
        "stock_count": 100,
        "price": 99.99,
        "discount_rate": 0.0,
        "in_stock": True,
        "is_featured": True,
        "reviews": [5, 4, 5, 5],
        "metadata": {"size": "M", "color": "blue", "material": "cotton", "trending": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Item now popular")

def validate_fashion_seasonal(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Summer Dress - End of Season",
        "category": "Sale",
        "quantity": 5,
        "stock_count": 5,
        "price": 49.99,
        "discount_rate": 0.5,
        "in_stock": True,
        "is_featured": False,
        "reviews": [5, 4, 5, 5, 3],
        "metadata": {"size": "M", "color": "blue", "material": "cotton", "trending": True, "season": "summer2024"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Seasonal sale applied")


# Grocery store validators
def validate_grocery_stock(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Organic Apples",
        "category": "Fresh Produce",
        "quantity": 200,
        "stock_count": 200,
        "price": 4.99,
        "discount_rate": 0.0,
        "in_stock": True,
        "is_featured": False,
        "reviews": [4, 5],
        "metadata": {"origin": "Washington", "organic": True, "unit": "per lb"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Grocery stocked")

def validate_grocery_promo(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Organic Apples - Weekly Special",
        "category": "Fresh Produce",
        "quantity": 150,
        "stock_count": 150,
        "price": 3.99,
        "discount_rate": 0.2,
        "in_stock": True,
        "is_featured": True,
        "reviews": [4, 5, 5],
        "metadata": {"origin": "Washington", "organic": True, "unit": "per lb", "promo_week": 42}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Promo applied")

def validate_grocery_lowstock(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "product_name": "Organic Apples",
        "category": "Fresh Produce",
        "quantity": 10,
        "stock_count": 10,
        "price": 5.99,
        "discount_rate": 0.0,
        "in_stock": True,
        "is_featured": False,
        "reviews": [4, 5, 5],
        "metadata": {"origin": "Washington", "organic": True, "unit": "per lb", "promo_week": 42, "reorder": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Low stock processed")


# ============================================================================
# EXPORTS
# ============================================================================

tools = []

variables = [
    Variable("product_name", product_name, "Product name (str, initial: '')."),
    Variable("category", category, "Product category (str, initial: ''). Use exact category names as given (e.g., 'Programming Books', 'Fresh Produce', 'Women\\'s Apparel')."),
    Variable("quantity", quantity, "Available quantity (int, initial: 0)."),
    Variable("stock_count", stock_count, "Total stock count (int, initial: 0)."),
    Variable("price", price, "Product price (float, initial: 0.0)."),
    Variable("discount_rate", discount_rate, "Discount rate 0-1 (float, initial: 0.0)."),
    Variable("in_stock", in_stock, "In stock status (bool, initial: False)."),
    Variable("is_featured", is_featured, "Featured status (bool, initial: False)."),
    Variable("reviews", reviews, "Review scores (list[int], initial: []). Each item is a star rating 1-5."),
    Variable("metadata", metadata, "Product metadata (dict, initial: {}). Key-value store for additional product attributes like brand, year, color, author, pages, ISBN, etc. Use metadata['key'] = value to add/update entries."),
]

validators = {
    "validate_product_init": validate_product_init,
    "validate_product_sale": validate_product_sale,
    "validate_product_update": validate_product_update,
    "validate_inventory_init": validate_inventory_init,
    "validate_inventory_restock": validate_inventory_restock,
    "validate_inventory_clearance": validate_inventory_clearance,
    "validate_book_new": validate_book_new,
    "validate_book_bestseller": validate_book_bestseller,
    "validate_book_reprint": validate_book_reprint,
    "validate_fashion_launch": validate_fashion_launch,
    "validate_fashion_popular": validate_fashion_popular,
    "validate_fashion_seasonal": validate_fashion_seasonal,
    "validate_grocery_stock": validate_grocery_stock,
    "validate_grocery_promo": validate_grocery_promo,
    "validate_grocery_lowstock": validate_grocery_lowstock,
}
