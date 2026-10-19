"""Q5 chain study: runs, crossings, re-runs and first attempts, per arm.

    uv run python analysis/x5_audit.py \
        --model deepseek=../../caveagent-results/bench/experiments/x5-rounds-deepseek-v4-flash-oneapi \
        --model qwen3.8=../../caveagent-results/bench/experiments/x5-rounds-qwen3.8-flash \
        --model qwen-coder=../../caveagent-results/bench/experiments/x5-rounds-qwen3-coder-30b \
        cave=cave-v1 file=file-v1 text=text-v1 json=json-v1 [--json out.json]

Each ``--model NAME=PREFIX`` names one model's experiments; each ``ARM=SUFFIX``
is read as ``PREFIX-SUFFIX`` for every model, and a model missing an arm is
skipped for it. The counting rules, which the paper's figures follow:

* A run is *intact* if the object matched the host's reference after every
  stage (``applied`` on every hop), the paper's Table 15. Cells are out of the
  runs the arm was to make (``--planned``, 9 per depth by default: 3 objects x
  3 repeats), so a run that never finished counts against the arm.
* A crossing is a hop after the producer whose ``carried`` is not None; the
  object crossed *unchanged* if ``carried`` is true. Crossings within one run
  are not independent, so the pooled counts are descriptive; the unit of
  replication is the run. ``input_seen`` says who observed the crossing: the
  host, from the worker's input slot (the cave arms), or the agent's own binding
  of what it received (every other arm).
* A *re-run* is a worker run more than once in a run. Only a worker's last run
  is judged in ``hops``; where the record keeps every run (``invocations``,
  written by the current runner), a run is *intact on first attempt* if every
  worker's first run completed and left the object matching the reference. For
  older records only bounds exist: an intact run with no re-run was intact on
  its first attempt (lower bound), and any intact run may have been (upper).
* *Producer correct*: the object as built matched the reference, so any later
  loss happened in the chain (a crossing or an edit) rather than at the start.
* *Answered from a degraded object*: the consumer's answer was right although
  the object it held was not the reference (the run's ``success`` is false),
  which a final-answer check alone would have passed. This is the paper's
  count (23 and 29 of 81 runs in the text arms, 10 of 162 in the object arms).
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import statistics

PLANNED = 9


def load(prefix: str, suffix: str) -> list[dict]:
    return [json.load(open(path)) for path in sorted(glob.glob(f"{prefix}-{suffix}/runs/*/*/*/pipeline.json"))]


def intact(run: dict) -> bool:
    return all(hop["applied"] for hop in run["hops"])


def rerun(run: dict) -> bool:
    return any(worker["runs"] > 1 for worker in run["workers"])


def first_attempt(run: dict) -> bool | None:
    """Intact on every worker's first run, or None where the record keeps only the last run."""
    if not all("invocations" in worker for worker in run["workers"]):
        return None
    for worker in run["workers"]:
        first = worker["invocations"][0] if worker["invocations"] else None
        if first is None or not first["completed"] or not first.get("applied"):
            return False
    return True


def crossings(run: dict, *, first: bool = False) -> collections.Counter:
    """Observed and unchanged crossings, by who observed them; ``first`` reads first runs only."""
    count = collections.Counter()
    for worker, hop in zip(run["workers"][1:], run["hops"][1:]):
        if first:
            runs = worker.get("invocations") or []
            hop = runs[0] if runs and runs[0]["completed"] else {}
        if hop.get("carried") is None:
            continue
        seen = hop.get("input_seen") or "unknown"
        count[f"observed_{seen}"] += 1
        count[f"unchanged_{seen}"] += bool(hop["carried"])
    return count


