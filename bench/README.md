# bench — Q4 (capability-matched ablation) and Q5 (handoff between agents)

Agents answer financial-analysis cases by running Python over data tables; each case is scored
programmatically against a reference recomputed from the same tables.

| Path | Contents |
|---|---|
| `evals/` | 117 small-output cases (Q4) |
| `cases/table_delivery/`, `cases/table_control/` | 120 and 30 table-delivery cases (Q4); each generated from its `_<task>.py` by `scripts/build_cases.py` |
| `cases/pipeline/` | Q5 pipeline study: 24 tasks × 3 sizes handed through three agents |
| `cases/rounds/`, `cases/fidelity/` | Q5 chain study: three objects and their per-hop edits |
| `core/paradigms.py`, `core/prompts.py` | the four Q4 arms and every prompt |
| `core/orchestration*.py`, `core/rounds*.py` | the Q5 orchestrator, arms and per-hop judging |
| `scripts/run.py`, `scripts/compare_paradigms.py` | Q4 runner and paired comparison |
| `scripts/run_pipeline.py`, `scripts/drivers/` | Q5 runner, arm drivers and tables |
| `scripts/measure_runtime_cost.py`, `scripts/measure_security_rules.py` | §5.2 runtime cost, §3.1.3 security checks |
| `analysis/` | Q4 success by size and by answer size |
| `analysis/efficiency.py` | LLM calls, estimated tokens and wall-clock per run for Q4/Q5: `uv run python analysis/efficiency.py <experiment dir>...` |
| `analysis/run_accounting.py` | planned, recorded and scored runs per Q4/Q5 study, unscored runs by reason: `uv run python analysis/run_accounting.py <experiment dir>...` |
| `analysis/q4_sensitivity.py` | Q4 paired differences, missing-as-failure beside scored-only: `uv run python analysis/q4_sensitivity.py <comparisons dir>` |
| `analysis/x3_omitted_paths.py` | Q5 pipeline runs whose downstream instruction lacked the file path, or skipped a worker |
| `analysis/x5_audit.py` | Q5 chain: runs intact, first attempts, re-runs, crossings by observer: `uv run python analysis/x5_audit.py --model NAME=PREFIX... ARM=SUFFIX...` |
| `cave_parity`, `file_parity`, `text_parity`, `json_parity` | the chain study's metadata-parity arms (`--study rounds --channel <arm>`; `core/orchestration.py` `Arm.parity`) |

Setup: `uv sync`, `cp models.toml.example models.toml`, data tables in `datasets/dataset_new/`
(see the top-level README). Tests: `uv run --group dev python -m pytest`.

One design check fails and is left as run: in `tests/test_pipeline_cases.py`,
`test_no_answer_is_the_same_at_every_size[treasury_securities_outstanding]` reports that one of
that task's answer fields takes the same value at all three sizes. The task's full answers still
differ between sizes (`test_every_size_is_told_apart_from_every_other` passes), so a table of the
wrong size is still detected.
