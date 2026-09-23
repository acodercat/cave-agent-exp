"""The paradigm comparison, on data small enough to check by hand."""

import json

import pytest

import scripts.compare_paradigms as comparison
from core.results import atomic_write_json, result_path, verification_path
from scripts.compare_paradigms import (
    ALL_STRATA, CaseTask, Run, Study, Turn, cell_accuracy, compare, load_study,
    paired_difference, table_losses, task_means,
)


TASKS = {
    "t1_10": CaseTask("t1", "10"), "t1_100": CaseTask("t1", "100"),
    "t2_10": CaseTask("t2", "10"), "t2_100": CaseTask("t2", "100"),
    "t3_10": CaseTask("t3", "10"), "t3_100": CaseTask("t3", "100"),
}


def turns(paradigm, outcomes, **fields):
    """Turns from {case: [success of each run]}."""
    return [
        Turn(paradigm, case, f"run{index}", success, success, **fields)
        for case, successes in outcomes.items()
        for index, success in enumerate(successes)
    ]


def study(paradigm, outcomes, *, spent=None, settings=None, model=None):
    runs = [
        Run(paradigm, case, f"run{index}", spent or {}, {})
        for case, successes in outcomes.items() for index in range(len(successes))
    ]
    return Study(
        paradigm, turns=turns(paradigm, outcomes), runs=runs,
        model=model or {"model_id": "m", "thinking": "disabled"},
        settings=settings or {"total_step_budget": 14},
    )


# -- averaging and pairing ---------------------------------------------------------

def test_runs_average_within_a_case_and_cases_within_a_task():
    observations = [("t1_10", "a", 1.0), ("t1_10", "b", 0.0), ("t1_100", "a", 1.0)]
    assert task_means(observations, TASKS) == {"t1": {"t1_10": 0.5, "t1_100": 1.0}}


def test_the_difference_is_the_mean_over_tasks_of_the_task_differences():
    reference = {"t1": {"c": 0.5}, "t2": {"c": 1.0}, "t3": {"c": 0.0}}
    other = {"t1": {"c": 1.0}, "t2": {"c": 1.0}, "t3": {"c": 0.5}}
    report = paired_difference(reference, other, label="x", margin=0.1)
    assert report["tasks"] == 3
    assert report["mean_difference"] == pytest.approx((0.5 + 0.0 + 0.5) / 3)
    low, high = report["ci95"]
    assert 0.0 <= low <= report["mean_difference"] <= high <= 0.5


def test_a_task_is_paired_on_the_cases_both_paradigms_have():
    reference = {"t1": {"t1_10": 1.0, "t1_100": 0.0}}
    other = {"t1": {"t1_10": 1.0}}
    assert paired_difference(reference, other, label="x", margin=0.1)["mean_difference"] == 0.0


def test_identical_paradigms_are_equivalent_and_do_not_differ():
    same = {task: {"c": value} for task, value in (("t1", 1.0), ("t2", 0.0), ("t3", 0.5))}
    report = paired_difference(same, same, label="x", margin=0.1)
    assert report["ci90"] == report["ci95"] == [0.0, 0.0]
    assert report["equivalent_within_margin"] and not report["differs_from_zero"]


def test_a_consistent_gap_beyond_the_margin_differs_and_is_not_equivalent():
    reference = {f"t{i}": {"c": 0.2} for i in range(10)}
    other = {f"t{i}": {"c": 0.6} for i in range(10)}
    report = paired_difference(reference, other, label="x", margin=0.1)
    assert report["differs_from_zero"] and not report["equivalent_within_margin"]


def test_a_cost_is_compared_as_a_ratio_without_equivalence():
    reference = {"t1": {"c": 100.0}, "t2": {"c": 300.0}}
    other = {"t1": {"c": 200.0}, "t2": {"c": 600.0}}
    report = paired_difference(reference, other, label="x", ratio=True)
    assert report["ratio"] == pytest.approx(2.0)
    assert report["ratio_ci95"] == pytest.approx([2.0, 2.0])
    assert "equivalent_within_margin" not in report


def test_the_bootstrap_is_reproducible():
    reference = {"t1": {"c": 0.0}, "t2": {"c": 1.0}, "t3": {"c": 0.5}}
    other = {"t1": {"c": 1.0}, "t2": {"c": 1.0}, "t3": {"c": 0.0}}
    first = paired_difference(reference, other, label="same label", margin=0.1)
    assert paired_difference(reference, other, label="same label", margin=0.1) == first


# -- cell accuracy -----------------------------------------------------------------

