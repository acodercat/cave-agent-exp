"""Compare the arms on τ² task by task, paired, with a bootstrap over tasks.

Reviewer R3's fifth comment is that several τ² improvements are small relative to
run-to-run variance, and that a combined standard deviation is not a substitute
for a task-level paired test:

    Since the same task set is evaluated under both systems, paired bootstrap
    confidence intervals or another task-level paired test would be more
    informative.

So the unit resampled here is the task, not the run: a task's repeats are
averaged first, giving one value per task per arm, and the draws resample tasks.
That is also the method ``cave-bench/scripts/compare_paradigms.py`` uses for the
self-built ablation, reproduced rather than reinvented so the two comparisons in
the paper are one statistic. Draws are seeded from what is being estimated, so a
report is reproducible from the same files.

Three arms make three contrasts, and each answers a different question:

* ``json_exec_agent - llm_agent`` — what remains of the paper's JSON gap once the
  baseline is given the same persistent runtime and the same operations. This is
  the number R3 #3 asks for.
* ``cave_agent - json_exec_agent`` — the action format alone, with the runtime and
  the injected operations held fixed. This is why the third arm exists.
* ``cave_agent - llm_agent`` — recomputed here so the three means are
  arithmetically consistent (the first two sum to this one).

    uv run python paired.py --model qwen3.8-flash

A report is refused unless the arms agree on everything but the arm: the model
and its settings, the user simulator, the step and error budgets, the seeds, and
the task set. Silently comparing across configurations would be worse than not
comparing, so the check reuses ``merge.py``'s own notion of a pinned setting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from statistics import fmean
from typing import Any

import numpy as np

from merge import TRANSPORT, load

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
DRAWS = 10_000

# A bound lands on the grid of achievable task means, so a percentile that truly
# sits at zero can come back as a few parts in 1e15 either side of it through the
# interpolation. An interval whose limit is that close to zero touches zero and
# does not exclude it; without this a boundary case reads as a finding.
TOUCHES_ZERO = 1e-9

# What every arm must agree on for a comparison to mean anything. The arm itself
# lives in agent_info["implementation"], which is expected to differ; everything
# else about how the run was set up is not. The seed is checked apart, because it
# varies by design: run.py derives it as 300 + run - 1, so runs of one arm differ
# from each other while run n of every arm must agree — which is what lets a pair
# be taken at (task, trial) rather than only at task.
PINNED = ("user_info", "environment_info", "max_steps", "max_errors")
ARMS = ("cave_agent", "json_exec_agent", "llm_agent")
CONTRASTS = (
    ("json_exec_agent", "llm_agent"),
    ("cave_agent", "json_exec_agent"),
    ("cave_agent", "llm_agent"),
)

# One model that two gateways serve under two names, listed as the (name, gateway)
# pairs that are the same deployment. A sweep that had to move gateway partway can
# then still be compared with its own runs. The list grants exactly this — the
# name and the gateway — and only for models with no reasoning mode, for which an
# explicit "thinking: disabled" and an unset thinking field request the same
# thing. Every other model that changed endpoint is still refused.
DEPLOYMENTS = {
    ("deepseek-v4-flash", "https://gateway.example/v1"): "deepseek-v4-flash",
    ("deepseek-v4-flash-0731", "https://gateway.example/v1"): "deepseek-v4-flash",
}
NO_REASONING_REQUEST = {"extra_body": {"thinking": {"type": "disabled"}}}


def canonical_deployment(llm: str, llm_args: dict) -> tuple[str, dict]:
    """Fold a listed deployment onto the model's own name, dropping what it moved.

    Anything not listed comes back untouched, so an unrecognised endpoint still
    reads as a different configuration.
    """
    name = (llm or "").rsplit("/", 1)[-1]
    canonical = DEPLOYMENTS.get((name, (llm_args or {}).get("base_url")))
    if canonical is None:
        return llm, llm_args
    settings = {key: value for key, value in llm_args.items() if key != "base_url"}
    if {"extra_body": settings.get("extra_body")} == NO_REASONING_REQUEST:
        settings.pop("extra_body")
    return canonical, settings


def runs_of(arm: str, model: str, domain: str) -> list[Path]:
    """Every result file of one arm, oldest first."""
    return sorted(RESULTS.glob(f"*_{domain}_{arm}_{model}_run*.json"))


def run_index(path: Path) -> int:
    """The run number the filename carries, which fixes the seed."""
    match = re.search(r"_run(\d+)\.json$", path.name)
    return int(match.group(1)) if match else 0


def _agent_settings(info: dict) -> dict:
    """The model the agent ran, and how it was configured, in a form the arms share.

    The arms name the same model two ways, by the harness's own design: a code
    arm passes a bare id to cave-agent's LiteLLMModel with the provider beside it
    in `custom_llm_provider`, while tau2's own agent takes "provider/model". So
    the provider is folded into the id and dropped from the arguments, leaving a
    comparison of what the model actually was. Transport-only arguments go too,
    following merge.py.
    """
    agent = info.get("agent_info") or {}
    llm_args = {k: v for k, v in (agent.get("llm_args") or {}).items() if k not in TRANSPORT}
    provider = llm_args.pop("custom_llm_provider", None)
    model = agent.get("llm") or ""
    if provider and not model.startswith(f"{provider}/"):
        model = f"{provider}/{model}"
    model, llm_args = canonical_deployment(model, llm_args)
    return {"llm": model, "llm_args": llm_args}


def _user_settings(info: dict) -> dict:
    """The user simulator, folded the same way: it too can move gateway mid-sweep."""
    user = info.get("user_info") or {}
    llm_args = {k: v for k, v in (user.get("llm_args") or {}).items() if k not in TRANSPORT}
    model, llm_args = canonical_deployment(user.get("llm") or "", llm_args)
    return user | {"llm": model, "llm_args": llm_args}


def configuration(payload: dict) -> dict:
    """The settings a comparison requires to be equal across arms."""
    info = payload["info"]
    pinned = {key: info.get(key) for key in PINNED if key != "user_info"}
    return pinned | {"user": _user_settings(info), "agent": _agent_settings(info)}


def check_comparable(files: dict[str, list[Path]]) -> None:
    """Refuse to compare arms that were not run the same way.

    Every run of every arm must share one configuration. When they do not, the
    message names one file per distinct configuration, so the odd run out is
    visible rather than merely counted.
    """
    seen: dict[str, list[str]] = defaultdict(list)
    seeds: dict[int, dict[Any, list[str]]] = defaultdict(lambda: defaultdict(list))
    for arm, paths in files.items():
        for path in paths:
            payload = load(path)
            shape = json.dumps(configuration(payload), sort_keys=True, default=str)
            seen[shape].append(f"{arm}: {path.name}")
            seeds[run_index(path)][payload["info"].get("seed")].append(f"{arm}: {path.name}")
    problems = []
    if len(seen) > 1:
        problems.append(
            "the arms were not run the same way, so a paired comparison would mix "
            "configurations:\n" + "\n".join(
                f"  configuration {n}: {group[0]}"
                + (f" (and {len(group) - 1} more)" if len(group) > 1 else "")
                for n, group in enumerate(seen.values(), start=1)
            )
            + "\n(compared: " + ", ".join(PINNED) + ", agent model and llm_args)"
        )
    for run, by_seed in sorted(seeds.items()):
        if len(by_seed) > 1:
            problems.append(
                f"run {run} used more than one seed, so its trials are not paired:\n"
                + "\n".join(f"  seed {seed}: {group[0]}" for seed, group in by_seed.items())
            )
    if problems:
        raise SystemExit("\n\n".join(problems))


def rewards(paths: list[Path]) -> dict[str, list[float]]:
    """Task id to its rewards across the runs given."""
    out: dict[str, list[float]] = defaultdict(list)
    for path in paths:
        for simulation in load(path)["simulations"]:
            reward = (simulation.get("reward_info") or {}).get("reward")
            if reward is not None:
                out[simulation["task_id"]].append(float(reward))
    return dict(out)


def per_task(paths: list[Path]) -> dict[str, float]:
    """One value per task: its repeats averaged, so the bootstrap resamples tasks."""
    return {task: fmean(values) for task, values in rewards(paths).items()}


def draws_for(size: int, label: str) -> np.ndarray:
    """Task indices for every draw, seeded by what is being estimated."""
    seed = int(hashlib.sha256(label.encode()).hexdigest()[:16], 16)
    return np.random.default_rng(seed).integers(0, size, size=(DRAWS, size))


def interval(values: np.ndarray, level: int) -> list[float]:
    tail = (100 - level) / 2
    low, high = np.percentile(values, [tail, 100 - tail])
    return [float(low), float(high)]


def paired_difference(first: dict[str, float], second: dict[str, float], *, label: str) -> dict:
    """``first - second`` over the tasks both arms answered, with bootstrap intervals."""
    tasks = sorted(first.keys() & second.keys())
    if not tasks:
        return {"tasks": 0}
    a = np.array([first[task] for task in tasks])
    b = np.array([second[task] for task in tasks])
    differences = a - b
    resampled = differences[draws_for(len(tasks), label)].mean(axis=1)
    low95, high95 = interval(resampled, 95)
    return {
        "tasks": len(tasks),
        "mean_first": float(a.mean()), "mean_second": float(b.mean()),
        "mean_difference": float(differences.mean()),
        "ci90": interval(resampled, 90), "ci95": [low95, high95],
        "differs_from_zero": low95 > TOUCHES_ZERO or high95 < -TOUCHES_ZERO,
        "tasks_differing": int((differences != 0).sum()),
        # McNemar's counts on the task means: where one arm solved and the other did not.
        "first_only": int((differences > 0).sum()), "second_only": int((differences < 0).sum()),
    }


def mcnemar(report: dict) -> dict:
    """An exact two-sided sign test on the tasks the arms disagree about."""
    wins, losses = report.get("first_only", 0), report.get("second_only", 0)
    if wins + losses == 0:
        return {"discordant": 0, "p_value": 1.0}
    from scipy.stats import binomtest

    result = binomtest(wins, wins + losses, 0.5, alternative="two-sided")
    return {"discordant": wins + losses, "p_value": float(result.pvalue)}


def secondary(paths: list[Path]) -> dict:
    """Per-task cost signals, averaged the same way the reward is.

    Tokens are reported with a caveat and never carry a claim: a fenced reply is
    read only to its first closed block, before the provider reports usage, so
    that arm's figure is cave-agent's estimate, while a tool call is read to its
    end and carries the provider's count. Wall-clock and the number of model
    calls per turn are directly comparable.
    """
    tokens: dict[str, list[float]] = defaultdict(list)
    duration: dict[str, list[float]] = defaultdict(list)
    steps: list[int] = []
    corrections = fillers = turns = 0
    sources = {"reported": 0, "estimated": 0}
    for path in paths:
        for simulation in load(path)["simulations"]:
            task = simulation["task_id"]
            duration[task].append(simulation.get("duration") or 0.0)
            used = 0
            for message in simulation["messages"]:
                usage = message.get("usage") or {}
                used += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                raw = message.get("raw_data") or {}
                if "steps" in raw:
                    steps.append(raw["steps"])
                    turns += 1
                    corrections += raw.get("format_corrections", 0)
                if raw.get("stood_in_for_an_empty_reply"):
                    fillers += 1
                # Cumulative per task, so the last turn's count is the task's.
                for source, count in (raw.get("usage_sources") or {}).items():
                    sources[source] = max(sources.get(source, 0), count)
            tokens[task].append(used)
    return {
        "tokens_per_task": fmean(fmean(v) for v in tokens.values()) if tokens else None,
        "seconds_per_task": fmean(fmean(v) for v in duration.values()) if duration else None,
        "model_calls_per_turn": fmean(steps) if steps else None,
        "turns": turns,
        "format_corrections": corrections,
        "empty_reply_fillers": fillers,
        # How the tokens above were counted. A figure resting mostly on estimates
        # is not comparable with one resting on the provider's own count, so a
        # table reporting tokens has to report this beside them.
        "usage_estimated_share": (
            sources["estimated"] / total if (total := sum(sources.values())) else None),
    }


def contrasts_among(arms: Sequence[str]) -> tuple[tuple[str, str], ...]:
    """The contrasts both of whose arms were asked for, in the order defined above.

    The third arm exists on one model so far; on the others the comparison is the
    pair the paper reports, and asking for a missing arm is an error rather than
    a silently narrower report.
    """
    chosen = set(arms)
    return tuple(pair for pair in CONTRASTS if chosen.issuperset(pair))


def build_report(model: str, domain: str, arms: Sequence[str] = ARMS) -> dict:
    files = {arm: runs_of(arm, model, domain) for arm in arms}
    missing = [arm for arm, paths in files.items() if not paths]
    if missing:
        raise SystemExit(f"no results for {', '.join(missing)} on {domain}/{model}")
    check_comparable(files)

    scores = {arm: per_task(paths) for arm, paths in files.items()}
    report = {
        "domain": domain, "model": model, "bootstrap_draws": DRAWS,
        "runs": {arm: [path.name for path in paths] for arm, paths in files.items()},
        "arms": {
            arm: {
                "tasks": len(scores[arm]),
                "mean_reward": fmean(scores[arm].values()) if scores[arm] else None,
                **secondary(files[arm]),
            }
            for arm in arms
        },
        "contrasts": {},
    }
    for first, second in contrasts_among(arms):
        difference = paired_difference(
            scores[first], scores[second], label=f"{domain}:{model}:{first}-{second}")
        report["contrasts"][f"{first} - {second}"] = difference | {"mcnemar": mcnemar(difference)}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True, help="model id as it appears in the filenames")
    parser.add_argument("--domain", default="telecom")
    parser.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS),
                        help="the arms to compare (default: all three)")
    parser.add_argument("--out", type=Path, help="write the report here as JSON")
    args = parser.parse_args()

    report = build_report(args.model, args.domain, args.arms)
    def shown(value: float | None, spec: str) -> str:
        """A figure, or a dash where an arm does not record it.

        Only the arms that run a CaveAgent loop trace their per-turn model calls;
        tau2's own agent makes exactly one per turn and records none.
        """
        return format(value, spec) if value is not None else "—"

    for arm, summary in report["arms"].items():
        print(f"{arm:16} reward {shown(summary['mean_reward'], '.3f')} "
              f"over {summary['tasks']} tasks "
              f"| {shown(summary['tokens_per_task'], ',.0f')} tokens/task "
              f"| {shown(summary['seconds_per_task'], '.0f')}s/task "
              f"| {shown(summary['model_calls_per_turn'], '.2f')} calls/turn "
              f"| {summary['format_corrections']} corrections")
    print()
    for name, contrast in report["contrasts"].items():
        low, high = contrast["ci95"]
        print(f"{name:34} {contrast['mean_difference']:+.3f} "
              f"[{low:+.3f}, {high:+.3f}] differs={contrast['differs_from_zero']} "
              f"| {contrast['tasks_differing']}/{contrast['tasks']} tasks differ "
              f"| McNemar p={contrast['mcnemar']['p_value']:.3f}")
    if args.out:
        args.out.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(f"\n{args.out}")


if __name__ == "__main__":
    main()
