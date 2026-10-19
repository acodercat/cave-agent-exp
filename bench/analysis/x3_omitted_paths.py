"""Q5 pipeline: runs in which the orchestrator left a downstream worker without its file path.

    uv run python analysis/x3_omitted_paths.py [--json OUT] <prefix> ARM=SUFFIX...
    uv run python analysis/x3_omitted_paths.py experiments/x3-orch-qwen file=file-v7 cave=cave-v6

Arguments are as for ``scripts/drivers/x3_paired.py``. §4.5 (4) reports that in
106 of the 216 Qwen3-Coder file-arm runs "the orchestrator omitted the file path
from at least one downstream instruction" and that these runs succeeded at
0.066. That count is the union of two ways a downstream worker (narrower or
analyst) can go without a path, which this script separates:

* ``no_path_in_instruction`` — some run of a downstream worker was given an
  instruction with no ``.parquet`` path in it. A worker run's instruction is the
  first user message after a system message in the worker's transcript (each
  run of a worker starts with its system prompt, so a worker run twice has two).
* ``worker_never_run`` — not the above, but a downstream worker was never run
  (the record's ``skipped`` names it), so no instruction carried its path.

Counting rule: every stored run that has a trajectory (an orchestrator record)
is counted once, in the first of these that applies, and its success is the
record's. Runs without a trajectory (timed out, adjudicated) have no transcript
and are reported apart. The path test only means something for an arm whose
workers exchange files; for the other arms only ``worker_never_run`` is
reported, as the same statistic for a medium in which no path is needed.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

DOWNSTREAM = ("narrower", "analyst")
FILE_ARMS = ("file",)


def instructions(transcript: Path) -> list[str]:
    """The instruction each run of a worker started with."""
    messages = [json.loads(line) for line in transcript.read_text().splitlines() if line.strip()]
    out = []
    for i, message in enumerate(messages):
        if message.get("role") == "system":
            user = next((m for m in messages[i + 1:] if m.get("role") == "user"), None)
            content = "" if user is None else user.get("content")
            out.append(content if isinstance(content, str) else json.dumps(content))
    return out


def classify(path: str, record: dict, files: bool) -> str:
    if files:
        for worker in record["workers"]:
            if worker["name"] in DOWNSTREAM and worker.get("runs"):
                transcript = Path(path).parent / worker["transcript"]
                if any(".parquet" not in text for text in instructions(transcript)):
                    return "no_path_in_instruction"
    if any(name in DOWNSTREAM for name in record.get("skipped", [])):
        return "worker_never_run"
    return "path_given" if files else "every_worker_run"


def study(prefix: str, arm: str, suffix: str) -> dict:
    groups: dict[str, list[bool]] = {}
    without_trajectory = 0
    for path in sorted(glob.glob(f"{prefix}-{suffix}/runs/*/*/*/pipeline.json")):
        record = json.load(open(path))
        if "orchestrator" not in record:
            without_trajectory += 1
            continue
        groups.setdefault(classify(path, record, arm in FILE_ARMS), []).append(bool(record["success"]))
    rate = lambda runs: sum(runs) / len(runs) if runs else None
    out = {
        "experiment": f"{os.path.basename(prefix)}-{suffix}",
        "runs": sum(map(len, groups.values())),
        "runs_without_trajectory": without_trajectory,
        "groups": {k: {"runs": len(v), "successes": sum(v), "success_rate": rate(v)}
                   for k, v in sorted(groups.items())},
    }
    if arm in FILE_ARMS:
        omitted = groups.get("no_path_in_instruction", []) + groups.get("worker_never_run", [])
        out["path_omitted"] = {"runs": len(omitted), "successes": sum(omitted), "success_rate": rate(omitted)}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("prefix")
    parser.add_argument("arms", nargs="+", metavar="ARM=SUFFIX")
    parser.add_argument("--json", help="write the results here (merged into an existing file, keyed by study)")
    args = parser.parse_args()
    results = {}
    for arm, suffix in (a.split("=") for a in args.arms):
        r = results[arm] = study(args.prefix, arm, suffix)
        print(f"{r['experiment']}: {r['runs']} runs with a trajectory"
              + (f" ({r['runs_without_trajectory']} without)" if r["runs_without_trajectory"] else ""))
        for name, g in r["groups"].items():
            print(f"  {name:24} {g['runs']:4} runs, {g['successes']:3} successes, success {g['success_rate']:.3f}")
        if "path_omitted" in r:
            g = r["path_omitted"]
            print(f"  {'path omitted (both)':24} {g['runs']:4} runs, {g['successes']:3} successes, "
                  f"success {g['success_rate']:.3f}" if g["runs"] else f"  {'path omitted (both)':24}    0 runs")
    if args.json:
        try:
            with open(args.json) as f:
                stored = json.load(f)
        except FileNotFoundError:
            stored = {}
        stored[os.path.basename(args.prefix)] = results
        with open(args.json, "w") as f:
            json.dump(stored, f, indent=1)
            f.write("\n")


if __name__ == "__main__":
    main()
