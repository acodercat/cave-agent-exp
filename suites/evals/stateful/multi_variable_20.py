"""
Multi-Variable (20) - Stateful Benchmark

Tests: Managing 20 variables of diverse types modified in each turn.
"""

from typing import List
from cave_agent import Variable, IPythonRuntime
from core.validation import ValidatorResult
from core.types import Turn, ToolCall


# ============================================================================
# INITIAL STATE - 20 variables with diverse types
# ============================================================================

# Strings (4)
company_name = ""
industry = ""
ceo = ""
headquarters = ""

# Integers (4)
employees = 0
founded_year = 0
offices = 0
products = 0

# Floats (4)
revenue = 0.0
profit_margin = 0.0
stock_price = 0.0
market_cap = 0.0

# Booleans (4)
public = False
profitable = False
hiring = False
international = False

# Collections (4)
departments = []
locations = []
financials = {}
contacts = {}


# ============================================================================
# VALIDATORS
# ============================================================================

# Validation Strategy:
# - Lists (departments, locations): Exact order comparison for appended items.
# - Dicts (financials, contacts): Exact key-value comparison.
# - Floats: Compared with 0.01 tolerance for floating-point precision.


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


def validate_startup_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "TechStart",
        "industry": "Software",
        "ceo": "Alice Johnson",
        "headquarters": "San Francisco",
        "employees": 50,
        "founded_year": 2020,
        "offices": 1,
        "products": 2,
        "revenue": 5000000.0,
        "profit_margin": 0.1,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": True,
        "hiring": True,
        "international": False,
        "departments": ["Engineering", "Sales", "Marketing"],
        "locations": ["SF"],
        "financials": {"funding": 10000000, "round": "Series A"},
        "contacts": {"email": "info@techstart.com", "phone": "555-0100"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Startup initialized")

def validate_startup_growth(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "TechStart",
        "industry": "Software",
        "ceo": "Alice Johnson",
        "headquarters": "San Francisco",
        "employees": 150,
        "founded_year": 2020,
        "offices": 3,
        "products": 5,
        "revenue": 15000000.0,
        "profit_margin": 0.15,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": True,
        "hiring": True,
        "international": True,
        "departments": ["Engineering", "Sales", "Marketing", "HR", "Finance"],
        "locations": ["SF", "NYC", "London"],
        "financials": {"funding": 10000000, "round": "Series A", "valuation": 100000000},
        "contacts": {"email": "info@techstart.com", "phone": "555-0100", "support": "555-0200"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Growth phase complete")

def validate_startup_ipo(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": ("TechStart Inc.", "TechStart Inc"),
        "industry": "Enterprise Software",
        "ceo": "Alice Johnson",
        "headquarters": "San Francisco",
        "employees": 500,
        "founded_year": 2020,
        "offices": 10,
        "products": 10,
        "revenue": 50000000.0,
        "profit_margin": 0.2,
        "stock_price": 25.0,
        "market_cap": 500000000.0,
        "public": True,
        "profitable": True,
        "hiring": True,
        "international": True,
        "departments": ["Engineering", "Sales", "Marketing", "HR", "Finance", "Legal", "IR"],
        "locations": ["SF", "NYC", "London", "Tokyo", "Berlin"],
        "financials": {"funding": 10000000, "round": "Series A", "valuation": 100000000, "ipo": True},
        "contacts": {"email": "info@techstart.com", "phone": "555-0100", "support": "555-0200", "ir": "ir@techstart.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "IPO complete")


def validate_enterprise_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "MegaCorp",
        "industry": "Conglomerate",
        "ceo": "Bob Williams",
        "headquarters": "New York",
        "employees": 10000,
        "founded_year": 1990,
        "offices": 50,
        "products": 100,
        "revenue": 1000000000.0,
        "profit_margin": 0.12,
        "stock_price": 150.0,
        "market_cap": 50000000000.0,
        "public": True,
        "profitable": True,
        "hiring": False,
        "international": True,
        "departments": ["All"],
        "locations": ["Global"],
        "financials": {"debt": 500000000, "assets": 2000000000},
        "contacts": {"ir": "ir@megacorp.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Enterprise initialized")

def validate_enterprise_restructure(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "MegaCorp",
        "industry": "Technology",
        "ceo": "Carol Lee",
        "headquarters": "New York",
        "employees": 8000,
        "founded_year": 1990,
        "offices": 30,
        "products": 50,
        "revenue": 800000000.0,
        "profit_margin": 0.18,
        "stock_price": 180.0,
        "market_cap": 60000000000.0,
        "public": True,
        "profitable": True,
        "hiring": True,
        "international": True,
        "departments": ["Tech", "Cloud", "AI"],
        "locations": ["Americas", "Europe", "Asia"],
        "financials": {"debt": 200000000, "assets": 2500000000},
        "contacts": {"ir": "ir@megacorp.com", "press": "press@megacorp.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Restructure complete")

def validate_enterprise_acquire(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "MegaCorp Global",
        "industry": "Technology",
        "ceo": "Carol Lee",
        "headquarters": "New York",
        "employees": 12000,
        "founded_year": 1990,
        "offices": 45,
        "products": 75,
        "revenue": 1200000000.0,
        "profit_margin": 0.15,
        "stock_price": 200.0,
        "market_cap": 80000000000.0,
        "public": True,
        "profitable": True,
        "hiring": True,
        "international": True,
        "departments": ["Tech", "Cloud", "AI", "Acquired"],
        "locations": ["Americas", "Europe", "Asia", "Australia"],
        "financials": {"debt": 200000000, "assets": 2500000000, "acquisition": 500000000},
        "contacts": {"ir": "ir@megacorp.com", "press": "press@megacorp.com", "ma": "ma@megacorp.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Acquisition complete")


# Nonprofit organization validators
def validate_nonprofit_launch(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "GreenFuture Foundation",
        "industry": "Environmental",
        "ceo": "Emma Green",
        "headquarters": "Portland",
        "employees": 25,
        "founded_year": 2018,
        "offices": 1,
        "products": 3,
        "revenue": 500000.0,
        "profit_margin": 0.0,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": False,
        "hiring": True,
        "international": False,
        "departments": ["Programs", "Fundraising", "Outreach"],
        "locations": ["Portland"],
        "financials": {"grants": 300000, "donations": 200000},
        "contacts": {"email": "info@greenfuture.org", "donate": "donate@greenfuture.org"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Nonprofit launched")

def validate_nonprofit_expand(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "GreenFuture Foundation",
        "industry": "Environmental",
        "ceo": "Emma Green",
        "headquarters": "Portland",
        "employees": 75,
        "founded_year": 2018,
        "offices": 5,
        "products": 8,
        "revenue": 2000000.0,
        "profit_margin": 0.0,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": False,
        "hiring": True,
        "international": True,
        "departments": ["Programs", "Fundraising", "Outreach", "Research", "Education"],
        "locations": ["Portland", "Seattle", "Denver", "Vancouver", "Austin"],
        "financials": {"grants": 1200000, "donations": 800000, "endowment": 500000},
        "contacts": {"email": "info@greenfuture.org", "donate": "donate@greenfuture.org", "volunteer": "volunteer@greenfuture.org"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Nonprofit expanded")

def validate_nonprofit_global(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "GreenFuture International",
        "industry": "Environmental NGO",
        "ceo": "Emma Green",
        "headquarters": "Portland",
        "employees": 200,
        "founded_year": 2018,
        "offices": 15,
        "products": 20,
        "revenue": 10000000.0,
        "profit_margin": 0.0,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": False,
        "hiring": True,
        "international": True,
        "departments": ["Programs", "Fundraising", "Outreach", "Research", "Education", "Policy", "Global Ops"],
        "locations": ["Portland", "Seattle", "Denver", "Vancouver", "Austin", "London", "Berlin", "Tokyo"],
        "financials": {"grants": 5000000, "donations": 3000000, "endowment": 2000000, "un_funding": 1000000},
        "contacts": {"email": "info@greenfuture.org", "donate": "donate@greenfuture.org", "volunteer": "volunteer@greenfuture.org", "press": "press@greenfuture.org"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Nonprofit went global")


# Retail chain validators
def validate_retail_open(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "FreshMart",
        "industry": "Grocery Retail",
        "ceo": "David Chen",
        "headquarters": "Chicago",
        "employees": 500,
        "founded_year": 2015,
        "offices": 10,
        "products": 5000,
        "revenue": 25000000.0,
        "profit_margin": 0.03,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": True,
        "hiring": True,
        "international": False,
        "departments": ["Operations", "Buying", "Logistics", "Marketing"],
        "locations": ["Chicago", "Milwaukee", "Indianapolis"],
        "financials": {"inventory": 5000000, "loans": 2000000},
        "contacts": {"customer": "1-800-FRESH", "suppliers": "buying@freshmart.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Retail chain opened")

def validate_retail_franchise(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "FreshMart",
        "industry": "Grocery Retail",
        "ceo": "David Chen",
        "headquarters": "Chicago",
        "employees": 2000,
        "founded_year": 2015,
        "offices": 50,
        "products": 8000,
        "revenue": 150000000.0,
        "profit_margin": 0.05,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": True,
        "hiring": True,
        "international": False,
        "departments": ["Operations", "Buying", "Logistics", "Marketing", "Franchise", "Training"],
        "locations": ["Midwest", "Great Lakes", "Plains"],
        "financials": {"inventory": 20000000, "loans": 0, "franchise_fees": 5000000},
        "contacts": {"customer": "1-800-FRESH", "suppliers": "buying@freshmart.com", "franchise": "franchise@freshmart.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Franchise model launched")

def validate_retail_ipo(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "FreshMart Holdings",
        "industry": "Grocery Retail",
        "ceo": "David Chen",
        "headquarters": "Chicago",
        "employees": 8000,
        "founded_year": 2015,
        "offices": 200,
        "products": 15000,
        "revenue": 800000000.0,
        "profit_margin": 0.06,
        "stock_price": 35.0,
        "market_cap": 2000000000.0,
        "public": True,
        "profitable": True,
        "hiring": True,
        "international": True,
        "departments": ["Operations", "Buying", "Logistics", "Marketing", "Franchise", "Training", "IR", "E-commerce"],
        "locations": ["USA", "Canada", "Mexico"],
        "financials": {"inventory": 80000000, "loans": 0, "franchise_fees": 5000000, "ipo_raised": 500000000},
        "contacts": {"customer": "1-800-FRESH", "suppliers": "buying@freshmart.com", "franchise": "franchise@freshmart.com", "ir": "ir@freshmart.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Retail IPO complete")


# Gaming studio validators
def validate_gaming_indie(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "PixelDream Studios",
        "industry": "Video Games",
        "ceo": "Maya Rodriguez",
        "headquarters": "Austin",
        "employees": 15,
        "founded_year": 2019,
        "offices": 1,
        "products": 2,
        "revenue": 1000000.0,
        "profit_margin": 0.25,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": True,
        "hiring": False,
        "international": False,
        "departments": ["Development", "Art", "QA"],
        "locations": ["Austin"],
        "financials": {"steam_revenue": 800000, "console_revenue": 200000},
        "contacts": {"press": "press@pixeldream.com", "support": "support@pixeldream.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Indie studio established")

def validate_gaming_hit(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "PixelDream Studios",
        "industry": "Video Games",
        "ceo": "Maya Rodriguez",
        "headquarters": "Austin",
        "employees": 80,
        "founded_year": 2019,
        "offices": 2,
        "products": 5,
        "revenue": 25000000.0,
        "profit_margin": 0.35,
        "stock_price": 0.0,
        "market_cap": 0.0,
        "public": False,
        "profitable": True,
        "hiring": True,
        "international": True,
        "departments": ["Development", "Art", "QA", "Marketing", "Community"],
        "locations": ["Austin", "Montreal"],
        "financials": {"steam_revenue": 15000000, "console_revenue": 8000000, "mobile_revenue": 2000000},
        "contacts": {"press": "press@pixeldream.com", "support": "support@pixeldream.com", "business": "biz@pixeldream.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Hit game released")

def validate_gaming_publisher(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "company_name": "PixelDream Entertainment",
        "industry": "Video Games & Publishing",
        "ceo": "Maya Rodriguez",
        "headquarters": "Austin",
        "employees": 300,
        "founded_year": 2019,
        "offices": 5,
        "products": 15,
        "revenue": 150000000.0,
        "profit_margin": 0.3,
        "stock_price": 45.0,
        "market_cap": 800000000.0,
        "public": True,
        "profitable": True,
        "hiring": True,
        "international": True,
        "departments": ["Development", "Art", "QA", "Marketing", "Community", "Publishing", "Esports"],
        "locations": ["Austin", "Montreal", "Tokyo", "London", "Seoul"],
        "financials": {"steam_revenue": 50000000, "console_revenue": 60000000, "mobile_revenue": 30000000, "publishing_revenue": 10000000},
        "contacts": {"press": "press@pixeldream.com", "support": "support@pixeldream.com", "business": "biz@pixeldream.com", "ir": "ir@pixeldream.com"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Publisher established")


# ============================================================================
# EXPORTS
# ============================================================================

tools = []

variables = [
    Variable("company_name", company_name, "Company name (str, initial: ''). For suffixes like 'Inc', both 'Inc.' and 'Inc' are acceptable."),
    Variable("industry", industry, "Industry sector (str, initial: '')."),
    Variable("ceo", ceo, "CEO name (str, initial: '')."),
    Variable("headquarters", headquarters, "HQ city (str, initial: '')."),
    Variable("employees", employees, "Employee count (int, initial: 0)."),
    Variable("founded_year", founded_year, "Year founded (int, initial: 0)."),
    Variable("offices", offices, "Number of offices (int, initial: 0)."),
    Variable("products", products, "Product count (int, initial: 0)."),
    Variable("revenue", revenue, "Annual revenue in dollars (float, initial: 0.0). Use full dollar amount, e.g., $5M = 5000000.0."),
    Variable("profit_margin", profit_margin, "Profit margin 0-1 (float, initial: 0.0)."),
    Variable("stock_price", stock_price, "Stock price (float, initial: 0.0)."),
    Variable("market_cap", market_cap, "Market capitalization in dollars (float, initial: 0.0)."),
    Variable("public", public, "Publicly traded (bool, initial: False)."),
    Variable("profitable", profitable, "Profitable status (bool, initial: False)."),
    Variable("hiring", hiring, "Currently hiring (bool, initial: False)."),
    Variable("international", international, "International presence (bool, initial: False)."),
    Variable("departments", departments, "Department names (list[str], initial: [])."),
    Variable("locations", locations, "Office locations (list[str], initial: [])."),
    Variable("financials", financials, "Financial data (dict, initial: {}). Valid keys: funding (int), round (str), valuation (int), ipo (bool), debt (int), assets (int), acquisition (int), grants (int), donations (int), endowment (int), un_funding (int), inventory (int), loans (int), franchise_fees (int), ipo_raised (int), steam_revenue (int), console_revenue (int), mobile_revenue (int), publishing_revenue (int)."),
    Variable("contacts", contacts, "Contact info (dict, initial: {}). Valid keys: email (str), phone (str), support (str), ir (str), press (str), ma (str), donate (str), volunteer (str), customer (str), suppliers (str), franchise (str), business (str)."),
]

validators = {
    "validate_startup_init": validate_startup_init,
    "validate_startup_growth": validate_startup_growth,
    "validate_startup_ipo": validate_startup_ipo,
    "validate_enterprise_init": validate_enterprise_init,
    "validate_enterprise_restructure": validate_enterprise_restructure,
    "validate_enterprise_acquire": validate_enterprise_acquire,
    "validate_nonprofit_launch": validate_nonprofit_launch,
    "validate_nonprofit_expand": validate_nonprofit_expand,
    "validate_nonprofit_global": validate_nonprofit_global,
    "validate_retail_open": validate_retail_open,
    "validate_retail_franchise": validate_retail_franchise,
    "validate_retail_ipo": validate_retail_ipo,
    "validate_gaming_indie": validate_gaming_indie,
    "validate_gaming_hit": validate_gaming_hit,
    "validate_gaming_publisher": validate_gaming_publisher,
}
