"""Stable experiment/run artifact contract shared by runners and scorers.

Each run is a directory. The verification verdict therefore cannot be mistaken
for a trajectory by a ``*.json`` glob, and one study can retain multiple models
and repeated invocations without overwriting earlier output.

The only supported result layout is::

    experiments/<study>/runs/<case>/<model>/<run_id>/
        run.json
        programmatic_verification.json
        transcripts/<conversation>.jsonl
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Iterator

import numpy as np

from config import EXPERIMENTS_DIR
from core.types import conversations_of


RESULT_SCHEMA = "finbench-run-v4"
RUNS_DIR = "runs"
RUN_FILE = "run.json"
VERIFICATION_FILE = "programmatic_verification.json"
AGGREGATES_DIR = "aggregates"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id(started_at: datetime | None = None) -> str:
    """Return a sortable invocation id with enough precision for retries."""
    value = started_at or datetime.now()
    return value.strftime("%Y%m%d_%H%M%S_%f")


def sanitize_component(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-_")
    if not safe:
        raise ValueError("identifier does not contain a filesystem-safe character")
    return safe


def _lossless_default(value):
    """The conversions that preserve a value; anything else can only be text."""
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def json_default(value):
    try:
        return _lossless_default(value)
    except TypeError:
        return str(value)


def unserializable_outputs(values: dict[str, Any]) -> list[str]:
    """Names that `json_default` could only store as a repr.

    Stringifying is the right fallback for writing a trajectory, but it means
    the stored text is not what the validator saw live. Replaying it would
    report a wrong value for what is really a storage limit, so the names are
    recorded and the verification channel refuses them. Derived from
    `_lossless_default` rather than restating it, so the two cannot drift.
    """
    lossy = []
    for name, value in values.items():
        try:
            json.dumps(value, default=_lossless_default)
        except (TypeError, ValueError):
            lossy.append(name)
    return sorted(lossy)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    content = json.dumps(
        payload, indent=2, ensure_ascii=False, default=json_default
    ) + "\n"
    atomic_write_text(path, content)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def result_path(
    experiment_dir: Path,
    case_name: str,
    api_model: str,
    run_id: str = "run",
) -> Path:
    """Return the trajectory marker for one case/model/invocation."""
    return (
        experiment_dir / RUNS_DIR / sanitize_component(case_name)
        / sanitize_component(api_model) / sanitize_component(run_id) / RUN_FILE
    )


def verification_path(result_file: Path) -> Path:
    """The programmatic-verification verdict next to a current run artifact."""
    if result_file.name != RUN_FILE:
        raise ValueError(f"{result_file}: expected a {RUN_FILE} artifact")
    return result_file.parent / VERIFICATION_FILE


def result_identity(result_file: Path) -> tuple[str, str, str]:
    """Return ``(case_id, model_id, run_id)`` from a current run path."""
    if result_file.name != RUN_FILE:
        raise ValueError(f"{result_file}: expected a {RUN_FILE} artifact")
    try:
        runs_index = result_file.parts.index(RUNS_DIR)
        case_name, model_id, run_id = result_file.parts[runs_index + 1:runs_index + 4]
    except (ValueError, IndexError) as error:
        raise ValueError(f"{result_file}: malformed run path") from error
    return case_name, model_id, run_id


def iter_result_files(
    experiment_dir: Path,
    case_names: set[str] | None = None,
) -> Iterator[tuple[str, Path]]:
    """Yield every current run artifact in a study."""
    if not experiment_dir.exists():
        raise FileNotFoundError(experiment_dir)
    runs_root = experiment_dir / RUNS_DIR
    if not runs_root.is_dir():
        return
    for path in sorted(runs_root.glob(f"*/*/*/{RUN_FILE}")):
        case_name, _, _ = result_identity(path)
        if not case_names or case_name in case_names:
            yield case_name, path


def latest_result_path(
    experiment_dir: Path,
    case_name: str,
    api_model: str,
) -> Path | None:
    model_dir = (
        experiment_dir / RUNS_DIR / sanitize_component(case_name)
        / sanitize_component(api_model)
    )
    candidates = sorted(model_dir.glob(f"*/{RUN_FILE}")) if model_dir.is_dir() else []
    return candidates[-1] if candidates else None


def resolve_experiment(value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = EXPERIMENTS_DIR / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(EXPERIMENTS_DIR.resolve()):
        raise ValueError("experiment must be inside experiments/")
    if not resolved.exists():
        raise FileNotFoundError(resolved)
    return resolved


def load_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != RESULT_SCHEMA
        or not isinstance(payload.get("conversations"), list)
    ):
        raise ValueError(f"{path}: invalid FinBench result payload")
    return payload


def _turn_counts(payload: dict[str, Any]) -> dict[str, int] | None:
    """Conversation id to turn count, or None when the shape is unusable."""
    conversations = payload.get("conversations")
    if not isinstance(conversations, list) or not conversations:
        return None
    counts: dict[str, int] = {}
    for conversation in conversations:
        if not isinstance(conversation, dict):
            return None
        identifier = conversation.get("id")
        turns = conversation.get("turns")
        if not isinstance(identifier, str) or not isinstance(turns, list) or not turns:
            return None
        if identifier in counts:
            return None
        counts[identifier] = len(turns)
    return counts


def result_is_complete(
    payload: dict[str, Any], expected: dict[str, Any] | None = None
) -> bool:
    """Whether this stored run answered the case, and still answers today's.

    With `expected`, the stored conversation and turn shape must still match the
    case: a case that grew a turn makes the stored run incomplete rather than
    merely stale, because the missing turn was never asked.
    """
    if payload.get("schema") != RESULT_SCHEMA:
        return False
    counts = _turn_counts(payload)
    if counts is None:
        return False
    if expected is not None:
        wanted = {
            conversation.id: len(conversation.turns)
            for conversation in conversations_of(expected)
        }
        if wanted != counts:
            return False
    for conversation in payload["conversations"]:
        for turn in conversation["turns"]:
            if not isinstance(turn, dict) or turn.get("infrastructure_error"):
                return False
            if not isinstance(turn.get("response"), str) or not isinstance(
                turn.get("outputs"), dict
            ):
                return False
    return True


def programmatic_verification(result_file: Path) -> tuple[bool | None, dict | None]:
    """Read the programmatic-verification verdict of one run.

    PV stores one verdict per turn. A case is scored only when every stored turn
    has a boolean verdict, and passes only when every turn passes.
    """
    path = verification_path(result_file)
    if path.exists():
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None, None
        conversations = payload.get("conversations")
        if isinstance(conversations, list) and conversations:
            successes = []
            for conversation in conversations:
                turns = conversation.get("turns") if isinstance(conversation, dict) else None
                if not isinstance(turns, list) or not turns:
                    return None, payload
                for turn in turns:
                    turn_verdict = (
                        turn.get("programmatic_verification")
                        if isinstance(turn, dict) else None
                    )
                    if not (
                        isinstance(turn_verdict, dict)
                        and isinstance(turn_verdict.get("success"), bool)
                    ):
                        return None, payload
                    successes.append(turn_verdict["success"])
            if successes:
                return all(successes), payload
        return None, payload
    return None, None


def experiment_summary(
    experiment_dir: Path,
    *,
    model_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    passed = failed = completed = 0
    for _, path in iter_result_files(experiment_dir):
        _, stored_model, stored_run = result_identity(path)
        if model_id and stored_model != sanitize_component(model_id):
            continue
        if run_id and stored_run != run_id:
            continue
        try:
            payload = load_result(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not result_is_complete(payload):
            continue
        completed += 1
        success, _ = programmatic_verification(path)
        passed += int(success is True)
        failed += int(success is False)
    error_paths = list((experiment_dir / RUNS_DIR).glob("*/*/*/error.json"))
    if model_id:
        error_paths = [
            path for path in error_paths
            if result_identity(path.with_name(RUN_FILE))[1] == sanitize_component(model_id)
        ]
    if run_id:
        error_paths = [path for path in error_paths if path.parent.name == run_id]
    return {
        "completed": completed,
        "pv_scored": passed + failed,
        "passed": passed,
        "failed": failed,
        "infrastructure_errors": len(error_paths),
    }
