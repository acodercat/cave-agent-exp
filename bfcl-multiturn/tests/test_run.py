"""What the runner keeps when it resumes a file, and what it runs again.

A run is restartable, so this decision is what stops a gateway hiccup from
becoming a permanent wrong answer.
"""

import json

import pytest

from run import already_scored


@pytest.fixture
def written(tmp_path):
    def write(rows):
        path = tmp_path / "cave_model_run1.json"
        path.write_text(json.dumps({"arm": "cave", "model": "m", "run": 1, "tasks": rows}))
        return path
    return write


class TestResuming:
    def test_a_scored_task_is_kept_whether_it_passed_or_failed(self, written):
        path = written([{"id": "t1", "valid": True}, {"id": "t2", "valid": False}])

        assert set(already_scored(path)) == {"t1", "t2"}

    def test_an_errored_task_is_run_again(self, written):
        """An outage is not a result, so it must not become a permanent failure."""
        path = written([{"id": "t1", "valid": True},
                        {"id": "t2", "valid": False, "error": "BadRequestError"}])

        assert set(already_scored(path)) == {"t1"}

    def test_the_kept_rows_come_back_whole(self, written):
        """They are written straight back out, so nothing may be dropped."""
        path = written([{"id": "t1", "valid": True, "turns": [{"turn": 0}], "elapsed": 1.5}])

        assert already_scored(path)["t1"]["turns"] == [{"turn": 0}]

    def test_a_file_that_does_not_exist_yet(self, tmp_path):
        assert already_scored(tmp_path / "absent.json") == {}


class TestATaskThatStopsMakingProgress:
    """litellm retries a gateway error inside its own call, so a task can hang.

    Without a deadline the run never ends, and a campaign waiting on it stalls
    with it -- which is what happened on deepseek-v4-flash's last task, after nine
    "Backend buffer overflow" replies from the gateway.
    """

    def test_a_timeout_is_recorded_as_an_error_not_a_failure(self):
        import asyncio

        async def never():
            await asyncio.Event().wait()

        async def guarded():
            try:
                return await asyncio.wait_for(never(), timeout=0.01)
            except TimeoutError:
                return {"id": "t", "valid": False, "error": "TimeoutError: no result within 0s"}

        row = asyncio.run(guarded())

        assert row["error"].startswith("TimeoutError")
        from bfcl_multiturn import results
        assert not results.is_evidence(row)     # excluded, and retried on a rerun
