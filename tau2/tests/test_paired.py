"""Tests for the paired comparison: what it computes, and what it refuses to.

The refusal matters as much as the arithmetic. A statistics script that quietly
compares arms run under different configurations produces a number that looks
like evidence and is not, so the guard is tested first.
"""

import json

import pytest

import paired


def write_run(directory, arm, model, run, rewards, *, domain="telecom", base_url="https://h/v1",
              seed=300, steps=200, duration=10.0, tokens=100):
    """A result file in tau2's shape, holding one simulation per reward given."""
    payload = {
        "info": {
            "agent_info": {
                "implementation": arm, "llm": model,
                "llm_args": {"temperature": 0.2, "base_url": base_url, "api_key": "secret"},
            },
            "user_info": {"llm": "sim", "llm_args": {"temperature": 0.2}},
            "environment_info": {"domain_name": domain},
            "max_steps": steps, "max_errors": 3, "num_trials": 1, "seed": seed,
            "git_commit": "abc123",
        },
        "simulations": [
            {
                "task_id": f"task_{i}", "trial": run - 1, "duration": duration,
                "reward_info": {"reward": reward},
                "messages": [{
                    "role": "assistant",
                    "usage": {"prompt_tokens": tokens, "completion_tokens": 0},
                    "raw_data": {"steps": 2, "format_corrections": 0},
                }],
            }
            for i, reward in enumerate(rewards)
        ],
    }
    path = directory / f"2026-01-0{run}T00:00:00_{domain}_{arm}_{model}_run{run}.json"
    path.write_text(json.dumps(payload))
    return path


@pytest.fixture
def results(tmp_path, monkeypatch):
    monkeypatch.setattr(paired, "RESULTS", tmp_path)
    return tmp_path


class TestItRefusesToCompareAcrossConfigurations:
    def test_a_different_endpoint_is_refused(self, results):
        write_run(results, "cave_agent", "m", 1, [1.0, 0.0])
        write_run(results, "json_exec_agent", "m", 1, [1.0, 1.0])
        write_run(results, "llm_agent", "m", 1, [0.0, 0.0], base_url="https://other/v1")

        with pytest.raises(SystemExit, match="not run the same way"):
            paired.build_report("m", "telecom")

    def test_one_arm_seeded_differently_in_the_same_run_is_refused(self, results):
        """Run n of every arm must share a seed; that is what pairs their trials."""
        write_run(results, "cave_agent", "m", 1, [1.0])
        write_run(results, "json_exec_agent", "m", 1, [1.0])
        write_run(results, "llm_agent", "m", 1, [0.0], seed=999)

        with pytest.raises(SystemExit, match="run 1 used more than one seed"):
            paired.build_report("m", "telecom")

    def test_seeds_that_differ_between_runs_are_expected(self, results):
        """run.py derives 300 + run - 1, so each run of an arm has its own seed."""
        for arm in paired.ARMS:
            for run in (1, 2):
                write_run(results, arm, "m", run, [1.0], seed=299 + run)

        assert paired.build_report("m", "telecom")["arms"]["cave_agent"]["tasks"] == 1

    def test_a_missing_arm_is_refused(self, results):
        write_run(results, "cave_agent", "m", 1, [1.0])
        write_run(results, "json_exec_agent", "m", 1, [1.0])

        with pytest.raises(SystemExit, match="no results for llm_agent"):
            paired.build_report("m", "telecom")

    def test_a_listed_deployment_of_one_model_is_compared(self, results):
        """A sweep that moved gateway mid-way still compares with its own runs.

        Only for the pairs DEPLOYMENTS names: the same model, served under the
        gateway's own name, with reasoning stated rather than left unset.
        """
        (canonical, home), (alias, elsewhere) = paired.DEPLOYMENTS
        for run in (1, 2):
            write_run(results, "cave_agent", canonical, run, [1.0], base_url=home, seed=299 + run)
            write_run(results, "llm_agent", canonical, run, [0.0], base_url=home, seed=299 + run)
        moved = write_run(results, "cave_agent", canonical, 3, [1.0], base_url=elsewhere, seed=302)
        payload = json.loads(moved.read_text())
        payload["info"]["agent_info"]["llm"] = alias
        payload["info"]["agent_info"]["llm_args"] |= paired.NO_REASONING_REQUEST
        moved.write_text(json.dumps(payload))
        write_run(results, "llm_agent", canonical, 3, [0.0], base_url=home, seed=302)

        report = paired.build_report(canonical, "telecom", ["cave_agent", "llm_agent"])

        assert report["contrasts"]["cave_agent - llm_agent"]["mean_difference"] == 1.0

    def test_an_unlisted_model_that_moved_gateway_is_still_refused(self, results):
        write_run(results, "cave_agent", "m", 1, [1.0])
        write_run(results, "llm_agent", "m", 1, [0.0], base_url="https://elsewhere/v1")

        with pytest.raises(SystemExit, match="not run the same way"):
            paired.build_report("m", "telecom", ["cave_agent", "llm_agent"])

    def test_the_api_key_and_timeout_do_not_count_as_a_difference(self, results):
        """They govern transport, not what the model does; merge.py agrees."""
        write_run(results, "cave_agent", "m", 1, [1.0])
        write_run(results, "json_exec_agent", "m", 1, [1.0])
        path = write_run(results, "llm_agent", "m", 1, [0.0])
        payload = json.loads(path.read_text())
        payload["info"]["agent_info"]["llm_args"] |= {"api_key": "other", "timeout": 900}
        path.write_text(json.dumps(payload))

        assert paired.build_report("m", "telecom")["arms"]["llm_agent"]["tasks"] == 1


