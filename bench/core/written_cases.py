"""Cases written out from a task, for the families whose cases are generated.

The benchmark's contract is one JSON spec and one module per case, which the
loader, the runner and the replayed verification all rely on. A family whose
cases are variations of one task — a question at several sizes, a conversation
under several conditions — defines the task once, and the task says what each
of its cases is: a :class:`WrittenCase`. ``scripts.build_cases`` writes them and
registers them, and is the only writer of those files.
"""

from __future__ import annotations

from dataclasses import dataclass
import textwrap


@dataclass(frozen=True)
class WrittenCase:
    name: str
    spec: dict
    module: str
    financial_domain: str


def case_spec(family: str, name: str, data_sources: tuple[str, ...], turns: list[dict]) -> dict:
    """A case's JSON spec, in the shape every case in the benchmark has."""
    return {
        "name": name,
        "module": f"cases.{family}.{name}",
        "task_family": family,
        "data_sources": list(data_sources),
        "difficulty": "medium",
        "case_type": "baseline",
        "conversations": [{"id": "main", "turns": turns}],
    }


def turn(query: str, validator: str, stores: list[str]) -> dict:
    return {"query": query, "validator": validator, "stores": stores}


def module_source(summary: str, body: str, code: str) -> str:
    """A written case module: what it asks, where the task lives, and the members it takes."""
    return f'''"""{summary}

{body}

Written by scripts.build_cases: edit the task and rebuild, never this file.
"""

{code}
'''


def quoted(text: str) -> str:
    """A question as a docstring quotes it: indented and wrapped."""
    return textwrap.fill(text, width=84, initial_indent="    ", subsequent_indent="    ")
