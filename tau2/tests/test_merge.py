"""Tests for folding re-run tasks back into a sweep."""

import json

import pytest

from merge import disagreements, load, merge
from missing import missing_tasks
from run import number_simulations


def result(simulations, **info) -> dict:
    """A results file with the given simulations, in tau2's shape."""
    task_ids = {s["task_id"] for s in simulations}
    return {
        "timestamp": "2026-09-16T00:00:00",
        "info": {"max_steps": 200, "seed": None, "num_trials": 1, "git_commit": "abc",
                 "user_info": {}, "agent_info": {}, "environment_info": {}} | info,
        "tasks": [{"id": t} for t in sorted(task_ids)],
        "simulations": simulations,
    }


def simulation(task_id: str, reward: float, trial: int = 0, marker: str = "") -> dict:
    return {"task_id": task_id, "trial": trial, "marker": marker,
            "reward_info": {"reward": reward}}


class TestMerge:
    def test_adds_a_missing_task(self):
        base = result([simulation("a", 1.0)])
        patch = result([simulation("b", 0.0)])

        merged, taken = merge(base, patch)

        assert taken == ["b"]
        assert [s["task_id"] for s in merged["simulations"]] == ["a", "b"]

    def test_rerun_replaces_the_earlier_attempt(self):
        """The re-run is the reason for merging, so it wins."""
        base = result([simulation("a", 0.0, marker="first")])
        patch = result([simulation("a", 1.0, marker="rerun")])

        merged, _ = merge(base, patch)

        assert len(merged["simulations"]) == 1
        assert merged["simulations"][0]["marker"] == "rerun"

    def test_trials_of_one_task_stay_apart(self):
        base = result([simulation("a", 1.0, trial=0), simulation("a", 0.0, trial=1)])
        patch = result([simulation("a", 1.0, trial=1, marker="rerun")])

        merged, _ = merge(base, patch)

        assert len(merged["simulations"]) == 2
        assert {s["trial"]: s.get("marker") for s in merged["simulations"]} == {0: "", 1: "rerun"}

    def test_task_definitions_follow_their_simulations(self):
        base = result([simulation("a", 1.0)])
        patch = result([simulation("b", 1.0)])

        merged, _ = merge(base, patch)

        assert [t["id"] for t in merged["tasks"]] == ["a", "b"]

    def test_run_settings_are_kept(self):
        base = result([simulation("a", 1.0)], max_steps=200)
        patch = result([simulation("b", 1.0)], max_steps=200)

        merged, _ = merge(base, patch)

        assert merged["info"]["max_steps"] == 200
        assert merged["timestamp"] == base["timestamp"]

    def test_base_is_not_mutated(self):
        base = result([simulation("a", 1.0)])
        merge(base, result([simulation("b", 1.0)]))

        assert len(base["simulations"]) == 1


class TestDisagreements:
    def test_identical_settings_agree(self):
        assert disagreements(result([]), result([])) == []

    @pytest.mark.parametrize("field, value", [
        ("max_steps", 100), ("seed", 7), ("num_trials", 3),
        ("agent_info", {"llm": "other-model"}), ("git_commit", "def"),
    ])
    def test_a_different_setting_is_reported(self, field, value):
        """Merging two configurations into one file would make it meaningless."""
        assert disagreements(result([]), result([], **{field: value})) == [field]


def test_load_reads_a_file(tmp_path):
    path = tmp_path / "run.json"
    path.write_text(json.dumps(result([simulation("a", 1.0)])))

    assert load(path)["simulations"][0]["task_id"] == "a"


def test_merging_into_an_empty_run_succeeds(tmp_path, monkeypatch, capsys):
    """A run cut short before any task finished leaves an empty file to resume."""
    import merge as merge_cli

    base, patch = tmp_path / "run.json", tmp_path / "patch.json"
    base.write_text(json.dumps(result([])))
    patch.write_text(json.dumps(result([])))
    monkeypatch.setattr("sys.argv", ["merge.py", str(base), str(patch)])

    assert merge_cli.main() == 0
    assert "0 simulations, 0 solved" in capsys.readouterr().out