def table(**counts):
    base = {
        "rows_expected": 10, "rows_delivered": 10, "rows_matched": 10, "rows_missing": 0,
        "cell_errors": {"share": 0, "name": 0},
        "columns_absent": {"id": 0, "share": 0, "name": 0},
    }
    return base | counts


def test_a_perfect_table_is_fully_accurate_and_an_undelivered_one_scores_nothing():
    assert cell_accuracy(table()) == 1.0
    assert cell_accuracy(None) == 0.0 and cell_accuracy({}) == 0.0


def test_a_wrong_cell_costs_its_share_of_the_cells():
    assert cell_accuracy(table(cell_errors={"share": 1, "name": 0})) == pytest.approx(19 / 20)


def test_missing_and_extra_rows_both_cost_their_cells():
    missing = table(rows_delivered=8, rows_matched=8, rows_missing=2)
    extra = table(rows_delivered=12, rows_matched=10)
    assert cell_accuracy(missing) == pytest.approx(16 / 20)
    assert cell_accuracy(extra) == pytest.approx(20 / 24)


def test_a_repeated_row_cannot_stand_in_for_a_missing_one():
    swapped = table(rows_delivered=10, rows_matched=10, rows_missing=1)
    assert cell_accuracy(swapped) == pytest.approx(18 / 20)


def test_a_column_left_out_costs_its_cells_and_a_key_column_is_not_counted():
    left_out = table(columns_absent={"id": 0, "share": 10, "name": 0})
    assert cell_accuracy(left_out) == pytest.approx(10 / 20)


def test_cell_accuracy_is_compared_with_its_own_narrower_margin():
    reference = {f"t{i}": {"c": 1.0} for i in range(10)}
    other = {f"t{i}": {"c": 0.97} for i in range(10)}
    narrow = paired_difference(reference, other, label="x", margin=0.02)
    wide = paired_difference(reference, other, label="x", margin=0.10)
    assert not narrow["equivalent_within_margin"] and wide["equivalent_within_margin"]


# -- a whole comparison ------------------------------------------------------------

def test_each_size_is_compared_on_its_own_and_all_together():
    reference = study("cave", {case: [True, True] for case in TASKS})
    other = study("codeblock", {
        "t1_10": [True, True], "t1_100": [False, False],
        "t2_10": [True, True], "t2_100": [False, True],
        "t3_10": [True, True], "t3_100": [False, False],
    })
    report = compare({"cave": reference, "codeblock": other}, TASKS, reference="cave")
    by_stratum = report["comparisons"]["codeblock"]
    assert list(by_stratum) == [ALL_STRATA, "10", "100"]
    assert by_stratum["10"]["success"]["mean_difference"] == 0.0
    assert by_stratum["100"]["success"]["mean_difference"] == pytest.approx(-(1 + 0.5 + 1) / 3)
    # Each task's two sizes averaged first: (-0.5, -0.25, -0.5).
    assert by_stratum[ALL_STRATA]["success"]["mean_difference"] == pytest.approx(-1.25 / 3)


def test_a_failed_run_counts_only_in_the_missing_as_failure_outcome():
    reference = study("cave", {"t1_10": [True], "t2_10": [True], "t3_10": [True]})
    other = study("codeblock", {"t1_10": [True], "t2_10": [True], "t3_10": [True]})
    other.turns.append(Turn("codeblock", "t1_10", "run9", False, False, missing=True))
    tasks = {case: TASKS[case] for case in ("t1_10", "t2_10", "t3_10")}
    report = compare({"cave": reference, "codeblock": other}, tasks, reference="cave")
    overall = report["comparisons"]["codeblock"][ALL_STRATA]
    assert overall["success"]["mean_difference"] == 0.0
    assert overall["success_missing_as_failure"]["mean_difference"] == pytest.approx(-0.5 / 3)


def test_costs_come_from_the_estimate_every_paradigm_shares():
    spent = {"model_calls": 3, "estimated_prompt_tokens": 90, "estimated_completion_tokens": 10}
    reference = study("cave", {"t1_10": [True], "t2_10": [True]}, spent=spent)
    other = study("codeblock", {"t1_10": [True], "t2_10": [True]},
                  spent={**spent, "estimated_completion_tokens": 30})
    tasks = {case: TASKS[case] for case in ("t1_10", "t2_10")}
    report = compare({"cave": reference, "codeblock": other}, tasks, reference="cave")
    overall = report["comparisons"]["codeblock"][ALL_STRATA]
    assert overall["estimated_tokens"]["ratio"] == pytest.approx(120 / 100)
    assert overall["estimated_completion_tokens"]["ratio"] == pytest.approx(3.0)
    assert overall["model_calls"]["ratio"] == 1.0


