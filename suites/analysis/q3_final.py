"""Q3 final table: cave and bash from q3v2, json from q3v3, repeats r1-r3 only."""
import json, statistics, re
from collections import defaultdict
from pathlib import Path

root = Path("experiments/token_efficiency")
STUDY = {"cave": "q3v2", "bash": "q3v2", "json": "q3v3"}
cells = defaultdict(lambda: defaultdict(list))
for directory in sorted(root.glob("q3v[23]-*")):
    m = re.fullmatch(r"(q3v[23])-(.+)-r([1-3])_(cave|json|bash)", directory.name)
    if not m or STUDY[m.group(4)] != m.group(1):
        continue
    study, model, _, arm = m.groups()
    t = dict(turns=0, passed=0, prompt=0, completion=0, steps=0)
    for result in directory.glob("*.json"):
        payload = json.loads(result.read_text())
        scenarios = payload.get("results") or payload
        for scenario in (scenarios.values() if isinstance(scenarios, dict) else scenarios):
            if isinstance(scenario, dict) and "metrics" in scenario:
                k = scenario["metrics"]
                t["turns"] += k.get("total_turns", 0); t["passed"] += k.get("successful_turns", 0)
                t["prompt"] += k.get("total_prompt_tokens", 0); t["completion"] += k.get("total_completion_tokens", 0)
                t["steps"] += k.get("total_steps", 0)
    for key, value in t.items():
        cells[(model, arm)][key].append(value)

order = ["deepseek-v3.2", "deepseek-v4-flash", "gemini-3.1-pro", "qwen3-coder-30b"]
print(f"{'model':<20}{'arm':<6}{'n':>2}{'turns':>6}{'compl.rate':>11}{'prompt':>11}{'compl':>9}{'total':>11}{'steps':>6}{'tok/compl.turn':>15}{'x cave':>8}")
for model in order:
    base = None
    for arm in ("cave", "json", "bash"):
        c = cells.get((model, arm))
        if not c: continue
        mean = {k: statistics.fmean(v) for k, v in c.items()}
        total = mean["prompt"] + mean["completion"]; per = total / mean["passed"]
        base = base or per
        print(f"{model:<20}{arm:<6}{len(c['turns']):>2}{mean['turns']:>6.0f}{mean['passed']/mean['turns']:>11.3f}"
              f"{mean['prompt']:>11,.0f}{mean['completion']:>9,.0f}{total:>11,.0f}{mean['steps']:>6.0f}{per:>15,.0f}{per/base:>8.2f}")
