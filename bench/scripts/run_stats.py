"""Aggregate programmatic verification and runtime cost across a study."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
import hashlib
import json
import random
import statistics
from pathlib import Path
from typing import Any, Iterable

from config import BENCHMARKS_JSON
from core.evaluator import load_specs
from core.results import (
    AGGREGATES_DIR, RUNS_DIR, atomic_write_json, iter_result_files, load_result,
    programmatic_verification, resolve_experiment, result_identity,
    result_is_complete, utc_now,
)


RUN_STATS_SCHEMA = "finbench-run-stats-v3"
BOOTSTRAP_DRAWS = 2000


def _mean(values: Iterable[float]) -> float | None:
    values = list(values)
    return statistics.fmean(values) if values else None


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _stable_seed(label: str) -> int:
    return int(hashlib.sha256(label.encode()).hexdigest()[:16], 16)


def _metric_summary(records: list[dict[str, Any]], field: str, *, label: str) -> dict:
    """Average repeats inside model×arm×case, then bootstrap those case units."""
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    trajectories = 0
    for record in records:
        value = record.get(field)
        if isinstance(value, bool):
            value = float(value)
        if not isinstance(value, (int, float)):
            continue
        trajectories += 1
        grouped[(record["model"], record["arm"], record["case"])].append(float(value))
    unit_values = [statistics.fmean(values) for values in grouped.values()]
    if not unit_values:
        interval = None
    elif len(unit_values) == 1:
        interval = [unit_values[0], unit_values[0]]
    else:
        # Cluster bootstrap: sample case units and then repeats within each unit.
        rng = random.Random(_stable_seed(label))
        clusters = list(grouped.values())
        draws = []
        for _ in range(BOOTSTRAP_DRAWS):
            selected = [rng.choice(clusters) for _ in clusters]
            draws.append(statistics.fmean(
                statistics.fmean(rng.choice(cluster) for _ in cluster)
                for cluster in selected
            ))
        interval = [_percentile(draws, 0.025), _percentile(draws, 0.975)]
    return {
        "n_trajectories": trajectories,
        "n_case_units": len(unit_values),
        "mean": _mean(unit_values),
        "ci95_hierarchical_bootstrap": interval,
        "bootstrap_draws": BOOTSTRAP_DRAWS if len(unit_values) > 1 else 0,
    }


def _runtime_summary(records: list[dict]) -> dict:
    runtime = [record.get("runtime", {}) for record in records]
    def numbers(key: str) -> list[float]:
        return [float(item[key]) for item in runtime if isinstance(item.get(key), (int, float))]
    failures = Counter(str(item["pv_failure_type"]) for item in records if item.get("pv_failure_type"))
    priced_costs = numbers("estimated_cost_usd")
    return {
        "trajectories": len(records),
        "total_steps": int(sum(numbers("steps"))), "mean_steps": _mean(numbers("steps")),
        "prompt_tokens": int(sum(numbers("prompt_tokens"))),
        "completion_tokens": int(sum(numbers("completion_tokens"))),
        "total_tokens": int(sum(numbers("total_tokens"))),
        "mean_total_tokens": _mean(numbers("total_tokens")),
        "elapsed_seconds": sum(numbers("elapsed")),
        "mean_elapsed_seconds": _mean(numbers("elapsed")),
        "estimated_agent_cost_usd": sum(priced_costs) if priced_costs else None,
        "priced_trajectories": len(priced_costs),
        "unpriced_trajectories": len(records) - len(priced_costs),
        "failure_types": dict(sorted(failures.items())),
        "protocol_repair_attempted": sum(bool(item.get("protocol_repair_attempted")) for item in runtime),
        "protocol_repair_successes": sum(bool(item.get("protocol_repair_success")) for item in runtime),
    }


def _rollup(records: list[dict], label: str) -> dict:
    result = {
        "trajectories": len(records),
        "case_units": len({(r["model"], r["arm"], r["case"]) for r in records}),
        "programmatic_verification": _metric_summary(records, "pv_numeric", label=f"{label}:pv"),
        "variable_accuracy": _metric_summary(records, "pv_variable_accuracy", label=f"{label}:variable"),
        "runtime": _runtime_summary(records),
    }
    result["pv_pass_rate"] = result["programmatic_verification"]["mean"]
    return result


def _paired_differences(records: list[dict]) -> list[dict]:
    output = []
    fields = {"pv_pass_rate": "pv_numeric", "variable_accuracy": "pv_variable_accuracy"}
    for arm in sorted({r["arm"] for r in records}):
        arm_records = [r for r in records if r["arm"] == arm]
        for model_a, model_b in combinations(sorted({r["model"] for r in arm_records}), 2):
            comparison = {"arm": arm, "model_a": model_a, "model_b": model_b,
                          "direction": "model_b_minus_model_a", "metrics": {}}
            for label, field in fields.items():
                values: dict[tuple[str, str], list[float]] = defaultdict(list)
                for record in arm_records:
                    value = record.get(field)
                    if record["model"] in {model_a, model_b} and isinstance(value, (bool, int, float)):
                        values[(record["model"], record["case"])].append(float(value))
                common = sorted(
                    {case for model, case in values if model == model_a}
                    & {case for model, case in values if model == model_b}
                )
                diffs = [statistics.fmean(values[(model_b, case)]) - statistics.fmean(values[(model_a, case)]) for case in common]
                if len(diffs) > 1:
                    rng = random.Random(_stable_seed(f"paired:{arm}:{model_a}:{model_b}:{field}"))
                    draws = [statistics.fmean(rng.choice(diffs) for _ in diffs) for _ in range(BOOTSTRAP_DRAWS)]
                    interval = [_percentile(draws, .025), _percentile(draws, .975)]
                else:
                    interval = [diffs[0], diffs[0]] if diffs else None
                comparison["metrics"][label] = {"common_cases": len(common), "mean_difference": _mean(diffs), "ci95_case_bootstrap": interval}
            output.append(comparison)
    return output


def _group_rollups(records: list[dict], key: str, label: str) -> dict:
    values: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        memberships = record.get(key)
        if not isinstance(memberships, list):
            memberships = [memberships or "unclassified"]
        for membership in memberships:
            values[str(membership)].append(record)
    return {value: _rollup(group, f"{label}:{value}") for value, group in sorted(values.items())}


def build_report(experiment: Path) -> dict[str, Any]:
    specs = {spec["name"]: spec for spec in load_specs(BENCHMARKS_JSON)}
    models_seen: dict[str, dict] = {}
    records, missing_pv, invalid_results = [], [], []

    for case_name, result_path in iter_result_files(experiment):
        _, model_id, run_id = result_identity(result_path)
        identity_base = {"case": case_name, "model": model_id, "run_id": run_id}
        try:
            saved = load_result(result_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            invalid_results.append({**identity_base, "error": str(error)})
            continue
        if not result_is_complete(saved):
            invalid_results.append({**identity_base, "error": "incomplete_result"})
            continue
        if isinstance(saved.get("model"), dict):
            models_seen.setdefault(model_id, saved["model"])
        model_metadata = saved.get("model", {})
        input_price = model_metadata.get("input_cost_per_million_usd")
        output_price = model_metadata.get("output_cost_per_million_usd")
        snapshot = specs.get(case_name, {"name": case_name})
        arm = str(saved.get("run", {}).get("arm") or "unclassified")
        # One record per scored turn: a multi-turn case is several units of
        # measurement, and pooling them would weight a long conversation more
        # heavily than a short one at the same case.
        _, pv_payload = programmatic_verification(result_path)
        pv_turns = {
            (c["id"], t["turn"]): t
            for c in (pv_payload.get("conversations", []) if isinstance(pv_payload, dict) else [])
            for t in c.get("turns", [])
        }
        for conversation in saved["conversations"]:
            for position, result in enumerate(conversation["turns"]):
                identity = {**identity_base, "conversation": conversation["id"],
                            "turn": position + 1}
                pv_turn = pv_turns.get((conversation["id"], position + 1), {})
                pv_verdict = pv_turn.get("programmatic_verification", {})
                pv_success = pv_verdict.get("success")
                if pv_success is None:
                    missing_pv.append(identity)
                variable = pv_verdict.get("variable_verification", {})
                agent_cost = (
                    float(result.get("prompt_tokens", 0) or 0) * input_price / 1_000_000
                    + float(result.get("completion_tokens", 0) or 0) * output_price / 1_000_000
                    if input_price is not None and output_price is not None else None
                )
                records.append({
                    **identity, "arm": arm, "task_family": snapshot.get("task_family", "unclassified"),
                    "source_mode": snapshot.get("source_mode", "unclassified"),
                    "financial_domains": snapshot.get("financial_domains", ["unclassified"]),
                    "result_file": str(result_path.relative_to(experiment)),
                    "pv_passed": pv_success, "pv_numeric": float(pv_success) if pv_success is not None else None,
                    "pv_failure_type": pv_verdict.get("failure_type"),
                    "pv_variable_accuracy": variable.get("accuracy"), "pv_variable_verification": variable or None,
                    "tables_unreferenced": result.get("tables_unreferenced") or [],
                    "runtime": {key: result.get(key) for key in ("steps", "prompt_tokens", "completion_tokens", "total_tokens", "elapsed")} | {
                        "estimated_cost_usd": agent_cost,
                        "protocol_repair_attempted": bool(isinstance(result.get("protocol_repair"), dict) and result["protocol_repair"].get("attempted")),
                        "protocol_repair_success": bool(pv_turn.get("protocol_repair_verification", {}).get("success")),
                    },
                })

    infrastructure_errors = []
    for path in sorted((experiment / RUNS_DIR).glob("*/*/*/error.json")):
        try:
            payload = json.loads(path.read_text())
            infrastructure_errors.append({"case": path.parents[2].name, "model": path.parents[1].name,
                                          "run_id": path.parent.name, "error_type": payload.get("error_type"), "error": payload.get("error")})
        except (OSError, json.JSONDecodeError) as error:
            infrastructure_errors.append({"path": str(path), "error": str(error)})
    overall = _rollup(records, "overall")
    return {
        "schema": RUN_STATS_SCHEMA, "generated_at": utc_now(), "experiment": experiment.name,
        "models": models_seen,
        "statistical_policy": {
            "unit": "model x arm x case after averaging repeat invocations",
            "confidence_interval": "95% deterministic hierarchical bootstrap over case units and repeats",
            "bootstrap_draws": BOOTSTRAP_DRAWS,
        },
        "overall": overall,
        "programmatic_verification": {
            "completed_trajectories": len(records),
            "scored": overall["programmatic_verification"]["n_trajectories"],
            "passed": sum(r.get("pv_passed") is True for r in records),
            "failed": sum(r.get("pv_passed") is False for r in records),
            "pass_rate": overall["programmatic_verification"]["mean"],
            "ci95_hierarchical_bootstrap": overall["programmatic_verification"]["ci95_hierarchical_bootstrap"],
            "variable_accuracy": overall["variable_accuracy"],
        },
        "runtime": overall["runtime"],
        "by_model": _group_rollups(records, "model", "model"), "by_arm": _group_rollups(records, "arm", "arm"),
        "by_task_family": _group_rollups(records, "task_family", "task"),
        "by_source_mode": _group_rollups(records, "source_mode", "source"),
        "by_financial_domain": _group_rollups(records, "financial_domains", "domain"),
        "paired_model_differences": _paired_differences(records),
        "missing": {"programmatic_verification": missing_pv,
                    "invalid_results": invalid_results, "infrastructure_errors": infrastructure_errors},
        "case_scores": records,
    }


def write_reports(experiment: Path) -> dict[str, Any]:
    report = build_report(experiment)
    atomic_write_json(experiment / AGGREGATES_DIR / "run_stats.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True)
    args = parser.parse_args()
    print(json.dumps(write_reports(resolve_experiment(args.experiment)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
