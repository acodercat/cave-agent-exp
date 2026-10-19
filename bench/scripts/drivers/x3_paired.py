"""X3 for the paper: success, task-paired differences against the cave arm, and token cost.

    python scripts/drivers/x3_paired.py experiments/x3-orch-deepseek cave=cave-v6 file=file-v7 text=text-v6 json=json-v6
    python scripts/drivers/x3_paired.py ... --unit case        # case-level intervals
    python scripts/drivers/x3_paired.py ... --json out.json    # also write everything printed (merged into out.json)

Each case (task × size, named ``<task>_<size>``) carries the mean of its runs; a
run that never completed is a failure, as in the results tables. The interval is
a paired bootstrap, 10,000 resamples, as Q4 reports its intervals, over the
resampling unit ``--unit``:

* ``task`` (default): the 24 tasks are drawn with replacement and each brings
  its three sizes along, so the interval allows for sizes of one task being
  alike. The statistic is the mean over every case drawn.
* ``case``: the 72 cases are drawn independently. This gives the earlier,
  case-level intervals.

The point estimates do not depend on the unit. Tokens are the study's estimated
prompt + completion over every agent of a run; the per-case median is reported,
and the ratio to cave is bootstrapped over the same unit, per-case medians
divided case by case. Token figures are conditional on a run having a record
with agents: a run that timed out, was closed by manual adjudication or was
never stored has none, and the number of runs each figure rests on is printed.

Unfinished runs are the cases × 3 planned runs (the cases being those stored in
any arm) that have no completed trajectory, by reason: ``timed_out`` (stored at
the pipeline guard), ``manual_adjudication`` (closed as failed by the operator,
``uncompleted_at_user_cutoff``), ``missing`` (no record stored).
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import random
import statistics

RESAMPLES = 10_000
PLANNED = 3
SEED = 20260922


def tokens(run: dict) -> int:
    def spent(s):
        return s.get("estimated_prompt_tokens", 0) + s.get("estimated_completion_tokens", 0)
    return spent(run["orchestrator"]["spent"]) + sum(spent(w["spent"]) for w in run["workers"])


def task_of(case: str) -> str:
    return case.rsplit("_", 1)[0]


def unfinished_reason(run: dict) -> str | None:
    if "orchestrator" in run:
        return None
    if run.get("timed_out"):
        return "timed_out"
    if run.get("record_origin") == "manual_adjudication":
        return "manual_adjudication"
    return "no_trajectory"


def load(prefix: str, experiment: str) -> dict[str, dict]:
    """case -> {'success': mean over planned runs, 'tokens': median over completed runs, ...}."""
    by_case: dict[str, list[dict]] = collections.defaultdict(list)
    for path in glob.glob(f"{prefix}-{experiment}/runs/*/*/*/pipeline.json"):
        run = json.load(open(path))
        by_case[run["case"]].append(run)
    out = {}
    for case, runs in by_case.items():
        ran = [r for r in runs if "orchestrator" in r]
        out[case] = {
            "success": sum(bool(r["success"]) for r in runs) / PLANNED,
            "tokens": statistics.median(tokens(r) for r in ran) if ran else None,
            "size": case.rsplit("_", 1)[1],
            "ran": len(ran),
            "unfinished": collections.Counter(filter(None, map(unfinished_reason, runs))),
            "stored": len(runs),
        }
    return out


def interval(values: list[float], draws: int = RESAMPLES, seed: int = SEED) -> tuple[float, float]:
    """Percentile interval of the mean, resampling values independently (``--unit case``)."""
    rng = random.Random(seed)
    n = len(values)
    means = sorted(statistics.fmean(rng.choice(values) for _ in range(n)) for _ in range(draws))
    return means[int(0.025 * (draws - 1))], means[int(0.975 * (draws - 1))]


def clustered_interval(clusters: list[list[float]], draws: int = RESAMPLES,
                       seed: int = SEED) -> tuple[float, float]:
    """The same with whole clusters drawn: the mean over every value of the drawn clusters."""
    rng = random.Random(seed)
    n = len(clusters)
    means = []
    for _ in range(draws):
        drawn = [rng.choice(clusters) for _ in range(n)]
        means.append(sum(map(sum, drawn)) / sum(map(len, drawn)))
    means.sort()
    return means[int(0.025 * (draws - 1))], means[int(0.975 * (draws - 1))]


def bootstrap(per_case: dict[str, float], unit: str) -> tuple[float, float]:
    cases = sorted(per_case)
    if unit == "case":
        return interval([per_case[c] for c in cases])
    by_task = collections.defaultdict(list)
    for c in cases:
        by_task[task_of(c)].append(per_case[c])
    return clustered_interval([by_task[t] for t in sorted(by_task)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("prefix", help="experiment path up to the arm, e.g. experiments/x3-orch-deepseek")
    parser.add_argument("arms", nargs="+", metavar="ARM=SUFFIX", help="the first must be cave=...")
    parser.add_argument("--unit", choices=("task", "case"), default="task",
                        help="bootstrap resampling unit (default: task; case = case-level)")
    parser.add_argument("--json", help="also write the results here")
    args = parser.parse_args()
    arms = dict(a.split("=") for a in args.arms)
    data = {arm: load(args.prefix, exp) for arm, exp in arms.items()}
    # A case with no stored run in some arm was never completed there: it is a failure
    # in that arm, not a case to drop.
    cases = sorted(set.union(*(set(d) for d in data.values())))
    absent = {"success": 0.0, "tokens": None, "size": None, "ran": 0,
              "unfinished": collections.Counter(), "stored": 0}
    for d in data.values():
        for c in cases:
            d.setdefault(c, dict(absent, size=c.rsplit("_", 1)[1], unfinished=collections.Counter()))
    tasks = sorted({task_of(c) for c in cases})
    base = data["cave"]
    result = {"prefix": args.prefix, "arms": arms, "unit": args.unit, "resamples": RESAMPLES,
              "seed": SEED, "cases": len(cases), "tasks": len(tasks), "planned_per_arm": PLANNED * len(cases),
              "rows": {}}
    print(f"{len(cases)} cases ({len(tasks)} tasks) paired across {list(arms)}; "
          f"bootstrap over {args.unit}s, {RESAMPLES:,} resamples")
    print(f"{'arm':6} {'success':>8} {'Δ vs cave [95% CI]':>26} {'tok med':>8} {'tok@500':>8} {'ratio [95% CI]':>22}")
    for arm, d in data.items():
        succ = statistics.fmean(d[c]["success"] for c in cases)
        tok = statistics.median(d[c]["tokens"] for c in cases if d[c]["tokens"] is not None)
        tok500 = statistics.median(d[c]["tokens"] for c in cases if d[c]["size"] == "500" and d[c]["tokens"] is not None)
        unfinished = collections.Counter()
        for c in cases:
            unfinished.update(d[c]["unfinished"])
            unfinished["missing"] += PLANNED - d[c]["stored"]
        row = {
            "success": succ, "tokens_median": tok, "tokens_median_500": tok500,
            "token_runs": sum(d[c]["ran"] for c in cases),
            "token_runs_500": sum(d[c]["ran"] for c in cases if d[c]["size"] == "500"),
            "token_cases": sum(d[c]["tokens"] is not None for c in cases),
            "unfinished": {k: v for k, v in sorted(unfinished.items()) if v},
            "unfinished_cases": {
                c: {k: v for k, v in dict(d[c]["unfinished"], missing=PLANNED - d[c]["stored"]).items() if v}
                for c in cases if d[c]["ran"] < PLANNED},
        }
        result["rows"][arm] = row
        if arm == "cave":
            print(f"{arm:6} {succ:8.3f} {'—':>26} {tok/1000:7.0f}k {tok500/1000:7.0f}k {'—':>22}")
            continue
        diffs = {c: d[c]["success"] - base[c]["success"] for c in cases}
        lo, hi = bootstrap(diffs, args.unit)
        paired = [c for c in cases if d[c]["tokens"] is not None and base[c]["tokens"] is not None]
        ratios = {c: d[c]["tokens"] / base[c]["tokens"] for c in paired}
        rlo, rhi = bootstrap(ratios, args.unit)
        row.update(difference=statistics.fmean(diffs.values()), difference_ci95=[lo, hi],
                   ratio=statistics.fmean(ratios.values()), ratio_ci95=[rlo, rhi], ratio_cases=len(paired))
        print(f"{arm:6} {succ:8.3f} {row['difference']:+7.3f} [{lo:+.3f}, {hi:+.3f}]     "
              f"{tok/1000:7.0f}k {tok500/1000:7.0f}k {row['ratio']:5.2f}× [{rlo:.2f}, {rhi:.2f}]")
    print(f"\nRuns behind the token figures (of {PLANNED * len(cases)} planned; "
          f"{PLANNED * sum(c.endswith('_500') for c in cases)} at 500 rows), and unfinished runs:")
    for arm, row in result["rows"].items():
        why = ", ".join(f"{k} {v}" for k, v in row["unfinished"].items()) or "none"
        print(f"{arm:6} tokens over {row['token_runs']} runs ({row['token_runs_500']} at 500 rows, "
              f"{row['token_cases']} cases); unfinished: {why}")
        for c, reasons in row["unfinished_cases"].items():
            print(f"{'':8}{c}: " + ", ".join(f"{k} {v}" for k, v in reasons.items()))
    if args.json:
        # Several studies accumulate in one file, keyed by study and unit.
        try:
            with open(args.json) as f:
                stored = json.load(f)
        except FileNotFoundError:
            stored = {}
        stored[f"{os.path.basename(args.prefix)} unit={args.unit}"] = result
        with open(args.json, "w") as f:
            json.dump(stored, f, indent=1)
            f.write("\n")


if __name__ == "__main__":
    main()
