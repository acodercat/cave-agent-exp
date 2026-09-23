"""The driver's resume counts a run only under its own configuration.

Skipping over a run made with a different depth or budget would quietly mix two
studies in one directory, and nothing downstream would notice.
"""

import json
from pathlib import Path

from cases.pipeline import PIPELINE_CASES, depth_cases
from core.pipeline import CHANNELS
from core.pipeline_evaluator import PipelineSettings
from scripts.run_pipeline import (
    PIPELINE_FILE, case_directory, run_configuration, stored_runs,
)


def _store(experiment: Path, case, model: str, run_id: str, settings: dict) -> None:
    path = case_directory(experiment, case.name, model) / run_id / PIPELINE_FILE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"settings": settings}))


def test_a_run_under_the_same_configuration_is_counted(tmp_path):
    case, channel, settings = PIPELINE_CASES[0], CHANNELS["object"], PipelineSettings()
    configuration = run_configuration(case, channel, settings)
    _store(tmp_path, case, "m", "r1", configuration)
    assert stored_runs(tmp_path, case, "m", configuration) == 1


def test_a_run_under_another_budget_or_depth_is_not_counted(tmp_path, capsys):
    case, channel = PIPELINE_CASES[0], CHANNELS["object"]
    wanted = run_configuration(case, channel, PipelineSettings())
    other_budget = run_configuration(case, channel, PipelineSettings(step_budget=20))
    deeper = run_configuration(depth_cases(4)[0], channel, PipelineSettings())
    other_channel = run_configuration(case, CHANNELS["text"], PipelineSettings())
    _store(tmp_path, case, "m", "r1", other_budget)
    _store(tmp_path, case, "m", "r2", deeper)
    _store(tmp_path, case, "m", "r3", other_channel)
    assert stored_runs(tmp_path, case, "m", wanted) == 0
    assert capsys.readouterr().out.count("IGNORE") == 3


def test_the_configuration_names_everything_a_study_holds_fixed():
    keys = set(run_configuration(PIPELINE_CASES[0], CHANNELS["object"], PipelineSettings()))
    assert {"channel", "agents", "roles", "step_budget", "max_protocol_nudges",
            "max_exec_output", "size", "task", "producer_paradigm", "questions"} <= keys


def test_a_run_under_a_reworded_question_is_not_counted(tmp_path):
    """A follow-up that was reworded is a different experiment of the same case."""
    from dataclasses import replace
    case, channel, settings = PIPELINE_CASES[0], CHANNELS["object"], PipelineSettings()
    reworded = replace(case, follow_up=replace(case.follow_up, query="Something else."))
    _store(tmp_path, case, "m", "r1", run_configuration(reworded, channel, settings))
    assert stored_runs(tmp_path, case, "m", run_configuration(case, channel, settings)) == 0


def test_the_hosted_configuration_did_not_change_shape():
    """Every stored hosted run must still match; a new key would unmatch them all."""
    configuration = run_configuration(PIPELINE_CASES[0], CHANNELS["object"], PipelineSettings())
    assert "study" not in configuration


def test_an_orchestrated_run_never_counts_towards_a_hosted_run(tmp_path):
    from core.orchestration import ARMS
    case, settings = PIPELINE_CASES[0], PipelineSettings()
    import scripts.run_pipeline as driver
    orchestrated = run_configuration(
        case, ARMS["cave"], settings, "orchestrated", driver.Protocol({"model_id": "m"}, "abc"))
    hosted = run_configuration(case, CHANNELS["object"], settings)
    assert orchestrated != hosted
    _store(tmp_path, case, "m", "r1", orchestrated)
    assert stored_runs(tmp_path, case, "m", hosted) == 0


def test_an_orchestrated_run_under_another_model_protocol_or_code_is_not_counted(tmp_path):
    """The same api_model with another max_tokens, or older code, is another experiment."""
    from core.orchestration import ARMS
    import scripts.run_pipeline as driver
    case, settings, arm = PIPELINE_CASES[0], PipelineSettings(), ARMS["cave"]
    model = {"model_id": "m", "temperature": 0.1, "max_tokens": 32768, "thinking": None}
    protocol = driver.Protocol(model, "abc123")
    wanted = run_configuration(case, arm, settings, "orchestrated", protocol)
    _store(tmp_path, case, "m", "r1", wanted)
    _store(tmp_path, case, "m", "r2", run_configuration(
        case, arm, settings, "orchestrated", driver.Protocol(model | {"max_tokens": 8192}, "abc123")))
    _store(tmp_path, case, "m", "r3", run_configuration(
        case, arm, settings, "orchestrated", driver.Protocol(model, "def456")))
    assert stored_runs(tmp_path, case, "m", wanted) == 1


