"""Full conversation transcripts, written under the run that cites them.

A result file records what a turn produced: the parsed code blocks, the final
response, the variables it set. That is enough to score a turn and not enough to
explain one, because the gap is everything the harness did NOT parse. A model
that wraps its code in a provider-native token instead of a markdown fence has
its code read as prose and never executed; the result file then shows a turn
that computed nothing, with no trace of the code that was written. Only the raw
dialogue distinguishes that from a model that never tried.

So the transcript is the raw dialogue: every message, in order, verbatim,
including the system prompt the turn was actually given. Self-contained on
purpose — the prompt is about 2.7 KB and repeats across scenarios, but a
transcript you have to reassemble from two files is a transcript nobody reads.

Transcripts live in a subdirectory beside the result they belong to:

    experiments/{suite}/{exp}/{name}.json
    experiments/{suite}/{exp}/transcripts/{name}_{conversation}.jsonl

A directory rather than a suffixed sibling because the count is not fixed: a
scenario holds one transcript PER CONVERSATION, and `flight_booking` alone has
three. A directory is what holds a set whose size the layout cannot predict, and
it lets the filename drop a `_transcript` suffix the directory already states.

Nothing here knows the shape of the results tree — the reference is relative to
the result's own directory, so the same module serves a flat layout and a deeply
nested one.

JSON Lines, one message per line and nothing else. No provenance header: the
result file that cites this one already records the model and the topology,
and a second copy here would be a second thing to keep in step.

Greppable and streamable, which is the point of the format: `grep -n
'"role": "assistant"' transcript.jsonl` beats parsing a megabyte of nested JSON
to find where a run went wrong.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Mapping
from typing import Any, Dict, Iterable, List, Optional

TRANSCRIPTS_DIR = "transcripts"


def message_to_dict(index: int, message: Any) -> Dict[str, Any]:
    """One message as a JSON-serialisable record, in the shape it arrived in.

    The two topologies keep different message formats and neither is projected
    onto the other. `cave_agent` messages are plain objects, so the fields are
    read by name and `type` keeps the concrete class — the difference between
    an AssistantMessage and a CodeExecutionMessage is what tells you whether
    the model's code reached the runtime.

    The OpenAI-style adapters keep dicts, which are passed through whole. That
    is deliberate: projecting them onto role and content would drop the
    `tool_calls` payload, and for a function-calling agent that payload IS the
    turn — the same evidence `type` carries on the other side.
    """
    if isinstance(message, Mapping):
        return {"index": index, **message}

    role = getattr(message, "wire_role", None) or getattr(message, "role", None)
    return {
        "index": index,
        "type": type(message).__name__,
        "role": getattr(role, "value", role),
        "content": getattr(message, "content", ""),
    }


def transcript_path(result_path: Path, conversation_id: str) -> Path:
    """Where a conversation's transcript belongs, given its result file."""
    return result_path.parent / transcript_reference(result_path, conversation_id)


def transcript_reference(result_path: Path, conversation_id: str) -> str:
    """The path a result file stores to cite its transcript.

    Relative to the result's own directory, so a reader joins the two and
    nothing has to know where that directory sits.
    """
    return f"{TRANSCRIPTS_DIR}/{result_path.stem}_{conversation_id}.jsonl"


def write_transcript(path: Path, messages: Iterable[Any]) -> None:
    """Write one conversation's messages, atomically.

    Atomic because the result file cites this path: a crash mid-write must not
    leave a result pointing at a half-transcript.
    """
    lines = [
        json.dumps(message_to_dict(index, message), ensure_ascii=False)
        for index, message in enumerate(messages)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".jsonl.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_transcript(path: Path) -> List[Dict[str, Any]]:
    """Read one back as its list of messages. The inverse of `write_transcript`."""
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def messages_of(agent: Any) -> Optional[List[Any]]:
    """An agent's conversation history, or None where the adapter has none.

    Mirrors the `Agent.runtime` contract: not every topology keeps a single
    linear history, and the caller treats absence as "nothing to record"
    rather than as an error.
    """
    return getattr(agent, "messages", None)
