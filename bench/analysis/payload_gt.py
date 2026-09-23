"""Success against the answer's size in output budgets, sized from the reference answer.

The answer is a property of the case, so its size is read off the reference table
(the JSON text of its rows, at four characters a token) and every case is binned,
for both models alike.
"""
import importlib, json, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, ".")
CAP = 32768
BINS = [(0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 8.0), (8.0, 1e9)]
ARMS = ["cave", "codeblock_files", "codeblock", "json_exec"]
REPEATS = 3          # planned runs per case; a run that was never stored counts as a failure
sizes_file = Path(sys.argv[1])

cases = sorted(p.name for p in Path("experiments/x1-b1-v1-cave/runs").iterdir())
if sizes_file.exists():
    sizes = json.loads(sizes_file.read_text())
else:
    sizes = {}
    for case in cases:
        module = importlib.import_module(f"cases.table_delivery.{case}")
        sizes[case] = len(json.dumps(module.ground_truth()[0])) / 4
    sizes_file.write_text(json.dumps(sizes, indent=1))


def outcomes(suffix, arm, case):
    passed = total = 0
    for run in Path(f"experiments/x1-b1-{suffix}-{arm}/runs/{case}").glob("*/*/run.json"):
        total += 1                                   # a run without a verdict counts as a failure
        verdict_file = run.with_name("programmatic_verification.json")
        if not verdict_file.exists():
            continue
        turn = json.loads(verdict_file.read_text())["conversations"][0]["turns"][0]
        if turn.get("status") != "scored":
            continue
        verdict = turn.get("protocol_repair_verification") or turn["programmatic_verification"]
        passed += int(bool(verdict.get("success")))
    if total > REPEATS:
        raise SystemExit(f"{suffix} {arm} {case}: {total} runs stored, {REPEATS} planned")
    return passed, REPEATS, REPEATS - total


for suffix in sys.argv[2:]:
    tally = {arm: defaultdict(lambda: [0, 0]) for arm in ARMS}
    missing = defaultdict(list)
    per_bin = defaultdict(int)
    for case in cases:
        ratio = sizes[case] / CAP
        index = next(i for i, (low, high) in enumerate(BINS) if low <= ratio < high)
        per_bin[index] += 1
        for arm in ARMS:
            passed, total, absent = outcomes(suffix, arm, case)
            if absent:
                missing[arm].append(f"{case} x{absent}")
            tally[arm][index][0] += passed; tally[arm][index][1] += total
    print(f"== {suffix}   payload/cap" + "".join(f"{a:>22}" for a in ARMS) + "   cases")
    for i, (low, high) in enumerate(BINS):
        label = f"{low:g}-{high:g}" if high < 1e9 else f">={low:g}"
        row = f"{label:>20}"
        for arm in ARMS:
            passed, total = tally[arm][i]
            row += f"{passed/total:>14.3f} ({passed:3}/{total:3})" if total else f"{'-':>22}"
        print(row + f"{per_bin[i]:>8}")
    above = [sum(tally[a][i][k] for i in (3, 4, 5)) for a in ("codeblock", "json_exec") for k in (0, 1)]
    print(f"   text arms above ratio 1: codeblock {above[0]}/{above[1]}, json_exec {above[2]}/{above[3]}")
    for arm, names in missing.items():
        print(f"   planned runs never stored, counted as failures: {arm}: {', '.join(names)}")
