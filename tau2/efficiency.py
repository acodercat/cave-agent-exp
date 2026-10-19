"""Efficiency proxies on τ²: the agent's LLM calls, its tokens, and wall-clock per task.

Per domain, model and arm, over every simulation of every run file
(`results/<ts>_<domain>_<arm>_<model>_run<N>.json`):

* LLM calls per task, mean and median. The code arms (`cave_agent`,
  `json_exec_agent`) record each agent turn's model calls as `raw_data.steps`
  on the message carrying the turn; tau2's `llm_agent` makes one call per
  assistant message, so those are counted, leaving out the fixed greeting that
  opens every conversation (no usage, no raw_data: not a model call).
* agent tokens per task (mean, median) and per successful task (a run's agent
  tokens over its tasks with reward 1, averaged over runs). Only assistant
  messages are summed: `paired.py`'s `secondary` sums `usage` over every
  message, which includes the user simulator's, so its figure is not the
  agent's and is not reused here.
* wall-clock: the simulation's `duration` per task (mean, median), and per run
  the sum of task durations (task-seconds; tasks ran concurrently, so this is
  not the run's own length).
* where the tokens come from. The code arms read cave-agent's accounting, which
  estimates a call whose provider reported no usage (a fenced reply is read
  only to its first closed block, before the usage chunk arrives). Runs written
  after the counter existed record `usage_sources` per task; the share of
  estimated calls is printed for them and "n/r" (not recorded) otherwise -- the
  Telecom `cave_agent` runs predate it, so their token figures may rest partly
  on estimates. `llm_agent` tokens are the provider's counts.

Wall-clock is a weak proxy and carries no claim. Confounds: all runs share one
gateway (agent and user simulator alike), so latency follows its load;
litellm's internal retries on gateway errors sit inside `duration` and inflate
it without adding a counted call; several tasks and several runs were in flight
at once; `duration` covers the whole conversation, including every user
simulator call and the environment's tool execution, not only the agent; the
CaveAgent arm's time includes executing its code in the runtime; and the arms
were run at different times (json_exec_agent days after the others, see the
filename timestamps), so provider-side speed may differ between them. Calls
and tokens do not share these confounds; token counts carry the caveat above.

    uv run python efficiency.py --results <dir> [--domain telecom] [--out efficiency.json]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import fmean, median

from merge import load
from paired import ARMS, RESULTS, run_index

FILENAME = re.compile(r"_(airline|retail|telecom)_(cave_agent|json_exec_agent|llm_agent)_(.+)_run(\d+)\.json$")


def calls(simulation: dict, arm: str) -> int:
    """The agent's model calls in one conversation."""
    agent = [m for m in simulation["messages"] if m["role"] == "assistant"]
    if arm == "llm_agent":
        return sum(1 for m in agent if m.get("raw_data") is not None)
    return sum((m.get("raw_data") or {}).get("steps", 0) for m in agent)


def agent_tokens(simulation: dict) -> int:
    """Prompt plus completion tokens over the agent's messages only."""
    return sum((m.get("usage") or {}).get("prompt_tokens", 0)
               + (m.get("usage") or {}).get("completion_tokens", 0)
               for m in simulation["messages"] if m["role"] == "assistant")


def sources(simulation: dict) -> dict[str, int] | None:
    """The task's count of reported and estimated calls, if the run recorded it.

    The count is cumulative within a task, so the largest is the task's.
    """
    found = None
    for message in simulation["messages"]:
        counted = (message.get("raw_data") or {}).get("usage_sources")
        if counted:
            found = {key: max((found or {}).get(key, 0), value) for key, value in counted.items()}
    return found


