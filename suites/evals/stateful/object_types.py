"""
Object Types - Stateful Benchmark

Tests: Custom classes with attributes and methods.
"""

from typing import List
from cave_agent import Variable, IPythonRuntime, Type
from core.validation import ValidatorResult
from core.types import Turn, ToolCall


# ============================================================================
# CUSTOM CLASSES
# ============================================================================

class Person:
    def __init__(self, name: str = "", age: int = 0, city: str = ""):
        self.name = name
        self.age = age
        self.city = city

    def introduce(self) -> str:
        """Introduce the person."""
        return f"Hi, I'm {self.name}, {self.age} years old from {self.city}."

    def have_birthday(self):
        """Increment the age of the person by 1."""
        self.age += 1


class BankAccount:
    def __init__(self, balance: float = 0.0):
        self.balance = balance
        self.transactions = []

    def deposit(self, amount: float):
        """Deposit an amount into the bank account."""
        self.balance += amount
        self.transactions.append(f"+{amount}")

    def withdraw(self, amount: float):
        """Withdraw an amount from the bank account."""
        self.balance -= amount
        self.transactions.append(f"-{amount}")

    def apply_interest(self, rate: float):
        """Apply interest to the bank account."""
        interest = self.balance * rate
        self.balance += interest


class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_item(self, item: dict):
        """Add an item to the shopping cart."""
        self.items.append(item)

    def remove_item(self, name: str):
        """Remove an item from the shopping cart."""
        self.items = [i for i in self.items if i.get("name") != name]

    def get_total(self) -> float:
        """Get the total price of the shopping cart."""
        return sum(item.get("price", 0) * item.get("quantity", 1) for item in self.items)

    def clear(self):
        """Clear the shopping cart."""
        self.items = []


class Counter:
    def __init__(self, value: int = 0):
        """Initialize the counter with a value."""
        self.value = value

    def increment(self):
        """Increment the value of the counter by 1."""
        self.value += 1

    def decrement(self):
        """Decrement the value of the counter by 1."""
        self.value -= 1

    def add(self, n: int):
        """Add a number to the value of the counter."""
        self.value += n

    def reset(self):
        """Reset the value of the counter to 0."""
        self.value = 0


class Stack:
    def __init__(self):
        """Initialize the stack."""
        self._items = []

    def push(self, item):
        """Push an item onto the stack."""
        self._items.append(item)

    def pop(self):
        """Pop an item from the stack."""
        if self._items:
            return self._items.pop()
        return None

    def peek(self):
        """Peek at the top item of the stack."""
        if self._items:
            return self._items[-1]
        return None

    def size(self) -> int:
        """Get the size of the stack."""
        return len(self._items)


# ============================================================================
# INITIAL STATE
# ============================================================================

person = Person()
account = BankAccount(balance=1000.0)
cart = ShoppingCart()
counter = Counter(value=0)
stack = Stack()

# Result variables (reused)
result_str = ""
result_num = 0.0


# ============================================================================
# VALIDATORS - Person
# ============================================================================

def validate_person_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    p = runtime.retrieve("person")
    ok = p.name == "Alice" and p.age == 25
    return ValidatorResult(ok, f"name='{p.name}', age={p.age}")

