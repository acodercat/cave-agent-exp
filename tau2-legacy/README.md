# tau2-legacy — Tau²-bench Airline and Retail (six models)

The harness that produced the Airline and Retail results, with the CaveAgent 0.5.0 library it
ran (`cave_agent/`, including the changes made for these runs).

- `run_cave_agent_with_tau2_<model>.py`: CaveAgent on both domains for one model.
- `adapters/`, `core/`: the tau2 agent adapter and conversation recording.
- The function-calling baseline is tau2's own agent: `uv run tau2 run --domain <domain>
  --agent llm_agent --agent-llm <model> --user-llm <model> --num-trials 1`.

Needs the patched tau2 clone in `../third_party/tau2-bench` (top-level README).