class TestArmSelection:
    def test_two_arms_give_the_one_contrast_between_them(self, results):
        """The third arm exists on one model; the rest report the pair."""
        write_run(results, "cave_agent", "m", 1, [1.0, 1.0])
        write_run(results, "llm_agent", "m", 1, [1.0, 0.0])

        report = paired.build_report("m", "telecom", ["cave_agent", "llm_agent"])

        assert list(report["contrasts"]) == ["cave_agent - llm_agent"]
        assert report["contrasts"]["cave_agent - llm_agent"]["mean_difference"] == 0.5

    def test_asking_for_an_arm_that_was_not_run_is_an_error(self, results):
        write_run(results, "cave_agent", "m", 1, [1.0])

        with pytest.raises(SystemExit, match="no results for llm_agent"):
            paired.build_report("m", "telecom", ["cave_agent", "llm_agent"])


class TestWhatItComputes:
    def test_repeats_are_averaged_before_tasks_are_resampled(self, results):
        """A task solved twice of three runs counts 2/3, not as three observations."""
        for run, rewards in enumerate([[1.0], [1.0], [0.0]], start=1):
            write_run(results, "cave_agent", "m", run, rewards)
        assert paired.per_task(paired.runs_of("cave_agent", "m", "telecom")) == {
            "task_0": pytest.approx(2 / 3)
        }

    def test_a_difference_is_paired_on_the_tasks_both_answered(self, results):
        first = {"a": 1.0, "b": 0.0, "c": 1.0}
        second = {"a": 0.0, "b": 0.0}
        report = paired.paired_difference(first, second, label="x")
        assert report["tasks"] == 2                      # c is not in both
        assert report["mean_difference"] == pytest.approx(0.5)
        assert report["tasks_differing"] == 1
        assert report["first_only"] == 1 and report["second_only"] == 0

    def test_identical_arms_do_not_differ(self, results):
        same = {f"t{i}": float(i % 2) for i in range(10)}
        report = paired.paired_difference(same, same, label="x")
        assert report["mean_difference"] == 0.0
        assert report["ci95"] == [0.0, 0.0]
        assert not report["differs_from_zero"]

    def test_a_consistent_gap_differs_from_zero(self, results):
        better = {f"t{i}": 1.0 for i in range(20)}
        worse = {f"t{i}": 0.0 for i in range(20)}
        report = paired.paired_difference(better, worse, label="x")
        assert report["differs_from_zero"]
        assert report["mcnemar"]["p_value"] < 0.001 if "mcnemar" in report else True

    def test_an_interval_whose_limit_sits_on_zero_does_not_exclude_it(self, results):
        """One task ahead and the rest tied: many draws miss it, so the bound is zero.

        Two published cells land exactly here. Zero can come back from the
        interpolation as a few parts in 1e15 above itself, and read literally
        that would turn a boundary case into a finding.
        """
        ahead = {f"t{i}": float(i == 0) for i in range(20)}
        tied = {f"t{i}": 0.0 for i in range(20)}

        report = paired.paired_difference(ahead, tied, label="one ahead")

        assert report["mean_difference"] > 0
        assert report["ci95"][0] == pytest.approx(0.0, abs=paired.TOUCHES_ZERO)
        assert not report["differs_from_zero"]

    def test_the_bootstrap_is_reproducible(self, results):
        first = {f"t{i}": float(i % 3 == 0) for i in range(12)}
        second = {f"t{i}": float(i % 2 == 0) for i in range(12)}
        a = paired.paired_difference(first, second, label="same")
        b = paired.paired_difference(first, second, label="same")
        assert a == b
        c = paired.paired_difference(first, second, label="other")
        assert c["ci95"] != a["ci95"] or c["mean_difference"] == a["mean_difference"]

    def test_the_three_contrasts_are_arithmetically_consistent(self, results):
        """cave-json plus json-fc must equal cave-fc on the means."""
        write_run(results, "cave_agent", "m", 1, [1.0, 1.0, 0.0])
        write_run(results, "json_exec_agent", "m", 1, [1.0, 0.0, 0.0])
        write_run(results, "llm_agent", "m", 1, [0.0, 0.0, 0.0])

        contrasts = paired.build_report("m", "telecom")["contrasts"]
        step_one = contrasts["json_exec_agent - llm_agent"]["mean_difference"]
        step_two = contrasts["cave_agent - json_exec_agent"]["mean_difference"]
        whole = contrasts["cave_agent - llm_agent"]["mean_difference"]
        assert step_one + step_two == pytest.approx(whole)

    def test_mcnemar_is_two_sided_on_the_discordant_tasks(self):
        report = {"first_only": 9, "second_only": 1}
        assert paired.mcnemar(report)["discordant"] == 10
        assert paired.mcnemar(report)["p_value"] < 0.05
        assert paired.mcnemar({"first_only": 0, "second_only": 0})["p_value"] == 1.0


