"""Token Efficiency Benchmark Runner (paper Q3, Table 7).

Three multi-turn scenarios (inventory 15 turns, financial analysis 20, smart
farm 13) run under all three paradigms of Table 7 — CaveAgent, JSON function
calling, and a bash agent that persists state on the filesystem. The comparison
is token usage, reported in each result file's metrics.

Examples:
    uv run python -m scripts.token_efficiency                   # all three, model=deepseek
    uv run python -m scripts.token_efficiency -a cave -m gemini
    uv run python -m scripts.token_efficiency -b inventory_management --exp run1
"""

import argparse
import asyncio

from scripts._common import (
    get_model,
    make_bash_factory,
    make_cave_factory,
    make_json_factory,
    resolve_benchmarks,
    load_scenarios,
    output_path,
    experiment_meta,
)
from runner import evaluate

SUITE = "token_efficiency"


async def main(agent_type: str, model_name: str, exp: str, only: str, no_skip: bool, thinking: str):
    cfg = get_model(model_name)
    benchmarks = resolve_benchmarks(SUITE, only)
    exp_id = exp or model_name
    if thinking:
        exp_id = f"{exp_id}_think-{thinking}"

    runs = []
    if agent_type in ("cave", "all"):
        runs.append(("cave", make_cave_factory(cfg, thinking)))
    if agent_type in ("json", "all"):
        runs.append(("json", make_json_factory(cfg, thinking)))
    if agent_type in ("bash", "all"):
        runs.append(("bash", make_bash_factory(cfg, thinking)))

    for tag, factory in runs:
        for name in benchmarks:
            print(f"\n{'='*60}\nBenchmark: {name} ({tag})\n{'='*60}")
            scenarios = load_scenarios(SUITE, name)
            output = output_path(SUITE, name, f"{exp_id}_{tag}")
            meta = experiment_meta(cfg, exp_id=f"{exp_id}_{tag}", mode=tag, thinking=thinking)
            await evaluate(factory, scenarios, output, resume=not no_skip, meta=meta)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Token Efficiency Benchmark Runner")
    parser.add_argument("--agent", "-a", choices=["cave", "json", "bash", "all"], default="all",
                        help="Agent type: cave (Python code), json (JSON function calling), "
                             "bash (filesystem persistence), or all")
    parser.add_argument("--model", "-m", default="deepseek",
                        help="Model section name from models.toml (default: deepseek)")
    parser.add_argument("--benchmark", "-b", default=None,
                        help="Run a single benchmark by name (default: all in suite)")
    parser.add_argument("--exp", default=None,
                        help="Experiment id for output dir; reuse to resume (default: model name)")
    parser.add_argument("--no-skip", action="store_true",
                        help="Delete existing output and re-run from scratch")
    parser.add_argument("--thinking", choices=["on", "off"], default=None,
                        help="Select the model's thinking variant (needs a [model.thinking] table)")
    args = parser.parse_args()
    asyncio.run(main(args.agent, args.model, args.exp, args.benchmark, args.no_skip, args.thinking))