@pytest.mark.parametrize("difference", [
    {"settings": {"total_step_budget": 20}},
    {"model": {"model_id": "m", "thinking": "enabled"}},
])
def test_studies_that_ran_under_different_configurations_are_not_compared(difference):
    reference = study("cave", {"t1_10": [True]})
    other = study("codeblock", {"t1_10": [True]}, **difference)
    with pytest.raises(ValueError, match="differ"):
        compare({"cave": reference, "codeblock": other}, TASKS, reference="cave")


def test_cell_errors_are_rates_over_the_cells_compared_by_kind():
    tasks = {"t1_10": CaseTask("t1", "10", {"share": "decimal", "name": "text"})}
    table = {
        "rows_expected": 10, "rows_matched": 8, "rows_missing": 2, "rows_unexpected": 1,
        "rows_repeated": 0, "cell_errors": {"share": 2, "name": 0},
    }
    turn = Turn("codeblock", "t1_10", "run0", False, False, tables={"t": table})
    losses = table_losses([turn], tasks)["10"]
    assert losses["row_miss_rate"] == 0.2
    assert losses["cell_error_rate"] == pytest.approx(2 / 16)
    assert losses["cell_error_rate_by_kind"] == {"decimal": 0.25, "text": 0.0}


# -- reading a study from disk -----------------------------------------------------

SPEC = {"name": "t1_10", "module": "cases.table_delivery.flood_claim_payments_10",
        "task_family": "table_delivery", "conversations": [
            {"id": "main", "turns": [{"query": "q", "validator": "validate", "stores": ["t"]}]},
        ]}
SPECS = {"t1_10": SPEC}
CASE_TASKS = {"t1_10": CaseTask("t1", "10", {"value": "decimal"})}


@pytest.fixture(autouse=True)
def answer_key(monkeypatch):
    """The current answer key, as the fingerprint a verdict must carry to be read."""
    monkeypatch.setattr(comparison, "_answer_key", lambda module: "current")


def _write_run(experiment, run_id, *, first, repaired=None, paradigm="codeblock",
               fingerprint="current", thinking="disabled"):
    path = result_path(experiment, "t1_10", "model", run_id)
    atomic_write_json(path, {
        "schema": "finbench-run-v4", "case": "t1_10",
        "model": {"model_id": "model", "thinking": thinking},
        "run": {"run_id": run_id, "paradigm": paradigm, "total_step_budget": 14,
                "max_protocol_nudges": 1, "max_exec_output": 100000, "injection": "lazy",
                "failed_attempts": [{"attempt": 1, "spent": {"model_calls": 2}}]},
        "spent": {"model_calls": 5, "estimated_prompt_tokens": 500,
                  "estimated_completion_tokens": 50},
        "conversations": [{"id": "main", "loop_events": {"usage_estimated": 5}, "turns": [
            {"turn": 1, "query": "q", "stores": ["t"], "response": "r", "outputs": {"t": None},
             "stop_cause": "output_truncated"},
        ]}],
    })
    verdict = {"status": "scored", "programmatic_verification": {"success": first}}
    if repaired is not None:
        verdict["protocol_repair_verification"] = {"success": repaired}
    atomic_write_json(verification_path(path), {
        "validator": {"fingerprint": fingerprint},
        "conversations": [{"id": "main", "turns": [{"turn": 1, **verdict}]}],
    })
    return path


def _write_failure(experiment, run_id):
    path = result_path(experiment, "t1_10", "model", run_id).with_name("error.json")
    atomic_write_json(path, {"failed_attempts": [{"attempt": 1}, {"attempt": 2}]})


def test_a_table_turn_carries_its_cell_accuracy_and_a_missing_run_scores_zero(tmp_path):
    path = _write_run(tmp_path, "run1", first=False)
    verdict = verification_path(path)
    payload = json.loads(verdict.read_text())
    first_pass = payload["conversations"][0]["turns"][0]["programmatic_verification"]
    first_pass["variable_verification"] = {
        "items": {"t": {"table": table(rows_delivered=8, rows_matched=8, rows_missing=2)}},
    }
    atomic_write_json(verdict, payload)
    loaded = load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=2)
    assert sorted(turn.cell_accuracy for turn in loaded.turns) == [0.0, pytest.approx(0.8)]