def validate_person_update(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    p = runtime.retrieve("person")
    ok = p.age == 26 and p.city == "Boston"
    return ValidatorResult(ok, f"age={p.age}, city='{p.city}'")

def validate_person_method(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_str")
    expected = "Hi, I'm Alice, 26 years old from Boston."
    return ValidatorResult(r == expected, f"result_str = '{r}'")


def validate_person_birthday_init(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    p = runtime.retrieve("person")
    ok = p.name == "Bob" and p.age == 30
    return ValidatorResult(ok, f"name='{p.name}', age={p.age}")

def validate_person_birthday(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    p = runtime.retrieve("person")
    return ValidatorResult(p.age == 31, f"age = {p.age}, expected 31")

def validate_person_birthday2(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    p = runtime.retrieve("person")
    return ValidatorResult(p.age == 32, f"age = {p.age}, expected 32")


# ============================================================================
# VALIDATORS - BankAccount
# ============================================================================

def validate_account_deposit(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    a = runtime.retrieve("account")
    ok = abs(a.balance - 1500.0) < 0.01
    return ValidatorResult(ok, f"balance = {a.balance}")

def validate_account_withdraw(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    a = runtime.retrieve("account")
    ok = abs(a.balance - 1300.0) < 0.01
    return ValidatorResult(ok, f"balance = {a.balance}")

def validate_account_interest(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    a = runtime.retrieve("account")
    expected = 1300.0 * 1.10
    ok = abs(a.balance - expected) < 0.01
    return ValidatorResult(ok, f"balance = {a.balance}")


def validate_account_multi_deposit(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    a = runtime.retrieve("account")
    ok = abs(a.balance - 1300.0) < 0.01
    return ValidatorResult(ok, f"balance = {a.balance}")

def validate_account_multi_withdraw(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    a = runtime.retrieve("account")
    ok = abs(a.balance - 1050.0) < 0.01
    return ValidatorResult(ok, f"balance = {a.balance}")

def validate_account_balance(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_num")
    ok = abs(r - 1050.0) < 0.01
    return ValidatorResult(ok, f"result_num = {r}")


# ============================================================================
# VALIDATORS - ShoppingCart
# ============================================================================

def validate_cart_add(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("cart")
    ok = len(c.items) == 1 and c.items[0].get("name") == "Book"
    return ValidatorResult(ok, f"items = {c.items}")

def validate_cart_add2(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("cart")
    ok = len(c.items) == 2
    return ValidatorResult(ok, f"items count = {len(c.items)}")

def validate_cart_total(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_num")
    expected = 15.99 + 2.50
    ok = abs(r - expected) < 0.01
    return ValidatorResult(ok, f"result_num = {r}")


def validate_cart_qty_add(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("cart")
    ok = len(c.items) == 1 and c.items[0].get("quantity") == 3
    return ValidatorResult(ok, f"items = {c.items}")

def validate_cart_qty_add2(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("cart")
    ok = len(c.items) == 2
    return ValidatorResult(ok, f"items count = {len(c.items)}")

def validate_cart_qty_total(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_num")
    expected = 10.0 * 3 + 5.0 * 2
    ok = abs(r - expected) < 0.01
    return ValidatorResult(ok, f"result_num = {r}")


# ============================================================================
# VALIDATORS - Counter
# ============================================================================

def validate_counter_inc(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("counter")
    return ValidatorResult(c.value == 3, f"value = {c.value}")

def validate_counter_mixed(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("counter")
    return ValidatorResult(c.value == 4, f"value = {c.value}")

def validate_counter_reset(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("counter")
    return ValidatorResult(c.value == 0, f"value = {c.value}")


def validate_counter_add10(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("counter")
    return ValidatorResult(c.value == 10, f"value = {c.value}")

def validate_counter_add5(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("counter")
    return ValidatorResult(c.value == 15, f"value = {c.value}")

def validate_counter_store(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_num")
    return ValidatorResult(r == 15, f"result_num = {r}")


# ============================================================================
# VALIDATORS - Stack
# ============================================================================

def validate_stack_push(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("stack")
    ok = s.size() == 3
    return ValidatorResult(ok, f"size = {s.size()}")

def validate_stack_pop(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("stack")
    r = runtime.retrieve("result_str")
    ok = s.size() == 2 and r == "C"
    return ValidatorResult(ok, f"size = {s.size()}, popped = {r}")

def validate_stack_peek(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("stack")
    r = runtime.retrieve("result_str")
    ok = s.size() == 2 and r == "B"
    return ValidatorResult(ok, f"size = {s.size()}, top = {r}")


def validate_stack_push_nums(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("stack")
    ok = s.size() == 5
    return ValidatorResult(ok, f"size = {s.size()}")

def validate_stack_pop_sum(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("stack")
    r = runtime.retrieve("result_num")
    # Popped 5 + 4 = 9
    ok = s.size() == 3 and r == 9
    return ValidatorResult(ok, f"size = {s.size()}, sum = {r}")

def validate_stack_size(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    r = runtime.retrieve("result_num")
    return ValidatorResult(r == 3, f"result_num = {r}")


# ============================================================================
# VALIDATORS - ShoppingCart Removal
# ============================================================================

def validate_cart_add_items(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("cart")
    # Should have Laptop and Mouse
    names = [item.get("name") for item in c.items]
    ok = len(c.items) == 2 and "Laptop" in names and "Mouse" in names
    return ValidatorResult(ok, f"items = {names}")

def validate_cart_remove(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("cart")
    # Mouse should be removed, only Laptop remains
    names = [item.get("name") for item in c.items]
    ok = len(c.items) == 1 and "Laptop" in names and "Mouse" not in names
    return ValidatorResult(ok, f"items = {names}")

def validate_cart_clear(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    c = runtime.retrieve("cart")
    ok = len(c.items) == 0
    return ValidatorResult(ok, f"items count = {len(c.items)}, expected 0")


# ============================================================================
# VALIDATORS - Stack Advanced
# ============================================================================

def validate_stack_multi_push(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("stack")
    ok = s.size() == 4
    return ValidatorResult(ok, f"size = {s.size()}, expected 4")

def validate_stack_pop_until(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("stack")
    r = runtime.retrieve("result_num")
    # Popped 'D', 'C', 'B' (3 items), sum of their ASCII or count
    # Stack should have 1 item left ('A')
    ok = s.size() == 1 and r == 3
    return ValidatorResult(ok, f"size = {s.size()}, popped count = {r}")

def validate_stack_peek_after(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    s = runtime.retrieve("stack")
    r = runtime.retrieve("result_str")
    ok = s.size() == 1 and r == "A"
    return ValidatorResult(ok, f"size = {s.size()}, top = {r}")


# ============================================================================
# EXPORTS
# ============================================================================

tools = []

variables = [
    Variable("person", person, "Person object. Attributes: name (str), age (int), city (str). Methods: introduce() -> str, have_birthday()."),
    Variable("account", account, "BankAccount with balance=1000.0. Methods: deposit(amount), withdraw(amount), apply_interest(rate)."),
    Variable("cart", cart, "ShoppingCart with empty items list. Methods: add_item(dict with keys: name, price, quantity), remove_item(name), get_total() -> float, clear()."),
    Variable("counter", counter, "Counter with value=0. Methods: increment(), decrement(), add(n), reset()."),
    Variable("stack", stack, "Stack (LIFO). Methods: push(item), pop() -> item, peek() -> item, size() -> int."),
    Variable("result_str", result_str, "Store string results here."),
    Variable("result_num", result_num, "Store numeric results here."),
]

types = [
    Type(Person),
    Type(BankAccount),
    Type(ShoppingCart),
    Type(Counter),
    Type(Stack),
]

validators = {
    # Person
    "validate_person_init": validate_person_init,
    "validate_person_update": validate_person_update,
    "validate_person_method": validate_person_method,
    "validate_person_birthday_init": validate_person_birthday_init,
    "validate_person_birthday": validate_person_birthday,
    "validate_person_birthday2": validate_person_birthday2,
    # BankAccount
    "validate_account_deposit": validate_account_deposit,
    "validate_account_withdraw": validate_account_withdraw,
    "validate_account_interest": validate_account_interest,
    "validate_account_multi_deposit": validate_account_multi_deposit,
    "validate_account_multi_withdraw": validate_account_multi_withdraw,
    "validate_account_balance": validate_account_balance,
    # ShoppingCart
    "validate_cart_add": validate_cart_add,
    "validate_cart_add2": validate_cart_add2,
    "validate_cart_total": validate_cart_total,
    "validate_cart_qty_add": validate_cart_qty_add,
    "validate_cart_qty_add2": validate_cart_qty_add2,
    "validate_cart_qty_total": validate_cart_qty_total,
    # Counter
    "validate_counter_inc": validate_counter_inc,
    "validate_counter_mixed": validate_counter_mixed,
    "validate_counter_reset": validate_counter_reset,
    "validate_counter_add10": validate_counter_add10,
    "validate_counter_add5": validate_counter_add5,
    "validate_counter_store": validate_counter_store,
    # Stack
    "validate_stack_push": validate_stack_push,
    "validate_stack_pop": validate_stack_pop,
    "validate_stack_peek": validate_stack_peek,
    "validate_stack_push_nums": validate_stack_push_nums,
    "validate_stack_pop_sum": validate_stack_pop_sum,
    "validate_stack_size": validate_stack_size,
    # ShoppingCart Removal
    "validate_cart_add_items": validate_cart_add_items,
    "validate_cart_remove": validate_cart_remove,
    "validate_cart_clear": validate_cart_clear,
    # Stack Advanced
    "validate_stack_multi_push": validate_stack_multi_push,
    "validate_stack_pop_until": validate_stack_pop_until,
    "validate_stack_peek_after": validate_stack_peek_after,
}
