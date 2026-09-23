"""Whether a recording accounts for everything the agent changed.

The two arms reach the benchmark's state by different routes, and only one of
them is narrow. The function-calling arm emits a JSON call, which is dispatched
to one bound method: what it did is what was recorded. The cave arm writes
arbitrary Python against a runtime holding those methods, so a recording is a
claim about that code rather than a transcript of it -- and the benchmark scores
the claim, replaying it onto fresh instances. A change the recording misses is
therefore scored as a change the agent never made.

Such changes are reachable by more routes than are worth enumerating, which is
why this compares states rather than looking for them. Three are known:

* `functools.wraps` leaves `__wrapped__` on each wrapper, whose `__self__` is the
  live instance, so `mkdir.__wrapped__.__self__` hands back every method
  unwrapped;
* an attribute can be assigned directly;
* a getter can hand back the instance's own container. `TradingBot`'s
  `get_order_details` returns the very dict it stores, so an agent writing
  `details["total_value"] = ...` into the value it got back has changed the
  benchmark's state through no method call at all. Found this way, on a real task,
  after the first two had been thought of.

So the check compares the state the agent actually reached against a replay of
what was recorded. Any divergence, however it happened, shows up as a difference
-- the same comparison the benchmark itself makes, so it answers in the
benchmark's own terms.

Private attributes are excluded, as upstream's checker excludes them: they carry
timestamps and random streams that differ between two runs of the same calls.
"""

from __future__ import annotations

from typing import Any

from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
    execute_multi_turn_func_call,
)

from bfcl_multiturn.benchmark import Task


def public_state(instances: dict[str, Any]) -> dict[str, dict[str, str]]:
    """What the benchmark would compare, as text it can be compared by."""
    return {name: {key: repr(value) for key, value in vars(instance).items()
                   if not key.startswith("_")}
            for name, instance in instances.items()}


def unrecorded_change(task: Task, instances: dict[str, Any],
                      calls_per_turn: list[list[list[str]]], tag: str) -> dict[str, list[str]]:
    """The attributes the agent changed that replaying its record does not.

    Empty when the recording accounts for the state, which is the case that must
    hold for a verdict to be about the agent. A non-empty result names the
    classes and attributes that differ, for a runner to report rather than score.
    """
    flat = [call for turn in calls_per_turn for step in turn for call in step]
    _, replayed = execute_multi_turn_func_call(
        flat, task.initial_config, list(task.involved_classes),
        model_name=f"{tag}_fidelity", test_entry_id=task.id,
        long_context=False, is_evaL_run=False)

    reached, reconstructed = public_state(instances), public_state(replayed)
    differing = {}
    for class_name, attributes in reached.items():
        other = reconstructed.get(class_name, {})
        names = sorted(key for key, value in attributes.items() if other.get(key) != value)
        if names:
            differing[class_name] = names
    return differing
