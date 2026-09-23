"""X3 for the paper: success, task-paired differences against the cave arm, and token cost.

    python scripts/drivers/x3_paired.py experiments/x3-orch-deepseek cave=cave-v6 file=file-v7 text=text-v6 json=json-v6

Each case (task × size) carries the mean of its runs; a run that never completed is a
failure, as in the results tables. The interval is a paired bootstrap over cases,
10,000 resamples, as Q4 reports its intervals. Tokens are the study's estimated
prompt + completion over every agent of a run; the per-case median is reported, and the
ratio to cave is bootstrapped the same way over per-case medians.
"""
from __future__ import annotations

import collections
import glob
import json
import random
import statistics
import sys

RESAMPLES = 10_000
PLANNED = 3


def tokens(run: dict) -> int:
    def spent(s):
        return s.get("estimated_prompt_tokens", 0) + s.get("estimated_completion_tokens", 0)
    return spent(run["orchestrator"]["spent"]) + sum(spent(w["spent"]) for w in run["workers"])


def load(prefix: str, experiment: str) -> dict[str, dict]:
    """case -> {'success': mean over planned runs, 'tokens': median over completed runs}."""
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
        }
    return out


def interval(values: list[float], draws: int = RESAMPLES, seed: int = 20260922) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(values)
    means = sorted(statistics.fmean(rng.choice(values) for _ in range(n)) for _ in range(draws))
    return means[int(0.025 * (draws - 1))], means[int(0.975 * (draws - 1))]


def main() -> None:
    prefix = sys.argv[1]
    arms = dict(a.split("=") for a in sys.argv[2:])
    data = {arm: load(prefix, exp) for arm, exp in arms.items()}
    # A case with no stored run in some arm was never completed there: it is a failure
    # in that arm, not a case to drop.
    cases = sorted(set.union(*(set(d) for d in data.values())))
    absent = {"success": 0.0, "tokens": None, "size": None}
    for d in data.values():
        for c in cases:
            d.setdefault(c, dict(absent, size=c.rsplit("_", 1)[1]))
    base = data["cave"]
    print(f"{len(cases)} cases paired across {list(arms)}")
    print(f"{'arm':6} {'success':>8} {'Δ vs cave [95% CI]':>26} {'tok med':>8} {'tok@500':>8} {'ratio [95% CI]':>22}")
    for arm, d in data.items():
        succ = statistics.fmean(d[c]["success"] for c in cases)
        tok = statistics.median(d[c]["tokens"] for c in cases if d[c]["tokens"] is not None)
        tok500 = statistics.median(d[c]["tokens"] for c in cases if d[c]["size"] == "500" and d[c]["tokens"] is not None)
        if arm == "cave":
            print(f"{arm:6} {succ:8.3f} {'—':>26} {tok/1000:7.0f}k {tok500/1000:7.0f}k {'—':>22}")
            continue
        diffs = [d[c]["success"] - base[c]["success"] for c in cases]
        lo, hi = interval(diffs)
        paired = [c for c in cases if d[c]["tokens"] is not None and base[c]["tokens"] is not None]
        ratios = [d[c]["tokens"] / base[c]["tokens"] for c in paired]
        rlo, rhi = interval(ratios)
        print(f"{arm:6} {succ:8.3f} {statistics.fmean(diffs):+7.3f} [{lo:+.3f}, {hi:+.3f}]     "
              f"{tok/1000:7.0f}k {tok500/1000:7.0f}k {statistics.fmean(ratios):5.2f}× [{rlo:.2f}, {rhi:.2f}]")


if __name__ == "__main__":
    main()
