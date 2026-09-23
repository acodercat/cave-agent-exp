"""Where the paradigms differ, task by task, for reading a result rather than
reporting it.

`paired.py` gives the number the paper reports. This says what is behind it: the
tasks one paradigm solved and the other did not, how each failed, and how much
work each did, so a difference can be explained rather than only measured.

    uv run python compare.py --model qwen3.8-flash
"""

from __future__ import annotations

import argparse
from collections import Counter
from statistics import fmean, median

from bfcl_multiturn import results
from paired import ARMS, runs


def outcomes(payloads: list[dict]) -> dict[str, dict]:
    """One row per task, from the first run that produced evidence for it."""
    rows: dict[str, dict] = {}
    for payload in payloads:
        for task in results.scored(payload):
            rows.setdefault(task["id"], task)
    return rows


def effort(task: dict) -> tuple[int, int]:
    """How much the arm did: calls made, and steps the model took."""
    calls = sum(len(step) for turn in task["turns"] for step in turn["calls"])
    steps = sum(turn["model_steps"] for turn in task["turns"])
    return calls, steps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True)
    parser.add_argument("--show", type=int, default=10, help="how many differing tasks to list")
    options = parser.parse_args()

    sides = {arm: outcomes(runs(arm, options.model)) for arm in ARMS}
    for arm, rows in sides.items():
        if not rows:
            raise SystemExit(f"no {arm} results for {options.model}")
    shared = sorted(set(sides["cave"]) & set(sides["fc"]))
    print(f"\n## {options.model}: {len(shared)} tasks both arms scored")

    for arm in ARMS:
        rows = [sides[arm][task] for task in shared]
        solved = sum(row["valid"] for row in rows)
        calls = [effort(row)[0] for row in rows]
        steps = [effort(row)[1] for row in rows]
        repaired = sum(1 for row in rows for turn in row["turns"] if turn.get("repaired"))
        exhausted = sum(1 for row in rows for turn in row["turns"]
                        if turn["stop_reason"] == "max_steps")
        print(f"\n  {arm}: {solved}/{len(rows)} = {100 * solved / len(rows):.1f}%")
        print(f"    calls per task  median {median(calls):.0f}, mean {fmean(calls):.1f}")
        print(f"    model steps     median {median(steps):.0f}, mean {fmean(steps):.1f}")
        print(f"    turns that exhausted the budget: {exhausted}"
              + (f", asked to repair their format: {repaired}" if repaired else ""))
        failures = Counter(row.get("error_type") for row in rows if not row["valid"])
        for kind, count in failures.most_common():
            print(f"    {count:3} x {kind}")

    only = {arm: [task for task in shared
                  if sides[arm][task]["valid"] and not sides[other][task]["valid"]]
            for arm, other in (("cave", "fc"), ("fc", "cave"))}
    print(f"\n  solved by cave alone: {len(only['cave'])}"
          f" | by fc alone: {len(only['fc'])}"
          f" | by both: {sum(sides['cave'][t]['valid'] and sides['fc'][t]['valid'] for t in shared)}"
          f" | by neither: {sum(not sides['cave'][t]['valid'] and not sides['fc'][t]['valid'] for t in shared)}")

    for arm in ARMS:
        if not only[arm]:
            continue
        print(f"\n  tasks only {arm} solved (first {options.show}):")
        for task in only[arm][:options.show]:
            other = "fc" if arm == "cave" else "cave"
            classes = ", ".join(sides[arm][task]["involved_classes"])
            print(f"    {task:22} {classes:40} {other} failed: "
                  f"{sides[other][task].get('error_type')}")


if __name__ == "__main__":
    main()
