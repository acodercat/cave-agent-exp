"""Q4 paired differences with missing runs counted as failures and over scored runs only.

    uv run python analysis/q4_sensitivity.py [--json OUT] [--md OUT] <comparisons dir or report.json>...

Reads the ``report.json`` that ``scripts/compare_paradigms.py`` wrote for each
Q4 comparison (``comparisons/paper-<set>-<model>/``) and sets side by side, for
every arm against CaveAgent over all sizes:

* ``success_missing_as_failure`` — every turn of a planned run that has no
  verdict counts as failed. This is what §4.4 reports.
* ``success`` — the primary outcome of ``compare_paradigms``: each case over the
  runs it has scored, so an unscored run drops out of its case's mean.

Both are the mean task-paired difference arm − CaveAgent with its 95% interval
from a bootstrap that resamples tasks (10,000 draws), as stored in the report;
nothing is recomputed. The clustering unit is the task: a case set's sizes of
one task are one cluster (20 for ``b1``, 5 for ``b1t``), an imported case its
own (117 for ``a``). The token ratio is the ratio of mean estimated tokens
(prompt + completion over every call), arm / CaveAgent, with its interval.

``--check`` asserts that the reported column reproduces the numbers printed in
§4.4 of the paper (to the three decimals printed) and exits non-zero otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ARM_NAMES = {"codeblock_files": "Code->file", "codeblock": "Code->text", "json_exec": "JSON->text"}
SET_NAMES = {"table_delivery": "b1", "table_control": "b1t", "imported": "a"}
# §4.4 as printed: (set, model, arm) -> (difference, ci95 low, ci95 high) of
# success_missing_as_failure, or a token ratio printed to the given decimals.
PAPER_DIFFERENCES = {
    ("b1", "deepseek", "codeblock"): (-0.381, -0.439, -0.319),
    ("b1", "deepseek", "json_exec"): (-0.431, -0.497, -0.356),
    ("b1", "qwen", "codeblock"): (-0.378, -0.514, -0.244),
    ("b1", "qwen", "json_exec"): (-0.442, -0.586, -0.300),
    ("b1", "deepseek", "codeblock_files"): (+0.008, -0.019, +0.036),
    ("b1", "qwen", "codeblock_files"): (+0.119, +0.033, +0.214),
    ("a", "qwen", "json_exec"): (+0.055, +0.016, +0.093),
}
PAPER_RATIOS = {
    ("b1", "deepseek", "codeblock"): (3.9, 1), ("b1", "deepseek", "json_exec"): (5.0, 1),
    ("b1", "qwen", "codeblock"): (2.6, 1), ("b1", "qwen", "json_exec"): (1.5, 1),
    ("a", "deepseek", "json_exec"): (2.08, 2), ("a", "qwen", "json_exec"): (0.81, 2),
}
# "On DeepSeek neither text arm is separated from CaveAgent" on the small-output set.
PAPER_NOT_SEPARATED = [("a", "deepseek", "codeblock"), ("a", "deepseek", "json_exec")]


def reports(paths: list[Path]) -> list[Path]:
    found = []
    for path in paths:
        found += sorted(path.glob("paper-*/report.json")) if path.is_dir() else [path]
    return found


def rows(report_path: Path) -> list[dict]:
    report = json.loads(report_path.read_text())
    set_name = SET_NAMES[report["case_set"]]
    model = report_path.parent.name.rsplit("-", 1)[1]
    reference = report["paradigms"][report["reference"]]
    out = []
    for arm, comparison in report["comparisons"].items():
        overall = comparison["all"]
        paradigm = report["paradigms"][arm]
        pick = lambda key: {"tasks": overall[key]["tasks"], "mean": overall[key]["mean_difference"],
                            "ci95": overall[key]["ci95"], "differs": overall[key]["differs_from_zero"]}
        out.append({
            "comparison": report_path.parent.name, "set": set_name, "model": model, "arm": arm,
            "clusters": overall["success_missing_as_failure"]["tasks"],
            "scored_runs": {"cave": reference["scored_runs"], arm: paradigm["scored_runs"]},
            "missing_runs": {"cave": reference["missing_runs"], arm: paradigm["missing_runs"]},
            "missing_as_failure": pick("success_missing_as_failure"),
            "scored_only": pick("success"),
            "token_ratio": {"ratio": overall["estimated_tokens"]["ratio"],
                            "ci95": overall["estimated_tokens"]["ratio_ci95"]},
        })
    return out


def check(table: list[dict]) -> list[str]:
    """Every §4.4 number against the reported column; returns the mismatches."""
    by_key = {(r["set"], r["model"], r["arm"]): r for r in table}
    problems = []
    for key, printed in PAPER_DIFFERENCES.items():
        d = by_key[key]["missing_as_failure"]
        got = tuple(round(x, 3) for x in (d["mean"], *d["ci95"]))
        if got != printed:
            problems.append(f"{key}: paper {printed}, report {got}")
    for key, (printed, places) in PAPER_RATIOS.items():
        got = round(by_key[key]["token_ratio"]["ratio"], places)
        if got != printed:
            problems.append(f"{key} token ratio: paper {printed}, report {got}")
    for key in PAPER_NOT_SEPARATED:
        if by_key[key]["missing_as_failure"]["differs"]:
            problems.append(f"{key}: paper says not separated, report's interval excludes zero")
    return problems


def markdown(table: list[dict]) -> str:
    ci = lambda d: f"{d['mean']:+.3f} [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}]"
    lines = ["| set | model | arm | tasks (clusters) | scored runs cave / arm | missing as failure (paper) | scored runs only | token ratio [95% CI] |",
             "|---|---|---|---:|---|---|---|---|"]
    for r in table:
        runs = " / ".join(str(v) for v in r["scored_runs"].values())
        tok = r["token_ratio"]
        lines.append(f"| {r['set']} | {r['model']} | {ARM_NAMES[r['arm']]} | {r['clusters']} | {runs} | "
                     f"{ci(r['missing_as_failure'])} | {ci(r['scored_only'])} | "
                     f"{tok['ratio']:.2f}x [{tok['ci95'][0]:.2f}, {tok['ci95'][1]:.2f}] |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--md", type=Path)
    parser.add_argument("--check", action="store_true", help="assert the paper's §4.4 numbers")
    args = parser.parse_args()
    order = {"b1": 0, "b1t": 1, "a": 2}
    table = sorted((r for p in reports(args.reports) for r in rows(p)),
                   key=lambda r: (order[r["set"]], r["model"], list(ARM_NAMES).index(r["arm"])))
    print(markdown(table))
    problems = check(table) if args.check else []
    for problem in problems:
        print("MISMATCH", problem)
    if args.check and not problems:
        print(f"all {len(PAPER_DIFFERENCES) + len(PAPER_RATIOS) + len(PAPER_NOT_SEPARATED)} §4.4 numbers reproduced")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"rows": table, "paper_check": problems if args.check else None}, indent=1) + "\n")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(markdown(table))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