class TestRunNumbering:
    """Separate sweeps of the same experiment have to stay apart once merged."""

    @staticmethod
    def write(tmp_path, simulations):
        path = tmp_path / "run.json"
        path.write_text(json.dumps(result(simulations)))
        return path

    def test_first_run_is_left_alone(self, tmp_path):
        path = self.write(tmp_path, [simulation("a", 1.0, trial=0)])

        number_simulations(path, run=1, trials=1)

        assert json.loads(path.read_text())["simulations"][0]["trial"] == 0

    def test_later_runs_are_shifted(self, tmp_path):
        path = self.write(tmp_path, [simulation("a", 1.0, trial=0)])

        number_simulations(path, run=3, trials=1)

        assert json.loads(path.read_text())["simulations"][0]["trial"] == 2

    def test_repeats_within_a_sweep_keep_their_spacing(self, tmp_path):
        path = self.write(tmp_path, [simulation("a", 1.0, trial=0), simulation("a", 0.0, trial=1)])

        number_simulations(path, run=2, trials=2)

        assert sorted(s["trial"] for s in json.loads(path.read_text())["simulations"]) == [2, 3]

    def test_runs_of_one_task_survive_a_merge(self, tmp_path):
        """The point of the shift: three sweeps merge into three trials, not one."""
        runs = []
        for index in (1, 2, 3):
            path = tmp_path / f"run{index}.json"
            # separate runs carry their own seeds, as run.py assigns them
            path.write_text(json.dumps(result([simulation("a", 1.0, trial=0)], seed=299 + index)))
            number_simulations(path, run=index, trials=1)
            runs.append(load(path))

        merged = runs[0]
        for patch in runs[1:]:
            merged, _ = merge(merged, patch)

        assert sorted(s["trial"] for s in merged["simulations"]) == [0, 1, 2]


class TestMissingTasks:
    """Resuming a cut-short sweep must ask for exactly what is missing."""

    @pytest.fixture(autouse=True)
    def split(self, monkeypatch):
        """Stand in for tau2's task loader with a three-task split."""
        from types import SimpleNamespace

        tasks = [SimpleNamespace(id=name) for name in ("a", "b", "c")]
        monkeypatch.setattr("tau2.run.load_tasks", lambda domain, split: tasks)

    def test_lists_what_is_absent(self, tmp_path):
        path = tmp_path / "run.json"
        path.write_text(json.dumps(result([simulation("a", 1.0)])))

        assert missing_tasks(path, "telecom", "base") == ["b", "c"]

    def test_a_complete_file_leaves_nothing(self, tmp_path):
        path = tmp_path / "run.json"
        path.write_text(json.dumps(result([simulation(t, 1.0) for t in ("a", "b", "c")])))

        assert missing_tasks(path, "telecom", "base") == []

    def test_an_unscored_task_counts_as_missing(self, tmp_path):
        """tau2 writes a simulation without reward_info when a task dies mid-flight."""
        path = tmp_path / "run.json"
        unscored = simulation("b", 0.0) | {"reward_info": None}
        path.write_text(json.dumps(result([simulation("a", 1.0), unscored])))

        assert missing_tasks(path, "telecom", "base") == ["b", "c"]

    def test_split_order_is_kept(self, tmp_path):
        path = tmp_path / "run.json"
        path.write_text(json.dumps(result([simulation("b", 1.0)])))

        assert missing_tasks(path, "telecom", "base") == ["a", "c"]


