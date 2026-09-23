"""Success per delivery size, a run without a verdict counted as a failure (3 runs per case)."""
import json, re, sys
from collections import defaultdict
from pathlib import Path
ARMS = ["cave", "codeblock_files", "codeblock", "json_exec"]
ORDER = ["10", "100", "250", "500", "1k", "5k", "10k"]

def passed(run: Path) -> bool:
    verdict = run.with_name("programmatic_verification.json")
    if not verdict.exists(): return False
    turn = json.loads(verdict.read_text())["conversations"][0]["turns"][0]
    if turn.get("status") != "scored": return False
    v = turn.get("protocol_repair_verification") or turn["programmatic_verification"]
    return bool(v.get("success"))

for study in sys.argv[1:]:
    arms = [a for a in ARMS if Path(f"experiments/{study}-{a}").is_dir()]
    table = {a: defaultdict(lambda: [0, 0]) for a in arms}
    for a in arms:
        for case in Path(f"experiments/{study}-{a}/runs").iterdir():
            size = case.name.rsplit("_", 1)[1] if re.search(r"_(\d+k?)$", case.name) else "all"
            runs = list(case.glob("*/*/run.json"))
            for key in (size, "all") if size != "all" else ("all",):
                table[a][key][0] += sum(passed(r) for r in runs); table[a][key][1] += max(len(runs), 3)
    print(f"== {study}"); print(f"{'size':>6}" + "".join(f"{a:>22}" for a in arms))
    for size in [s for s in ORDER if s in table[arms[0]]] + ["all"]:
        print(f"{size:>6}" + "".join(f"{table[a][size][0]/table[a][size][1]:>13.3f} ({table[a][size][0]:3}/{table[a][size][1]:3})" for a in arms))
