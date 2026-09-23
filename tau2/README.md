# tau2 — Tau²-bench with CaveAgent 0.8

Telecom (all three arms, four models) and Gemini 3.1 Pro on Airline and Retail.

| Path | Contents |
|---|---|
| `run.py` | one domain, one arm: `cave_agent`, `llm_agent` (tau2's function calling) or `json_exec_agent` |
| `tau2_cave/`, `tau2_json_exec/` | the CaveAgent and JSON→code agents |
| `campaign.sh`, `sweep.sh`, `gemini31_domains.sh` | the sweeps behind the paper's runs |
| `paired.py` | task-paired intervals and sign tests |
| `bfcl_paired.py` | BFCL single-turn: per-run counts and paired differences, including the Gemini 3.1 Pro rows (reads `../bfcl/results`) |
| `merge.py`, `missing.py`, `redact.py` | fold re-run tasks into a run; list missing tasks; remove API keys from results |

Needs the patched tau2 clone in `../third_party/tau2-bench` (top-level README).