def cell(runs: list[dict], planned: int) -> dict:
    exact = [first_attempt(run) for run in runs]
    row = {
        "runs": len(runs), "planned": planned,
        "intact": sum(intact(run) for run in runs),
        # The producer built the object right: what is left to lose is the chain's.
        "producer_correct": sum(bool(run["hops"][0]["applied"]) for run in runs),
        "success": sum(bool(run["success"]) for run in runs),
        "with_rerun": sum(rerun(run) for run in runs),
        "extra_worker_runs": sum(max(worker["runs"] - 1, 0) for run in runs for worker in run["workers"]),
        "skipped_workers": sum(bool(run["skipped"]) for run in runs),
        "budget_exceeded": sum(bool(run["budget_exceeded"]) for run in runs),
        "answered_degraded": sum(
            bool(run["workers"][-1].get("answered")) and not run["success"] for run in runs
        ),
        "median_tokens": statistics.median(run["tokens"] for run in runs) if runs else None,
        "median_elapsed_s": statistics.median(run["elapsed_s"] for run in runs) if runs else None,
        "crossings": dict(sum((crossings(run) for run in runs), collections.Counter())),
    }
    if runs and all(value is not None for value in exact):
        row["first_attempt_intact"] = sum(exact)
        row["first_attempt_crossings"] = dict(
            sum((crossings(run, first=True) for run in runs), collections.Counter()),
        )
    else:
        row["first_attempt_intact_bounds"] = [
            sum(intact(run) and not rerun(run) for run in runs), row["intact"],
        ]
    return row


def audit(models: dict[str, str], arms: dict[str, str], planned: int) -> dict:
    out = {}
    for model, prefix in models.items():
        for arm, suffix in arms.items():
            runs = load(prefix, suffix)
            if not runs:
                continue
            by_depth = collections.defaultdict(list)
            for run in runs:
                by_depth[run["depth"]].append(run)
            out.setdefault(model, {})[arm] = {
                depth: cell(rows, planned) for depth, rows in sorted(by_depth.items())
            }
    return out


def pooled_crossings(result: dict) -> dict[str, list[int]]:
    """Unchanged / observed crossings per arm over every model and depth (descriptive)."""
    pooled = collections.defaultdict(collections.Counter)
    for arms in result.values():
        for arm, depths in arms.items():
            for row in depths.values():
                pooled[arm].update(row["crossings"])
    return {
        arm: [sum(v for k, v in c.items() if k.startswith("unchanged")),
              sum(v for k, v in c.items() if k.startswith("observed"))]
        for arm, c in pooled.items()
    }


def show(result: dict) -> None:
    head = (f"{'model':11} {'arm':12} {'d':>2} {'built':>5} {'intact':>7} {'first':>7} {'rerun':>5} "
            f"{'budget':>6} {'degr.ans':>8} {'tokens':>7} {'wall':>6}  crossings unchanged/observed")
    print(head)
    for model, arms in result.items():
        for arm, depths in arms.items():
            for depth, row in depths.items():
                first = (f"{row['first_attempt_intact']}/{row['planned']}" if "first_attempt_intact" in row
                         else "{}-{}".format(*row["first_attempt_intact_bounds"]))
                c = row["crossings"]
                seen = ", ".join(
                    f"{who}: {c.get(f'unchanged_{who}', 0)}/{c[f'observed_{who}']}"
                    for who in ("host", "agent", "unknown") if f"observed_{who}" in c
                )
                print(
                    f"{model:11} {arm:12} {depth:>2} {row['producer_correct']:>5} "
                    f"{row['intact']:>3}/{row['planned']:<3} {first:>7} "
                    f"{row['with_rerun']:>5} {row['budget_exceeded']:>6} {row['answered_degraded']:>8} "
                    f"{row['median_tokens'] / 1000:>6.0f}k {row['median_elapsed_s']:>5.0f}s  {seen}"
                )
    print("\npooled crossings, unchanged/observed (descriptive: crossings within a run are dependent)")
    for arm, (unchanged, observed) in pooled_crossings(result).items():
        print(f"  {arm:12} {unchanged}/{observed}" + (f" = {unchanged / observed:.3f}" if observed else ""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", action="append", required=True, metavar="NAME=PREFIX")
    parser.add_argument("--planned", type=int, default=PLANNED, help="runs per arm and depth")
    parser.add_argument("--json", metavar="PATH", help="also write the result as JSON")
    parser.add_argument("arms", nargs="+", metavar="ARM=SUFFIX")
    args = parser.parse_args()
    models = dict(m.split("=", 1) for m in args.model)
    arms = dict(a.split("=", 1) for a in args.arms)
    result = audit(models, arms, args.planned)
    show(result)
    if args.json:
        with open(args.json, "w") as out:
            json.dump({"models": models, "arms": arms, "cells": result,
                       "pooled_crossings": pooled_crossings(result)}, out, indent=1)


if __name__ == "__main__":
    main()
