"""Result-file inspection helpers shared by the runner's resume logic.

Output files are stable per (suite, exp_id, benchmark) — no timestamps, no
sibling files — so the only convention that matters here is distinguishing
a COMPLETE result (every turn evaluated, pass or fail) from one frozen by an
infrastructure error (API failure, bad import), which must be retried on
resume rather than permanently recorded as a model failure.
"""

from typing import Any, Dict


def result_has_infra_error(data: Dict[str, Any]) -> bool:
    """True if any turn in a loaded result dict carries an infra `error`.

    Turns written by `runner._make_error_result` (scenario-level crash) and
    turns aborted mid-conversation both set `error`; genuine model failures
    do not. Resume logic treats such results as retryable, not completed.
    """
    for scenario in data.values():
        if not isinstance(scenario, dict):
            continue
        for conv in scenario.get("conversations", []):
            for turn in conv.get("turns", []):
                if turn.get("error"):
                    return True
    return False


def result_is_complete(data: Dict[str, Any]) -> bool:
    """True if every turn in a loaded result dict was evaluated.

    "Evaluated" means the turn has a `success` verdict — pass or fail — and
    no infrastructure `error`. A result where the model legitimately failed
    counts as complete; a result frozen by an API outage does not.
    """
    for scenario in data.values():
        if not isinstance(scenario, dict):
            continue
        for conv in scenario.get("conversations", []):
            for turn in conv.get("turns", []):
                if "success" not in turn or turn.get("error"):
                    return False
    return True
