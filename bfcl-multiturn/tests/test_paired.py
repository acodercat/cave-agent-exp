"""What the estimator must do, and what it must refuse.

The arithmetic is checked on constructed runs rather than on real ones, so a
change in the estimator fails here rather than shifting a number in the paper.
"""

import json

import pytest

import paired


def write(tmp_path, arm, run, outcomes, **settings):
    """One run file: task ids mapped to valid/invalid, or None for an error."""
    base = {"arm": arm, "model": "m", "api_model": "m", "run": run, "base_url": "u",
            "provider": "openai", "temperature": 0.2, "thinking": "disabled",
            "max_steps": 10, "category": "c"}
    base.update(settings)
    tasks = [{"id": task, "valid": bool(value)} if value is not None
             else {"id": task, "valid": False, "error": "Timeout"}
             for task, value in outcomes.items()]
    scored = [t for t in tasks if "error" not in t]
    path = tmp_path / f"{arm}_m_run{run}.json"
    path.write_text(json.dumps({**base, "tasks": tasks,
                                "solved": sum(t["valid"] for t in scored), "scored": len(scored),
                                "errored": len(tasks) - len(scored)}))
    return path


@pytest.fixture(autouse=True)
def results(tmp_path, monkeypatch):
    monkeypatch.setattr(paired, "RESULTS", tmp_path)
    # These runs are a task or two, not 200, so the completeness check is told
    # what a whole one is here; the tests that exercise it set their own.
    monkeypatch.setattr(paired, "SPLIT_SIZE", 1)
    return tmp_path


class TestTheDifference:
    def test_a_clean_win_is_the_difference_in_rates(self, results):
        write(results, "cave", 1, {"a": 1, "b": 1})
        write(results, "fc", 1, {"a": 1, "b": 0})

        out = paired.report("m")

        assert out["mean_difference"] == 0.5
        assert out["tasks"] == 2
        assert out["tasks_differing"] == 1

    def test_a_task_is_averaged_over_its_runs_before_resampling(self, results):
        write(results, "cave", 1, {"a": 1})
        write(results, "cave", 2, {"a": 0})
        write(results, "fc", 1, {"a": 0})
        write(results, "fc", 2, {"a": 0})

        assert paired.report("m")["mean_difference"] == 0.5

    def test_only_tasks_both_arms_have_are_paired(self, results):
        write(results, "cave", 1, {"a": 1, "b": 1})
        write(results, "fc", 1, {"a": 0})

        assert paired.report("m")["tasks"] == 1

    def test_a_task_on_an_incomplete_record_counts_as_failed(self, results):
        """Not dropped: only one arm can produce one, so dropping favours it."""
        first = write(results, "cave", 1, {"a": 1, "b": 1})
        payload = json.loads(first.read_text())
        payload["tasks"][1]["unrecorded_change"] = {"X": ["y"]}
        first.write_text(json.dumps(payload))
        write(results, "fc", 1, {"a": 1, "b": 1})

        out = paired.report("m")

        assert out["tasks"] == 2                        # both still paired
        assert out["mean_difference"] == -0.5           # cave loses the doubtful one

    def test_an_errored_task_is_left_out_not_counted_wrong(self, results):
        """An outage is not evidence about a paradigm."""
        write(results, "cave", 1, {"a": 1, "b": None})
        write(results, "fc", 1, {"a": 1, "b": 1})

        out = paired.report("m")

        assert out["tasks"] == 1                    # b dropped, not scored 0
        assert out["mean_difference"] == 0.0

    def test_no_difference_gives_an_interval_that_includes_zero(self, results):
        write(results, "cave", 1, {"a": 1, "b": 0})
        write(results, "fc", 1, {"a": 1, "b": 0})

        out = paired.report("m")

        assert out["mean_difference"] == 0.0
        assert not out["differs_from_zero"]

    def test_the_report_reproduces(self, results):
        write(results, "cave", 1, {f"t{i}": i % 3 > 0 for i in range(40)})
        write(results, "fc", 1, {f"t{i}": i % 4 > 0 for i in range(40)})

        assert paired.report("m")["ci95"] == paired.report("m")["ci95"]


class TestWhatItRefuses:
    @pytest.mark.parametrize("difference", [
        {"temperature": 0.7}, {"thinking": "enabled"}, {"max_steps": 20},
        {"model": "other"}, {"base_url": "elsewhere"}, {"category": "other"},
    ])
    def test_arms_called_differently_are_not_pooled(self, results, difference):
        write(results, "cave", 1, {"a": 1}, **difference)
        write(results, "fc", 1, {"a": 0})

        with pytest.raises(SystemExit, match="not called the same way"):
            paired.report("m")

    def test_a_missing_arm_is_named(self, results):
        write(results, "cave", 1, {"a": 1})

        with pytest.raises(SystemExit, match="no fc runs"):
            paired.report("m")


class TestTheSignTest:
    def test_it_counts_only_the_tasks_they_disagree_on(self, results):
        write(results, "cave", 1, {"a": 1, "b": 1, "c": 1})
        write(results, "fc", 1, {"a": 1, "b": 0, "c": 0})

        test = paired.report("m")["mcnemar"]

        assert (test["wins"], test["losses"]) == (2, 0)

    def test_full_agreement_is_not_evidence(self, results):
        write(results, "cave", 1, {"a": 1})
        write(results, "fc", 1, {"a": 1})

        assert paired.report("m")["mcnemar"]["p_value"] == 1.0


class TestAnIncompleteRun:
    """A file exists from its first task, so a run being written is not a run."""

    def test_it_is_left_out(self, results, monkeypatch, capsys):
        monkeypatch.setattr(paired, "SPLIT_SIZE", 3)
        write(results, "cave", 1, {"a": 1, "b": 1, "c": 1})
        write(results, "cave", 2, {"a": 0})                 # still running
        write(results, "fc", 1, {"a": 0, "b": 0, "c": 0})

        out = paired.report("m")

        assert len(out["rates"]["cave"]) == 1                # run 2 not averaged in
        assert "skipping" in capsys.readouterr().err

    def test_a_complete_run_is_kept(self, results, monkeypatch):
        monkeypatch.setattr(paired, "SPLIT_SIZE", 3)
        write(results, "cave", 1, {"a": 1, "b": 1, "c": 1})
        write(results, "cave", 2, {"a": 1, "b": 1, "c": 0})
        write(results, "fc", 1, {"a": 0, "b": 0, "c": 0})

        assert len(paired.report("m")["rates"]["cave"]) == 2


class TestTheDeployedId:
    """A model's label and the id its endpoint serves are not always the same."""

    def test_arms_on_different_deployments_are_not_pooled(self, results):
        write(results, "cave", 1, {"a": 1}, api_model="m-0731")
        write(results, "fc", 1, {"a": 0}, api_model="m-0801")

        with pytest.raises(SystemExit, match="not called the same way"):
            paired.report("m")

    def test_a_file_predating_the_field_matches_one_that_records_the_label(self, results):
        """So old results stay poolable with new ones."""
        first = write(results, "cave", 1, {"a": 1})
        payload = json.loads(first.read_text())
        del payload["api_model"]
        first.write_text(json.dumps(payload))
        write(results, "fc", 1, {"a": 0}, api_model="m")

        assert paired.report("m")["mean_difference"] == 1.0
