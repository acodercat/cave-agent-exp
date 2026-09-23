"""
Multi-Variable (15) - Stateful Benchmark

Tests: Managing 15 variables of diverse types modified in each turn.
"""

from typing import List
from cave_agent import Variable, IPythonRuntime
from core.validation import ValidatorResult
from core.types import Turn, ToolCall


# ============================================================================
# INITIAL STATE - 15 variables with diverse types
# ============================================================================

# Strings (3)
title = ""
author = ""
publisher = ""

# Integers (3)
year = 0
pages = 0
edition = 0

# Floats (3)
price = 0.0
rating = 0.0
weight = 0.0

# Booleans (3)
available = False
bestseller = False
ebook = False

# Collections (3)
genres = []
chapters = []
info = {}


# ============================================================================
# VALIDATORS
# ============================================================================

# Validation Strategy:
# - Lists (genres, chapters): Exact order comparison. Items are appended chronologically.
# - Dicts (info): Exact key-value comparison. Agent must include exactly specified keys.
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


def validate_book_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Python Guide",
        "author": "John Smith",
        "publisher": "TechBooks",
        "year": 2023,
        "pages": 450,
        "edition": 1,
        "price": 49.99,
        "rating": 4.5,
        "weight": 1.2,
        "available": True,
        "bestseller": False,
        "ebook": True,
        "genres": ["programming", "education"],
        "chapters": ["Intro", "Basics", "Advanced"],
        "info": {"isbn": "123-456", "language": "English"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Book initialized")

def validate_book_update(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Python Guide 2nd Edition",
        "author": "John Smith",
        "publisher": "TechBooks Pro",
        "year": 2024,
        "pages": 550,
        "edition": 2,
        "price": 59.99,
        "rating": 4.7,
        "weight": 1.4,
        "available": True,
        "bestseller": True,
        "ebook": True,
        "genres": ["programming", "education", "reference"],
        "chapters": ["Intro", "Basics", "Advanced", "Expert"],
        "info": {"isbn": "123-456", "language": "English", "updated": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Book updated")

def validate_book_discount(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "[SALE] Python Guide 2nd Edition",
        "author": "John Smith",
        "publisher": "TechBooks Pro",
        "year": 2024,
        "pages": 550,
        "edition": 2,
        "price": 47.99,
        "rating": 4.7,
        "weight": 1.4,
        "available": True,
        "bestseller": True,
        "ebook": True,
        "genres": ["programming", "education", "reference", "sale"],
        "chapters": ["Intro", "Basics", "Advanced", "Expert"],
        "info": {"isbn": "123-456", "language": "English", "updated": True, "discount": 0.2}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Discount applied")


def validate_course_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Web Development",
        "author": "Jane Doe",
        "publisher": "LearnOnline",
        "year": 2024,
        "pages": 0,
        "edition": 1,
        "price": 199.0,
        "rating": 0.0,
        "weight": 0.0,
        "available": True,
        "bestseller": False,
        "ebook": False,
        "genres": ["web", "frontend", "backend"],
        "chapters": [],
        "info": {"hours": 40, "level": "beginner"}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Course initialized")

def validate_course_progress(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Web Development",
        "author": "Jane Doe",
        "publisher": "LearnOnline",
        "year": 2024,
        "pages": 10,
        "edition": 1,
        "price": 199.0,
        "rating": 4.8,
        "weight": 0.0,
        "available": True,
        "bestseller": True,
        "ebook": False,
        "genres": ["web", "frontend", "backend"],
        "chapters": ["HTML", "CSS", "JavaScript"],
        "info": {"hours": 40, "level": "beginner", "students": 1000}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Progress updated")

def validate_course_complete(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Web Development [COMPLETE]",
        "author": "Jane Doe",
        "publisher": "LearnOnline",
        "year": 2024,
        "pages": 20,
        "edition": 2,
        "price": 249.0,
        "rating": 4.9,
        "weight": 0.0,
        "available": True,
        "bestseller": True,
        "ebook": True,
        "genres": ["web", "frontend", "backend", "fullstack"],
        "chapters": ["HTML", "CSS", "JavaScript", "React", "Node"],
        "info": {"hours": 40, "level": "beginner", "students": 1000, "complete": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Course completed")


# Magazine validators
def validate_magazine_launch(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Tech Weekly",
        "author": "Editorial Team",
        "publisher": ("MediaGroup Inc.", "MediaGroup Inc"),
        "year": 2024,
        "pages": 64,
        "edition": 1,
        "price": 9.99,
        "rating": 0.0,
        "weight": 0.3,
        "available": True,
        "bestseller": False,
        "ebook": True,
        "genres": ["technology", "news", "gadgets"],
        "chapters": ["Cover Story", "Reviews", "Interviews"],
        "info": {"frequency": "weekly", "issue": 1, "circulation": 50000}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Magazine launched")

def validate_magazine_growth(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Tech Weekly",
        "author": "Editorial Team",
        "publisher": ("MediaGroup Inc.", "MediaGroup Inc"),
        "year": 2024,
        "pages": 80,
        "edition": 12,
        "price": 12.99,
        "rating": 4.5,
        "weight": 0.4,
        "available": True,
        "bestseller": True,
        "ebook": True,
        "genres": ["technology", "news", "gadgets", "AI"],
        "chapters": ["Cover Story", "Reviews", "Interviews", "Deep Dive"],
        "info": {"frequency": "weekly", "issue": 12, "circulation": 100000, "subscribers": 25000}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Magazine growing")

def validate_magazine_special(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Tech Weekly - Annual Special",
        "author": "Editorial Team + Guests",
        "publisher": ("MediaGroup Inc.", "MediaGroup Inc"),
        "year": 2024,
        "pages": 150,
        "edition": 52,
        "price": 19.99,
        "rating": 4.8,
        "weight": 0.6,
        "available": True,
        "bestseller": True,
        "ebook": True,
        "genres": ["technology", "news", "gadgets", "AI", "special"],
        "chapters": ["Cover Story", "Reviews", "Interviews", "Deep Dive", "Year in Review", "Predictions"],
        "info": {"frequency": "weekly", "issue": 52, "circulation": 150000, "subscribers": 25000, "special_edition": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Special edition published")


# Podcast validators
def validate_podcast_create(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Code Talk",
        "author": "Mike Chen",
        "publisher": "PodNetwork",
        "year": 2023,
        "pages": 10,
        "edition": 1,
        "price": 0.0,
        "rating": 4.2,
        "weight": 0.0,
        "available": True,
        "bestseller": False,
        "ebook": False,
        "genres": ["tech", "interviews", "coding"],
        "chapters": ["Ep1", "Ep2", "Ep3", "Ep4", "Ep5"],
        "info": {"platform": "Spotify", "duration_avg": 45}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Podcast created")

def validate_podcast_monetize(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Code Talk",
        "author": "Mike Chen",
        "publisher": "PodNetwork Pro",
        "year": 2024,
        "pages": 50,
        "edition": 2,
        "price": 4.99,
        "rating": 4.6,
        "weight": 0.0,
        "available": True,
        "bestseller": True,
        "ebook": True,
        "genres": ["tech", "interviews", "coding", "premium"],
        "chapters": ["Ep1", "Ep2", "Ep3", "Ep4", "Ep5", "Bonus"],
        "info": {"platform": "Spotify", "duration_avg": 60, "sponsors": 3}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Podcast monetized")

def validate_podcast_expand(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Code Talk Network",
        "author": "Mike Chen & Team",
        "publisher": "PodNetwork Pro",
        "year": 2024,
        "pages": 100,
        "edition": 3,
        "price": 9.99,
        "rating": 4.9,
        "weight": 0.0,
        "available": True,
        "bestseller": True,
        "ebook": True,
        "genres": ["tech", "interviews", "coding", "premium", "video"],
        "chapters": ["Ep1", "Ep2", "Ep3", "Ep4", "Ep5", "Bonus", "Live"],
        "info": {"platform": "Multi", "duration_avg": 60, "sponsors": 3, "shows": 3}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Podcast expanded")


# Documentary validators
def validate_doc_filming(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Ocean Secrets",
        "author": "Sarah Blake",
        "publisher": "NatureFilms",
        "year": 2024,
        "pages": 0,
        "edition": 1,
        "price": 0.0,
        "rating": 0.0,
        "weight": 0.0,
        "available": False,
        "bestseller": False,
        "ebook": False,
        "genres": ["documentary", "nature", "ocean"],
        "chapters": ["Deep Sea", "Coral Reefs", "Arctic Waters"],
        "info": {"runtime": 90, "status": "filming", "budget": 500000}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Documentary in production")

def validate_doc_release(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Ocean Secrets",
        "author": "Sarah Blake",
        "publisher": "NatureFilms",
        "year": 2024,
        "pages": 4,
        "edition": 1,
        "price": 14.99,
        "rating": 4.7,
        "weight": 0.1,
        "available": True,
        "bestseller": False,
        "ebook": True,
        "genres": ["documentary", "nature", "ocean", "educational"],
        "chapters": ["Deep Sea", "Coral Reefs", "Arctic Waters", "Behind the Scenes"],
        "info": {"runtime": 120, "status": "released", "budget": 500000, "streaming": True}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Documentary released")

def validate_doc_award(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "title": "Ocean Secrets - Award Winner",
        "author": "Sarah Blake",
        "publisher": "NatureFilms Premium",
        "year": 2024,
        "pages": 6,
        "edition": 2,
        "price": 19.99,
        "rating": 4.9,
        "weight": 0.15,
        "available": True,
        "bestseller": True,
        "ebook": True,
        "genres": ["documentary", "nature", "ocean", "educational", "award-winning"],
        "chapters": ["Deep Sea", "Coral Reefs", "Arctic Waters", "Behind the Scenes", "Director Commentary", "Extended Cuts"],
        "info": {"runtime": 150, "status": "released", "budget": 500000, "streaming": True, "awards": 3}
    }
    errors = _validate_state(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Documentary won awards")


# ============================================================================
# EXPORTS
# ============================================================================

tools = []

variables = [
    Variable("title", title, "Item title (str, initial: '')."),
    Variable("author", author, "Author/creator name (str, initial: '')."),
    Variable("publisher", publisher, "Publisher name (str, initial: ''). For suffixes like 'Inc', both 'Inc.' and 'Inc' are acceptable."),
    Variable("year", year, "Publication year (int, initial: 0)."),
    Variable("pages", pages, "Page count or lessons (int, initial: 0)."),
    Variable("edition", edition, "Edition number (int, initial: 0)."),
    Variable("price", price, "Price in dollars (float, initial: 0.0)."),
    Variable("rating", rating, "Average rating 0-5 (float, initial: 0.0)."),
    Variable("weight", weight, "Weight in kg (float, initial: 0.0)."),
    Variable("available", available, "Availability status (bool, initial: False)."),
    Variable("bestseller", bestseller, "Bestseller status (bool, initial: False)."),
    Variable("ebook", ebook, "Digital version available (bool, initial: False)."),
    Variable("genres", genres, "Category/genre tags (list[str], initial: [])."),
    Variable("chapters", chapters, "Chapter/section names (list[str], initial: [])."),
    Variable("info", info, "Additional metadata (dict, initial: {}). Valid keys: isbn (str), language (str), updated (bool), discount (float), hours (int), level (str), students (int), complete (bool), frequency (str), issue (int), circulation (int), subscribers (int), special_edition (bool), platform (str), duration_avg (int), sponsors (int), shows (int), runtime (int), status (str), budget (int), streaming (bool), awards (int)."),
]

validators = {
    "validate_book_init": validate_book_init,
    "validate_book_update": validate_book_update,
    "validate_book_discount": validate_book_discount,
    "validate_course_init": validate_course_init,
    "validate_course_progress": validate_course_progress,
    "validate_course_complete": validate_course_complete,
    "validate_magazine_launch": validate_magazine_launch,
    "validate_magazine_growth": validate_magazine_growth,
    "validate_magazine_special": validate_magazine_special,
    "validate_podcast_create": validate_podcast_create,
    "validate_podcast_monetize": validate_podcast_monetize,
    "validate_podcast_expand": validate_podcast_expand,
    "validate_doc_filming": validate_doc_filming,
    "validate_doc_release": validate_doc_release,
    "validate_doc_award": validate_doc_award,
}
