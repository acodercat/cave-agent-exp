"""Tests for FunctionCallTracker (sys.monitoring-based tool-call capture).

The load-bearing behaviour: only the agent-initiated (outermost) tool call is
recorded. When a tool's body calls another tracked tool, that inner call must
NOT be counted as a separate agent call.
"""

import sys
import threading

from core.tracker import FunctionCallTracker


def _inner(x):
    return x + 1


def _outer(x):
    # Calls another tracked tool internally — must not be double-counted.
    return _inner(x) * 2


def _other(y):
    return y


class TestFunctionCallTracker:
    def test_records_top_level_call_only(self):
        with FunctionCallTracker(target_functions=["_outer", "_inner"]) as t:
            _outer(1)
        calls = t.get_tool_calls()
        # _inner is called inside _outer, so it is NOT an agent call.
        assert [c.function for c in calls] == ["_outer"]
        assert calls[0].arguments == {"x": 1}

    def test_two_separate_top_level_calls(self):
        with FunctionCallTracker(target_functions=["_outer", "_other"]) as t:
            _outer(1)
            _other(2)
        assert [c.function for c in t.get_tool_calls()] == ["_outer", "_other"]

    def test_recursion_records_outermost_only(self):
        def recurse(n):
            return recurse(n - 1) if n > 0 else 0

        with FunctionCallTracker(target_functions=["recurse"]) as t:
            recurse(3)
        assert len(t.get_tool_calls()) == 1

    def test_non_target_calls_ignored(self):
        with FunctionCallTracker(target_functions=["_outer"]) as t:
            _other(5)      # not a tracked tool
            _outer(1)
        assert [c.function for c in t.get_tool_calls()] == ["_outer"]

    def test_arguments_captured(self):
        def tool(a, b=2):
            return a + b

        with FunctionCallTracker(target_functions=["tool"]) as t:
            tool(10, b=5)
        assert t.get_tool_calls()[0].arguments == {"a": 10, "b": 5}

    def test_track_all_mode_keeps_nested(self):
        # target_functions=None = "track everything"; no nesting skip applies.
        with FunctionCallTracker(target_functions=None) as t:
            _outer(1)
        names = [c.function for c in t.get_tool_calls()]
        assert "_outer" in names and "_inner" in names


class TestExactMatchingByCodeObject:
    """Passing callables matches by code object, not name — a tool called
    ``add`` must not pick up ``WeakSet.add``, which asyncio invokes for every
    async generator it registers. Under an agent framework built on async
    generators that noise outnumbered the real call 18:1 and made required-call
    validation pass for a model that never called the tool."""

    def test_stdlib_same_name_calls_are_not_tracked(self):
        import weakref

        def add(a, b):
            return a + b

        with FunctionCallTracker(target_functions=[add]) as t:
            registry = weakref.WeakSet()
            registry.add(TestExactMatchingByCodeObject)  # stdlib frame named "add"
            add(2, 3)

        calls = t.get_tool_calls()
        assert len(calls) == 1
        assert calls[0].arguments == {"a": 2, "b": 3}

    def test_async_generator_registration_noise_is_ignored(self):
        import asyncio

        def add(a, b):
            return a + b

        async def scenario():
            async def agen():
                yield 1

            async for _ in agen():  # asyncio registers it via WeakSet.add
                pass
            return add(1, 2)

        with FunctionCallTracker(target_functions=[add]) as t:
            asyncio.run(scenario())

        assert [c.arguments for c in t.get_tool_calls()] == [{"a": 1, "b": 2}]

    def test_nested_tracked_tools_still_collapse(self):
        def inner(x):
            return x

        def outer(x):
            return inner(x)

        with FunctionCallTracker(target_functions=[outer, inner]) as t:
            outer(5)

        assert [c.function for c in t.get_tool_calls()] == ["outer"]

    def test_mixing_names_and_callables_is_rejected(self):
        def tool():
            pass

        try:
            FunctionCallTracker(target_functions=[tool, "other"])
        except TypeError:
            pass
        else:
            raise AssertionError("mixed targets should raise")


class TestMonitoringSemantics:
    """Properties that come from sys.monitoring rather than sys.setprofile.

    Capture is per-interpreter, not per-thread: agent-generated code that
    hands work to a thread must still be observed. Under setprofile these
    calls were invisible, and invisible reads downstream as "the model never
    called the tool" rather than as broken instrumentation.
    """

    def test_captures_calls_from_other_threads(self):
        def tool(x):
            return x

        with FunctionCallTracker(target_functions=[tool]) as t:
            thread = threading.Thread(target=tool, args=(7,))
            thread.start()
            thread.join()

        assert [c.arguments for c in t.get_tool_calls()] == [{"x": 7}]

    def test_concurrent_calls_get_unique_ids(self):
        def tool(x):
            return x

        with FunctionCallTracker(target_functions=[tool]) as t:
            threads = [threading.Thread(target=tool, args=(i,)) for i in range(16)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        calls = t.get_tool_calls()
        assert len(calls) == 16
        # call_id is assigned under a lock; a race would collide or skip.
        assert len({c.call_id for c in calls}) == 16

    def test_tool_id_is_released_on_exit(self):
        def tool():
            pass

        for _ in range(3):
            with FunctionCallTracker(target_functions=[tool]):
                tool()
        # A leaked id would make the next use_tool_id raise, so reaching here
        # with a fresh acquisition succeeding is the assertion.
        assert FunctionCallTracker(target_functions=[tool])._tool_id is None

    def test_tool_id_released_when_body_raises(self):
        def tool():
            pass

        try:
            with FunctionCallTracker(target_functions=[tool]):
                raise RuntimeError("boom")
        except RuntimeError:
            pass

        with FunctionCallTracker(target_functions=[tool]) as t:
            tool()
        assert len(t.get_tool_calls()) == 1

    def test_coexists_with_another_monitoring_client(self):
        """A debugger/coverage tool holding an id must not break capture."""
        def tool(x):
            return x

        taken = 3  # first candidate the tracker tries
        sys.monitoring.use_tool_id(taken, "occupier")
        try:
            with FunctionCallTracker(target_functions=[tool]) as t:
                assert t._tool_id != taken
                tool(1)
        finally:
            sys.monitoring.free_tool_id(taken)

        assert [c.arguments for c in t.get_tool_calls()] == [{"x": 1}]
