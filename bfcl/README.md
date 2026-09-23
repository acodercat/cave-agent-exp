# bfcl — BFCL v3 single-turn categories

`simple`, `multiple`, `parallel` and `parallel_multiple` (1,000 entries), CaveAgent against native
function calling.

- `bfcl_cave_agent_<model>.py`, `bfcl_tool_calling_<model>.py`: one model, one paradigm, all
  four categories; `run_gemini31.py`: Gemini 3.1 Pro under both paradigms.
- `scenarios/`: the four categories converted from BFCL v3 (Apache-2.0): ground truth plus the
  function definitions of each entry.
- `evaluation.py`, `core/validation.py`: a response is correct if every expected call is matched
  by name and arguments; both paradigms use the same checker.
- `cave-agent/`: the CaveAgent 0.5.1 library these runs used.

Setup: `PROJECT_ROOT=$PWD uv sync`.
