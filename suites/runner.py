"""Main evaluation runner for agents.

This module provides the evaluate function which can run any agent
implementation that conforms to the AgentFactory interface.
"""

import json
from datetime import datetime
import logging
import importlib
import os
import warnings
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.errors import BenchmarkSpecificationError
from core.evaluator import Evaluator
from core.results import result_has_infra_error
from core.transcripts import (
    transcript_path,
    transcript_reference,
    write_transcript,
)
from core.types import (
    Conversation,
    ConversationResult,
    ScenarioMetrics,
    ScenarioResult,
    TurnMetrics,
    TurnResult,
)
from core.agent import AgentFactory

logger = logging.getLogger(__name__)


# Suppress Pydantic serialization warnings from LiteLLM response objects
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


def _json_fallback(obj: Any) -> str:
    """Bounded repr for values json.dump can't serialize.

    Result payloads are diagnostics; a truncated repr is far better than a
    TypeError that aborts the incremental save after the file was truncated.
    """
    r = repr(obj)
    return r if len(r) <= 2000 else r[:2000] + "…[truncated]"


def _make_error_result(scenario: Dict[str, Any], error_msg: str) -> ScenarioResult:
    """Build a failed ScenarioResult for a scenario that crashed on an
    infrastructure error (bad module import, API/DB failure).

    Lets the run continue past one broken scenario instead of aborting the
    whole pass; the failure is recorded (every turn failed, `error` set) so
    it shows up in the output rather than silently vanishing.
    """
    conv_results = []
    total_turns = 0
    for conv in scenario.get("conversations", []):
        turns = conv.get("turns", [])
        total_turns += len(turns)
        turn_results = [
            TurnResult(
                query=t.get("query", ""),
                reference_response="",
                response="",
                expected_calls=[],
                actual_calls=[],
                validation_errors=[f"Infrastructure error: {error_msg}"],
                metrics=TurnMetrics(),
                success=False,
                error=error_msg,
            )
            for t in turns
        ]
        conv_results.append(ConversationResult(
            id=conv.get("id", "unknown"),
            turns=turn_results,
        ))

    return ScenarioResult(
        scenario=scenario.get("name", "unknown"),
        conversations=conv_results,
        metrics=ScenarioMetrics(total_turns=total_turns, failed_turns=total_turns),
    )


def _load_results(path: Path) -> Dict[str, Any]:
    """The scenario map inside an existing result file, any generation.

    Three on-disk generations are readable: the current
    ``{"metrics": ..., "results": ...}`` layout, the brief ``_meta`` interim,
    and the original flat ``{scenario: ...}`` dict.
    """
    with open(path) as f:
        loaded = json.load(f)
    if isinstance(loaded.get("results"), dict):
        return loaded["results"]
    loaded.pop("_meta", None)
    return loaded


