"""Where every planned run of a Q4 or Q5 study went: recorded, scored, or why not.

    uv run python analysis/run_accounting.py [--json OUT] [--md OUT] <experiment dir>...

Each argument is one study directory (``x1-<set>-<model>-<arm>``,
``x3-orch-<model>-<arm>-v<k>`` or ``x5-rounds-<model>-<arm>-v<k>``), read from
wherever the results were extracted.

Planned runs are the study's cases × 3 repeats. The cases are the protocol's,
not the ones that happen to be stored:

* Q4 (``x1-<set>-*``): the entries of ``benchmarks.json`` under the set's
  directory — ``a`` = ``evals/`` (117), ``b1`` = ``cases/table_delivery/``
  (120), ``b1t`` = ``cases/table_control/`` (30).
* Q5 pipeline (``x3-orch-*``): ``cases.pipeline.PIPELINE_CASES`` (72).
* Q5 chain (``x5-rounds-*``): ``cases.rounds.ROUNDS_CASES`` (9); the
  ``file_shared`` arm at depth 8 only (3), as ``scripts/drivers/x5_arm.sh``
  runs it, and so the metadata-parity arms (``*_parity``).

Counting rule. A planned run is *recorded* when a run record holding a model
trajectory is stored for it (``run.json``; a ``pipeline.json`` with an
orchestrator). It is *scored* when it carries a verdict: for Q4 a programmatic
verification with status ``scored`` on every turn, for Q5 every recorded run
(the verdict is part of the record). Every planned run that is not scored has
exactly one of two kinds of reason, and every scored run that failed one kind:

* ``infrastructure`` — no trajectory because of the endpoint or the guard: a
  planned run with no record (the run was abandoned after its retries, leaving
  ``error.json`` files of schema ``finbench-infrastructure-error-v1`` for Q4, or
  nothing for Q5), or a Q5 record stored as ``timed_out``;
* ``harness`` — a trajectory or slot the scorer or the operator closed without
  a verdict: a Q4 turn the scorer refused (``lossy_snapshot`` and the other
  ``REFUSALS`` of ``scripts/score_programmatic_verification.py``), or a Q5
  ``manual_adjudication`` record (``uncompleted_at_user_cutoff``);
* ``agent`` — a scored run that failed. Q4: the first failed turn's
  ``stop_cause`` if the provider cut the reply (``output_truncated``), else its
  ``failure_type`` (``core.evaluator.classify_failure``: ``variables_not_set``,
  ``max_steps``, ``wrong_value``). Q5: ``token_budget_exceeded`` (chain study's
  budget), else ``orchestrator_max_steps`` when the failing stage never ran and
  the orchestrator hit its step limit, ``worker_not_run`` when it never ran
  otherwise, else the failing worker's last stop reason (``max_steps``,
  ``model_error``) or, when it completed, ``variables_not_set`` ("required
  output not set") or ``wrong_value``.

A multi-turn Q4 run (set ``a``) counts as a success here only if every turn
passed; the paper's rates for that set average turns, so they are not these
run counts divided by the planned runs.

Unscored runs count as failures in the paper's success rates; the paired Q4
differences in ``report.json`` come in both forms (see ``q4_sensitivity.py``).

Retries are counted apart from the planned runs. Q4 stores each recorded run's
abandoned first attempts in ``run.failed_attempts``, and a run abandoned after
every attempt as ``error.json``; both are reported. The Q5 runner retries an
outage but keeps no trace of it in the record, so Q5 has no retry count.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
REPEATS = 3
Q4_SETS = {"a": ("evals",), "b1": ("cases", "table_delivery"), "b1t": ("cases", "table_control")}
# The chain study ran these arms at one depth only (scripts/drivers/x5_arm.sh
# and the parity arms).
X5_DEPTHS = {"file_shared": (8,), **{f"{arm}_parity": (8,) for arm in ("cave", "file", "text", "json")}}
INFRA_SCHEMA = "finbench-infrastructure-error-v1"


def planned_cases(name: str) -> list[str]:
    if name.startswith("x1-"):
        prefix = Q4_SETS[name.split("-")[1]]
        cases = json.loads(Path("benchmarks.json").read_text())["cases"]
        return sorted(c for c, path in cases.items() if tuple(Path(path).parts[:len(prefix)]) == prefix)
    if name.startswith("x3-"):
        from cases.pipeline import PIPELINE_CASES
        return sorted(c.name for c in PIPELINE_CASES)
    if name.startswith("x5-"):
        from cases.rounds import ROUNDS_CASES
        depths = X5_DEPTHS.get(arm_of(name))
        return sorted(c.name for c in ROUNDS_CASES if depths is None or c.depth in depths)
    raise SystemExit(f"{name}: not a Q4 (x1-) or Q5 (x3-, x5-) study")


def arm_of(name: str) -> str:
    parts = name.split("-")
    return parts[-1] if name.startswith("x1-") else parts[-2]


def q4_run(run_path: Path) -> tuple[str, str]:
    """('scored', 'success' | agent cause) or ('harness', refusal) for one run.json."""
    verdict_path = run_path.with_name("programmatic_verification.json")
    if not verdict_path.exists():
        return "harness", "no_verdict"
    verdict = json.loads(verdict_path.read_text())
    record = json.loads(run_path.read_text())
    turns = [(t, r) for vc, rc in zip(verdict["conversations"], record["conversations"])
             for t, r in zip(vc["turns"], rc["turns"])]
    refused = [t["status"] for t, _ in turns if t.get("status") != "scored"]
    if refused:                                  # partially_scored: the run has no full verdict
        return "harness", refused[0]
    for turn, stored in turns:
        v = turn.get("protocol_repair_verification") or turn["programmatic_verification"]
        if not v.get("success"):
            return "scored", stored.get("stop_cause") or v["failure_type"]
    return "scored", "success"


def q5_run(record: dict) -> tuple[str, str]:
    """The same for one pipeline.json of the pipeline or chain study."""
    if record.get("timed_out"):
        return "infrastructure", f"timed_out_{record.get('timeout_s')}s"
    if record.get("record_origin") == "manual_adjudication":
        return "harness", f"manual_adjudication:{record.get('failure')}"
    if "orchestrator" not in record:
        return "harness", "record_without_trajectory"
    if record["success"]:
        return "scored", "success"
    if record.get("budget_exceeded"):
        return "scored", "token_budget_exceeded"
    worker = next((w for w in record["workers"] if w["name"] == record["failure"]), None)
    if worker is None or not worker.get("stop_reasons"):
        orchestrator_limit = "max_steps" in record["orchestrator"].get("stop_reasons", [])
        return "scored", "orchestrator_max_steps" if orchestrator_limit else "worker_not_run"
    last = worker["stop_reasons"][-1]
    if last != "completed":
        return "scored", last
    message = worker.get("message") or worker.get("answer_message") or ""
    return "scored", "variables_not_set" if "not set" in message else "wrong_value"


def account(directory: Path) -> dict:
    name = directory.name
    cases = planned_cases(name)
    planned = set(cases)
    out = {
        "study": name[:2], "arm": arm_of(name), "planned_cases": len(cases), "repeats": REPEATS,
        "planned": len(cases) * REPEATS, "recorded": 0, "scored": 0, "succeeded": 0,
        "unscored": {"infrastructure": collections.Counter(), "harness": collections.Counter()},
        "failed": {"agent": collections.Counter()},
        "unscored_cases": collections.defaultdict(collections.Counter),
        "unplanned_records": 0,
    }
    if name.startswith("x1-"):
        out.update(retried_runs=0, failed_attempts=0, abandoned_runs=0, abandoned_attempts=0)
    runs_dir = directory / "runs"
    stored_cases = {p.name for p in runs_dir.iterdir()} if runs_dir.is_dir() else set()
    out["unplanned_records"] = len(stored_cases - planned)
    for case in cases:
        outcomes = []                            # (kind, reason), one per stored record
        errors = 0
        for run_dir in sorted((runs_dir / case).glob("*/*")):
            if name.startswith("x1-"):
                if (run_dir / "run.json").exists():
                    record = json.loads((run_dir / "run.json").read_text())
                    attempts = record["run"].get("failed_attempts") or []
                    out["retried_runs"] += bool(attempts)
                    out["failed_attempts"] += len(attempts)
                    outcomes.append(q4_run(run_dir / "run.json"))
                elif (run_dir / "error.json").exists():
                    error = json.loads((run_dir / "error.json").read_text())
                    assert error["schema"] == INFRA_SCHEMA, run_dir
                    errors += 1
                    out["abandoned_runs"] += 1
                    out["abandoned_attempts"] += int(error.get("attempts", 1))
            elif (run_dir / "pipeline.json").exists():
                outcomes.append(q5_run(json.loads((run_dir / "pipeline.json").read_text())))
        if len(outcomes) > REPEATS:
            raise SystemExit(f"{name} {case}: {len(outcomes)} records stored, {REPEATS} planned")
        for _ in range(REPEATS - len(outcomes)):
            reason = "missing_record" + (" (error.json present)" if errors else "")
            outcomes.append(("infrastructure", reason))
        for kind, reason in outcomes:
            if kind == "scored":
                out["recorded"] += 1
                out["scored"] += 1
                if reason == "success":
                    out["succeeded"] += 1
                else:
                    out["failed"]["agent"][reason] += 1
                continue
            # A refused Q4 run still holds a trajectory; a Q5 timeout or adjudication does not.
            out["recorded"] += kind == "harness" and name.startswith("x1-")
            out["unscored"][kind][reason] += 1
            out["unscored_cases"][f"{kind}:{reason}"][case] += 1
    out["unscored_total"] = out["planned"] - out["scored"]
    out["success_rate_planned"] = out["succeeded"] / out["planned"]
    return json.loads(json.dumps(out))           # Counters and defaultdicts to plain dicts


def markdown(results: dict[str, dict]) -> str:
    lines = ["| study | planned | recorded | scored | success | infrastructure | harness | agent failures | retried (attempts) | abandoned (error.json) |",
             "|---|---:|---:|---:|---:|---|---|---|---|---|"]
    fmt = lambda c: ", ".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda kv: -kv[1])) or "—"
    for name, r in results.items():
        retried = f"{r['retried_runs']} ({r['failed_attempts']})" if "retried_runs" in r else "not recorded"
        abandoned = str(r["abandoned_runs"]) if "abandoned_runs" in r else "—"
        lines.append(
            f"| {name} | {r['planned']} | {r['recorded']} | {r['scored']} | {r['succeeded']} | "
            f"{fmt(r['unscored']['infrastructure'])} | {fmt(r['unscored']['harness'])} | "
            f"{fmt(r['failed']['agent'])} | {retried} | {abandoned} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("experiments", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, help="write the accounting here")
    parser.add_argument("--md", type=Path, help="write a summary table here")
    args = parser.parse_args()
    results = {d.name: account(d) for d in sorted(args.experiments, key=lambda p: p.name)}
    print(markdown(results))
    for name, r in results.items():
        for reason, cases in r["unscored_cases"].items():
            print(f"  {name} {reason}: " + ", ".join(f"{c} x{n}" for c, n in sorted(cases.items())))
    errors = sum(r.get("abandoned_runs", 0) for r in results.values())
    print(f"error.json files ({INFRA_SCHEMA}): {errors}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"repeats": REPEATS, "studies": results}, indent=1) + "\n")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(markdown(results))


if __name__ == "__main__":
    main()