def test_a_study_is_read_with_its_repairs_spend_and_failures(tmp_path):
    _write_run(tmp_path, "run1", first=False, repaired=True)
    _write_run(tmp_path, "run2", first=False)
    _write_failure(tmp_path, "run3")

    loaded = load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=3)
    scored = [turn for turn in loaded.turns if not turn.missing]
    assert [(t.success, t.strict_success) for t in scored] == [(True, False), (False, False)]
    assert all(t.stop_cause == "output_truncated" for t in scored)
    assert loaded.missing_runs == 1 and len(loaded.failed_runs) == 1
    assert len(loaded.failed_attempts) == 4
    assert loaded.runs[0].spent["estimated_prompt_tokens"] == 500
    assert loaded.runs[0].loop_events == {"usage_estimated": 5}


def test_a_failed_run_that_was_run_again_is_not_missing(tmp_path):
    _write_failure(tmp_path, "run1")
    _write_run(tmp_path, "run2", first=True)
    loaded = load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=1)
    assert loaded.missing_runs == 0 and not [t for t in loaded.turns if t.missing]
    assert len(loaded.failed_runs) == 1


def test_a_case_never_run_is_short_of_every_repeat(tmp_path):
    (tmp_path / "runs").mkdir()
    loaded = load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=3)
    assert loaded.missing_runs == 3 and len(loaded.turns) == 3


def test_more_runs_than_the_protocol_allows_are_refused(tmp_path):
    _write_run(tmp_path, "run1", first=True)
    _write_run(tmp_path, "run2", first=True)
    with pytest.raises(ValueError, match="2 scored runs, the protocol 1"):
        load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=1)


def test_a_verdict_reached_against_another_answer_key_is_refused(tmp_path):
    _write_run(tmp_path, "run1", first=True, fingerprint="older")
    with pytest.raises(ValueError, match="score the study again"):
        load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=1)


def test_a_run_without_a_verdict_is_refused(tmp_path):
    verification_path(_write_run(tmp_path, "run1", first=True)).unlink()
    with pytest.raises(ValueError, match="score the study before"):
        load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=1)


def test_a_run_of_another_paradigm_in_a_study_is_refused(tmp_path):
    _write_run(tmp_path, "run1", first=True, paradigm="cave")
    with pytest.raises(ValueError, match="a run of 'cave'"):
        load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=1)


def test_runs_under_different_model_settings_in_one_study_are_refused(tmp_path):
    _write_run(tmp_path, "run1", first=True)
    _write_run(tmp_path, "run2", first=True, thinking="enabled")
    with pytest.raises(ValueError, match="differ from the study"):
        load_study("codeblock", tmp_path, SPECS, CASE_TASKS, repeats=2)


# -- staleness -----------------------------------------------------------------------

REVISION_SPEC = {"name": "r_unstated", "module": "cases.state_revision.r_unstated",
                 "task_family": "state_revision", "conversations": [{"id": "main", "turns": [
                     {"query": "q1", "validator": "validate_first", "stores": ["a"]},
                     {"query": "q2", "validator": "validate_second", "stores": ["b", "c"]},
                 ]}]}


def _write_revision_run(experiment, run_id, *, first, second, stale, named=("t",)):
    path = result_path(experiment, "r_unstated", "model", run_id)
    atomic_write_json(path, {
        "schema": "finbench-run-v4", "case": "r_unstated",
        "model": {"model_id": "model", "thinking": "disabled"},
        "run": {"run_id": run_id, "paradigm": "codeblock"},
        "conversations": [{"id": "main", "turns": [
            {"turn": 1, "query": "q1", "stores": ["a"], "response": "r", "outputs": {"a": 1}},
            {"turn": 2, "query": "q2", "stores": ["b", "c"], "response": "r",
             "outputs": {"b": 1, "c": 1}, "tables_referenced": list(named)},
        ]}],
    })
    items = {name: {"stale": True} if stale else {} for name in ("b", "c")}
    atomic_write_json(verification_path(path), {
        "validator": {"fingerprint": "current"},
        "conversations": [{"id": "main", "turns": [
            {"turn": 1, "status": "scored", "programmatic_verification": {"success": first}},
            {"turn": 2, "status": "scored", "programmatic_verification": {
                "success": second, "variable_verification": {"items": items}}},
        ]}],
    })


@pytest.mark.parametrize(("first", "stale", "expected"), [
    (True, True, True), (True, False, False), (False, True, None),
])
def test_a_second_turn_is_stale_only_after_a_first_turn_that_passed(
    tmp_path, first, stale, expected,
):
    _write_revision_run(tmp_path, "run1", first=first, second=False, stale=stale)
    tasks = {"r_unstated": CaseTask("r", "unstated", measures_staleness=True)}
    loaded = load_study("codeblock", tmp_path, {"r_unstated": REVISION_SPEC}, tasks, repeats=1)
    assert [turn.stale for turn in loaded.turns] == [None, expected]


