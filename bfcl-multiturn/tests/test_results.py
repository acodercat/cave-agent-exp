"""Which of a run's rows are evidence about the paradigm that produced them.

One definition, because the runner, the estimator and the comparison all ask it
and must not answer differently.
"""

import json

from bfcl_multiturn import results


def payload(*rows):
    return {"arm": "cave", "model": "m", "tasks": list(rows)}


class TestWhatCounts:
    def test_a_solved_task(self):
        assert results.is_evidence({"id": "t", "valid": True})
        assert results.counts_as_solved({"id": "t", "valid": True})

    def test_a_failed_task(self):
        """A wrong answer is evidence; that is the point of measuring."""
        assert results.is_evidence({"id": "t", "valid": False})


class TestWhatDoesNot:
    def test_a_task_that_raised(self):
        assert not results.is_evidence({"id": "t", "valid": False, "error": "Timeout"})


class TestARecordThatFellShort:
    """It counts, as a failure, rather than being dropped.

    Only the cave arm can produce one, so dropping it would remove tasks from one
    arm alone -- and the first real case was a task that arm had failed, so
    dropping it would have raised its score. The arm whose record fell short
    carries the doubt instead.
    """

    def test_it_still_counts_towards_the_rate(self):
        row = {"id": "t", "valid": False, "unrecorded_change": {"GorillaFileSystem": ["root"]}}

        assert results.is_evidence(row)

    def test_it_is_not_credited_even_when_scored_correct(self):
        row = {"id": "t", "valid": True, "unrecorded_change": {"TwitterAPI": ["tweets"]}}

        assert results.is_evidence(row)
        assert not results.counts_as_solved(row)

    def test_the_rate_it_produces(self):
        payload = {"tasks": [{"id": "a", "valid": True},
                             {"id": "b", "valid": True, "unrecorded_change": {"X": ["y"]}}]}

        assert len(results.scored(payload)) == 2        # both count
        assert results.solved(payload) == 1             # one is credited


class TestReporting:
    def test_the_rows_that_count_keep_their_order(self):
        kept = results.scored(payload({"id": "a", "valid": True},
                                      {"id": "b", "valid": False, "error": "x"},
                                      {"id": "c", "valid": False}))

        assert [row["id"] for row in kept] == ["a", "c"]

    def test_an_incomplete_record_is_reported_though_it_counts(self):
        aside = results.set_aside(payload({"id": "a", "valid": True,
                                           "unrecorded_change": {"X": ["y"]}}))

        assert aside["unaccounted"] == ["a"]

    def test_the_rest_are_named_by_why(self):
        aside = results.set_aside(payload(
            {"id": "a", "valid": True},
            {"id": "b", "valid": False, "error": "Timeout"},
            {"id": "c", "valid": True, "unrecorded_change": {"X": ["y"]}}))

        assert aside == {"errored": ["b"], "unaccounted": ["c"]}

    def test_a_row_that_both_raised_and_was_unaccounted_counts_once(self):
        """As errored: it never got far enough for fidelity to mean anything."""
        aside = results.set_aside(payload(
            {"id": "a", "valid": False, "error": "Timeout", "unrecorded_change": {"X": ["y"]}}))

        assert aside == {"errored": ["a"], "unaccounted": []}

    def test_reading_a_file(self, tmp_path):
        path = tmp_path / "run.json"
        path.write_text(json.dumps(payload({"id": "a", "valid": True})))

        assert results.read(path)["tasks"][0]["id"] == "a"
