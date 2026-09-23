"""The rounds cases: one object, handed on and edited again and again.

Three objects, each at three depths — one crossing, four, eight — so that what
a chain loses can be read against how many times it crossed. The depths of one
object are prefixes of the same chain, so the first three hops of the deepest
run are exactly the hops of the middle one.

* :mod:`cases.rounds._tz_events` — a table whose start times carry a timezone,
  and a question at the end that only a chain which kept the zone can answer.
* :mod:`cases.rounds._equity_meta` — a tuple of a table and its metadata, where
  the metadata accumulates the chain's own trace.
* :mod:`cases.rounds._control_branches` — ten rows of plain types: the control,
  which measures what handing an object on and editing it costs when the object
  itself is easy.
"""

from __future__ import annotations

from cases.rounds import _control_branches, _equity_meta, _tz_events
from core.rounds import RoundsCase, cases

# One crossing (producer to consumer), four, and eight. Eight is seven revisers,
# which is what the chains define.
DEPTHS = (1, 4, 8)

ROUNDS_CASES: list[RoundsCase] = [
    case
    for module in (_tz_events, _equity_meta, _control_branches)
    for case in cases(module.TASK, module.REVISIONS, DEPTHS)
]
