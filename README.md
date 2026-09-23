# CaveAgent: Experiment Code and Results

This repository contains the code, tasks and validators behind the experiments in *CaveAgent:
Transforming LLMs into Stateful Runtime Operators*, together with links to the raw results of every
run reported in the paper. With the results archive you can recompute the paper's tables without
calling any model; with the code you can rerun the experiments themselves.

## Contents

Each directory is a separate [uv](https://docs.astral.sh/uv/) project.

| Paper section | Directory | Where to start |
|---|---|---|
| §4.1 Tau²-bench, Airline and Retail | `tau2-legacy/` | `run_cave_agent_with_tau2_<model>.py` |
| §4.1 Tau²-bench, Telecom and the Gemini 3.1 rows; §4.4 Telecom arms | `tau2/` | `run.py`, `paired.py` |
| §4.1 BFCL, single-turn | `bfcl/` | `bfcl_cave_agent_<model>.py`, `bfcl_tool_calling_<model>.py` |
| §4.1 BFCL, multi-turn | `bfcl-multiturn/` | `run.py`, `paired.py` |
| §4.2 (Q2) Stateful management | `suites/` | `scripts/stateful.py` |
| §4.3 (Q3) Token efficiency | `suites/` | `scripts/token_efficiency.py` |
| §4.4 (Q4) Capability-matched ablation | `bench/` | `scripts/run.py`, `scripts/compare_paradigms.py` |
| §4.5 (Q5) Handoff between agents | `bench/` | `scripts/drivers/` |
| §5.2 Runtime cost | `bench/` | `scripts/measure_runtime_cost.py` |
| Figures | `figures/` | `make_q*_figure*.py` |

Every directory has its own README with more detail.

## Results and data

Two archives are kept outside Git because of their size:

- **Results** — [`caveagent-results.tar.gz`](https://drive.google.com/file/d/1z079EPEkhv0jLGFiEYrgk0iageR2rVEe/view?usp=sharing)
  (359 MB, SHA-256 `5402c50ca5084d6e5297a0aa4eb782cf146f924cfa232c82f2814775d6f4d736`).
  The per-run outputs of every experiment in the paper, laid out like this repository. Extract it
  at the repository root with `tar -xzf caveagent-results.tar.gz`, and each set of results ends up
  next to the code that reads it. The per-run outputs of Q2 were not kept.
- **Data** — [`caveagent-data.tar.gz`](https://drive.google.com/file/d/1KguVRReHF46tJYvneozdxIjaEXWZliCE/view?usp=sharing)
  (1.2 GB, SHA-256 `de79800b20523ff9fd3fb176e4830bb7171c4684a19cc1f2eb15955baf2a0dcf`).
  The public U.S. financial tables used by Q4 and Q5. Extract it with
  `tar -xzf caveagent-data.tar.gz -C bench`; it creates `bench/datasets/dataset_new/`.

API keys, private gateway addresses and local paths have been removed from the results.

## Setup

You need Python 3.12 and uv. Run `uv sync` in the directory you want to use.

API keys are read from environment variables. `bench/` and `suites/` take their model settings
from `models.toml`, which you create from `models.toml.example`. The τ² and BFCL scripts name the
variables they read at the top of each script. `campaign.sh` and `run_gemini31.py` also need
`GATEWAY`, an OpenAI-compatible endpoint given without `/v1`.

Both τ² directories use the upstream Tau²-bench with a small patch:

```bash
git clone https://github.com/sierra-research/tau2-bench third_party/tau2-bench
git -C third_party/tau2-bench checkout 0ed2fd8
git -C third_party/tau2-bench apply ../tau2.patch
```

The BFCL single-turn inputs in `bfcl/scenarios/` are converted from the Berkeley Function Calling
Leaderboard (Apache-2.0); the multi-turn subset comes from the `bfcl-eval` package.

To run the tests: `uv run --group dev python -m pytest` in `bench/`, and
`uv run --with pytest python -m pytest` elsewhere. Tests that need the data tables are skipped
until the data archive is extracted.

## Recomputing the tables from the results

After extracting the results archive:

```bash
# Q3 (from suites/)
python analysis/q3_final.py
python analysis/q3_intervals.py

# Q4 (from bench/)
uv run python analysis/paper_rates.py x1-b1-v1        # also x1-b1t-v1, x1-b1-qwen, ...
uv run python -m scripts.compare_paradigms --name b1 --set table_delivery --reference cave \
    --study cave=x1-b1-v1-cave --study codeblock_files=x1-b1-v1-codeblock_files \
    --study codeblock=x1-b1-v1-codeblock --study json_exec=x1-b1-v1-json_exec \
    --repeats cave=3 --repeats codeblock_files=3 --repeats codeblock=3 --repeats json_exec=3

# Q5 (from bench/)
python scripts/drivers/x3_paired.py experiments/x3-orch-deepseek cave=cave-v6 file=file-v7 text=text-v6 json=json-v6
python scripts/drivers/x5_table.py  experiments/x5-rounds-deepseek-v4-flash-oneapi cave=cave-v1 file=file-v1 text=text-v1 json=json-v1

# Tau²-bench Telecom (from tau2/)
uv run python paired.py --model deepseek-v4-flash

# BFCL multi-turn (from bfcl-multiturn/)
uv run python paired.py --model <model>
```

`bench/experiments/README.md` in the results archive explains how its directory names map to
models and arms.

## Rerunning the experiments

Each study writes to `experiments/` or `results/` inside its own directory and skips runs it has
already stored, so an interrupted run can simply be started again.

Q2 and Q3, from `suites/`:

```bash
uv run python -m scripts.stateful -m <model> --exp <name>
uv run python -m scripts.token_efficiency -a cave -m <model> --exp q3v2-<model>-r1   # same for -a bash
uv run python -m scripts.token_efficiency -a json -m <model> --exp q3v3-<model>-r1   # r1 to r3
```

Q4, from `bench/`. The case sets are `evals/` (117 small-output cases), `cases/table_delivery/`
(120) and `cases/table_control/` (30). The arms are `cave` (CaveAgent), `codeblock_files`
(Code→file), `codeblock` (Code→text) and `json_exec` (JSON→text). Each case is run three times;
pass `--no-skip` for the second and third run.

```bash
cases() { uv run python -c "import json,sys; print(' '.join(k for k,v in json.load(open('benchmarks.json'))['cases'].items() if v.startswith(sys.argv[1])))" "$1"; }
uv run python -m scripts.run --model <model> --paradigm cave --experiment x1-b1-v1-cave \
    --case $(cases cases/table_delivery/) --score-inline
```

Q5, from `bench/`. The arms are `cave`, `file`, `text` and `json`, plus `file_shared` in the chain
study at depth 8.

```bash
scripts/drivers/x3_arm.sh <model> <arm>    # pipeline study, 216 runs per arm
scripts/drivers/x5_arm.sh <model> <arm>    # chain study, 27 runs per arm
```

Tau²-bench. In `tau2-legacy/`, run `uv run python run_cave_agent_with_tau2_<model>.py`; its
function-calling baseline is tau2's own agent (`uv run tau2 run --domain <airline|retail> --agent
llm_agent --agent-llm <model> ...`). In `tau2/`, run `uv run python run.py --domain telecom --agent
<cave_agent|llm_agent|json_exec_agent> --model <model> --base-url <url>`, or `./campaign.sh` for
the full sweep.

BFCL. In `bfcl/`, run `uv run python bfcl_cave_agent_<model>.py` and
`uv run python bfcl_tool_calling_<model>.py`. In `bfcl-multiturn/`, run
`uv run python run.py --arm <cave|fc> --model <model> --base-url <url> --run 1`.

The figure scripts in `figures/` contain the plotted values directly; run them with
`uv run --with matplotlib python figures/make_q5_figure.py`.
