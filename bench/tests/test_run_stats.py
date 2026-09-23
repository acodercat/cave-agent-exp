from core.results import RESULT_SCHEMA, atomic_write_json, result_path, verification_path
from scripts import run_stats
from scripts.run_stats import _metric_summary, _runtime_summary, write_reports


SPEC = {
    "name": "case_a", "task_family": "comparison_ranking", "source_mode": "multi",
    "financial_domains": ["capital_markets"],
    "conversations": [{"id": "main", "turns": [{"query": "q", "stores": ["x"]}]}],
}


def _write_run(experiment, case, *, success, repaired=None):
    run = result_path(experiment, case, "tested", "run-1")
    turn = {
        "turn": 1, "query": "q", "stores": ["x"], "response": "answer", "outputs": {"x": 1},
        "steps": 3, "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
        "elapsed": 2.5,
    }
    verdict = {
        "turn": 1, "status": "scored",
        "programmatic_verification": {
            "success": success,
            "failure_type": None if success else "variables_not_set",
            "variable_verification": {"accuracy": 1.0 if success else 0.0},
        },
    }
    if repaired is not None:
        turn["protocol_repair"] = {"attempted": True}
        verdict["protocol_repair_verification"] = {"success": repaired}
    atomic_write_json(run, {
        "schema": RESULT_SCHEMA, "case": case,
        "model": {"name": "tested", "model_id": "tested"},
        "conversations": [{"id": "main", "turns": [turn]}],
    })
    atomic_write_json(verification_path(run), {
        "conversations": [{"id": "main", "turns": [verdict]}],
    })


def test_run_stats_reports_verification_runtime_and_groups(tmp_path, monkeypatch):
    specs = [SPEC, {**SPEC, "name": "case_b"}]
    monkeypatch.setattr(run_stats, "load_specs", lambda _: specs)
    _write_run(tmp_path, "case_a", success=True)
    _write_run(tmp_path, "case_b", success=False, repaired=True)

    report = write_reports(tmp_path)

    assert report["programmatic_verification"]["completed_trajectories"] == 2
    assert report["programmatic_verification"]["pass_rate"] == 0.5
    assert report["runtime"]["total_tokens"] == 30
    assert report["runtime"]["mean_steps"] == 3
    assert report["runtime"]["failure_types"] == {"variables_not_set": 1}
    assert report["by_task_family"]["comparison_ranking"]["pv_pass_rate"] == 0.5
    assert report["by_financial_domain"]["capital_markets"]["trajectories"] == 2
    assert (tmp_path / "aggregates" / "run_stats.json").is_file()


def test_protocol_repair_success_is_read_from_the_turn_verdict(tmp_path, monkeypatch):
    """The scorer writes the repair verdict per turn; the report must read it there."""
    monkeypatch.setattr(run_stats, "load_specs", lambda _: [SPEC])
    _write_run(tmp_path, "case_a", success=False, repaired=True)

    runtime = write_reports(tmp_path)["runtime"]

    assert runtime["protocol_repair_attempted"] == 1
    assert runtime["protocol_repair_successes"] == 1


def test_run_stats_repeat_policy_uses_case_as_statistical_unit():
    records = [
        {"model": "m", "arm": "strict", "case": "a", "metric": 0},
        {"model": "m", "arm": "strict", "case": "a", "metric": 1},
        {"model": "m", "arm": "strict", "case": "b", "metric": 1},
    ]
    summary = _metric_summary(records, "metric", label="repeat-policy-test")
    assert summary["n_trajectories"] == 3
    assert summary["n_case_units"] == 2
    assert summary["mean"] == 0.75
    assert summary["ci95_hierarchical_bootstrap"] is not None


def test_failure_taxonomy_uses_the_authoritative_verdict():
    """A stale runtime verdict must not enter the taxonomy beside the PV verdict."""
    runtime = _runtime_summary([{
        "case": "a", "model": "provider-model", "run_id": "repeat-1", "arm": "strict",
        "pv_failure_type": "wrong_value",
        "runtime": {"failure_type": "stale_trajectory_value"},
    }])
    assert runtime["failure_types"] == {"wrong_value": 1}
