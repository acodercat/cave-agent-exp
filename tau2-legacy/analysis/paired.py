"""Table 6: the Airline and Retail results of Table 5, paired task by task.

The estimator is the one ``tau2/paired.py`` uses for the newer τ² runs, so the
paper reports one statistic throughout: a task's three runs are averaged first,
giving one value per task per paradigm; the paired difference (CaveAgent - FC)
is averaged over tasks; its 95% interval is the percentile interval of 10,000
bootstrap resamples of tasks; and an exact two-sided sign test runs on the
discordant tasks (those whose run-averaged difference is not zero). The draws
are seeded from the label ``tau2-legacy:<domain>:<model>:CaveAgent-FC`` (first
16 hex digits of its SHA-256), so a report reproduces from the same files.

Counting rule. A run succeeds on a task when ``reward == 1``. By default a task
of the split (the file's own ``tasks`` list: 50 Airline, 114 Retail) that a run
file has no simulation for counts as a failure in that run, as it does in Table
5's success rates. ``--scored-only`` instead leaves it out of that run's
average, the rule the published Table 6 was computed with; it reproduces the
published Δ, while the interval can move by a resample's worth because the
seed that table was drawn with was not recorded. Every missing task is listed.

The direction count across the twelve model-domain settings (how many of them
CaveAgent's mean exceeds FC's, with a two-sided exact binomial p) is printed
too. It is descriptive: the settings share tasks (six models on one split per
domain) and models (two domains each), so they are not independent trials and
the p value is not a test of anything beyond the count itself.

    uv run python analysis/paired.py --results <archive>/tau2-legacy/results
    uv run python analysis/paired.py --results <dir> --scored-only --out table6.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import comb
from pathlib import Path
from statistics import fmean

import numpy as np

DRAWS = 10_000
#: As in tau2/paired.py: a percentile this close to zero touches zero.
TOUCHES_ZERO = 1e-9
DOMAINS = ("airline", "retail")
ARMS = ("CaveAgent", "FC")
#: Directory name -> the row label of Tables 5 and 6, in their order.
MODELS = {
    "deepseek": "DeepSeek-V3.2",
    "qwen3-coder-30b": "Qwen3-Coder 30B",
    "kimi-k2-0905": "Kimi-K2-0905",
    "claude-sonnet-4.5": "Claude Sonnet 4.5",
    "gpt-5.1": "GPT-5.1",
    "gemini-3-pro": "Gemini 3 Pro",
}
#: Table 6 as published (Δ, 95% CI, p), in percentage points, for the check below.
PUBLISHED = {
    ("deepseek", "airline"): (4.7, (-2.0, 11.3), 0.332),
    ("deepseek", "retail"): (5.0, (0.0, 10.2), 0.117),
    ("qwen3-coder-30b", "airline"): (2.7, (-8.0, 13.3), 0.839),
    ("qwen3-coder-30b", "retail"): (13.5, (5.6, 21.1), 0.001),
    ("kimi-k2-0905", "airline"): (1.3, (-6.7, 9.3), 1.000),
    ("kimi-k2-0905", "retail"): (10.5, (3.5, 17.5), 0.004),
    ("claude-sonnet-4.5", "airline"): (-0.7, (-8.7, 7.3), 1.000),
    ("claude-sonnet-4.5", "retail"): (4.1, (-1.8, 9.6), 0.076),
    ("gpt-5.1", "airline"): (3.3, (-4.7, 11.3), 0.541),
    ("gpt-5.1", "retail"): (3.8, (-2.0, 9.6), 0.526),
    ("gemini-3-pro", "airline"): (6.7, (1.3, 12.0), 0.039),
    ("gemini-3-pro", "retail"): (5.6, (0.0, 10.8), 0.203),
}


def runs_of(results: Path, model: str, domain: str, arm: str) -> list[Path]:
    """One paradigm's run files, run 1 first."""
    return sorted((results / model / domain).glob(f"{arm}_run*.json"))


def outcomes(path: Path) -> tuple[list[str], dict[str, float]]:
    """A run's split (task ids) and its success per task it has a simulation for."""
    payload = json.loads(path.read_text())
    split = [task["id"] for task in payload["tasks"]]
    solved = {sim["task_id"]: float((sim.get("reward_info") or {}).get("reward") == 1)
              for sim in payload["simulations"]}
    return split, solved


def per_task(paths: list[Path], *, scored_only: bool) -> tuple[dict[str, float], dict, list]:
    """One value per task, its runs averaged; also each run's rate and missing tasks."""
    values: dict[str, list[float]] = {}
    rates, missing = {}, {}
    for path in paths:
        split, solved = outcomes(path)
        absent = [task for task in split if task not in solved]
        missing[path.name] = absent
        rates[path.name] = 100 * sum(solved.values()) / len(split)
        for task in split:
            if task in solved:
                values.setdefault(task, []).append(solved[task])
            elif not scored_only:
                values.setdefault(task, []).append(0.0)
    return {task: fmean(v) for task, v in values.items()}, rates, missing


def draws_for(size: int, label: str) -> np.ndarray:
    """Task indices for every draw, seeded by what is being estimated (tau2/paired.py)."""
    seed = int(hashlib.sha256(label.encode()).hexdigest()[:16], 16)
    return np.random.default_rng(seed).integers(0, size, size=(DRAWS, size))


