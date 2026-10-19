"""Efficiency proxies for Q4 and Q5: LLM calls, tokens per successful run, wall-clock.

    uv run python analysis/efficiency.py [--json OUT] [--md OUT] <experiment dir>...

Each argument is one study directory, read from wherever the results were
extracted; the kind of study is read from its name, as in run_accounting.py.
Per study (one model x arm, and for Q4 one case set), over the runs stored:

* Q4 (``x1-<set>-<model>-<arm>``, ``runs/<case>/<model>/<id>/run.json``):
  LLM calls ``spent.model_calls``; wall-clock ``cost.elapsed`` (seconds, the
  run's turns including any protocol repair); tokens are the estimated prompt +
  completion over every call (``spent.estimated_*``), the cost compare_paradigms
  reports, since a provider's own count is not comparable across actions.
* Q5 chain (``x5-rounds-*``, ``pipeline.json``): LLM calls are the
  orchestrator's ``spent.model_calls`` plus every worker's; wall-clock
  ``elapsed_s`` (the orchestrator's whole run, workers inside it); tokens the
  record's ``tokens`` (the shared budget's estimated prompt + completion).
* Q5 pipeline (``x3-orch-*``, ``pipeline.json``): LLM calls as for the chain,
  tokens as x3_paired.py computes them (estimated, orchestrator + workers). The
  record has no duration field, so no wall-clock is reported for this study.

For each: n records with a trajectory, mean and median of calls, tokens and
seconds per run, and tokens per successful run (all tokens of the recorded
runs over the number that succeeded). A Q5 record without a trajectory (timed
out, or closed by manual adjudication) has no spend and is counted apart. The
success column is the paper's rate, over the planned runs (3 per case; a
missing or unscored run fails): Q4 by paper_rates.py's rule (every turn passed;
the paper's set-``a`` rates instead average turns), Q5 the record's
``success``. As a check against the tables, ``case_median_tokens`` is
Table 14's *Tokens* (median over cases of each case's median run).

Wall-clock is a weak proxy and carries no claim. Confounds: DeepSeek-V4 Flash and
Qwen3.8 Flash share one gateway, so latency follows its load at the time, while
Qwen3-Coder 30B was served locally (``base_url`` in each record), so seconds are
not comparable across models; retries inside a model call (litellm's, or
the client's on a gateway error) are part of the elapsed time without adding a
counted call, while a Q4 attempt abandoned to an outage is not part of the run
at all; studies may have overlapped with one another (nothing records it);
every arm's time includes
executing its code in the kernel, and the file arms' reading and writing files;
and arms of one model were run at different times, not interleaved, so they met
the gateway at different loads.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, ".")
REPEATS = 3
# The protocol's cases, as run_accounting.py counts them: not the ones stored.
Q4_SETS = {"a": ("evals",), "b1": ("cases", "table_delivery"), "b1t": ("cases", "table_control")}
X5_DEPTHS = {"file_shared": (8,)}       # the chain study ran this arm at depth 8 only


def planned_cases(name: str) -> list[str]:
    if name.startswith("x1-"):
        prefix = Q4_SETS[name.split("-")[1]]
        cases = json.loads(Path("benchmarks.json").read_text())["cases"]
        return sorted(c for c, path in cases.items() if tuple(Path(path).parts[:len(prefix)]) == prefix)
    if name.startswith("x3-"):
        from cases.pipeline import PIPELINE_CASES
        return sorted(c.name for c in PIPELINE_CASES)
    from cases.rounds import ROUNDS_CASES
    depths = X5_DEPTHS.get(name.split("-")[-2])
    return sorted(c.name for c in ROUNDS_CASES if depths is None or c.depth in depths)


def q4_passed(run_path: Path) -> bool:
    """Every turn scored and passed (paper_rates.py, run_accounting.py)."""
    verdict = run_path.with_name("programmatic_verification.json")
    if not verdict.exists():
        return False
    for conversation in json.loads(verdict.read_text())["conversations"]:
        for turn in conversation["turns"]:
            if turn.get("status") != "scored":
                return False
            v = turn.get("protocol_repair_verification") or turn["programmatic_verification"]
            if not v.get("success"):
                return False
    return True


def q4_runs(directory: Path) -> list[dict]:
    rows = []
    for case in sorted((directory / "runs").iterdir()):
        for path in sorted(case.glob("*/*/run.json")):
            record = json.loads(path.read_text())
            spent = record["spent"]
            rows.append({"case": case.name, "success": q4_passed(path),
                         "calls": spent["model_calls"], "seconds": record["cost"]["elapsed"],
                         "tokens": spent["estimated_prompt_tokens"] + spent["estimated_completion_tokens"]})
    return rows


def estimated(spent: dict) -> int:
    return spent.get("estimated_prompt_tokens", 0) + spent.get("estimated_completion_tokens", 0)


def q5_runs(directory: Path, chain: bool) -> tuple[list[dict], int, int]:
    rows, untracked, succeeded = [], 0, 0
    for case in sorted((directory / "runs").iterdir()):
        for record in [json.loads(p.read_text()) for p in sorted(case.glob("*/*/pipeline.json"))]:
            succeeded += bool(record.get("success"))
            if "orchestrator" not in record:         # timed out or adjudicated: no spend recorded
                untracked += 1
                continue
            agents = [record["orchestrator"]["spent"]] + [w["spent"] for w in record["workers"]]
            rows.append({"case": case.name, "success": bool(record["success"]),
                         "calls": sum(s.get("model_calls", 0) for s in agents),
                         "tokens": record["tokens"] if chain else sum(estimated(s) for s in agents),
                         "seconds": record["elapsed_s"] if chain else None})
    return rows, untracked, succeeded


def summary(name: str, rows: list[dict], planned: int, succeeded: int, untracked: int = 0) -> dict:
    def stats(key):
        values = [r[key] for r in rows if r[key] is not None]
        return ({"mean": statistics.fmean(values), "median": statistics.median(values)}
                if values else None)
    by_case = defaultdict(list)
    for r in rows:
        by_case[r["case"]].append(r["tokens"])
    solved = sum(r["success"] for r in rows)
    return {"study": name, "records": len(rows), "without_trajectory": untracked,
            "planned": planned, "success_rate_planned": succeeded / planned,
            "calls": stats("calls"), "tokens": stats("tokens"), "seconds": stats("seconds"),
            "tokens_per_successful_run": sum(r["tokens"] for r in rows) / solved if solved else None,
            "case_median_tokens": statistics.median(statistics.median(v) for v in by_case.values())}


def study(directory: Path) -> dict:
    name = directory.name
    if not re.match(r"x[135]-", name):
        raise SystemExit(f"{name}: not a Q4 (x1-) or Q5 (x3-, x5-) study")
    planned = REPEATS * len(planned_cases(name))
    if name.startswith("x1-"):
        rows = q4_runs(directory)
        return summary(name, rows, planned, sum(r["success"] for r in rows))
    rows, untracked, succeeded = q5_runs(directory, chain=name.startswith("x5-"))
    return summary(name, rows, planned, succeeded, untracked)


def markdown(results: list[dict]) -> str:
    cell = lambda s, f: "—" if s is None else f"{s['mean']:{f}} / {s['median']:{f}}"
    lines = ["| study | n | no traj. | success | calls mean/med | est. tokens mean/med | tokens/success | case-median tokens | s/run mean/med |",
             "|---|---:|---:|---:|---|---|---:|---:|---|"]
    for r in results:
        lines.append(f"| {r['study']} | {r['records']} | {r['without_trajectory']} | {r['success_rate_planned']:.3f} "
                     f"| {cell(r['calls'], '.1f')} | {cell(r['tokens'], ',.0f')} "
                     f"| {'—' if r['tokens_per_successful_run'] is None else format(r['tokens_per_successful_run'], ',.0f')} | {r['case_median_tokens'] / 1000:,.0f}k"
                     f" | {cell(r['seconds'], '.0f')} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("experiments", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--md", type=Path)
    options = parser.parse_args()
    results = [study(d) for d in options.experiments]
    print(markdown(results), end="")
    if options.json:
        options.json.write_text(json.dumps(results, indent=2) + "\n")
    if options.md:
        options.md.write_text(markdown(results))


if __name__ == "__main__":
    main()
