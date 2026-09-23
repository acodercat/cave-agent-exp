import importlib
import re
from pathlib import Path

import pytest

from config import BENCHMARKS_JSON, CASES_DIR, EVALS_DIR
from core.evaluator import load_specs


def test_all_case_ground_truth_and_validators():
    specs = load_specs(BENCHMARKS_JSON)
    assert specs
    for spec in specs:
        module = importlib.import_module(spec["module"])
        expected = module.ground_truth()
        outputs = {variable.name: value for variable, value in zip(module.variables, expected)}
        verdict = module.validate(outputs)
        assert verdict.success, f"{spec['name']}: {verdict.message}"


def test_registry_covers_every_case_json_exactly_once():
    specs = load_specs(BENCHMARKS_JSON)
    registered = {Path(spec["_path"]).resolve() for spec in specs}
    case_json = {
        path.resolve() for root in (EVALS_DIR, CASES_DIR) for path in root.rglob("*.json")
    }
    assert registered == case_json


def test_cases_follow_the_verification_contract():
    """Every case is an admitted baseline that PV alone can score."""
    for spec in load_specs(BENCHMARKS_JSON):
        assert {"name", "module", "task_family", "data_sources", "difficulty",
                "case_type", "conversations"} <= spec.keys()
        assert "judge_reference" not in spec and "claims" not in spec
        assert spec["case_type"] == "baseline"
        assert spec["difficulty"] in {"medium", "hard"}
        assert spec["data_sources"]
        path = Path(spec["_path"])
        assert spec["module"] == f"{path.parents[1].name}.{path.parent.name}.{path.stem}"

        turns = [turn for conversation in spec["conversations"] for turn in conversation["turns"]]
        assert turns and all(turn.get("query") and turn.get("validator") for turn in turns)
        assert all("claims" not in turn for turn in turns)

        module = importlib.import_module(spec["module"])
        assert all(variable.description.startswith("Store ") for variable in module.variables)
        for turn in turns:
            for variable in module.variables:
                assert not re.search(
                    rf"(?<![A-Za-z0-9_]){re.escape(variable.name)}(?![A-Za-z0-9_])",
                    turn["query"],
                ), f"{spec['name']}: query leaks output variable {variable.name}"


def test_jpm_parent_name_accepts_both_declared_source_casings():
    module = importlib.import_module(
        "evals.comparison_ranking.jpm_standardized_advanced_cet1"
    )
    names = [variable.name for variable in module.variables]
    outputs = dict(zip(names, module.ground_truth()))
    for legal_name in ("JPMORGAN CHASE & CO.", "JPMorgan Chase & Co."):
        assert module.validate({**outputs, "parent_legal_name": legal_name}).success
    invalid = {**outputs, "parent_legal_name": "JPMORGAN CHASE BANK, N.A."}
    assert not module.validate(invalid).success


def test_jnj_point_in_time_recast_ground_truth():
    module = importlib.import_module(
        "evals.temporal_path.jnj_fy2022_revenue_point_in_time_recast"
    )
    truth = module.ground_truth()
    assert truth[:3] == (3, 3, 2)
    assert truth[3:6] == ("0000200406-23-000016", "2023-02-16T21:01:53", pytest.approx(94.943))
    assert truth[6:] == ("0000200406-24-000013", "2024-02-16T21:12:22", pytest.approx(79.990))