def sign_test(wins: int, losses: int) -> float:
    """Exact two-sided binomial p at 1/2: twice the smaller tail, capped at one."""
    total = wins + losses
    if not total:
        return 1.0
    tail = sum(comb(total, k) for k in range(min(wins, losses) + 1)) / 2 ** total
    return min(1.0, 2 * tail)


def paired(first: dict[str, float], second: dict[str, float], label: str) -> dict:
    """``first - second`` over shared tasks, with its bootstrap interval and sign test."""
    tasks = sorted(first.keys() & second.keys(), key=lambda t: (len(t), t))
    differences = np.array([first[t] - second[t] for t in tasks])
    resampled = differences[draws_for(len(tasks), label)].mean(axis=1)
    low, high = (float(v) for v in np.percentile(resampled, [2.5, 97.5]))
    wins, losses = int((differences > 0).sum()), int((differences < 0).sum())
    return {"tasks": len(tasks), "label": label,
            "mean_cave": fmean(first[t] for t in tasks),
            "mean_fc": fmean(second[t] for t in tasks),
            "delta": float(differences.mean()), "ci95": [low, high],
            "differs_from_zero": low > TOUCHES_ZERO or high < -TOUCHES_ZERO,
            "wins": wins, "losses": losses, "p_value": sign_test(wins, losses)}


def setting(results: Path, model: str, domain: str, *, scored_only: bool) -> dict:
    files = {arm: runs_of(results, model, domain, arm) for arm in ARMS}
    for arm, paths in files.items():
        if not paths:
            raise SystemExit(f"no {arm} runs under {results / model / domain}")
    scores, rates, missing = {}, {}, {}
    for arm, paths in files.items():
        scores[arm], rates[arm], found = per_task(paths, scored_only=scored_only)
        missing.update({f"{model}/{domain}/{name}": tasks for name, tasks in found.items()})
    result = paired(scores["CaveAgent"], scores["FC"],
                    label=f"tau2-legacy:{domain}:{model}:CaveAgent-FC")
    # Table 5's means: every run over the whole split, whatever the rule above.
    table5 = {arm: fmean(rates[arm].values()) for arm in ARMS}
    return {"model": model, "domain": domain, **result, "run_rates": rates,
            "table5_means": table5, "missing": {k: v for k, v in missing.items() if v}}


def direction(settings: list[dict]) -> dict:
    """How many settings favour CaveAgent on Table 5's means; descriptive only."""
    up = [s for s in settings if s["table5_means"]["CaveAgent"] > s["table5_means"]["FC"]]
    down = [f"{MODELS[s['model']]} {s['domain']} "
            f"{s['table5_means']['CaveAgent'] - s['table5_means']['FC']:+.1f}"
            for s in settings if s not in up]
    return {"cave_higher": len(up), "settings": len(settings), "not_higher": down,
            "binomial_p_two_sided": sign_test(len(up), len(settings) - len(up))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, required=True,
                        help="the tau2-legacy results directory (<model>/<domain>/<arm>_runN.json)")
    parser.add_argument("--scored-only", action="store_true",
                        help="leave a task a run file lacks out of that run, as published Table 6 did")
    parser.add_argument("--out", type=Path, help="write the report here as JSON")
    options = parser.parse_args()

    settings = [setting(options.results, model, domain, scored_only=options.scored_only)
                for model in MODELS for domain in DOMAINS]
    rule = "missing = scored only" if options.scored_only else "missing = failure"
    print(f"## Table 6 ({rule}); {DRAWS:,} task resamples\n")
    print(f"{'model':18} {'domain':7} {'n':>3} {'Δ':>6} {'95% CI':>16} {'p':>6} {'W/L':>6}"
          f" | published Δ [CI] p")
    for s in settings:
        low, high = (100 * v for v in s["ci95"])
        delta, (plow, phigh), pp = PUBLISHED[(s["model"], s["domain"])]
        mark = "*" if s["differs_from_zero"] else " "
        print(f"{MODELS[s['model']]:18} {s['domain']:7} {s['tasks']:>3} {100 * s['delta']:+6.2f}"
              f" [{low:+6.2f}, {high:+6.2f}]{mark}{s['p_value']:6.3f} {s['wins']:>2}/{s['losses']:<3}"
              f" | {delta:+.1f} [{plow:+.1f}, {phigh:+.1f}] {pp:.3f}")
    count = direction(settings)
    print(f"\nCaveAgent mean higher in {count['cave_higher']} of {count['settings']} settings"
          f" (not: {', '.join(count['not_higher']) or 'none'}); two-sided exact binomial"
          f" p={count['binomial_p_two_sided']:.5f} (descriptive: settings share tasks and models)")
    missing = {name: tasks for s in settings for name, tasks in s["missing"].items()}
    print("\ntasks missing from a run file:")
    for name, tasks in missing.items():
        print(f"  {name}: {', '.join(tasks)}")
    if not missing:
        print("  none")
    if options.out:
        options.out.parent.mkdir(parents=True, exist_ok=True)
        options.out.write_text(json.dumps(
            {"rule": rule, "draws": DRAWS, "settings": settings, "direction": count,
             "missing": missing}, indent=2) + "\n")


if __name__ == "__main__":
    main()