def test_a_negative_control_measures_no_staleness(tmp_path):
    _write_revision_run(tmp_path, "run1", first=True, second=True, stale=False)
    tasks = {"r_unstated": CaseTask("r", "unstated")}
    loaded = load_study("codeblock", tmp_path, {"r_unstated": REVISION_SPEC}, tasks, repeats=1)
    assert [turn.stale for turn in loaded.turns] == [None, None]


def test_staleness_is_compared_without_a_margin_or_missing_runs_as_failures():
    tasks = {f"t{i}_unstated": CaseTask(f"t{i}", "unstated", measures_staleness=True)
             for i in range(3)}

    def revision_study(paradigm, stale):
        return Study(paradigm, turns=[
            Turn(paradigm, case, "run0", True, True, stale=value)
            for case, value in zip(tasks, stale)
        ], model={"model_id": "m"}, settings={})
    report = compare({
        "cave": revision_study("cave", [False, False, True]),
        "codeblock": revision_study("codeblock", [True, True, True]),
    }, tasks, reference="cave")
    pairwise = report["comparisons"]["codeblock"][ALL_STRATA]
    assert pairwise["stale"]["mean_difference"] == pytest.approx(2 / 3)
    assert "margin" not in pairwise["stale"] and "stale_missing_as_failure" not in pairwise


def test_a_warning_is_contrasted_with_silence_within_each_paradigm():
    tasks = {
        f"t{i}_{condition}": CaseTask(f"t{i}", condition, measures_staleness=True)
        for i in range(3) for condition in ("announced", "unstated")
    }
    stale = {"announced": False, "unstated": True}
    turns = [Turn("cave", case, "run0", True, True, stale=stale[task.stratum])
             for case, task in tasks.items()]
    report = compare(
        {"cave": Study("cave", turns=turns, model={"model_id": "m"}, settings={})},
        tasks, reference="cave", baseline_stratum="unstated",
    )
    assert report["paradigms"]["cave"]["outcomes"]["unstated"]["stale"]["mean"] == 1.0
    assert report["paradigms"]["cave"]["outcomes"][ALL_STRATA]["stale"]["mean"] == 0.5
    contrast = report["contrasts"]["cave"]
    assert set(contrast) == {"announced"}
    assert contrast["announced"]["stale"]["mean_difference"] == -1.0
    assert contrast["announced"]["stale"]["tasks"] == 3


def test_a_delivery_set_is_contrasted_with_its_smallest_size():
    """What growing the table costs a paradigm, paired by task within that paradigm."""
    assert comparison.BASELINE_STRATA["table_delivery"] == "10"
    assert comparison.BASELINE_STRATA["table_control"] == "10"
    # Every task right at 10 rows, two of the three still right at 100.
    report = compare(
        {"cave": study("cave", {
            "t1_10": [True], "t1_100": [True],
            "t2_10": [True], "t2_100": [True],
            "t3_10": [True], "t3_100": [False],
        })},
        TASKS, reference="cave", baseline_stratum="10",
    )
    contrast = report["contrasts"]["cave"]
    assert set(contrast) == {"100"}
    assert contrast["100"]["success"]["mean_difference"] == pytest.approx(-1 / 3)
    assert contrast["100"]["success"]["tasks"] == 3


def test_a_second_turn_records_whether_it_named_the_data_again(tmp_path):
    _write_revision_run(tmp_path, "run1", first=True, second=False, stale=True, named=("t",))
    tasks = {"r_unstated": CaseTask("r", "unstated", measures_staleness=True)}
    loaded = load_study("codeblock", tmp_path, {"r_unstated": REVISION_SPEC}, tasks, repeats=1)
    second = loaded.turns[1]
    assert second.source_reread and second.stale


def test_going_back_to_the_data_and_still_answering_from_before_is_its_own_outcome(tmp_path):
    """Stale after a reread is the copy-based failure; without a reread it is not defined."""
    _write_revision_run(tmp_path, "run1", first=True, second=False, stale=True, named=())
    tasks = {"r_unstated": CaseTask("r", "unstated", measures_staleness=True)}
    loaded = load_study("codeblock", tmp_path, {"r_unstated": REVISION_SPEC}, tasks, repeats=1)
    second = loaded.turns[1]
    assert second.stale and not second.source_reread
    assert comparison.OUTCOMES["stale_after_reread"].value(second) is None
    assert comparison.OUTCOMES["source_reread"].value(second) == 0.0
