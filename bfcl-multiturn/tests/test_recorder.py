"""What the recorder must get right for a verdict to mean anything.

A missed or misrendered call is not an error here -- it is a state mismatch,
scored as a wrong answer. So these tests are about fidelity, not plumbing.
"""

import pytest

from bfcl_multiturn import benchmark
from bfcl_multiturn.recorder import Recorder, render


class TestRendering:
    @pytest.mark.parametrize("arguments, expected", [
        ({"folder": "document"}, "cd(folder='document')"),
        ({"a": True}, "cd(a=True)"),
        ({"lines": 20}, "cd(lines=20)"),
        ({"names": ["x", "y"]}, "cd(names=['x', 'y'])"),
        ({"updates": {"priority": 2}}, "cd(updates={'priority': 2})"),
        ({"content": "it's"}, 'cd(content="it\'s")'),
    ])
    def test_every_shape_the_ground_truth_uses(self, arguments, expected):
        assert render("cd", arguments) == expected

    def test_a_rendered_call_replays_through_the_benchmark(self):
        """The property that matters: the benchmark can execute what we write.

        Checked by writing the task's own ground truth through the renderer: if a
        rendering did not execute, the state would not match.
        """
        task = next(t for t in benchmark.tasks() if t.involved_classes == ("GorillaFileSystem",))
        import re
        rendered = []
        for turn in task.ground_truth:
            calls = []
            for call in turn:
                name = re.match(r"(\w+)", call).group(1)
                arguments = eval(f"dict({call[len(name) + 1:-1]})")   # the task's own literals
                calls.append(render(name, arguments))
            rendered.append([calls])

        assert benchmark.score(task, rendered, benchmark.tag("render", "probe", task.id))["valid"]


class TestRecording:
    def test_a_call_is_recorded_and_still_happens(self):
        task = next(t for t in benchmark.tasks() if t.involved_classes == ("GorillaFileSystem",))
        instances = benchmark.instantiate(task)
        recorder = Recorder()
        mkdir = recorder.wrap(instances["GorillaFileSystem"].mkdir)

        mkdir(dir_name="made")

        assert recorder.take_turn() == [["mkdir(dir_name='made')"]]
        assert "made" in str(instances["GorillaFileSystem"].ls())

    def test_defaults_are_recorded_because_the_replay_needs_them(self):
        task = next(t for t in benchmark.tasks() if t.involved_classes == ("GorillaFileSystem",))
        listing = Recorder()
        wrapped = listing.wrap(benchmark.instantiate(task)["GorillaFileSystem"].ls)

        wrapped()

        assert listing.take_turn() == [["ls(a=False)"]]

    def test_the_wrapper_keeps_what_the_model_is_shown(self):
        """cave-agent describes a tool from its signature and docstring."""
        task = next(t for t in benchmark.tasks() if t.involved_classes == ("GorillaFileSystem",))
        original = benchmark.instantiate(task)["GorillaFileSystem"].mkdir
        wrapped = Recorder().wrap(original)

        import inspect
        assert inspect.signature(wrapped) == inspect.signature(original)
        assert wrapped.__doc__ == original.__doc__
        assert wrapped.__name__ == original.__name__

    def test_steps_are_kept_apart_and_turns_start_clean(self):
        recorder = Recorder()
        task = next(t for t in benchmark.tasks() if t.involved_classes == ("GorillaFileSystem",))
        filesystem = benchmark.instantiate(task)["GorillaFileSystem"]
        recorder.wrap(filesystem.ls)()
        recorder.end_step()
        recorder.wrap(filesystem.pwd)()

        assert recorder.take_turn() == [["ls(a=False)"], ["pwd()"]]
        assert recorder.take_turn() == []


class TestSurvivingUpstreamsRewriting:
    """Upstream rewrites a call before replaying it, and eats a space doing so.

    Its pattern is `\\b(\\w+)\\s*(?=\\()` over the whole call, string literals
    included, so a space before `(` inside text is swallowed and the replayed
    state no longer matches. Found by the fidelity check on a real task, where an
    agent wrote "10 shares (Status: Completed)" into a ticket.
    """

    def rewritten(self, call, name):
        from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
            _process_method_calls,
        )
        return _process_method_calls(call, {name: "I"})

    def replayed_value(self, call, name, field):
        import re
        rewritten = self.rewritten(call, name)
        arguments = re.match(rf"I\.{name}\((.*)\)$", rewritten, re.S).group(1)
        return eval(f"dict({arguments})")[field]              # noqa: S307 - the replay's own eval

    def test_a_space_before_a_paren_survives(self):
        text = "10 shares (Status: Completed)"

        call = render("create_ticket", {"description": text})

        assert self.replayed_value(call, "create_ticket", "description") == text

    def test_several_in_one_string(self):
        text = "a (one) b (two) c (three)"

        call = render("create_ticket", {"description": text})

        assert self.replayed_value(call, "create_ticket", "description") == text

    def test_text_without_the_pattern_is_left_as_repr_wrote_it(self):
        call = render("cd", {"folder": "document"})

        assert call == "cd(folder='document')"

    def test_the_escape_is_invisible_to_the_rewriting(self):
        call = render("create_ticket", {"description": "x (y)"})

        assert "\\x20" in call
        assert "shares(" not in self.rewritten(call, "create_ticket")
