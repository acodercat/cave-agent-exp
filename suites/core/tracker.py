"""Function call tracker built on PEP 669 (``sys.monitoring``).

CaveAgent calls tools by executing generated Python, so there is no structured
tool-call payload to read off an API response. This tracker recovers the calls
by monitoring the interpreter and reconstructing ``ToolCall``s from live frames.

Why ``sys.monitoring`` rather than ``sys.setprofile`` (measured on a pandas
workload, CPython 3.12):

- **Cost.** ``setprofile`` fires a Python callback on *every* call and return
  in the thread — all of pandas' internals included — and the tracker then
  throws almost all of it away: 1.31x wall-clock. ``set_local_events`` arms
  only the tool code objects, so non-tool code runs unmonitored: 1.04x. This
  matters beyond speed, because ``TurnMetrics.elapsed`` is measured with the
  tracker installed and *only* the CaveAgent path installs one — profiling
  overhead would otherwise tax exactly one side of a cross-paradigm comparison.
- **Thread scope.** ``setprofile`` is per-thread; ``sys.monitoring`` is
  per-interpreter. A tool invoked from a thread the agent's code spawned is
  invisible to the former (verified) and captured by the latter. Silently
  capturing zero calls is the dangerous failure here: it reads downstream as
  "the model never called the tool" rather than as broken instrumentation.

``PY_START`` is the event to use: ``CALL`` reports only ``arg0``, which cannot
reconstruct keyword arguments. Events are suppressed while a callback runs
(verified), so the callback may freely call Python without recursing.
"""

import inspect
import sys
import threading
from types import CodeType, FrameType
from typing import Any, Dict, List, Optional, Set, Type

from core.types import ToolCall

# sys.monitoring reserves ids 0-2 (debugger, coverage, profiler) and 5
# (optimizer). 3 and 4 are free for general tools; take whichever is available
# so a tracker can coexist with another monitoring client — or with itself,
# should two trackers ever nest.
_TOOL_ID_CANDIDATES = (3, 4)


class FunctionCallTracker:
    """Tracker for tool calls made by agent-generated code.

    Pass the tool *callables* whenever they are at hand: matching is then by
    code object, which is exact, and monitoring is armed only on those code
    objects. Matching by bare name is kept for callers that only have names,
    but it needs interpreter-wide monitoring and it catches every same-named
    function in the process — a tool called ``add`` also matched ``WeakSet.add``,
    which asyncio invokes for each async generator it registers, so an agent
    framework built on async generators drowned the real call in stdlib noise
    (and made "was the required tool called?" validation pass for a model that
    never called it).
    """

    def __init__(self, target_functions: Optional[List[Any]] = None) -> None:
        """
        Initialize a function call tracker.

        Args:
            target_functions: Tool callables (exact, preferred) or function
                names (legacy) to track. Mixing the two is a caller bug and
                raises. If None, track all functions.
        """
        self.tool_calls: List[ToolCall] = []
        self.current_call_id: int = 0
        self.target_functions = target_functions

        self._codes: Optional[Dict[CodeType, str]] = None  # exact matching
        self._names: Optional[Set[str]] = None             # legacy matching
        if target_functions is not None:
            if all(callable(f) for f in target_functions):
                self._codes = {f.__code__: f.__name__ for f in target_functions}
            elif any(callable(f) for f in target_functions):
                raise TypeError("target_functions must be all callables or all names")
            else:
                self._names = set(target_functions)

        # Monitoring is interpreter-wide, so callbacks can now fire from
        # several threads at once; `current_call_id` is not atomic under +=.
        # Callbacks cannot re-enter (events are suppressed inside one), so a
        # plain Lock cannot deadlock here.
        self._lock = threading.Lock()
        self._tool_id: Optional[int] = None

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def _acquire_tool_id(self) -> int:
        """Claim a free sys.monitoring tool id."""
        for tool_id in _TOOL_ID_CANDIDATES:
            try:
                sys.monitoring.use_tool_id(tool_id, "cave-bench")
            except ValueError:
                continue  # already claimed by another monitoring client
            return tool_id
        raise RuntimeError(
            "no free sys.monitoring tool id: tried "
            f"{_TOOL_ID_CANDIDATES}, all in use"
        )

    def start(self) -> None:
        """Start tracking function calls."""
        self.tool_calls = []
        self.current_call_id = 0

        tool_id = self._acquire_tool_id()
        self._tool_id = tool_id
        events = sys.monitoring.events
        sys.monitoring.register_callback(tool_id, events.PY_START, self._on_py_start)

        if self._codes is not None:
            # Fast path: arm only the tool code objects. Everything else in the
            # process runs at full speed.
            for code in self._codes:
                sys.monitoring.set_local_events(tool_id, code, events.PY_START)
        else:
            # Legacy name matching / track-all: the code objects are not known
            # up front, so every Python call has to be seen and filtered.
            sys.monitoring.set_events(tool_id, events.PY_START)

    def stop(self) -> None:
        """Stop tracking function calls. Idempotent."""
        tool_id = self._tool_id
        if tool_id is None:
            return
        self._tool_id = None

        events = sys.monitoring.events
        try:
            if self._codes is not None:
                for code in self._codes:
                    sys.monitoring.set_local_events(tool_id, code, 0)
            else:
                sys.monitoring.set_events(tool_id, 0)
            sys.monitoring.register_callback(tool_id, events.PY_START, None)
        finally:
            # Leaking the id would make the next run's use_tool_id fail.
            sys.monitoring.free_tool_id(tool_id)

    def __enter__(self) -> "FunctionCallTracker":
        """Context manager entry - start tracking."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any]
    ) -> None:
        """Context manager exit - ensure tracking is stopped even on exception."""
        self.stop()

    # ------------------------------------------------------------------
    # capture
    # ------------------------------------------------------------------

    def _is_tracked(self, code: CodeType, name: str) -> bool:
        if self._codes is not None:
            return code in self._codes
        return name in self._names

    def _on_py_start(self, code: CodeType, instruction_offset: int) -> None:
        """PY_START callback: record an agent-initiated tool call."""
        # The callback runs one frame above the function that just started.
        frame: Optional[FrameType] = sys._getframe(1)
        if frame is not None and frame.f_code is not code:
            # Defensive: never observed, but a mismatch would silently attribute
            # the wrong locals to the call.
            while frame is not None and frame.f_code is not code:
                frame = frame.f_back
            if frame is None:
                return

        func_name = code.co_name

        if self._codes is not None or self._names is not None:
            if not self._is_tracked(code, func_name):
                return
            # Skip tool calls made *inside* another tracked tool: when a tool's
            # body calls another tool, the event still fires even though the
            # agent did not initiate it. Record only the outermost
            # (agent-initiated) call — i.e. when no ancestor frame is itself a
            # tracked tool.
            parent = frame.f_back
            while parent is not None:
                if self._is_tracked(parent.f_code, parent.f_code.co_name):
                    return
                parent = parent.f_back

        # Get function arguments
        arg_info = inspect.getargvalues(frame)
        arguments = {}

        # Process regular arguments
        for arg_name in arg_info.args:
            if arg_name == 'self':  # Skip self in methods
                continue

            if arg_name in arg_info.locals:
                value = arg_info.locals[arg_name]
                arguments[arg_name] = value

        with self._lock:
            self.current_call_id += 1
            call_id = self.current_call_id
            self.tool_calls.append(ToolCall(
                call_id=str(call_id),
                function=func_name,
                arguments=arguments
            ))

    def get_tool_calls(self) -> List[ToolCall]:
        """Get tracked tool calls"""
        return self.tool_calls
