# CaveAgent: experiment code

Code, task definitions and validators for the experiments in the paper. Each directory is a
self-contained [uv](https://docs.astral.sh/uv/) project. Run outputs are distributed separately (see Results).

| Paper | Directory | Entry point |
|---|---|---|
| §4.1 Tau²-bench Airline / Retail | `tau2-legacy/` | `run_cave_agent_with_tau2_<model>.py` |
| §4.1 Tau²-bench Telecom, Gemini 3.1 rows; §4.4 Telecom arms | `tau2/` | `run.py`, `campaign.sh`, `paired.py` |
| §4.1 BFCL single-turn | `bfcl/` | `bfcl_cave_agent_<model>.py`, `bfcl_tool_calling_<model>.py` |
| §4.1 BFCL multi-turn | `bfcl-multiturn/` | `run.py`, `paired.py` |
| §4.2 (Q2) stateful management | `suites/` | `scripts/stateful.py` |
| §4.3 (Q3) token efficiency | `suites/` | `scripts/token_efficiency.py`, `analysis/q3_*.py` |
| §4.4 (Q4) capability-matched ablation | `bench/` | `scripts/run.py`, `scripts/compare_paradigms.py`, `analysis/` |
| §4.5 (Q5) handoff between agents | `bench/` | `scripts/drivers/x3_*`, `scripts/drivers/x5_*` |
| §5.2 runtime cost | `bench/` | `scripts/measure_runtime_cost.py` |
| Figures | `figures/` | `make_q{3,4,5}_figure*.py` |

## Setup

Python 3.12 and `uv`. In each directory: `uv sync`. Tests: `uv run --group dev python -m pytest`
(`bench/`), `uv run --with pytest python -m pytest` (others).

**API keys** are read from the environment only. `bench/` and `suites/` read models from
`models.toml`: copy `models.toml.example`, where keys appear as `${VAR}`. The τ² and BFCL
scripts read `*_API_KEY` variables named in each script; `GATEWAY` (without `/v1`) is the
OpenAI-compatible endpoint used by `campaign.sh` and `run_gemini31.py`.

**Tau²-bench** (both `tau2*` directories) is the upstream benchmark with one patch:

```bash
git clone https://github.com/sierra-research/tau2-bench third_party/tau2-bench
git -C third_party/tau2-bench checkout 0ed2fd8
git -C third_party/tau2-bench apply ../tau2.patch
```

**Data tables for Q4 and Q5** (1.2 GB, public U.S. financial datasets): download
`caveagent-data.tar.gz` from [Google Drive](https://drive.google.com/file/d/1KguVRReHF46tJYvneozdxIjaEXWZliCE/view?usp=sharing) (SHA-256
`de79800b20523ff9fd3fb176e4830bb7171c4684a19cc1f2eb15955baf2a0dcf`) and run
`tar -xzf caveagent-data.tar.gz -C bench`, which creates `bench/datasets/dataset_new/`. Tests that
need the tables are skipped without them.

**Results.** The per-run outputs behind the paper's numbers are in `caveagent-results.tar.gz`
([Google Drive](https://drive.google.com/file/d/1z079EPEkhv0jLGFiEYrgk0iageR2rVEe/view?usp=sharing), 359 MB, SHA-256
`5402c50ca5084d6e5297a0aa4eb782cf146f924cfa232c82f2814775d6f4d736`). Extracted at the repository
root (`tar -xzf caveagent-results.tar.gz`), each result lands beside the code that reads it; its
README lists what is where.

**BFCL v3** single-turn inputs in `bfcl/scenarios/` are converted from the Berkeley Function
Calling Leaderboard (Apache-2.0). The multi-turn subset is read from the `bfcl-eval` package.

## Running

Every study writes to `experiments/` (or `results/`) inside its directory, and skips runs already
stored, so an interrupted command can be repeated.

**Q2 and Q3** (`suites/`):

```bash
uv run python -m scripts.stateful -m <model> --exp <id>
uv run python -m scripts.token_efficiency -a cave -m <model> --exp q3v2-<model>-r1   # and -a bash
uv run python -m scripts.token_efficiency -a json -m <model> --exp q3v3-<model>-r1   # r1-r3 for three runs
python analysis/q3_final.py && python analysis/q3_intervals.py
```

**Q4** (`bench/`). Case sets: `evals/` (117 small-output cases), `cases/table_delivery/` (120),
`cases/table_control/` (30). Arms: `cave` (CaveAgent), `codeblock_files` (Code→file),
`codeblock` (Code→text), `json_exec` (JSON→text). Three runs per case; add `--no-skip` to the
second and third.

```bash
cases() { uv run python -c "import json,sys; print(' '.join(k for k,v in json.load(open('benchmarks.json'))['cases'].items() if v.startswith(sys.argv[1])))" "$1"; }
uv run python -m scripts.run --model <model> --paradigm cave --experiment x1-b1-v1-cave \
    --case $(cases cases/table_delivery/) --score-inline
uv run python -m scripts.compare_paradigms --name b1 --set table_delivery --reference cave \
    --study cave=x1-b1-v1-cave --study codeblock_files=x1-b1-v1-codeblock_files \
    --study codeblock=x1-b1-v1-codeblock --study json_exec=x1-b1-v1-json_exec \
    --repeats cave=3 --repeats codeblock_files=3 --repeats codeblock=3 --repeats json_exec=3
uv run python analysis/paper_rates.py x1-b1-v1
uv run python analysis/payload_gt.py analysis/payload_sizes_gt.json v1
```

**Q5** (`bench/`). Arms: `cave`, `file`, `text`, `json` (and `file_shared`, chain study, depth 8).

```bash
scripts/drivers/x3_arm.sh <model> <arm>              # pipeline study, 216 runs per arm
scripts/drivers/x5_arm.sh <model> <arm>              # chain study, 27 runs per arm
uv run python scripts/drivers/x3_table.py  experiments/x3-orch-<model> cave=cave file=file text=text json=json --planned 216
uv run python scripts/drivers/x3_paired.py experiments/x3-orch-<model> cave=cave file=file text=text json=json
uv run python scripts/drivers/x5_table.py  experiments/x5-rounds-<model> cave=cave file=file text=text json=json
```

**Tau²-bench.** `tau2-legacy/`: `uv run python run_cave_agent_with_tau2_<model>.py`; its
function-calling baseline is tau2's own agent, `uv run tau2 run --domain <airline|retail>
--agent llm_agent --agent-llm <model> ...`. `tau2/`: `uv run python run.py --domain telecom
--agent cave_agent|llm_agent|json_exec_agent --model <model> --base-url <url>`, or
`GATEWAY=... ./campaign.sh`; paired intervals with `paired.py`.

**BFCL.** `bfcl/`: `uv run python bfcl_cave_agent_<model>.py` and
`bfcl_tool_calling_<model>.py`. `bfcl-multiturn/`: `uv run python run.py --arm cave|fc
--model <model> --base-url <url> --run 1`, then `paired.py --model <model>`.

**Figures**: `uv run --with matplotlib python figures/make_q5_figure.py` (values are typed in
from the paper's tables).
