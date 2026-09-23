"""List the tasks of a split that a results file does not hold.

    uv run python missing.py results/<sweep>.json           # one task id per line

`run.py --resume` uses this to pick up a sweep the gateway cut short, and
`sweep.sh` counts the lines to decide whether a run is finished.
"""

import argparse
import json
import sys
from pathlib import Path


def missing_tasks(path: Path, domain: str = "telecom", split: str = "base") -> list[str]:
    """The split's task ids absent from a results file, in the split's order.

    A simulation tau2 wrote without `reward_info` counts as absent: that is what
    a task killed mid-flight leaves behind, and it has to be run again.
    """
    import tau2_cave  # noqa: F401  — points tau2 at the right data directory
    from tau2.run import load_tasks

    results = json.loads(path.read_text())
    done = {s["task_id"] for s in results["simulations"] if s.get("reward_info")}
    return [task.id for task in load_tasks(domain, split) if task.id not in done]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", type=Path)
    parser.add_argument("--domain", default="telecom")
    parser.add_argument("--task-split", default="base")
    args = parser.parse_args()

    for task_id in missing_tasks(args.results, args.domain, args.task_split):
        print(task_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
