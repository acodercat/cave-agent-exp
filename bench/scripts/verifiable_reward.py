"""What the runtime state yields as a reward, read from runs already scored.

The paper lists verifiable rewards among the uses of runtime state, and the
reviewers ask what that would mean concretely (R1 #4, R2 #1). It needs no new
experiment: every scored turn in this benchmark already *is* a verifiable
reward. The host retrieves the turn's outputs from the runtime, a frozen
reference implementation recomputes the answer from the source data, and the two
are compared — no human judgement, no model judging the model.

    uv run python -m scripts.verifiable_reward --study x1-b2-v2 --study x1-b1-v1

Two properties decide whether such a signal is usable for learning, and both are
measured here over turns that have already been run:

* **how much room it leaves**: pass@1 against best-of-n over the repeats a study
  holds, which is the margin rejection sampling could select from;
* **how dense it is**: what a failed turn still scores. A scalar answer is right
  or wrong, so its reward is 0/1 and carries almost nothing. A delivered table is
  scored per row and per cell, so a failed turn still reports how much of the
  table was right — and that is only possible because the host holds the table
  itself rather than text the model wrote about it.

This reports the reward's availability and shape. It is not a training result:
nothing here fine-tunes a model, and best-of-n with the reward in hand is an
upper bound on what selection could reach, not a measured policy.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from config import EXPERIMENTS_DIR
from core.results import atomic_write_json, utc_now


def turn_reward(verdict: dict) -> tuple[bool, float | None]:
    """A turn's pass/fail, and the share of its outputs the runtime shows correct.

    A table output scores by cells: the cells of rows that matched, less the ones
    that were wrong, over the cells of the larger of the expected and delivered
    tables — the same shape ``scripts.compare_paradigms`` uses for cell accuracy.
    """
    items = verdict.get("variable_verification", {}).get("items", {})
    scores = []
    for item in items.values():
        if not isinstance(item, dict):
            continue
        table = item.get("table")
        if table and table.get("rows_expected"):
            width = max(len(table.get("cell_errors", {})), 1)
            delivered = max(table["rows_expected"], table.get("rows_delivered", 0))
            right = table.get("rows_matched", 0) * width - sum(table.get("cell_errors", {}).values())
            scores.append(max(0.0, right / max(delivered * width, 1)))
        else:
            scores.append(1.0 if item.get("correct") else 0.0)
    return bool(verdict["success"]), (statistics.fmean(scores) if scores else None)


def read_study(prefix: str) -> dict:
    """Every scored turn of every arm of a study, grouped by what a repeat is."""
    by_attempt: dict[tuple, list[bool]] = defaultdict(list)
    failed_credit: list[float] = []
    turns = 0
    for verdict_file in EXPERIMENTS_DIR.glob(f"{prefix}-*/runs/*/*/*/programmatic_verification.json"):
        arm = verdict_file.parents[4].name.replace(f"{prefix}-", "")
        case = verdict_file.parents[2].name
        payload = json.loads(verdict_file.read_text())
        for conversation in payload["conversations"]:
            for turn in conversation["turns"]:
                if turn.get("status") != "scored":
                    continue
                verdict = turn.get("protocol_repair_verification") or turn["programmatic_verification"]
                if "success" not in verdict:
                    continue
                passed, credit = turn_reward(verdict)
                turns += 1
                by_attempt[(arm, case, conversation["id"], turn["turn"])].append(passed)
                if not passed and credit is not None:
                    failed_credit.append(credit)
    if not turns:
        return {}
    attempts = list(by_attempt.values())
    # Reported per turn index as well: a study whose first turn is easy and whose
    # second carries the risk would otherwise read as one difficulty.
    by_index: dict[int, list[list[bool]]] = defaultdict(list)
    for (_, _, _, index), outcomes in by_attempt.items():
        by_index[index].append(outcomes)
    dense = [credit for credit in failed_credit if credit > 0]
    return {
        "turns": turns,
        "repeats_median": statistics.median(len(a) for a in attempts),
        "pass_at_1": round(statistics.fmean([sum(a) / len(a) for a in attempts]), 4),
        "best_of_n": round(statistics.fmean([float(any(a)) for a in attempts]), 4),
        "failed_turns": len(failed_credit),
        "failed_with_partial_credit": round(len(dense) / len(failed_credit), 4) if failed_credit else None,
        "median_credit_of_failures": round(statistics.median(failed_credit), 4) if failed_credit else None,
        "per_turn": {
            str(index): {
                "groups": len(groups),
                "pass_at_1": round(statistics.fmean([sum(g) / len(g) for g in groups]), 4),
                "best_of_n": round(statistics.fmean([float(any(g)) for g in groups]), 4),
            }
            for index, groups in sorted(by_index.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--study", action="append", required=True, dest="studies",
                        help="study id prefix, repeatable (the arm suffix is matched)")
    parser.add_argument("--out", type=Path, help="write the report here as well")
    args = parser.parse_args()

    report = {"read_at": utc_now(),
              "studies": {study: read_study(study) for study in args.studies}}
    for study, summary in report["studies"].items():
        if not summary:
            print(f"{study}: no scored turns")
            continue
        print(f"{study}: {summary['turns']} scored turns, median {summary['repeats_median']:.0f} repeats")
        print(f"  pass@1 {summary['pass_at_1']:.3f} -> best-of-n {summary['best_of_n']:.3f}")
        print(f"  failed turns carrying partial credit: {summary['failed_with_partial_credit']} "
              f"(median credit {summary['median_credit_of_failures']})")
        for index, turn in summary["per_turn"].items():
            print(f"    turn {index}: pass@1 {turn['pass_at_1']:.3f} -> "
                  f"best-of-n {turn['best_of_n']:.3f} over {turn['groups']} groups")
    if args.out:
        atomic_write_json(args.out / "verifiable_reward.json", report)
        print(args.out / "verifiable_reward.json")


if __name__ == "__main__":
    main()