def _file_metrics(results: Dict[str, Any], meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The file-level ``metrics`` header: provenance plus a rollup.

    Shares the lab's result-file layout (see AtmosCoder-Bench): one block
    answering both "what produced this" and "how did it go", with token usage
    nested. Recomputed from the stored scenarios on every save, so a resumed
    file's rollup always matches its contents.
    """
    total = passed = failed = errors = 0
    prompt_tokens = completion_tokens = total_tokens = 0
    for scenario in results.values():
        m = scenario.get("metrics", {})
        total += m.get("total_turns", 0)
        passed += m.get("successful_turns", 0)
        failed += m.get("failed_turns", 0)
        prompt_tokens += m.get("total_prompt_tokens", 0)
        completion_tokens += m.get("total_completion_tokens", 0)
        total_tokens += m.get("total_tokens", 0)
        for conversation in scenario.get("conversations", []):
            errors += sum(1 for turn in conversation.get("turns", []) if turn.get("error"))

    return {
        **(meta or {}),
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    }


def _write_transcripts(results: ScenarioResult, output_path: Path) -> None:
    """Persist each conversation's dialogue and record its path on the result.

    Mutates `results` so the reference reaches `to_dict()`. A conversation whose
    agent kept no history — the contract allows it — is simply skipped.
    """
    for conversation in results.conversations:
        if not conversation.messages:
            continue
        write_transcript(
            transcript_path(output_path, conversation.id), conversation.messages
        )
        conversation.transcript = transcript_reference(output_path, conversation.id)


async def evaluate(
    agent_factory: AgentFactory,
    scenarios: List[Dict[str, Any]],
    output_file: str,
    resume: bool = True,
    meta: Optional[Dict[str, Any]] = None,
) -> List[ScenarioResult]:
    """
    Run evaluation on scenarios and save results.

    Supports incremental evaluation - skips already evaluated scenarios
    and resumes from where it left off.

    Args:
        agent_factory: Factory for creating agent instances
        scenarios: List of scenario definitions with expected outputs
        output_file: Path to save/load evaluation results (JSON format)
        resume: When True (default), load any existing output file and skip
            scenarios already in it. When False, ignore it and re-run all.
        meta: Provenance merged into the file's "metrics" header — model
            fingerprint, mode, thinking axis. The filename used to be the
            only carrier of any of this, and filenames are what gets renamed.
            The rollup half of the header (totals, accuracy, usage) is
            computed here at save time.

    Returns:
        List of ScenarioResult objects for all evaluated scenarios

    Example:
        >>> from cave_agent.models import LiteLLMModel
        >>> from adapters import CaveAgentFactory
        >>>
        >>> model = LiteLLMModel(model_id="gpt-4o", ...)
        >>> factory = CaveAgentFactory(model)
        >>> scenarios = json.load(open("evals/function_calling/weather.json"))
        >>> results = await evaluate(factory, scenarios, "experiments/output.json")

    Example with LiteLLM (JSON function calling):
        >>> from adapters import LitellmAgentFactory, LitellmModel
        >>>
        >>> model = LitellmModel(model_id="gpt-4o", api_key="...", provider="openai")
        >>> factory = LitellmAgentFactory(model)
        >>> results = await evaluate(factory, scenarios, "experiments/output.json")
    """
    # Load existing results to resume; when resume=False, start fresh and
    # overwrite the file (already-evaluated scenarios are re-run).
    existing_results = {}
    output_path = Path(output_file)

    if resume and output_path.exists():
        existing_results = _load_results(output_path)
        logger.info(f"Loaded {len(existing_results)} existing results from {output_file}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize evaluator with the factory
    evaluator = Evaluator(agent_factory)

    total_scenarios = len(scenarios)
    logger.info(f"Starting evaluation: {total_scenarios} scenarios")

    # Collect all results for return value
    all_results: List[ScenarioResult] = []

    # Run evaluation on each scenario
    for idx, scenario in enumerate(scenarios, 1):
        scenario_name = scenario.get('name', f"scenario_{idx}")

        # Skip if already evaluated — but retry scenarios whose stored result
        # was frozen by an infrastructure error (API outage, bad import).
        # Without this, one transient failure would be permanently recorded
        # as a model failure, since resume is the default workflow here.
        existing = existing_results.get(scenario_name)
        if existing is not None and not result_has_infra_error({scenario_name: existing}):
            logger.debug(f"[{idx}/{total_scenarios}] Skipping {scenario_name} (already evaluated)")
            continue

        logger.info(f"[{idx}/{total_scenarios}] Evaluating: {scenario_name}")

        try:
            # Load tools module
            tools_module = importlib.import_module(scenario['module'])

            # Convert conversations to typed objects
            typed_conversations = [
                Conversation.from_dict(conversation)
                for conversation in scenario['conversations']
            ]

            # Run evaluation (pass scenario dict for description/instructions)
            results = await evaluator.evaluate(
                scenario_name,
                tools_module,
                typed_conversations,
                json_config=scenario  # Pass full scenario dict for description/instructions extraction
            )
        except BenchmarkSpecificationError:
            # Deterministic benchmark defect: recording it as a retryable
            # error result would make every resume re-run the same defect
            # forever. Fail loudly so it gets fixed instead.
            raise
        except Exception as e:
            # Infrastructure error (bad import, API/DB failure) — record as a
            # failed scenario and keep going instead of aborting the whole run.
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"[{idx}/{total_scenarios}] {scenario_name} crashed: {error_msg}")
            print(f"\n  ⚠ ERROR: {error_msg[:200]}")
            results = _make_error_result(scenario, error_msg)

        # Collect result
        all_results.append(results)

        # Print summary metrics
        metrics = results.metrics
        avg_steps = metrics.total_steps / metrics.total_turns if metrics.total_turns > 0 else 0
        print("\nResults:")
        print(f"  Success Rate: {metrics.success_rate:.1%} ({metrics.successful_turns}/{metrics.total_turns})")
        print(f"  Failed Turns: {metrics.failed_turns}")
        print(f"  Total Steps: {metrics.total_steps}")
        print(f"  Avg Steps/Turn: {avg_steps:.1f}")
        print("  Token Usage:")
        print(f"    Prompt Tokens: {metrics.total_prompt_tokens:,}")
        print(f"    Completion Tokens: {metrics.total_completion_tokens:,}")
        print(f"    Total Tokens: {metrics.total_tokens:,}")

        # Save results incrementally. Write-to-temp + atomic rename so a
        # serialization error or crash mid-dump can never truncate results
        # already on disk; `default=_json_fallback` keeps non-JSON values
        # (numpy scalars, DataFrames in tool-call args) from aborting the dump.
        # Write each conversation's transcript before the result that cites it,
        # so a crash between the two can only leave an unreferenced transcript —
        # never a result pointing at a file that does not exist.
        _write_transcripts(results, output_path)

        existing_results[scenario_name] = results.to_dict()
        document = {
            "metrics": _file_metrics(existing_results, meta),
            "results": existing_results,
        }
        tmp_path = output_path.with_suffix(".json.tmp")
        with open(tmp_path, 'w') as f:
            json.dump(document, f, indent=2, default=_json_fallback)
        os.replace(tmp_path, output_path)

        print(f"\nSaved to: {output_file}")
        print(f"Progress: {idx}/{total_scenarios} scenarios completed")

    # Final summary
    print(f"\n{'='*60}")
    print("EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total Scenarios: {total_scenarios}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}\n")

    return all_results
