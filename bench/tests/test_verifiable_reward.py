"""The reward read from a scored turn: pass/fail, and how much of it was right."""

from scripts.verifiable_reward import turn_reward


def scalar(correct: bool) -> dict:
    return {"success": correct,
            "variable_verification": {"items": {"total": {"correct": correct}}}}


def table(rows_matched: int, cell_errors: dict, rows_expected: int = 100) -> dict:
    return {"success": False, "variable_verification": {"items": {"t": {"table": {
        "rows_expected": rows_expected, "rows_delivered": rows_expected,
        "rows_matched": rows_matched, "cell_errors": cell_errors}}}}}


def test_a_scalar_answer_is_right_or_wrong():
    assert turn_reward(scalar(True)) == (True, 1.0)
    assert turn_reward(scalar(False)) == (False, 0.0)


def test_a_delivered_table_still_scores_what_it_got_right():
    passed, credit = turn_reward(table(rows_matched=100, cell_errors={"a": 10, "b": 0}))
    assert not passed and 0.9 < credit < 1.0      # ten wrong cells of two hundred


def test_a_table_that_lost_most_of_its_rows_scores_low():
    _, credit = turn_reward(table(rows_matched=10, cell_errors={"a": 0, "b": 0}))
    assert credit == 0.1


def test_credit_never_goes_below_zero():
    _, credit = turn_reward(table(rows_matched=5, cell_errors={"a": 100, "b": 100}))
    assert credit == 0.0


def test_a_turn_without_variable_verification_reports_no_credit():
    assert turn_reward({"success": True}) == (True, None)


def test_a_study_reports_each_turn_index_apart(tmp_path, monkeypatch):
    """A first turn that is easy and a second that is not must not read as one number."""
    import json

    from scripts import verifiable_reward

    runs = tmp_path / "study-arm" / "runs" / "case" / "model"
    for index, outcomes in enumerate([(True, True), (True, False)], start=1):
        pass
    for run_id, (first, second) in enumerate([(True, True), (True, False)]):
        directory = runs / f"run{run_id}"
        directory.mkdir(parents=True)
        (directory / "programmatic_verification.json").write_text(json.dumps({
            "conversations": [{"id": "main", "turns": [
                {"turn": 1, "status": "scored", "programmatic_verification": scalar(first)},
                {"turn": 2, "status": "scored", "programmatic_verification": scalar(second)},
            ]}],
        }))
    monkeypatch.setattr(verifiable_reward, "EXPERIMENTS_DIR", tmp_path)
    summary = verifiable_reward.read_study("study")
    assert summary["per_turn"]["1"]["pass_at_1"] == 1.0
    assert summary["per_turn"]["2"]["pass_at_1"] == 0.5
    assert summary["per_turn"]["2"]["best_of_n"] == 1.0
