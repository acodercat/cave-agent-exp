"""What a transcript must guarantee to be worth writing.

The feature exists because a result file records what a turn produced and not
what the model actually said, and the gap is where two unexplained readings hid.
So the properties worth pinning are the ones that make a transcript usable as
evidence: it survives a round trip unchanged, it keeps the message types that
say whether code reached the runtime, and the reference a result stores resolves
from that result's own directory.
"""

import json
from pathlib import Path

import pytest

from core.transcripts import (
    message_to_dict,
    messages_of,
    read_transcript,
    transcript_path,
    transcript_reference,
    write_transcript,
)


class FakeMessage:
    """Stands in for a cave_agent message: plain object, content and role."""

    def __init__(self, content: str, role: str):
        self.content = content
        self.wire_role = role


class SystemMessage(FakeMessage):
    pass


class CodeExecutionMessage(FakeMessage):
    pass


def _result_file(tmp_path: Path) -> Path:
    run = tmp_path / "function_calling" / "an_experiment"
    run.mkdir(parents=True)
    return run / "weather_query.json"


def test_reference_resolves_from_the_results_own_directory(tmp_path):
    result = _result_file(tmp_path)
    reference = transcript_reference(result, "a_conversation")
    written = transcript_path(result, "a_conversation")

    assert result.parent / reference == written, (
        "a result stores the reference and a reader joins it to the result's "
        "directory; the two must describe the same file"
    )
    assert written.parent.name == "transcripts"
    assert written.name == "weather_query_a_conversation.jsonl"


def test_round_trip_preserves_content_and_message_type(tmp_path):
    result = _result_file(tmp_path)
    path = transcript_path(result, "conv")
    messages = [
        SystemMessage("You are an agent.\nLine two.", "system"),
        CodeExecutionMessage("```python\nx = 1\n```", "assistant"),
    ]

    write_transcript(path, messages)
    records = read_transcript(path)

    assert [r["content"] for r in records] == [m.content for m in messages]
    assert [r["type"] for r in records] == ["SystemMessage", "CodeExecutionMessage"]
    assert [r["index"] for r in records] == [0, 1], "index is the position in the dialogue"
    assert [r["role"] for r in records] == ["system", "assistant"]


def test_message_type_survives_because_it_is_the_diagnostic(tmp_path):
    """The class distinguishes code that ran from prose that only looked like it.

    A model once emitted its code wrapped in a provider-native token; the parser
    read it as prose and the result file kept no trace. `type` is what makes
    that visible, so it is not an incidental field.
    """
    record = message_to_dict(3, CodeExecutionMessage("x = 1", "assistant"))
    assert record["type"] == "CodeExecutionMessage"
    assert record["index"] == 3


def test_write_is_atomic_leaving_no_temporary_behind(tmp_path):
    result = _result_file(tmp_path)
    path = transcript_path(result, "conv")

    write_transcript(path, [SystemMessage("only message", "system")])

    assert path.exists()
    assert list(path.parent.iterdir()) == [path], (
        "a crash mid-write must not strand a .tmp file next to the transcript"
    )


def test_one_line_per_message_so_the_file_stays_greppable(tmp_path):
    result = _result_file(tmp_path)
    path = transcript_path(result, "conv")
    write_transcript(
        path,
        [
            SystemMessage("first\nspans\nlines", "system"),
            CodeExecutionMessage("second", "assistant"),
        ],
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, "embedded newlines must not become extra lines"
    assert all(json.loads(line) for line in lines)


def test_a_dict_shaped_message_is_written_through_whole():
    """Both topologies' message shapes must survive, and they differ.

    The OpenAI-style adapters keep dicts. Projecting one onto role and content
    reads the fields off an object that has none, so the record comes out
    empty and the `tool_calls` payload — the only evidence of what that agent
    did — is gone. A file of empty records is worse than no transcript,
    because it looks like one.
    """
    record = message_to_dict(
        2,
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "c1", "function": {"name": "get_weather"}}],
        },
    )

    assert record["tool_calls"][0]["function"]["name"] == "get_weather"
    assert record["role"] == "assistant"
    assert record["index"] == 2


def test_an_agent_without_history_yields_nothing_to_record():
    """Mirrors the `Agent.runtime` contract: absence is not an error."""

    class NoHistory:
        pass

    assert messages_of(NoHistory()) is None


@pytest.mark.parametrize("conversation", ["conv", "with_underscores", "x"])
def test_conversation_qualifies_the_filename(tmp_path, conversation):
    """Two conversations of one run must not collide on one path."""
    result = _result_file(tmp_path)
    assert transcript_path(result, conversation).name.endswith(
        f"_{conversation}.jsonl"
    )