def test_an_outage_requeues_every_running_case_not_only_the_one_that_reported_it(tmp_path):
    """Two cases in flight; one hits a refused connection. Both must still complete."""
    import asyncio
    from types import SimpleNamespace
    import scripts.run_pipeline as driver
    from core.errors import InfrastructureError

    cases = PIPELINE_CASES[:2]
    calls = {"n": 0}

    async def fake_run_and_write(model, cfg, case, channel, settings, experiment_dir, run_id,
                                 study, protocol):
        calls["n"] += 1
        if calls["n"] == 1:
            await asyncio.sleep(0.01)
            raise InfrastructureError("Connection error: Connect call failed")
        await asyncio.sleep(0.05)
        _store(experiment_dir, case, cfg.api_model, run_id,
               run_configuration(case, channel, settings, study, protocol))
        return True

    async def no_wait(model):
        return None

    original = driver._run_and_write, driver._wait_for_endpoint
    driver._run_and_write, driver._wait_for_endpoint = fake_run_and_write, no_wait
    try:
        cfg = SimpleNamespace(api_model="m", name="m", base_url="u")
        totals = asyncio.run(driver.run_channel(
            None, cfg, list(cases), CHANNELS["object"], PipelineSettings(), tmp_path, 2, 1,
        ))
    finally:
        driver._run_and_write, driver._wait_for_endpoint = original
    assert totals["run"] == 2 and totals["abandoned"] == 0
    for case in cases:
        assert stored_runs(tmp_path, case, "m", run_configuration(
            case, CHANNELS["object"], PipelineSettings())) == 1


def test_a_study_continues_under_the_commit_it_began_at_only_if_no_run_determining_file_changed(
    tmp_path, monkeypatch,
):
    """A commit to the driver must not orphan a running study; a commit to core/ must.

    Run against a repository built for the test, so it holds whatever this
    checkout's history is.
    """
    import subprocess
    import pytest
    import scripts.run_pipeline as driver

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], capture_output=True, text=True, check=True,
        ).stdout.strip()

    def commit(path: str, text: str) -> str:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        git("add", path)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", path)
        return git("rev-parse", "HEAD")

    git("init", "-q")
    begun = commit("core/agents.py", "v1")
    commit("scripts/run_pipeline.py", "a log line")
    # The driver finds its repository from its own location.
    monkeypatch.setattr(driver, "__file__", str(tmp_path / "scripts" / "run_pipeline.py"))
    assert driver._study_commit(begun) == begun          # only the driver changed
    assert driver._study_commit(None) == git("rev-parse", "HEAD")
    (tmp_path / "core" / "agents.py").write_text("v2, uncommitted")
    with pytest.raises(SystemExit):                          # a dirty core/ refuses
        driver._study_commit(begun)
    commit("core/agents.py", "v2")
    with pytest.raises(SystemExit):                          # a committed change refuses
        driver._study_commit(begun)


def test_a_pipeline_past_the_guard_is_stored_as_a_failed_run_and_not_retried(tmp_path, monkeypatch):
    """The guard is the run's budget: past it, the case has failed, and its record says so."""
    import asyncio
    from types import SimpleNamespace
    import scripts.run_pipeline as driver

    async def never_returns(model, case, channel, settings, workdir):
        await asyncio.sleep(10)

    monkeypatch.setattr(driver, "PIPELINE_TIMEOUT_S", 0.05)
    monkeypatch.setattr(driver, "run_hosted", never_returns)
    monkeypatch.setattr(driver, "code_fingerprint", lambda: {})
    case, channel, settings = PIPELINE_CASES[0], CHANNELS["object"], PipelineSettings()
    cfg = SimpleNamespace(api_model="m", name="m", base_url="u")
    success = asyncio.run(driver._run_and_write(None, cfg, case, channel, settings, tmp_path, "r1"))
    assert success is False
    record = json.loads((case_directory(tmp_path, case.name, "m") / "r1" / PIPELINE_FILE).read_text())
    assert record["timed_out"] and record["success"] is False and "orchestrator" not in record
    assert stored_runs(tmp_path, case, "m", run_configuration(case, channel, settings)) == 1
