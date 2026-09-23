"""The security corpus says what the checker does, including where it stops short."""

from scripts.measure_security_rules import summarise, verdicts


def test_every_named_reach_is_refused_and_no_analysis_code_is():
    report = verdicts()
    summary = summarise(report)
    blocked = len(report["blocked"])
    allowed = len(report["allowed"])
    assert summary["blocked_caught"] == f"{blocked}/{blocked}"
    assert summary["allowed_kept"] == f"{allowed}/{allowed}"


def test_the_evasions_are_evasions():
    """A corpus entry that the checker refuses is not an evasion and must be relabelled."""
    report = verdicts()
    refused = [row["code"] for row in report["evades"] if row["refused"]]
    assert not refused, refused


def test_a_refusal_says_which_rule_spoke():
    report = verdicts()
    for row in report["blocked"]:
        assert row["rule_said"], row["code"]
