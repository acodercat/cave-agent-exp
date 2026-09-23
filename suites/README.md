# suites — Q2 (stateful management) and Q3 (token efficiency)

| Path | Contents |
|---|---|
| `evals/stateful/` | Q2: type proficiency (simple, object, scientific), multi-variable (5–25), multi-turn (Smart Home, Financial Account); each `<name>.json` lists the turns, `<name>.py` holds the state and validators |
| `evals/token_efficiency/` | Q3: inventory, financial analysis and smart-farm scenarios with their tools |
| `adapters/` | CaveAgent, JSON function calling (LiteLLM) and the bash filesystem agent |
| `scripts/stateful.py`, `scripts/token_efficiency.py` | runners |
| `analysis/q3_final.py`, `analysis/q3_intervals.py` | Q3 table and paired intervals |

Setup: `uv sync`, `cp models.toml.example models.toml`. Tests: `uv run --with pytest python -m pytest`.
