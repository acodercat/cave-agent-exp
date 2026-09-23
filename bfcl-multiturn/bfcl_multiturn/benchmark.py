"""The benchmark itself: its tasks, its stateful APIs and its verdict.

Everything here comes from the official ``bfcl-eval`` package. Nothing
reimplements an environment, so a task is scored by the same code that scores
the leaderboard.

Two facts about that package shape this module, both established by experiment
and pinned in ``tests/test_feasibility.py``:

* ``execute_multi_turn_func_call`` caches every instance in its own module
  globals and never releases one, so a second scoring under a tag it has already
  seen replays onto the state the first left behind. Every scoring therefore
  gets a tag of its own, and :func:`score` is the only place that builds one.
* That tag becomes part of a Python identifier: upstream builds an instance name
  from it, folds ``-`` ``.`` ``/`` ``:`` to ``_``, and the replay then refers to
  the instance by that name in ``eval``. A tag carrying anything else makes the
  name an invalid identifier, every replayed call fails with a syntax error, and
  both sides -- the model's and the ground truth's -- are left at the initial
  state, so they match and the task is scored **correct**. That is how a wrong
  answer becomes a right one silently; :func:`tag` asserts the identifier instead.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from bfcl_eval.constants.enums import ModelStyle
from bfcl_eval.constants.type_mappings import GORILLA_TO_OPENAPI
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import multi_turn_checker
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
    CLASS_FILE_PATH_MAPPING,
    STATELESS_CLASSES,
)
from bfcl_eval.model_handler.utils import convert_to_tool

CATEGORY = "BFCL_v4_multi_turn_base"
#: Joins the parts of a scoring tag: an underscore, which is both a valid
#: identifier character and left alone by upstream's folding.
TAG_SEPARATOR = "_"
#: The tool-document file each API class ships under; upstream names them by
#: module rather than by class.
_DOC_FILE = {class_name: module.rsplit(".", 1)[-1]
             for class_name, module in CLASS_FILE_PATH_MAPPING.items()}


@dataclass(frozen=True)
class Task:
    """One conversation: what the user says, and the state it starts from."""

    id: str
    turns: tuple[tuple[str, ...], ...]      # the user's messages, per turn
    initial_config: dict
    involved_classes: tuple[str, ...]
    ground_truth: tuple[tuple[str, ...], ...]
    #: A function the task withholds until a later turn, per miss_func; empty for base.
    missed_functions: dict[int, tuple[str, ...]]

    @property
    def turn_count(self) -> int:
        return len(self.turns)


def _read(name: str) -> list[dict]:
    lines = (files("bfcl_eval") / "data" / name).read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def tasks(category: str = CATEGORY) -> list[Task]:
    """Every task of a category, in the order the benchmark ships them."""
    answers = {row["id"]: row["ground_truth"] for row in _read(f"possible_answer/{category}.json")}
    loaded = []
    for entry in _read(f"{category}.json"):
        missed = {int(turn): tuple(names)
                  for turn, names in (entry.get("missed_function") or {}).items()}
        loaded.append(Task(
            id=entry["id"],
            turns=tuple(tuple(message["content"] for message in turn) for turn in entry["question"]),
            initial_config=entry["initial_config"],
            involved_classes=tuple(entry["involved_classes"]),
            ground_truth=tuple(tuple(turn) for turn in answers[entry["id"]]),
            missed_functions=missed,
        ))
    return loaded


def instantiate(task: Task) -> dict[str, Any]:
    """The task's APIs, seeded from its initial state.

    Built here rather than through upstream's helper because these instances are
    handed to an agent to act on, and the helper's are cached in its globals for
    the lifetime of the process.
    """
    instances = {}
    for class_name in task.involved_classes:
        module = importlib.import_module(CLASS_FILE_PATH_MAPPING[class_name])
        instance = getattr(module, class_name)()
        if class_name not in STATELESS_CLASSES:
            instance._load_scenario(copy.deepcopy(task.initial_config.get(class_name, {})))
        instances[class_name] = instance
    return instances


def methods(instances: dict[str, Any]) -> list[Callable]:
    """The bound methods those APIs expose, which are the task's tools.

    Bound, so an agent calling one acts on the instance it was handed. Ordered by
    name within each class so that two arms are given the same tools in the same
    order.
    """
    found = []
    for class_name in sorted(instances):
        instance = instances[class_name]
        for name in sorted(dir(instance)):
            if name.startswith("_"):
                continue
            attribute = getattr(instance, name)
            if callable(attribute):
                found.append(attribute)
    return found


def tool_documents(task: Task) -> list[dict]:
    """The benchmark's own JSON tool descriptions, converted as it converts them.

    Used rather than schemas derived from the methods, so the function-calling arm
    is given the tools as the benchmark defines them and not as this code would
    infer them. Ordered to match :func:`methods`.

    The conversion is upstream's own ``convert_to_tool``: the documents are
    written in the benchmark's dialect, where an object is spelled ``dict``, and
    they carry a ``response`` schema that describes a return value and is not
    part of a tool definition. Converting them here rather than by hand keeps the
    tools the benchmark's, and is what Gemini's API needs -- it rejects ``dict``
    as a type outright. ``response`` is dropped afterwards, because upstream's
    converter leaves it in place and it is not a field a tool definition has;
    Gemini rejects the request on the ``dict`` still inside it.
    """
    documented = {}
    for class_name in sorted(task.involved_classes):
        path = files("bfcl_eval") / "data" / "multi_turn_func_doc" / f"{_DOC_FILE[class_name]}.json"
        for line in path.read_text().splitlines():
            if line.strip():
                document = json.loads(line)
                documented[document["name"]] = document
    ordered = [documented[method.__name__] for method in methods(instantiate(task))
               if method.__name__ in documented]
    converted = convert_to_tool(ordered, GORILLA_TO_OPENAPI, ModelStyle.OPENAI_COMPLETIONS)
    for tool in converted:
        tool["function"].pop("response", None)
    return converted


def score(task: Task, calls_per_turn: list[list[list[str]]], tag: str) -> dict:
    """The official verdict on one conversation.

    ``calls_per_turn[turn][step]`` is the calls of one step, as source strings.
    ``tag`` distinguishes this scoring from every other one in the process; see
    the module docstring for why that is not optional.
    """
    _check_identifier(tag, task)
    return multi_turn_checker(calls_per_turn, [list(turn) for turn in task.ground_truth],
                              {"id": task.id, "initial_config": task.initial_config,
                               "involved_classes": list(task.involved_classes)},
                              CATEGORY, tag)


def tag(*parts: str) -> str:
    """A scoring tag of its own, which upstream can still build a name from.

    The parts are hashed rather than joined verbatim, because they contain the
    characters that would fold (a model id's dots and slashes) and because two
    different joins must not collapse into one key. The digest keeps the name a
    valid identifier, which is what the replay needs.
    """
    if not parts:
        raise ValueError("a tag needs at least one part")
    digest = hashlib.sha256(TAG_SEPARATOR.join(parts).encode()).hexdigest()[:16]
    return f"t{digest}"


def _check_identifier(tag: str, task: Task) -> None:
    """Refuse a tag upstream would turn into something ``eval`` cannot name.

    The failure this prevents is silent and scores wrong answers as right, so it
    is checked on every scoring rather than trusted to the tag builder.
    """
    for class_name in task.involved_classes:
        for suffix in (f"{tag}_eval", f"{tag}_ground_truth_eval"):
            name = re.sub(r"[-./:]", "_", f"{suffix}_{task.id}_{class_name}_instance")
            if not name.isidentifier():
                raise ValueError(
                    f"tag {tag!r} makes the instance name {name!r}, which is not a Python "
                    "identifier: the replay would fail on every call and score the task correct")
