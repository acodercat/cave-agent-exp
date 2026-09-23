"""Merge re-run tasks back into a results file.

A sweep of 114 tasks occasionally loses one to a gateway timeout or a dropped
connection, and tau2 writes the file without it. Re-running just that task
produces a second file with one simulation in it; this folds it into the first,
so one file holds the whole run rather than a main result plus a pile of
one-task patches.

    uv run python merge.py results/<sweep>.json results/<rerun>.json

A task present in both is replaced by the re-run, on the assumption that the
re-run is why you are here. The run's own settings (model, temperatures, step
budget, seed, trials, git commit) must match, or the merge is refused: silently
mixing two configurations into one file is how a result stops meaning anything.

Two kinds of difference are not treated as configuration. How a request is sent
— the api_key, redacted or absent, and the request timeout — does not change what
the model computes. And --allow-commit-change accepts a different code commit
while still holding every other setting: a sweep resumed after an unrelated fix
is the normal case for a long run, and each superseded patch keeps its own
commit on disk.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Settings that must agree for two files to describe the same run. `seed` and
# `num_trials` are included: a re-run under a different seed is a different
# sample, not a repair.
PINNED = ("user_info", "agent_info", "environment_info", "max_steps", "max_errors",
          "num_trials", "seed", "git_commit")

# llm_args keys that govern how a request is sent rather than what the model does.
TRANSPORT = ("api_key", "timeout")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _comparable(info: dict, key: str):
    """A pinned setting with its transport-only llm_args removed."""
    value = info.get(key)
    if key in ("agent_info", "user_info") and isinstance(value, dict):
        llm_args = {k: v for k, v in (value.get("llm_args") or {}).items() if k not in TRANSPORT}
        return value | {"llm_args": llm_args}
    return value


def disagreements(base: dict, patch: dict, ignore: tuple[str, ...] = ()) -> list[str]:
    """Which pinned settings differ between two result files."""
    return [key for key in PINNED
            if key not in ignore and _comparable(base["info"], key) != _comparable(patch["info"], key)]


def merge(base: dict, patch: dict) -> tuple[dict, list[str]]:
    """Return `base` with `patch`'s simulations folded in, and the task ids taken.

    Simulations are keyed by (task_id, trial), so a sweep with several trials
    per task keeps them apart.
    """
    def key(simulation: dict) -> tuple:
        return simulation["task_id"], simulation.get("trial")

    # A patch written by a run that was killed before numbering its simulations
    # still carries tau2's trial 0. Folded into a single-trial run numbered
    # otherwise, those would sit beside the run's own simulations as duplicates
    # rather than fill its gaps; take the run's number instead. Only for a patch
    # of the same run, recognised by its seed: separate runs of one experiment
    # have their own seeds and their own trial numbers, which must survive.
    base_trials = {s.get("trial") for s in base["simulations"]}
    same_run = base["info"].get("seed") == patch["info"].get("seed")
    if same_run and base["info"].get("num_trials") == 1 and len(base_trials) == 1:
        (trial,) = base_trials
        patch = patch | {"simulations": [s | {"trial": trial} for s in patch["simulations"]]}

    merged = {key(s): s for s in base["simulations"]}
    taken = []
    for simulation in patch["simulations"]:
        merged[key(simulation)] = simulation
        taken.append(simulation["task_id"])

    tasks = {t["id"]: t for t in base["tasks"]} | {t["id"]: t for t in patch["tasks"]}
    return base | {
        "tasks": sorted(tasks.values(), key=lambda t: t["id"]),
        "simulations": sorted(merged.values(), key=key),
    }, taken


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base", type=Path, help="the sweep to merge into, edited in place")
    parser.add_argument("patches", type=Path, nargs="+", help="re-run files to fold in")
    parser.add_argument("--force", action="store_true",
                        help="merge even if the runs' settings differ")
    parser.add_argument("--allow-commit-change", action="store_true",
                        help="accept a different code commit; every other setting must match")
    args = parser.parse_args()

    result = load(args.base)
    for path in args.patches:
        patch = load(path)
        differing = disagreements(result, patch,
                                  ignore=("git_commit",) if args.allow_commit_change else ())
        if differing and not args.force:
            print(f"{path.name}: settings differ from {args.base.name} ({', '.join(differing)}); "
                  f"not merged. Pass --force if the difference is immaterial.", file=sys.stderr)
            return 1
        result, taken = merge(result, patch)
        print(f"{path.name}: merged {len(taken)} task(s)")

    args.base.write_text(json.dumps(result, indent=2))
    solved = sum(1 for s in result["simulations"]
                 if s.get("reward_info") and s["reward_info"]["reward"] == 1)
    total = len(result["simulations"])
    rate = f" ({100 * solved / total:.1f}%)" if total else ""
    print(f"{args.base.name}: {total} simulations, {solved} solved{rate}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
