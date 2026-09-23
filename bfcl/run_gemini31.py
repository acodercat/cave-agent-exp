"""BFCL with gemini-3.1-pro-preview, for R1 #7.

Q3 had to use gemini-3.1-pro-preview once gemini-3-pro-preview was retired;
this repeats the Q1 BFCL runs on the new model. Everything else is kept as it
was for the Gemini 3 Pro rows — the same adapters, prompts, temperature 1.0 and
low thinking, on Gemini's native API — so the model is the only change. The
model is reached through the external gateway's native Gemini endpoint.

    EXTERNAL_API_KEY=... uv run python run_gemini31.py cave_agent --run 1
    EXTERNAL_API_KEY=... uv run python run_gemini31.py tool_calling --run 1 --category simple

Results land in results/<paradigm>/gemini-3.1-pro-preview_run_<n>/, one JSONL
file per category. A run that stops partway, or loses scenarios to connection
errors, is completed by starting it again: `evaluate` skips scenarios already
in the file.

Categories run one after another within a process. CaveAgent's call tracker
hooks `sys.setprofile`, which is process-wide, so two categories sharing a
process would record each other's calls; run categories in parallel as
separate processes instead.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

from adapters.cave_agent_adapter import CaveAgentFactory
from adapters.litellm_adapter import LitellmAgentFactory, LitellmModel
from cave_agent.models import GeminiModel
from evaluation import evaluate

MODEL_ID = "gemini-3.1-pro-preview"
GATEWAY = os.environ["GEMINI_BASE_URL"]  # an OpenAI/Gemini-compatible gateway
CATEGORIES = ("simple", "multiple", "parallel", "parallel_multiple")


def agent_factory(paradigm: str, api_key: str):
    """The same model settings the Gemini 3 Pro runs used, pointed at the gateway."""
    if paradigm == "cave_agent":
        # google-genai appends /v1beta itself
        return CaveAgentFactory(GeminiModel(model_id=MODEL_ID, api_key=api_key, base_url=GATEWAY,
                                            temperature=1))
    # litellm's gemini provider expects the versioned base; the adapter sets low reasoning
    return LitellmAgentFactory(LitellmModel(model_id=MODEL_ID, api_key=api_key, provider="gemini",
                                            base_url=f"{GATEWAY}/v1beta", temperature=1))


async def run_category(category: str, paradigm: str, out_dir: Path, api_key: str, limit: int | None):
    ground_truths = json.loads(Path(f"scenarios/BFCL_v3_{category}_ground_truth.json").read_text())
    await evaluate(agent_factory(paradigm, api_key), ground_truths[:limit], str(out_dir / f"BFCL_v3_{category}.json"))


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paradigm", choices=("cave_agent", "tool_calling"))
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--category", choices=CATEGORIES, action="append",
                        help="repeatable; all four by default")
    parser.add_argument("--limit", type=int, help="first N scenarios per category, for a pilot")
    parser.add_argument("--out", type=Path, help="results directory (default: results/<paradigm>/<model>_run_<n>)")
    args = parser.parse_args()

    api_key = os.environ["GEMINI_API_KEY"]
    out_dir = args.out or Path("results") / args.paradigm / f"{MODEL_ID}_run_{args.run}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for category in args.category or CATEGORIES:
        await run_category(category, args.paradigm, out_dir, api_key, args.limit)


if __name__ == "__main__":
    asyncio.run(main())
