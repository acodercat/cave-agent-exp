# bfcl-multiturn — BFCL multi_turn_base (200 tasks)

Each task is scored by the state its stateful API instances reach. Both arms get the same bound
methods, step budget and task text, and differ only in how an action is expressed.

- `run.py`: one arm (`cave` or `fc`), one model, one run.
- `bfcl_multiturn/`: arms, benchmark loading, recording and results.
- `campaign.sh`: the sweep behind the paper's runs; `paired.py`: task-paired intervals;
  `compare.py`: per-model summary.
- `uv run python paired.py --model <m> [<m> ...] --results <dir> [--errors-as-failures]`: Table 9;
  the flag counts errored task-runs as failures over 200, and errored tasks are always listed.
- `uv run python efficiency.py --results <dir>`: model steps and wall-clock per task, per model and arm.

The benchmark is read from the `bfcl-eval` package. Tests: `uv run --with pytest python -m pytest`.
