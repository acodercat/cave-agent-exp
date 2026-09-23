"""Save every request a paradigm sends, so the prompts can be compared and published.

A paradigm comparison claims that two arms differ only in how data and outputs
cross the host boundary. That claim is about the bytes sent to the model, so it
is checked on the bytes: this runs one case under each paradigm against the live
model and writes the requests each one made.

    uv run python -m scripts.capture_requests --case flood_claim_payments_10 \\
        --paradigm cave --paradigm codeblock --out experiments/requests/x1

Each paradigm's requests land in ``<out>/<case>__<paradigm>.json``, and
``<out>/manifest.json`` records the case, the settings, the public model
fingerprint, the code commit, the data catalog digest and each file's sha256, so
a published capture can be shown to be the one a study was frozen with. The API key stays in the environment and is
never part of a recorded request: only the fields below are kept.

A file paradigm's prompt lists the table files by absolute path, so a capture
carries the paths of the machine that made it; replace that prefix before
publishing if it should not be part of the record.

The capture calls the model, so it costs what one run of the case costs per
paradigm, and its answers are as variable as any single run. It is evidence
about prompts, not about accuracy.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from pathlib import Path
import subprocess

import litellm

from config import BENCHMARKS_JSON, MODELS_TOML, PROJECT_ROOT
from core.dataset_layers import catalog_digest
from core.evaluator import evaluate_case, load_specs
from core.models import load_model
from core.paradigms import INJECTION_MODES, PARADIGMS
from core.results import atomic_write_json, utc_now


# What a recorded request keeps: everything that varies with the paradigm, and
# nothing that authenticates the caller. The manifest carries the public model
# fingerprint beside it, which names the endpoint as a result file already does.
RECORDED_FIELDS = (
    "model", "messages", "tools", "tool_choice", "stream", "stream_options",
    "temperature", "max_tokens", "extra_body",
)


def _recorder(model, requests: list[dict]):
    """Point the model's litellm at a recording wrapper around the real one."""
    acompletion = litellm.acompletion

    async def recording(**request):
        requests.append({name: request[name] for name in RECORDED_FIELDS if name in request})
        return await acompletion(**request)

    model._litellm = type("RecordingLiteLLM", (), {
        "acompletion": staticmethod(recording),
        "get_supported_openai_params": staticmethod(litellm.get_supported_openai_params),
    })()


async def capture(spec: dict, paradigms: list[str], settings: dict, model_name: str) -> dict:
    """Run the case once per paradigm; return each one's requests and its outcome."""
    captures = {}
    for name in paradigms:
        model, cfg = load_model(MODELS_TOML, model_name)
        requests: list[dict] = []
        _recorder(model, requests)
        result = await evaluate_case(model, spec, paradigm=PARADIGMS[name], **settings)
        turns = [turn for conversation in result.conversations for turn in conversation.turns]
        captures[name] = {
            "requests": requests,
            "outcome": {
                "requests_sent": len(requests),
                "turns": [
                    {"success": turn.success, "steps": turn.steps,
                     "stop_cause": turn.stop_cause, "message": turn.validation_message}
                    for turn in turns
                ],
            },
            "model": cfg.public_fingerprint(),
        }
    return captures


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _code_commit() -> str | None:
    """The commit the capture was made from, when it was made from a checkout."""
    try:
        commit = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return commit.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", required=True, help="case id from benchmarks.json")
    parser.add_argument(
        "--paradigm", action="append", dest="paradigms", choices=sorted(PARADIGMS),
        help="repeatable; every paradigm by default")
    parser.add_argument("--model", default="deepseek-v4-flash-0731")
    parser.add_argument("--out", required=True, type=Path, help="directory for the capture")
    parser.add_argument("--injection", choices=sorted(INJECTION_MODES), default="eager")
    parser.add_argument("--step-budget", type=int, default=14)
    parser.add_argument("--protocol-nudges", type=int, choices=(0, 1, 2), default=1)
    parser.add_argument("--max-exec-output", type=int, default=100_000)
    args = parser.parse_args()

    specs = {spec["name"]: spec for spec in load_specs(BENCHMARKS_JSON)}
    if args.case not in specs:
        raise SystemExit(f"no such case: {args.case}")
    paradigms = args.paradigms or sorted(PARADIGMS)
    settings = {
        "injection": args.injection, "total_step_budget": args.step_budget,
        "max_protocol_nudges": args.protocol_nudges, "max_exec_output": args.max_exec_output,
    }

    captures = asyncio.run(capture(specs[args.case], paradigms, settings, args.model))
    args.out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, capture_result in captures.items():
        path = args.out / f"{args.case}__{name}.json"
        atomic_write_json(path, {
            "case": args.case, "paradigm": name, "settings": settings,
            "requests": capture_result["requests"],
        })
        files[path.name] = _sha256(path)
        print(f"{name}: {capture_result['outcome']}")
    atomic_write_json(args.out / "manifest.json", {
        "captured_at": utc_now(), "case": args.case, "settings": settings,
        "code_commit": _code_commit(), "catalog_digest": catalog_digest(),
        "model": next(iter(captures.values()))["model"],
        "outcomes": {name: capture["outcome"] for name, capture in captures.items()},
        "sha256": files,
    })
    print(args.out / "manifest.json")


if __name__ == "__main__":
    main()
