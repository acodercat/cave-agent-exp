"""Q3 paired intervals: each baseline against CaveAgent, per model.

Every paradigm runs the same 24 conversations (48 turns). Turns of one
conversation share state, so the conversation is the unit that is resampled:
10,000 paired bootstrap resamples of conversations, each carrying the mean of
its three runs. Reported for the success-rate difference (baseline - CaveAgent,
in points) and for the ratio of tokens per completed turn (baseline / CaveAgent).

After the table (Table 11's intervals, unchanged) come the turns that raised
instead of completing, and a sensitivity analysis that drops every conversation
holding one from all arms and recomputes the tokens-per-completed-turn ratios.
An errored turn is recorded with zero tokens and counted as a failed turn, so
it lowers the arm's success count and adds nothing to its tokens; dropping its
conversation removes it from both sides of the ratio. The only one in the Q3
runs: Gemini 3.1 Pro, CaveAgent, inventory_management/west_coast_emergency, the
second turn (index 1), RuntimeError model_error, in all three runs. The
sensitivity draws restart from the same seed, so the table above is unaffected.

    cd suites && python analysis/q3_intervals.py [--root <experiments/token_efficiency>] [--out f.json]
"""
import argparse, json, random, re
from collections import defaultdict
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--root", type=Path, default=Path("experiments/token_efficiency"))
parser.add_argument("--out", type=Path, help="also write the intervals and the sensitivity as JSON")
options = parser.parse_args()
root = options.root
STUDY = {"cave": "q3v2", "bash": "q3v2", "json": "q3v3"}
MODELS = ["deepseek-v3.2", "deepseek-v4-flash", "gemini-3.1-pro", "qwen3-coder-30b"]
DRAWS = 10_000

# (model, arm) -> conversation key -> [turns, passed, tokens] summed over the three runs
cells = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
errored = []  # turns that raised: (model, arm, run, scenario, conversation, turn index, error, tokens)
for directory in sorted(root.glob("q3v[23]-*")):
    m = re.fullmatch(r"(q3v[23])-(.+)-r([1-3])_(cave|json|bash)", directory.name)
    if not m or STUDY[m.group(4)] != m.group(1):
        continue
    _, model, run, arm = m.groups()
    for result in directory.glob("*.json"):
        for name, scenario in json.loads(result.read_text())["results"].items():
            for conversation in scenario["conversations"]:
                cell = cells[(model, arm)][(name, conversation["id"])]
                for index, turn in enumerate(conversation["turns"]):
                    if turn.get("error"):
                        errored.append((model, arm, int(run), name, conversation["id"], index,
                                        turn["error"], turn["metrics"]["total_tokens"]))
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


SEED = 20260921
random.seed(SEED)
report = {"seed": SEED, "draws": DRAWS, "intervals": [], "errored_turns": [], "sensitivity": []}
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
        report["intervals"].append({"model": model, "baseline": arm, "conversations": len(keys),
                                    "success_diff": [point[0], d_lo, d_hi],
                                    "token_ratio": [point[1], r_lo, r_hi]})

print(f"\nerrored turns (counted as failed, recorded with the tokens shown): {len(errored)}")
for model, arm, run, name, conversation, index, error, tokens in sorted(errored):
    print(f"  {model} {arm} r{run} {name}/{conversation} turn index {index}: {error} ({tokens} tokens)")
    report["errored_turns"].append({"model": model, "arm": arm, "run": run, "scenario": name,
                                    "conversation": conversation, "turn_index": index,
                                    "error": error, "total_tokens": tokens})

# Sensitivity: conversations holding an errored turn are dropped from every arm
# of that model, then the point estimates and intervals are recomputed.
dropped = defaultdict(set)
for model, _, _, name, conversation, *_ in errored:
    dropped[model].add((name, conversation))
random.seed(SEED)
print("\nsensitivity: conversations with an errored turn dropped from all arms")
print(f"{'model':<20}{'baseline':<6}{'convs':>6}{'success diff (pts)':>24}{'tok/turn ratio':>24}"
      f"{'cave tok/turn':>15}{'baseline':>10}")
for model in MODELS:
    if not dropped[model]:
        continue
    base = cells[(model, "cave")]
    keys = sorted(set(base) - dropped[model])
    for arm in ("json", "bash"):
        other = cells[(model, arm)]
        point = statistics(keys, base, other)
        draws = [statistics(random.choices(keys, k=len(keys)), base, other) for _ in range(DRAWS)]
        d_lo, d_hi = interval([d[0] for d in draws]); r_lo, r_hi = interval([d[1] for d in draws])
        per = lambda cell: sum(cell[k][2] for k in keys) / sum(cell[k][1] for k in keys)
        print(f"{model:<20}{arm:<6}{len(keys):>6}{point[0]:>+8.1f} [{d_lo:+6.1f}, {d_hi:+6.1f}]"
              f"{point[1]:>8.2f} [{r_lo:5.2f}, {r_hi:5.2f}]{per(base):>15,.0f}{per(other):>10,.0f}")
        report["sensitivity"].append({"model": model, "baseline": arm, "conversations": len(keys),
                                      "dropped": sorted(map(list, dropped[model])),
                                      "success_diff": [point[0], d_lo, d_hi],
                                      "token_ratio": [point[1], r_lo, r_hi],
                                      "tokens_per_completed_turn": {"cave": per(base), arm: per(other)}})
if options.out:
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(report, indent=2) + "\n")
