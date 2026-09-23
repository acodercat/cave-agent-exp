"""Difference the paradigms task by task, as the paper reports differences.

The same estimator the τ² and single-turn BFCL analyses use, so one statistic is
reported throughout: the resampling unit is the task, a task's repeats are
averaged before resampling, and the interval is a 10,000-draw bootstrap seeded
from a label so a report reproduces. McNemar's exact test accompanies it over
the tasks the paradigms disagree on.

Runs are refused rather than pooled when the two arms were not called the same
way, because a difference in temperature or reasoning is not the difference under
test.

    uv run python paired.py --model qwen3.8-flash
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from math import comb
from pathlib import Path
from statistics import fmean, stdev

import numpy

from bfcl_multiturn import results

RESULTS = Path(__file__).resolve().parent / "results"
ARMS = ("cave", "fc")
DRAWS = 10_000
#: A bound this close to zero came from a resample that touched it, so the
#: interval does not exclude zero however the arithmetic rounded.
TOUCHES_ZERO = 1e-9
#: Settings that must agree between the arms for their difference to be about
#: the action format. `arm` and `run` are expected to differ.
COMPARABLE = ("model", "api_model", "base_url", "provider", "temperature", "thinking",
              "max_steps", "category")


#: A run still being written is not a run. Reporting one would mix a partial
#: sample into the average and into the per-task scores, and it happens easily:
#: results are flushed after every task, so a file exists from the first one.
SPLIT_SIZE = 200


def runs(arm: str, model: str, *, complete_only: bool = True) -> list[dict]:
    """A model's runs under one paradigm, oldest first.

    Incomplete runs are left out by default, and named on stderr rather than
    silently: a file appears as soon as its first task is scored.
    """
    found = sorted(RESULTS.glob(f"{arm}_{model.replace('/', '-')}_run*.json"))
    kept = []
    for path in found:
        payload = results.read(path)
        if complete_only and len(payload["tasks"]) < SPLIT_SIZE:
            print(f"skipping {path.name}: {len(payload['tasks'])} of {SPLIT_SIZE} tasks",
                  file=sys.stderr)
            continue
        kept.append(payload)
    return kept


def per_task(payloads: list[dict]) -> dict[str, float]:
    """One value per task, its runs averaged, as the estimator expects.

    A task a run did not produce evidence for is left out of that run's average
    rather than counted as a failure; :mod:`results` says which those are.
    """
    scores: dict[str, list[float]] = {}
    for payload in payloads:
        for task in results.scored(payload):
            scores.setdefault(task["id"], []).append(float(results.counts_as_solved(task)))
    return {task: fmean(values) for task, values in scores.items()}


def paired_difference(first: dict[str, float], second: dict[str, float], label: str) -> dict:
    """The mean paired difference and its bootstrap interval, over shared tasks."""
    shared = sorted(set(first) & set(second))
    differences = numpy.array([first[task] - second[task] for task in shared])
    generator = numpy.random.default_rng(
        int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "big"))
    draws = generator.choice(differences, size=(DRAWS, len(differences)), replace=True).mean(axis=1)
    low, high = (float(value) for value in numpy.percentile(draws, [2.5, 97.5]))
    return {"tasks": len(shared), "mean_first": fmean(first[t] for t in shared),
            "mean_second": fmean(second[t] for t in shared),
            "mean_difference": float(differences.mean()), "ci95": [low, high],
            "differs_from_zero": low > TOUCHES_ZERO or high < -TOUCHES_ZERO,
            "tasks_differing": int((differences != 0).sum()),
            "_differences": differences.tolist()}


def mcnemar(difference: dict) -> dict:
    """An exact sign test over the tasks the paradigms disagree on."""
    wins = sum(1 for value in difference["_differences"] if value > 0)
    losses = sum(1 for value in difference["_differences"] if value < 0)
    total = wins + losses
    if not total:
        return {"wins": 0, "losses": 0, "p_value": 1.0}
    tail = sum(comb(total, k) for k in range(min(wins, losses) + 1)) / 2 ** total
    return {"wins": wins, "losses": losses, "p_value": min(1.0, 2 * tail)}


def report(model: str) -> dict:
    """The difference between the arms, refusing runs that are not comparable."""
    payloads = {arm: runs(arm, model) for arm in ARMS}
    for arm, found in payloads.items():
        if not found:
            raise SystemExit(f"no {arm} runs for {model} under {RESULTS}")
    # `api_model` defaults to the label, so a file written before the field
    # existed compares equal to one that records it explicitly.
    settings = {arm: [{key: payload.get(key, payload["model"] if key == "api_model" else None)
                       for key in COMPARABLE} for payload in found]
                for arm, found in payloads.items()}
    distinct = {json.dumps(setting, sort_keys=True) for group in settings.values() for setting in group}
    if len(distinct) > 1:
        raise SystemExit("the arms were not called the same way:\n  "
                         + "\n  ".join(sorted(distinct)))

    scores = {arm: per_task(payloads[arm]) for arm in ARMS}
    difference = paired_difference(scores["cave"], scores["fc"], label=f"bfcl-mt:{model}")
    rates = {arm: [100 * results.solved(payload) / len(results.scored(payload))
                   for payload in payloads[arm]] for arm in ARMS}
    aside = {arm: [results.set_aside(payload) for payload in payloads[arm]] for arm in ARMS}
    return {"model": model, "rates": rates, "set_aside": aside,
            **{k: v for k, v in difference.items() if not k.startswith("_")},
            "mcnemar": mcnemar(difference)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True)
    summary = report(parser.parse_args().model)

    print(f"\n## {summary['model']}: {summary['tasks']} tasks, BFCL multi_turn_base")
    for arm in ARMS:
        rates = summary["rates"][arm]
        spread = f" ± {stdev(rates):.1f}" if len(rates) > 1 else ""
        aside = summary["set_aside"][arm]
        errored = sum(len(run["errored"]) for run in aside)
        unaccounted = sum(len(run["unaccounted"]) for run in aside)
        reasons = ([f"{errored} errored, left out"] if errored else []) + \
                  ([f"{unaccounted} counted as failed, record incomplete"] if unaccounted else [])
        note = f"  ({'; '.join(reasons)})" if reasons else ""
        print(f"  {arm:5} runs {[f'{r:.1f}' for r in rates]} -> {fmean(rates):.1f}{spread}{note}")
    low, high = (100 * v for v in summary["ci95"])
    test = summary["mcnemar"]
    print(f"  cave - fc: {100 * summary['mean_difference']:+.1f} pp [{low:+.1f}, {high:+.1f}]"
          f" | excludes zero: {summary['differs_from_zero']}"
          f" | sign test p={test['p_value']:.3f} on {summary['tasks_differing']} differing"
          f" ({test['wins']} cave, {test['losses']} fc)")


if __name__ == "__main__":
    main()
