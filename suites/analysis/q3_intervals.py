"""Q3 paired intervals: each baseline against CaveAgent, per model.

Every paradigm runs the same 24 conversations (48 turns). Turns of one
conversation share state, so the conversation is the unit that is resampled:
10,000 paired bootstrap resamples of conversations, each carrying the mean of
its three runs. Reported for the success-rate difference (baseline - CaveAgent,
in points) and for the ratio of tokens per completed turn (baseline / CaveAgent).

    cd suites && python analysis/q3_intervals.py
"""
import json, random, re
from collections import defaultdict
from pathlib import Path

root = Path("experiments/token_efficiency")
STUDY = {"cave": "q3v2", "bash": "q3v2", "json": "q3v3"}
MODELS = ["deepseek-v3.2", "deepseek-v4-flash", "gemini-3.1-pro", "qwen3-coder-30b"]
DRAWS = 10_000

# (model, arm) -> conversation key -> [turns, passed, tokens] summed over the three runs
cells = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
for directory in sorted(root.glob("q3v[23]-*")):
    m = re.fullmatch(r"(q3v[23])-(.+)-r([1-3])_(cave|json|bash)", directory.name)
    if not m or STUDY[m.group(4)] != m.group(1):
        continue
    _, model, _, arm = m.groups()
    for result in directory.glob("*.json"):
        for name, scenario in json.loads(result.read_text())["results"].items():
            for conversation in scenario["conversations"]:
                cell = cells[(model, arm)][(name, conversation["id"])]
                for turn in conversation["turns"]:
                    cell[0] += 1
                    cell[1] += bool(turn["success"])
                    cell[2] += turn["metrics"]["total_tokens"]


def statistics(keys, base, other):
    turns = sum(base[k][0] for k in keys)
    rate = lambda cell: sum(cell[k][1] for k in keys) / turns
    cost = lambda cell: sum(cell[k][2] for k in keys) / max(sum(cell[k][1] for k in keys), 1)
    return (rate(other) - rate(base)) * 100, cost(other) / cost(base)


def interval(values):
    values = sorted(values)
    return values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]


random.seed(20260921)
print(f"{'model':<20}{'baseline':<6}{'success diff (pts)':>30}{'tokens/completed turn ratio':>34}")
for model in MODELS:
    base = cells[(model, "cave")]
    keys = sorted(base)
    assert len(keys) == 24, (model, len(keys))
    for arm in ("json", "bash"):
        other = cells[(model, arm)]
        assert sorted(other) == keys, (model, arm)
        point = statistics(keys, base, other)
        draws = [statistics(random.choices(keys, k=len(keys)), base, other) for _ in range(DRAWS)]
        d_lo, d_hi = interval([d[0] for d in draws]); r_lo, r_hi = interval([d[1] for d in draws])
        print(f"{model:<20}{arm:<6}{point[0]:>+10.1f} [{d_lo:+6.1f}, {d_hi:+6.1f}]"
              f"{point[1]:>14.2f} [{r_lo:5.2f}, {r_hi:5.2f}]")
