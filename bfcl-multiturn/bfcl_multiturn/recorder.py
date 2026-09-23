r"""Recording what an agent did, in the form the benchmark scores.

The benchmark scores a conversation by replaying the calls it was told the agent
made, onto fresh instances, and comparing the resulting state. So the calls have
to be reported as source strings -- ``"mkdir(dir_name='temp')"`` -- and a call
the recorder misses is a call the replay never makes, which shows up as a state
mismatch rather than as an error. Two consequences:

* the wrapper is transparent to :mod:`inspect`, because cave-agent describes a
  tool to the model from its signature and docstring alone;
* arguments are rendered with :func:`repr`, which round-trips every shape the
  benchmark's own ground truth uses (strings, numbers, bools, lists, dicts);
* a space before ``(`` inside a string is written ``\x20``, to survive the
  rewriting upstream does before it replays a call. That rewriting matches
  ``\b(\w+)\s*(?=\()`` across the whole call, string literals included, and its
  ``\s*`` swallows the space: text like ``"10 shares (Status: done)"`` comes back
  as ``"10 shares(Status: done)"`` and the state no longer matches. The escape is
  the same character to Python and invisible to the regex. Upstream's own ground
  truth never trips this -- none of its 1,142 answers contain the pattern -- so
  only an agent writing free text is affected, and both arms would be.

What the recorder cannot see is state changed without going through a wrapped
method -- an attribute assigned directly, or a method reached through
``__wrapped__.__self__``. That would be scored as a wrong answer, so
:func:`bfcl_multiturn.fidelity.unrecorded_change` checks each task for it and the
runner reports it instead.
"""

from __future__ import annotations

import functools
import inspect
import re
from collections.abc import Callable
from typing import Any

#: A space that upstream's call rewriting would swallow: one before a ``(`` that
#: follows an identifier. See the module docstring.
_SWALLOWED_SPACE = re.compile(r"(\w) (\()")


def _survives_rewriting(rendered: str) -> str:
    """``repr`` output with the spaces upstream would eat written as ``\x20``."""
    while _SWALLOWED_SPACE.search(rendered):
        rendered = _SWALLOWED_SPACE.sub(r"\1\\x20\2", rendered)
    return rendered


def render(name: str, arguments: dict[str, Any]) -> str:
    """One call, as the source the benchmark will replay."""
    joined = ", ".join(f"{key}={_survives_rewriting(repr(value))}"
                       for key, value in arguments.items())
    return f"{name}({joined})"


class Recorder:
    """The calls an agent made, in order, grouped into the steps it took."""

    def __init__(self) -> None:
        self._step: list[str] = []
        self._steps: list[list[str]] = []

    def wrap(self, method: Callable) -> Callable:
        """``method`` with recording added, and nothing else changed."""
        signature = inspect.signature(method)

        @functools.wraps(method)
        def recorded(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            self._step.append(render(method.__name__, dict(bound.arguments)))
            return method(*args, **kwargs)

        return recorded

    def end_step(self) -> None:
        """Close the current step, keeping it even if it made no calls."""
        self._steps.append(self._step)
        self._step = []

    def take_turn(self) -> list[list[str]]:
        """The steps of the turn just finished, and start the next one."""
        if self._step:
            self.end_step()
        steps, self._steps = self._steps, []
        return steps