class TestSecondarySignals:
    def test_cost_signals_are_read_per_task(self, results):
        write_run(results, "cave_agent", "m", 1, [1.0, 1.0], duration=20.0, tokens=500)
        summary = paired.secondary(paired.runs_of("cave_agent", "m", "telecom"))
        assert summary["tokens_per_task"] == 500
        assert summary["seconds_per_task"] == 20.0
        assert summary["model_calls_per_turn"] == 2
        assert summary["turns"] == 2 and summary["format_corrections"] == 0

    def test_the_empty_reply_filler_is_counted(self, results):
        path = write_run(results, "json_exec_agent", "m", 1, [1.0])
        payload = json.loads(path.read_text())
        payload["simulations"][0]["messages"].append(
            {"role": "assistant", "raw_data": {"stood_in_for_an_empty_reply": True}})
        path.write_text(json.dumps(payload))

        summary = paired.secondary(paired.runs_of("json_exec_agent", "m", "telecom"))
        assert summary["empty_reply_fillers"] == 1


class TestTheTokenCaveatIsQuantified:
    """A token figure has to say how much of it the provider actually reported."""

    def test_the_estimated_share_is_read_from_the_trace(self, results):
        path = write_run(results, "cave_agent", "m", 1, [1.0])
        payload = json.loads(path.read_text())
        payload["simulations"][0]["messages"][0]["raw_data"] |= {
            "usage_sources": {"reported": 1, "estimated": 3}}
        path.write_text(json.dumps(payload))

        summary = paired.secondary(paired.runs_of("cave_agent", "m", "telecom"))
        assert summary["usage_estimated_share"] == 0.75

    def test_an_arm_that_records_no_source_reports_none(self, results):
        """tau2's own agent does not run a CaveAgent loop, so it has no such count."""
        write_run(results, "llm_agent", "m", 1, [1.0])
        summary = paired.secondary(paired.runs_of("llm_agent", "m", "telecom"))
        assert summary["usage_estimated_share"] is None
