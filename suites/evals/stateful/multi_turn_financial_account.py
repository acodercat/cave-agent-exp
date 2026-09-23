"""
Financial Account Benchmark - Multi-Turn Stateful Management

Tests agent's ability to maintain and manipulate state across 20 turns.
Each turn requires reading from runtime state to perform operations.

Checkpoints: Turn 5, 10, 15, 20

Key principle: Queries do NOT include current values - agent must read from runtime.

Conversations:
- alice: Savings growth - starts with $1000, earns interest, reaches gold status
- carol: Debt paydown - starts with $2000 loan, pays it off, then builds savings
"""

from typing import List
from cave_agent import Variable, IPythonRuntime
from core.validation import ValidatorResult
from core.types import Turn, ToolCall


# ============================================================================
# INITIAL STATE
# ============================================================================

account_name = ""
balance = 0.0
status = ""
interest_rate = 0.0
history = []
loan_balance = 0.0
rewards_points = 0


# ============================================================================
# VALIDATORS - HELPER
# ============================================================================

def _compare_history_entry(actual: dict, expected: dict) -> bool:
    """Compare two history entries, treating 488.0 == 488."""
    if actual.get("type") != expected.get("type"):
        return False
    if "amount" in expected:
        if "amount" not in actual:
            return False
        # Accept float amounts equal to int (488.0 == 488)
        if abs(float(actual["amount"]) - float(expected["amount"])) > 0.01:
            return False
    return True


def _check_history(actual: list, expected: list) -> bool:
    """Check if all expected entries exist in actual history (in order, allows extra entries)."""
    if len(actual) < len(expected):
        return False
    exp_idx = 0
    for act_entry in actual:
        if exp_idx < len(expected) and _compare_history_entry(act_entry, expected[exp_idx]):
            exp_idx += 1
    return exp_idx == len(expected)


def _check(runtime: IPythonRuntime, expected: dict) -> list:
    """Validate runtime state against expected values."""
    errors = []
    for key, exp_val in expected.items():
        actual = runtime.retrieve(key)
        if isinstance(exp_val, float):
            if not isinstance(actual, (int, float)) or abs(actual - exp_val) > 0.01:
                errors.append(f"{key}={actual} (expected {exp_val})")
        elif isinstance(exp_val, list) and key == "history":
            # For history, check expected entries exist in order (allow extra)
            if not _check_history(actual, exp_val):
                errors.append(f"{key}={actual} (expected {exp_val})")
        elif isinstance(exp_val, list):
            if actual != exp_val:
                errors.append(f"{key}={actual} (expected {exp_val})")
        else:
            if actual != exp_val:
                errors.append(f"{key}={actual} (expected {exp_val})")
    return errors


# ============================================================================
# VALIDATORS - ALICE (Conversation 1: Savings Growth)
# ============================================================================

