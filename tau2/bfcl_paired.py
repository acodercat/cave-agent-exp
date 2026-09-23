"""Summarise a model's BFCL runs, and difference the paradigms task by task.

R1's seventh comment is that Q3 had to move to gemini-3.1-pro-preview once
gemini-3-pro-preview was retired, and asks for the new model in the earlier
experiments. BFCL is where that is cheap to answer, so this reads the runs from
``../bfcl/results`` and reports what the two tables of the paper need: the
per-run, per-category counts of the supplementary table, and the averages of
the summary table. The difference between the paradigms is estimated the way
``paired.py`` estimates it for τ², over the 1,000 questions rather than over
runs, so the paper reports one statistic throughout.

    uv run python bfcl_paired.py gemini-3.1-pro-preview gemini-3-pro-preview
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean, stdev

from paired import mcnemar, paired_difference

BFCL = Path(__file__).resolve().parent.parent / "bfcl" / "results"
ARMS = {"CaveAgent": "cave_agent", "FC": "tool_calling"}
CATEGORIES = {"simple": 400, "multiple": 200, "parallel": 200, "parallel_multiple": 200}


def run_directories(arm: str, model: str) -> list[Path]:
    return sorted((BFCL / ARMS[arm]).glob(f"{model}_run_*"))


def scored(directory: Path, category: str) -> dict[str, bool]:
    """Every question of one category in one run, and whether it was solved."""
    path = directory / f"BFCL_v3_{category}.json"
    lines = (line for line in path.read_text().splitlines() if line.strip())
    records = (json.loads(line) for line in lines)
    return {f"{category}:{record['scenario']}": record["metrics"].get("success_rate") == 1.0
            for record in records}


def arm_runs(arm: str, model: str) -> list[dict[str, bool]]:
    return [{task: ok for category in CATEGORIES for task, ok in scored(directory, category).items()}
            for directory in run_directories(arm, model)]


def per_task(runs: list[dict[str, bool]]) -> dict[str, float]:
    """One value per question, its runs averaged, as the estimator expects."""
    tasks = set().union(*runs) if runs else set()
    return {task: fmean(float(run[task]) for run in runs if task in run) for task in tasks}


def report(model: str) -> dict:
    runs = {arm: arm_runs(arm, model) for arm in ARMS}
    missing = [arm for arm, values in runs.items() if not values]
    if missing:
        raise SystemExit(f"no {', '.join(missing)} runs for {model} under {BFCL}")
    counts = {
        arm: [{category: sum(scored(directory, category).values()) for category in CATEGORIES}
              for directory in run_directories(arm, model)]
        for arm in ARMS
    }
    # over the split, as the published table counts it: a question the run never
    # scored counts against it rather than leaving the run a shorter benchmark.
    total = sum(CATEGORIES.values())
    rates = {arm: [100 * sum(run.values()) / total for run in counts[arm]] for arm in ARMS}
    short = {arm: [total - len(run) for run in runs[arm]] for arm in ARMS}
    difference = paired_difference(per_task(runs["CaveAgent"]), per_task(runs["FC"]),
                                   label=f"bfcl:{model}:CaveAgent-FC")
    return {"model": model, "counts": counts, "rates": rates, "unscored": short,
            **difference, "mcnemar": mcnemar(difference)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("models", nargs="+")
    args = parser.parse_args()

    for model in args.models:
        summary = report(model)
        print(f"\n## {model}: {summary['tasks']} questions")
        for arm in ARMS:
            rates = summary["rates"][arm]
            spread = f" ± {stdev(rates):.2f}" if len(rates) > 1 else ""
            print(f"  {arm:10} runs {[f'{rate:.1f}' for rate in rates]} -> {fmean(rates):.1f}{spread}")
            for run, counts in enumerate(summary["counts"][arm], start=1):
                cells = "  ".join(f"{category} {counts[category]}/{total}"
                                  for category, total in CATEGORIES.items())
                unscored = summary["unscored"][arm][run - 1]
                note = f"  ({unscored} question(s) never scored)" if unscored else ""
                print(f"    run {run}: {cells}  overall {sum(counts.values())}/1000{note}")
        low, high = (100 * value for value in summary["ci95"])
        print(f"  CaveAgent - FC: {100 * summary['mean_difference']:+.2f} pp "
              f"[{low:+.2f}, {high:+.2f}] | excludes zero: {summary['differs_from_zero']} "
              f"| McNemar p={summary['mcnemar']['p_value']:.3f} "
              f"on {summary['tasks_differing']} discordant questions")


if __name__ == "__main__":
    main()
