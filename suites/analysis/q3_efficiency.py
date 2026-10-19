"""Q3 efficiency proxies: LLM calls, tokens per completed turn, and wall-clock.

Same runs and selection as q3_final.py (cave and bash from q3v2, json from q3v3,
repeats r1-r3). The unit is the turn (48 per run, 24 conversations). Per
(model, paradigm) cell:

* steps: the turn's `metrics.steps`, the number of LLM calls the agent made;
  mean and median per turn, and the per-run total averaged over runs (Table 11's
  Steps column);
* tokens per completed turn: total tokens over successful turns, summed over a
  run and averaged over runs as in q3_final.py (Table 11's Tok./turn);
* wall-clock: the turn's `metrics.elapsed` in seconds; mean and median per turn,
  and the per-run sum, mean and median over the three runs.

An errored turn (see q3_intervals.py) is recorded with 0 steps, 0 tokens and 0 s
and is kept, as in the tables; it lowers the per-turn means slightly.

Wall-clock is a weak proxy and carries no claim. Confounds: all runs share one
gateway, so latency depends on its load at the time; litellm's internal retries
(`litellm.num_retries = 3` in scripts/_common.py) on rate limits or dropped
connections are inside `elapsed`, inflating it without an extra counted step;
a run executes its scenarios one after another, but runs of different cells
may have overlapped (nothing records it), so a turn's time can include waiting
for capacity other runs were using; CaveAgent's and bash's time includes executing code
(and bash a fresh process per call), JSON FC's only tool dispatch; and the arms
ran at different times (json in q3v3, later than q3v2), so provider-side speed
may differ between them. Steps and tokens do not have these confounds.

    cd suites && python analysis/q3_efficiency.py [--root <experiments/token_efficiency>] [--out f.json]
"""
import argparse, json, re, statistics
from collections import defaultdict
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--root", type=Path, default=Path("experiments/token_efficiency"))
parser.add_argument("--out", type=Path, help="also write the table as JSON")
options = parser.parse_args()

STUDY = {"cave": "q3v2", "bash": "q3v2", "json": "q3v3"}
ORDER = ["deepseek-v3.2", "deepseek-v4-flash", "gemini-3.1-pro", "qwen3-coder-30b"]
# (model, arm) -> run -> list of turn metrics
cells = defaultdict(lambda: defaultdict(list))
for directory in sorted(options.root.glob("q3v[23]-*")):
    m = re.fullmatch(r"(q3v[23])-(.+)-r([1-3])_(cave|json|bash)", directory.name)
    if not m or STUDY[m.group(4)] != m.group(1):
        continue
    _, model, run, arm = m.groups()
    for result in sorted(directory.glob("*.json")):
        for scenario in json.loads(result.read_text())["results"].values():
            for conversation in scenario["conversations"]:
                for turn in conversation["turns"]:
                    k = turn["metrics"]
                    cells[(model, arm)][run].append(dict(
                        steps=k["steps"], tokens=k["total_tokens"], elapsed=k.get("elapsed", 0.0),
                        passed=bool(turn["success"]), errored=bool(turn.get("error"))))

rows = []
print(f"{'model':<20}{'arm':<6}{'n':>2}{'turns':>6}{'steps/turn':>12}{'steps/run':>10}"
      f"{'tok/compl.turn':>15}{'s/turn mean':>12}{'med':>6}{'s/run mean':>11}{'med':>7}")
for model in ORDER:
    for arm in ("cave", "json", "bash"):
        runs = cells.get((model, arm))
        if not runs:
            continue
        turns = [t for run in runs.values() for t in run]
        per_run = {key: [sum(t[key] for t in run) for run in runs.values()]
                   for key in ("steps", "tokens", "elapsed", "passed")}
        row = dict(
            model=model, arm=arm, runs=len(runs), turns_per_run=len(turns) / len(runs),
            errored_turns=sum(t["errored"] for t in turns),
            steps_per_turn_mean=statistics.fmean(t["steps"] for t in turns),
            steps_per_turn_median=statistics.median(t["steps"] for t in turns),
            steps_per_run_mean=statistics.fmean(per_run["steps"]),
            tokens_per_completed_turn=statistics.fmean(per_run["tokens"]) / statistics.fmean(per_run["passed"]),
            seconds_per_turn_mean=statistics.fmean(t["elapsed"] for t in turns),
            seconds_per_turn_median=statistics.median(t["elapsed"] for t in turns),
            seconds_per_run_mean=statistics.fmean(per_run["elapsed"]),
            seconds_per_run_median=statistics.median(per_run["elapsed"]),
            seconds_per_run=per_run["elapsed"])
        rows.append(row)
        print(f"{model:<20}{arm:<6}{row['runs']:>2}{row['turns_per_run']:>6.0f}"
              f"{row['steps_per_turn_mean']:>7.2f} /{row['steps_per_turn_median']:>3.0f}"
              f"{row['steps_per_run_mean']:>10.0f}{row['tokens_per_completed_turn']:>15,.0f}"
              f"{row['seconds_per_turn_mean']:>12.1f}{row['seconds_per_turn_median']:>6.1f}"
              f"{row['seconds_per_run_mean']:>11.0f}{row['seconds_per_run_median']:>7.0f}")
if options.out:
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(rows, indent=2) + "\n")