def test_missing_py_runs_from_any_directory(tmp_path):
    """missing.py is called by sweep.sh, so it must not depend on the cwd.

    tau2 resolves its data directory at import time; a missing TAU2_DATA_DIR
    used to leave this crashing with FileNotFoundError halfway through a sweep.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    project = Path(__file__).resolve().parents[1]
    results = tmp_path / "run.json"
    results.write_text(json.dumps(result([])))
    env = {k: v for k, v in os.environ.items() if k != "TAU2_DATA_DIR"}

    completed = subprocess.run(
        [sys.executable, str(project / "missing.py"), str(results)],
        cwd=tmp_path, capture_output=True, text=True, env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert len(completed.stdout.split()) == 114        # the whole telecom base split


class TestFileSlug:
    """Gateways prefix model ids with a vendor, and a slash is a path separator."""

    def test_vendor_prefix_is_flattened(self):
        from run import file_slug

        assert file_slug("deepseek/deepseek-v3.2") == "deepseek-deepseek-v3.2"

    def test_a_plain_id_is_untouched(self):
        from run import file_slug

        assert file_slug("qwen3.8-flash") == "qwen3.8-flash"


class TestSeedPerRun:
    """Repeated runs must not derive the same LLM seed from the same default.

    tau2 seeds each trial from RunConfig.seed; three runs launched as separate
    single-trial processes would all take the same branch of that sequence.
    """

    @staticmethod
    def derived(base):
        import random

        random.seed(base)
        return random.randint(0, 1000000)

    def test_default_seed_differs_per_run(self):
        from run import DEFAULT_SEED

        seeds = {self.derived(DEFAULT_SEED + run - 1) for run in (1, 2, 3)}
        assert len(seeds) == 3

    def test_run_one_keeps_tau2s_default(self):
        from run import DEFAULT_SEED

        assert DEFAULT_SEED == 300


class TestTransportIsNotConfiguration:
    """How a request is sent must not block a merge; what the model does must."""

    @staticmethod
    def with_llm_args(**llm_args):
        return result([], agent_info={"llm": "m", "llm_args": llm_args})

    def test_redacted_and_absent_keys_agree(self):
        assert disagreements(self.with_llm_args(temperature=0.2, api_key="<redacted>"),
                             self.with_llm_args(temperature=0.2)) == []

    def test_a_request_timeout_does_not_count(self):
        assert disagreements(self.with_llm_args(temperature=0.2),
                             self.with_llm_args(temperature=0.2, timeout=300)) == []

    def test_a_different_temperature_still_counts(self):
        assert disagreements(self.with_llm_args(temperature=0.2),
                             self.with_llm_args(temperature=0.7)) == ["agent_info"]

    def test_a_commit_change_can_be_allowed_alone(self):
        base, patch = result([], git_commit="abc"), result([], git_commit="def")

        assert disagreements(base, patch, ignore=("git_commit",)) == []

    def test_allowing_a_commit_change_still_holds_the_rest(self):
        base = result([], git_commit="abc", seed=300)
        patch = result([], git_commit="def", seed=301)

        assert disagreements(base, patch, ignore=("git_commit",)) == ["seed"]


class TestUnnumberedPatches:
    """A patch from a run killed before numbering must not duplicate tasks."""

    def test_patch_takes_the_single_trial_runs_number(self):
        base = result([simulation("a", 1.0, trial=1)])
        patch = result([simulation("b", 1.0, trial=0)])

        merged, _ = merge(base, patch)

        assert sorted((s["task_id"], s["trial"]) for s in merged["simulations"]) == [("a", 1), ("b", 1)]

    def test_a_stray_trial_zero_replaces_rather_than_duplicates(self):
        base = result([simulation("a", 0.0, trial=1, marker="run")])
        patch = result([simulation("a", 1.0, trial=0, marker="patch")])

        merged, _ = merge(base, patch)

        assert len(merged["simulations"]) == 1

    def test_a_different_run_keeps_its_numbers(self):
        """Seed tells a patch of this run from another run of the experiment."""
        base = result([simulation("a", 1.0, trial=0)], seed=300)
        other_run = result([simulation("a", 1.0, trial=1)], seed=301)

        merged, _ = merge(base, other_run)

        assert sorted(s["trial"] for s in merged["simulations"]) == [0, 1]

    def test_multi_trial_runs_keep_their_numbers(self):
        base = result([simulation("a", 1.0, trial=0), simulation("a", 1.0, trial=1)], num_trials=2)
        patch = result([simulation("b", 1.0, trial=1)], num_trials=2)

        merged, _ = merge(base, patch)

        assert sorted(s["trial"] for s in merged["simulations"]) == [0, 1, 1]