def validate_alice_turn_1(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "account_name": "Alice",
        "balance": 1000.0,
        "status": "standard",
        "interest_rate": 0.03,
        "history": [{"type": "account_opened"}],
        "loan_balance": 0.0,
        "rewards_points": 0
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 1 passed")


def validate_alice_turn_2(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "balance": 1500.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 2 passed")


def validate_alice_turn_3(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "balance": 1200.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 3 passed")


def validate_alice_turn_4(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "status": "premium",
        "balance": 1200.0
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 4 passed")


def validate_alice_turn_5(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "balance": 1236.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 1 (Turn 5) passed")


def validate_alice_turn_6(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "balance": 1456.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 6 passed")


def validate_alice_turn_7(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "rewards_points": 14,
        "balance": 1456.0
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 7 passed")


def validate_alice_turn_8(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "balance": 1400.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}, {"type": "withdraw", "amount": 56}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 8 passed")


def validate_alice_turn_9(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "interest_rate": 0.05,
        "balance": 1400.0,
        "status": "premium"
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 9 passed")


def validate_alice_turn_10(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "balance": 1470.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}, {"type": "withdraw", "amount": 56}, {"type": "interest", "amount": 70}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 2 (Turn 10) passed")


def validate_alice_turn_11(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "loan_balance": 735.0,
        "balance": 2205.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}, {"type": "withdraw", "amount": 56}, {"type": "interest", "amount": 70}, {"type": "loan", "amount": 735}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 11 passed")


def validate_alice_turn_12(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "loan_balance": 588.0,
        "balance": 2058.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}, {"type": "withdraw", "amount": 56}, {"type": "interest", "amount": 70}, {"type": "loan", "amount": 735}, {"type": "loan_payment", "amount": 147}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 12 passed")


def validate_alice_turn_13(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "status": "gold",
        "balance": 2058.0,
        "loan_balance": 588.0
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 13 passed")


def validate_alice_turn_14(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    expected = {
        "interest_rate": 0.07,
        "status": "gold"
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 14 passed")


def validate_alice_turn_15(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    prev_balance = 2058
    rate = 0.07
    prev_rewards = 14
    interest = int(prev_balance * rate)
    expected_balance = prev_balance + interest
    bonus = int(interest / 10)
    expected = {
        "balance": float(expected_balance),
        "rewards_points": prev_rewards + bonus,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}, {"type": "withdraw", "amount": 56}, {"type": "interest", "amount": 70}, {"type": "loan", "amount": 735}, {"type": "loan_payment", "amount": 147}, {"type": "interest", "amount": interest}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 3 (Turn 15) passed")


def validate_alice_turn_16(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    prev_balance = 2058 + int(2058 * 0.07)  # from turn 15
    prev_loan = 588
    prev_rewards = 14 + int(int(2058 * 0.07) / 10)  # from turn 15
    expected = {
        "loan_balance": float(prev_loan - 100),
        "rewards_points": prev_rewards - 10,
        "balance": float(prev_balance)
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 16 passed")


def validate_alice_turn_17(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    prev_balance = 2058 + int(2058 * 0.07)  # 2202
    dividend = int(prev_balance * 0.02)  # gold = 2%
    expected = {
        "balance": float(prev_balance + dividend),
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}, {"type": "withdraw", "amount": 56}, {"type": "interest", "amount": 70}, {"type": "loan", "amount": 735}, {"type": "loan_payment", "amount": 147}, {"type": "interest", "amount": int(2058*0.07)}, {"type": "dividend", "amount": dividend}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 17 passed")


def validate_alice_turn_18(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    balance_after_15 = 2058 + int(2058 * 0.07)  # 2202
    dividend = int(balance_after_15 * 0.02)  # 44
    balance_after_17 = balance_after_15 + dividend  # 2246
    loan_to_pay = 588 - 100  # 488
    expected = {
        "balance": float(balance_after_17 - loan_to_pay),
        "loan_balance": 0.0,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}, {"type": "withdraw", "amount": 56}, {"type": "interest", "amount": 70}, {"type": "loan", "amount": 735}, {"type": "loan_payment", "amount": 147}, {"type": "interest", "amount": int(2058*0.07)}, {"type": "dividend", "amount": dividend}, {"type": "loan_payoff", "amount": loan_to_pay}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 18 passed")


def validate_alice_turn_19(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    interest_15 = int(2058 * 0.07)
    rewards_after_15 = 14 + int(interest_15 / 10)  # 28
    rewards_after_16 = rewards_after_15 - 10  # 18
    expected = {
        "rewards_points": rewards_after_16 + 50,  # +50 for loan payoff
        "loan_balance": 0.0
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 19 passed")


def validate_alice_turn_20(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    interest_15 = int(2058 * 0.07)  # 144
    balance_after_15 = 2058 + interest_15  # 2202
    dividend = int(balance_after_15 * 0.02)  # 44
    balance_after_17 = balance_after_15 + dividend  # 2246
    loan_paid = 588 - 100  # 488
    balance_after_18 = balance_after_17 - loan_paid  # 1758
    final_interest = int(balance_after_18 * 0.07)  # 123
    final_balance = balance_after_18 + final_interest  # 1881
    rewards_after_15 = 14 + int(interest_15 / 10)  # 28
    final_rewards = rewards_after_15 - 10 + 50  # 68
    expected = {
        "account_name": "Alice",
        "balance": float(final_balance),
        "status": "gold",
        "interest_rate": 0.07,
        "loan_balance": 0.0,
        "rewards_points": final_rewards,
        "history": [{"type": "account_opened"}, {"type": "deposit", "amount": 500}, {"type": "withdraw", "amount": 300}, {"type": "interest", "amount": 36}, {"type": "deposit", "amount": 220}, {"type": "withdraw", "amount": 56}, {"type": "interest", "amount": 70}, {"type": "loan", "amount": 735}, {"type": "loan_payment", "amount": 147}, {"type": "interest", "amount": interest_15}, {"type": "dividend", "amount": dividend}, {"type": "loan_payoff", "amount": loan_paid}, {"type": "interest", "amount": final_interest}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 4 (Turn 20) passed - ALICE COMPLETE")


# ============================================================================
# VALIDATORS - CAROL (Conversation 2: Debt Paydown Journey)
# Completely different query patterns - starts with debt, pays it off
# ============================================================================

def validate_carol_turn_1(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Initialize with existing debt"""
    expected = {
        "account_name": "Carol",
        "balance": 500.0,
        "status": "standard",
        "interest_rate": 0.08,  # This is LOAN rate (bad)
        "history": [{"type": "account_opened"}],
        "loan_balance": 2000.0,  # Starts with debt!
        "rewards_points": 0
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 1 passed")


def validate_carol_turn_2(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Loan interest ADDED to loan (negative for user)"""
    initial_loan = 2000
    rate = 0.08
    interest = int(initial_loan * rate)
    expected = {
        "loan_balance": float(initial_loan + interest),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": interest}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 2 passed")


def validate_carol_turn_3(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Receive paycheck - fixed 800 for standard status"""
    initial_balance = 500
    loan_interest = int(2000 * 0.08)
    paycheck = 800
    expected = {
        "balance": float(initial_balance + paycheck),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": loan_interest}, {"type": "paycheck", "amount": paycheck}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 3 passed")


def validate_carol_turn_4(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Pay minimum: smaller of 15% of balance or 15% of loan"""
    balance_3 = 500 + 800  # 1300
    loan_2 = 2000 + int(2000 * 0.08)  # 2160
    payment = min(int(balance_3 * 0.15), int(loan_2 * 0.15))  # min(195, 324) = 195
    expected = {
        "balance": float(balance_3 - payment),
        "loan_balance": float(loan_2 - payment),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 4 passed")


def validate_carol_turn_5(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Earn rewards for payment: 1 point per 50 paid"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    rewards = int(payment_4 / 50)
    expected = {
        "rewards_points": rewards,
        "loan_balance": float(loan_2 - payment_4)
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 1 (Turn 5) passed")


def validate_carol_turn_6(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Emergency expense: lose 30% of balance"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    balance_4 = balance_3 - payment_4  # 1105
    emergency = int(balance_4 * 0.30)
    expected = {
        "balance": float(balance_4 - emergency),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_4}, {"type": "emergency", "amount": emergency}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 6 passed")


def validate_carol_turn_7(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Second paycheck arrives"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    expected = {
        "balance": float(balance_7),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_4}, {"type": "emergency", "amount": emergency}, {"type": "paycheck", "amount": 800}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 7 passed")


def validate_carol_turn_8(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Aggressive payment: pay the LARGER of 40% of balance or 500"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    balance_4 = balance_3 - payment_4
    loan_4 = loan_2 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    expected = {
        "balance": float(balance_7 - payment_8),
        "loan_balance": float(loan_4 - payment_8),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_4}, {"type": "emergency", "amount": emergency}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_8}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 8 passed")


def validate_carol_turn_9(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Debt reduction milestone: if loan dropped 25%+ from original 2000, earn 20 bonus points"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    loan_8 = loan_4 - payment_8
    rewards_5 = int(payment_4 / 50)
    # Milestone: dropped 25%+ from original 2000
    rewards_9 = rewards_5 + 20  # dropped > 25%
    expected = {
        "rewards_points": rewards_9,
        "loan_balance": float(loan_8)
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 9 passed")


def validate_carol_turn_10(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Rate reduction reward: 2+ payments made, reduce rate from 0.08 to 0.05"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    loan_8 = loan_4 - payment_8
    expected = {
        "interest_rate": 0.05,
        "loan_balance": float(loan_8)
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 2 (Turn 10) passed")


def validate_carol_turn_11(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Monthly loan interest at new rate"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    loan_8 = loan_4 - payment_8
    interest_11 = int(loan_8 * 0.05)
    loan_11 = loan_8 + interest_11
    expected = {
        "loan_balance": float(loan_11),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_4}, {"type": "emergency", "amount": emergency}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_8}, {"type": "loan_interest", "amount": interest_11}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 11 passed")


def validate_carol_turn_12(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Bonus income: receive 50% of remaining loan as windfall"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    balance_8 = balance_7 - payment_8
    loan_8 = loan_4 - payment_8
    interest_11 = int(loan_8 * 0.05)
    loan_11 = loan_8 + interest_11
    bonus = int(loan_11 * 0.50)
    expected = {
        "balance": float(balance_8 + bonus),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_4}, {"type": "emergency", "amount": emergency}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_8}, {"type": "loan_interest", "amount": interest_11}, {"type": "bonus", "amount": bonus}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 12 passed")


def validate_carol_turn_13(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Convert rewards to payment: each point = $10 off loan"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    balance_8 = balance_7 - payment_8
    loan_8 = loan_4 - payment_8
    interest_11 = int(loan_8 * 0.05)
    loan_11 = loan_8 + interest_11
    bonus = int(loan_11 * 0.50)
    balance_12 = balance_8 + bonus
    rewards_5 = int(payment_4 / 50)
    rewards_9 = rewards_5 + 20
    points_value = rewards_9 * 10
    loan_13 = loan_11 - points_value
    expected = {
        "loan_balance": float(loan_13),
        "rewards_points": 0,
        "balance": float(balance_12)
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 13 passed")


def validate_carol_turn_14(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Upgrade check: if loan < balance, upgrade to premium"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    balance_8 = balance_7 - payment_8
    loan_8 = loan_4 - payment_8
    interest_11 = int(loan_8 * 0.05)
    loan_11 = loan_8 + interest_11
    bonus = int(loan_11 * 0.50)
    balance_12 = balance_8 + bonus
    rewards_5 = int(payment_4 / 50)
    rewards_9 = rewards_5 + 20
    points_value = rewards_9 * 10
    loan_13 = loan_11 - points_value
    expected = {
        "status": "premium",
        "loan_balance": float(loan_13),
        "balance": float(balance_12)
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 14 passed")


def validate_carol_turn_15(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Premium paycheck: 1000 instead of 800"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    balance_8 = balance_7 - payment_8
    loan_8 = loan_4 - payment_8
    interest_11 = int(loan_8 * 0.05)
    loan_11 = loan_8 + interest_11
    bonus = int(loan_11 * 0.50)
    balance_12 = balance_8 + bonus
    balance_15 = balance_12 + 1000
    expected = {
        "balance": float(balance_15),
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_4}, {"type": "emergency", "amount": emergency}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_8}, {"type": "loan_interest", "amount": interest_11}, {"type": "bonus", "amount": bonus}, {"type": "paycheck", "amount": 1000}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 3 (Turn 15) passed")


def validate_carol_turn_16(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Pay off entire loan if balance > loan, otherwise pay 75%"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    balance_8 = balance_7 - payment_8
    loan_8 = loan_4 - payment_8
    interest_11 = int(loan_8 * 0.05)
    loan_11 = loan_8 + interest_11
    bonus = int(loan_11 * 0.50)
    balance_12 = balance_8 + bonus
    rewards_5 = int(payment_4 / 50)
    rewards_9 = rewards_5 + 20
    points_value = rewards_9 * 10
    loan_13 = loan_11 - points_value
    balance_15 = balance_12 + 1000
    # balance_15 > loan_13, so pay off entire loan
    balance_16 = balance_15 - loan_13
    expected = {
        "balance": float(balance_16),
        "loan_balance": 0.0,
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_4}, {"type": "emergency", "amount": emergency}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_8}, {"type": "loan_interest", "amount": interest_11}, {"type": "bonus", "amount": bonus}, {"type": "paycheck", "amount": 1000}, {"type": "loan_payoff", "amount": loan_13}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 16 passed")


def validate_carol_turn_17(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Debt freedom bonus: 100 points for paying off loan"""
    expected = {
        "rewards_points": 100,
        "loan_balance": 0.0
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 17 passed")


def validate_carol_turn_18(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Switch to savings mode: change rate to 0.04 (now earning interest)"""
    expected = {
        "interest_rate": 0.04,
        "loan_balance": 0.0
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 18 passed")


def validate_carol_turn_19(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Upgrade to gold: loan = 0 AND balance > 1000 AND rewards >= 100"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    balance_8 = balance_7 - payment_8
    loan_8 = loan_4 - payment_8
    interest_11 = int(loan_8 * 0.05)
    loan_11 = loan_8 + interest_11
    bonus = int(loan_11 * 0.50)
    balance_12 = balance_8 + bonus
    rewards_5 = int(payment_4 / 50)
    rewards_9 = rewards_5 + 20
    points_value = rewards_9 * 10
    loan_13 = loan_11 - points_value
    balance_15 = balance_12 + 1000
    balance_16 = balance_15 - loan_13
    expected = {
        "status": "gold",
        "balance": float(balance_16),
        "rewards_points": 100
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Turn 19 passed")


def validate_carol_turn_20(response: str, runtime: IPythonRuntime, turn: Turn, actual_calls: List[ToolCall]) -> ValidatorResult:
    """Final: earn savings interest and complete journey"""
    balance_3 = 500 + 800
    loan_2 = 2000 + int(2000 * 0.08)
    payment_4 = min(int(balance_3 * 0.15), int(loan_2 * 0.15))
    loan_4 = loan_2 - payment_4
    balance_4 = balance_3 - payment_4
    emergency = int(balance_4 * 0.30)
    balance_6 = balance_4 - emergency
    balance_7 = balance_6 + 800
    payment_8 = max(int(balance_7 * 0.40), 500)
    balance_8 = balance_7 - payment_8
    loan_8 = loan_4 - payment_8
    interest_11 = int(loan_8 * 0.05)
    loan_11 = loan_8 + interest_11
    bonus = int(loan_11 * 0.50)
    balance_12 = balance_8 + bonus
    rewards_5 = int(payment_4 / 50)
    rewards_9 = rewards_5 + 20
    points_value = rewards_9 * 10
    loan_13 = loan_11 - points_value
    balance_15 = balance_12 + 1000
    balance_16 = balance_15 - loan_13
    final_interest = int(balance_16 * 0.04)
    final_balance = balance_16 + final_interest
    expected = {
        "account_name": "Carol",
        "balance": float(final_balance),
        "status": "gold",
        "interest_rate": 0.04,
        "loan_balance": 0.0,
        "rewards_points": 100,
        "history": [{"type": "account_opened"}, {"type": "loan_interest", "amount": int(2000*0.08)}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_4}, {"type": "emergency", "amount": emergency}, {"type": "paycheck", "amount": 800}, {"type": "loan_payment", "amount": payment_8}, {"type": "loan_interest", "amount": interest_11}, {"type": "bonus", "amount": bonus}, {"type": "paycheck", "amount": 1000}, {"type": "loan_payoff", "amount": loan_13}, {"type": "interest", "amount": final_interest}]
    }
    errors = _check(runtime, expected)
    if errors:
        return ValidatorResult(False, "; ".join(errors[:3]))
    return ValidatorResult(True, "Checkpoint 4 (Turn 20) passed - CAROL COMPLETE")


# ============================================================================
# VARIABLES DEFINITION
# ============================================================================

variables = [
    Variable("account_name", account_name, "Account holder's name (str)."),
    Variable("balance", balance, "Current account balance (float). Read this to know current balance."),
    Variable("status", status, "Account status: 'standard', 'premium', or 'gold' (str)."),
    Variable("interest_rate", interest_rate, "Current interest rate as decimal (float). For loans this rate is charged; for savings this rate is earned."),
    Variable("history", history, """List of event records (list[dict], initial: []). Each entry is a dict with 'type' (str) and optionally 'amount' (int).
Valid event types:
- account_opened: {'type': 'account_opened'} - no amount
- deposit: {'type': 'deposit', 'amount': 500}
- withdraw: {'type': 'withdraw', 'amount': 300}
- interest: {'type': 'interest', 'amount': 36} - interest earned on savings
- loan: {'type': 'loan', 'amount': 735} - taking out a loan
- loan_payment: {'type': 'loan_payment', 'amount': 147} - partial loan payment
- loan_payoff: {'type': 'loan_payoff', 'amount': 488} - full loan payoff
- loan_interest: {'type': 'loan_interest', 'amount': 160} - interest charged on loan
- paycheck: {'type': 'paycheck', 'amount': 800}
- emergency: {'type': 'emergency', 'amount': 331} - emergency expense
- bonus: {'type': 'bonus', 'amount': 701} - bonus received
- dividend: {'type': 'dividend', 'amount': 44}"""),
    Variable("loan_balance", loan_balance, "Outstanding loan amount (float)."),
    Variable("rewards_points", rewards_points, "Loyalty reward points (int)."),
]


validators = {
    # Alice validators (Savings Growth)
    "validate_alice_turn_1": validate_alice_turn_1,
    "validate_alice_turn_2": validate_alice_turn_2,
    "validate_alice_turn_3": validate_alice_turn_3,
    "validate_alice_turn_4": validate_alice_turn_4,
    "validate_alice_turn_5": validate_alice_turn_5,
    "validate_alice_turn_6": validate_alice_turn_6,
    "validate_alice_turn_7": validate_alice_turn_7,
    "validate_alice_turn_8": validate_alice_turn_8,
    "validate_alice_turn_9": validate_alice_turn_9,
    "validate_alice_turn_10": validate_alice_turn_10,
    "validate_alice_turn_11": validate_alice_turn_11,
    "validate_alice_turn_12": validate_alice_turn_12,
    "validate_alice_turn_13": validate_alice_turn_13,
    "validate_alice_turn_14": validate_alice_turn_14,
    "validate_alice_turn_15": validate_alice_turn_15,
    "validate_alice_turn_16": validate_alice_turn_16,
    "validate_alice_turn_17": validate_alice_turn_17,
    "validate_alice_turn_18": validate_alice_turn_18,
    "validate_alice_turn_19": validate_alice_turn_19,
    "validate_alice_turn_20": validate_alice_turn_20,
    # Carol validators (Debt Paydown)
    "validate_carol_turn_1": validate_carol_turn_1,
    "validate_carol_turn_2": validate_carol_turn_2,
    "validate_carol_turn_3": validate_carol_turn_3,
    "validate_carol_turn_4": validate_carol_turn_4,
    "validate_carol_turn_5": validate_carol_turn_5,
    "validate_carol_turn_6": validate_carol_turn_6,
    "validate_carol_turn_7": validate_carol_turn_7,
    "validate_carol_turn_8": validate_carol_turn_8,
    "validate_carol_turn_9": validate_carol_turn_9,
    "validate_carol_turn_10": validate_carol_turn_10,
    "validate_carol_turn_11": validate_carol_turn_11,
    "validate_carol_turn_12": validate_carol_turn_12,
    "validate_carol_turn_13": validate_carol_turn_13,
    "validate_carol_turn_14": validate_carol_turn_14,
    "validate_carol_turn_15": validate_carol_turn_15,
    "validate_carol_turn_16": validate_carol_turn_16,
    "validate_carol_turn_17": validate_carol_turn_17,
    "validate_carol_turn_18": validate_carol_turn_18,
    "validate_carol_turn_19": validate_carol_turn_19,
    "validate_carol_turn_20": validate_carol_turn_20,
}
