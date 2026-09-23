"""The result-file layout: {"metrics": header, "results": scenarios}.

The header follows the lab's shared layout (see AtmosCoder-Bench): one block
carrying provenance and rollup together. These tests pin the shape, the
rollup arithmetic, and that every on-disk generation still loads — the
guarantees resume and the analysis scripts depend on.
"""

import json

from runner import _file_metrics, _load_results


def _scenario(passed: int, failed: int, tokens: int, errors: int = 0) -> dict:
    turns = [{"success": True} for _ in range(passed)]
    turns += [{"success": False} for _ in range(failed - errors)]
    turns += [{"success": False, "error": "API down"} for _ in range(errors)]
    return {
        "conversations": [{"id": "c1", "turns": turns}],
        "metrics": {
            "total_turns": passed + failed,
            "successful_turns": passed,
            "failed_turns": failed,
            "total_prompt_tokens": tokens,
            "total_completion_tokens": tokens // 10,
            "total_tokens": tokens + tokens // 10,
        },
    }


class TestFileMetrics:
    def test_rollup_sums_scenarios_and_counts_infra_errors(self):
        results = {
            "s1": _scenario(passed=2, failed=0, tokens=100),
            "s2": _scenario(passed=1, failed=2, tokens=200, errors=1),
        }

        header = _file_metrics(results, {"model_id": "m", "mode": "cave"})

        assert header["total"] == 5
        assert header["passed"] == 3
        assert header["failed"] == 2
        assert header["errors"] == 1
        assert header["accuracy"] == 0.6
        assert header["usage"] == {
            "prompt_tokens": 300,
            "completion_tokens": 30,
            "total_tokens": 330,
        }
        assert header["model_id"] == "m" and header["mode"] == "cave"
        assert header["timestamp"]

    def test_empty_results_do_not_divide_by_zero(self):
        header = _file_metrics({}, None)

        assert header["total"] == 0 and header["accuracy"] == 0.0

    def test_meta_none_still_yields_a_complete_rollup(self):
        header = _file_metrics({"s": _scenario(1, 0, 10)}, None)

        assert header["passed"] == 1 and "usage" in header


class TestLoadResultsGenerations:
    """Resume must read every generation ever written to disk."""

    def test_current_wrapped_layout(self, tmp_path):
        scenarios = {"s1": _scenario(1, 0, 10)}
        f = tmp_path / "r.json"
        f.write_text(json.dumps({"metrics": {"total": 1}, "results": scenarios}))

        assert _load_results(f) == scenarios

    def test_interim_meta_layout(self, tmp_path):
        scenarios = {"s1": _scenario(1, 0, 10)}
        f = tmp_path / "r.json"
        f.write_text(json.dumps({"_meta": {"model": "m"}, **scenarios}))

        assert _load_results(f) == scenarios

    def test_original_flat_layout(self, tmp_path):
        scenarios = {"s1": _scenario(1, 0, 10)}
        f = tmp_path / "r.json"
        f.write_text(json.dumps(scenarios))

        assert _load_results(f) == scenarios