def cell(paths: list[Path], arm: str) -> dict:
    per_task = defaultdict(list)
    per_run = defaultdict(list)
    estimated = reported = unrecorded = 0
    for path in paths:
        run_tokens = run_solved = run_seconds = 0
        simulations = load(path)["simulations"]
        for simulation in simulations:
            solved = (simulation.get("reward_info") or {}).get("reward") == 1
            tokens = agent_tokens(simulation)
            per_task["calls"].append(calls(simulation, arm))
            per_task["tokens"].append(tokens)
            per_task["seconds"].append(simulation.get("duration") or 0.0)
            run_tokens += tokens
            run_solved += solved
            run_seconds += simulation.get("duration") or 0.0
            counted = sources(simulation)
            if counted is None:
                unrecorded += 1
            else:
                estimated += counted.get("estimated", 0)
                reported += counted.get("reported", 0)
        per_run["success"].append(100 * run_solved / len(simulations))
        per_run["tokens_per_solved"].append(run_tokens / run_solved if run_solved else None)
        per_run["task_seconds"].append(run_seconds)
    if arm == "llm_agent":
        share = "provider"
    elif unrecorded:
        share = "n/r" if not (estimated + reported) else f"partly n/r ({unrecorded} tasks)"
    else:
        share = estimated / (estimated + reported)
    return {"runs": len(paths), "task_runs": len(per_task["calls"]),
            "success_per_run": per_run["success"],
            "calls_per_task_mean": fmean(per_task["calls"]),
            "calls_per_task_median": median(per_task["calls"]),
            "agent_tokens_per_task_mean": fmean(per_task["tokens"]),
            "agent_tokens_per_task_median": median(per_task["tokens"]),
            "agent_tokens_per_solved_task": fmean(v for v in per_run["tokens_per_solved"] if v),
            "estimated_call_share": share,
            "seconds_per_task_mean": fmean(per_task["seconds"]),
            "seconds_per_task_median": median(per_task["seconds"]),
            "task_seconds_per_run_mean": fmean(per_run["task_seconds"]),
            "task_seconds_per_run_median": median(per_run["task_seconds"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--domain", nargs="+", default=["telecom", "airline", "retail"])
    parser.add_argument("--out", type=Path, help="also write the table as JSON")
    options = parser.parse_args()

    files = defaultdict(list)
    for path in sorted(options.results.glob("*.json"), key=run_index):
        match = FILENAME.search(path.name)
        if match and match.group(1) in options.domain:
            domain, arm, model, _ = match.groups()
            files[(domain, model, arm)].append(path)

    rows = []
    print(f"{'domain':8}{'model':28}{'arm':16}{'n':>4}{'success/run':>20}{'calls/task':>13}"
          f"{'tok/task':>17}{'tok/solved':>11}{'est.':>7}{'s/task':>13}{'task-s/run':>16}")
    for domain in options.domain:
        for model in sorted({m for d, m, _ in files if d == domain}):
            for arm in ARMS:
                if (domain, model, arm) not in files:
                    continue
                row = {"domain": domain, "model": model, "arm": arm,
                       **cell(files[(domain, model, arm)], arm)}
                rows.append(row)
                share = row["estimated_call_share"]
                share = f"{100 * share:.0f}%" if isinstance(share, float) else share[:5]
                print(f"{domain:8}{model:28}{arm:16}{row['task_runs']:>4}"
                      f"{' / '.join(f'{v:.1f}' for v in row['success_per_run']):>20}"
                      f"{row['calls_per_task_mean']:>8.1f} /{row['calls_per_task_median']:>3.0f}"
                      f"{row['agent_tokens_per_task_mean']:>9,.0f} /{row['agent_tokens_per_task_median']:>6,.0f}"
                      f"{row['agent_tokens_per_solved_task']:>11,.0f}{share:>7}"
                      f"{row['seconds_per_task_mean']:>7.0f} /{row['seconds_per_task_median']:>4.0f}"
                      f"{row['task_seconds_per_run_mean']:>9,.0f} /{row['task_seconds_per_run_median']:>6,.0f}")
    if options.out:
        options.out.parent.mkdir(parents=True, exist_ok=True)
        options.out.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
