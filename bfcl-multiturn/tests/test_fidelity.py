"""The invariant that makes a cave verdict mean something.

The cave arm writes free Python, so its recording is a claim about what it did.
These tests are about catching a claim that falls short of the state, whatever
route the agent took to get there.
"""

from bfcl_multiturn import benchmark
from bfcl_multiturn.fidelity import unrecorded_change
from bfcl_multiturn.recorder import Recorder


def prepared():
    task = next(t for t in benchmark.tasks() if t.involved_classes == ("GorillaFileSystem",))
    instances = benchmark.instantiate(task)
    recorder = Recorder()
    wrapped = {m.__name__: recorder.wrap(m) for m in benchmark.methods(instances)}
    return task, instances, recorder, wrapped


class TestWhatItAccepts:
    def test_a_recording_that_accounts_for_the_state(self):
        task, instances, recorder, wrapped = prepared()
        wrapped["mkdir"](dir_name="made")
        wrapped["cd"](folder="made")

        assert unrecorded_change(task, instances, [recorder.take_turn()],
                                 benchmark.tag("fid", "clean")) == {}

    def test_an_agent_that_did_nothing(self):
        task, instances, recorder, _ = prepared()

        assert unrecorded_change(task, instances, [recorder.take_turn()],
                                 benchmark.tag("fid", "idle")) == {}

    def test_a_call_that_only_reads(self):
        task, instances, recorder, wrapped = prepared()
        wrapped["ls"]()
        wrapped["pwd"]()

        assert unrecorded_change(task, instances, [recorder.take_turn()],
                                 benchmark.tag("fid", "reads")) == {}


class TestWhatItCatches:
    def test_a_method_reached_around_the_wrapper(self):
        """`__wrapped__.__self__` hands back every method unrecorded."""
        task, instances, recorder, wrapped = prepared()
        wrapped["mkdir"].__wrapped__.__self__.mkdir(dir_name="hidden")

        differing = unrecorded_change(task, instances, [recorder.take_turn()],
                                      benchmark.tag("fid", "around"))

        assert differing == {"GorillaFileSystem": ["root"]}

    def test_an_attribute_assigned_directly(self):
        task, instances, recorder, _ = prepared()
        instances["GorillaFileSystem"].long_context = True

        differing = unrecorded_change(task, instances, [recorder.take_turn()],
                                      benchmark.tag("fid", "assigned"))

        assert "long_context" in differing["GorillaFileSystem"]

    def test_it_reports_only_the_attributes_that_differ(self):
        task, instances, recorder, wrapped = prepared()
        wrapped["mkdir"](dir_name="made")                       # recorded
        instances["GorillaFileSystem"].long_context = True       # not

        differing = unrecorded_change(task, instances, [recorder.take_turn()],
                                      benchmark.tag("fid", "mixed"))

        assert differing == {"GorillaFileSystem": ["long_context"]}
