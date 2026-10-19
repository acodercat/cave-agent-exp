"""Efficiency proxies for Table 9: LLM calls and wall-clock per task, per model and arm.

What a run file records per task is the model steps of each turn (`model_steps`,
one LLM call each) and the task's wall-clock (`elapsed`, seconds, from building
the arm to the benchmark's verdict, so it includes scoring). No token counts are
recorded for this benchmark, so none are reported. Per model and arm, over all
task-runs that did not error:

* model steps per task, mean and median, and per solved task (all steps of the
  run over the tasks it solved, averaged over runs), the analogue here of
  tokens per successful task;
* wall-clock per task, mean and median; and per run the sum of task times
  (task-seconds, not the run's duration: tasks ran four at a time).

An errored task (a 900 s timeout, see paired.py) has neither field and is left
out; the count is printed beside n.

Wall-clock is a weak proxy and carries no claim. Confounds: every model runs
through one shared gateway, and the four models ran in parallel with four tasks
each in flight, so a task's time includes contention for that gateway; retries
inside one call -- litellm's on a gateway error (run.py), and for Gemini the
genai provider resampling an unusable response up to `gemini.RETRIES` times --
inflate `elapsed` without adding a step; the cave arm's time
includes executing its code; and the two arms of a model ran one after the
other, not interleaved, so they met the gateway at different loads.

    uv run python efficiency.py --results <dir> [--out efficiency.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean, median

import paired
from paired import ARMS

MODELS = ("qwen3.8-flash", "deepseek-v4-flash", "deepseek-v3.2", "gemini-3.1-pro-preview")


def cell(payloads: list[dict]) -> dict:
    """One model-arm's proxies over its runs."""
    steps, seconds, per_solved, task_seconds = [], [], [], []
    errored = 0
    for payload in payloads:
        rows = [row for row in payload["tasks"] if row.get("error") is None]
        errored += len(payload["tasks"]) - len(rows)
        run_steps = [sum(turn["model_steps"] for turn in row["turns"]) for row in rows]
        steps += run_steps
        seconds += [row["elapsed"] for row in rows]
        solved = sum(paired.results.counts_as_solved(row) for row in rows)
        per_solved.append(sum(run_steps) / solved)
        task_seconds.append(sum(row["elapsed"] for row in rows))
    return {"runs": len(payloads), "task_runs": len(steps), "errored_task_runs": errored,
            "steps_per_task_mean": fmean(steps), "steps_per_task_median": median(steps),
            "steps_per_solved_task": fmean(per_solved),
            "seconds_per_task_mean": fmean(seconds), "seconds_per_task_median": median(seconds),
            "task_seconds_per_run_mean": fmean(task_seconds),
            "task_seconds_per_run_median": median(task_seconds)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=paired.RESULTS)
    parser.add_argument("--model", nargs="+", default=list(MODELS))
    parser.add_argument("--out", type=Path, help="also write the table as JSON")
    options = parser.parse_args()
    paired.RESULTS = options.results

    rows = []
    print(f"{'model':24}{'arm':5}{'n':>5}{'err':>4}{'steps/task':>13}{'steps/solved':>13}"
          f"{'s/task':>13}{'task-s/run':>16}")
    for model in options.model:
        for arm in ARMS:
            row = {"model": model, "arm": arm, **cell(paired.runs(arm, model))}
            rows.append(row)
            print(f"{model:24}{arm:5}{row['task_runs']:>5}{row['errored_task_runs']:>4}"
                  f"{row['steps_per_task_mean']:>8.2f} /{row['steps_per_task_median']:>3.0f}"
                  f"{row['steps_per_solved_task']:>13.2f}"
                  f"{row['seconds_per_task_mean']:>7.1f} /{row['seconds_per_task_median']:>4.1f}"
                  f"{row['task_seconds_per_run_mean']:>9.0f} /{row['task_seconds_per_run_median']:>5.0f}")
    if options.out:
        options.out.parent.mkdir(parents=True, exist_ok=True)
        options.out.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
