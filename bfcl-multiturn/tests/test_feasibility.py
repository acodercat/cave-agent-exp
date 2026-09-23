"""What the official BFCL machinery must keep doing for this experiment to hold.

These are not tests of behaviour this project wrote: they pin properties of the
upstream package and of the way it must be called, so that an upstream change --
a renamed helper, a checker that stops returning the instances -- fails here
rather than halfway through a run. Two of them record faults that were found by
trying them, and that scored wrong answers as right.
"""

import pytest
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import state_checker
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
    execute_multi_turn_func_call,
)

from bfcl_multiturn import benchmark


@pytest.fixture(scope="module")
def subset():
    return {task.id: task for task in benchmark.tasks()}


@pytest.fixture(scope="module")
def filesystem_task(subset):
    """A task on one API, so a state difference has one place to be."""
    return next(task for task in subset.values()
                if task.involved_classes == ("GorillaFileSystem",))


def replay(task, calls_per_turn, tag):
    """Run a conversation's calls, returning the instances they acted on."""
    instances = None
    for calls in calls_per_turn:
        _, instances = execute_multi_turn_func_call(
            list(calls), task.initial_config, list(task.involved_classes),
            model_name=tag, test_entry_id=task.id, long_context=False, is_evaL_run=False,
        )
    return instances


def as_recorded(task):
    """The task's ground truth in the shape a run reports: turns of steps."""
    return [[list(turn)] for turn in task.ground_truth]


class TestTheSubset:
    def test_it_is_the_size_the_experiment_assumes(self, subset):
        assert len(subset) == 200
        assert all(task.ground_truth for task in subset.values())

    def test_every_task_names_the_apis_it_needs(self, subset):
        assert all(task.involved_classes for task in subset.values())


class TestWhatTheBenchmarkScores:
    def test_a_conversation_yields_the_instances_it_acted_on(self, subset):
        """The state, not a transcript, is what this benchmark compares."""
        task = subset["multi_turn_base_0"]

        instances = replay(task, task.ground_truth, "feasibility")

        assert sorted(instances) == sorted(task.involved_classes)
        assert state_checker(instances, instances) == {"valid": True}

    def test_the_state_checker_separates_right_actions_from_wrong_ones(self, filesystem_task):
        reference = replay(filesystem_task, filesystem_task.ground_truth, "truth")

        assert state_checker(replay(filesystem_task, filesystem_task.ground_truth, "same"),
                             reference)["valid"]
        verdict = state_checker(replay(filesystem_task, [["mkdir(dir_name='decoy')"]], "other"),
                                reference)

        assert verdict["error_type"] == "multi_turn:instance_state_mismatch"

    def test_the_apis_are_plain_objects_an_agent_can_be_handed(self, filesystem_task):
        """Which is what lets the cave arm operate on the real instances."""
        instances = benchmark.instantiate(filesystem_task)

        methods = [method.__name__ for method in benchmark.methods(instances)]

        assert len(methods) >= 15
        assert {"cd", "mkdir", "cat"} <= set(methods)


class TestTheTrapsUpstreamSetsForACaller:
    """Both were found by trying them, and both scored wrong answers as right."""

    def test_scoring_twice_under_one_tag_corrupts_the_second_verdict(self, subset):
        """Instances are cached in upstream's globals and never released.

        A second scoring under a tag it has seen replays onto the state the first
        left behind, and a correct conversation comes back invalid. Scoring the
        same correct conversation twice hides this -- the ground truth is replayed
        into the same dirty instance, so the two still match -- which is why the
        wrong conversation has to be scored first to see it.
        """
        task = subset["multi_turn_base_6"]
        correct = as_recorded(task)
        wrong = [[turn[:-1] if index == 0 else turn] for index, turn in enumerate(task.ground_truth)]

        shared = benchmark.tag("shared")
        assert not benchmark.score(task, wrong, shared)["valid"]
        assert not benchmark.score(task, correct, shared)["valid"]      # the corruption

        assert not benchmark.score(task, wrong, benchmark.tag("own", "a"))["valid"]
        assert benchmark.score(task, correct, benchmark.tag("own", "b"))["valid"]

    def test_a_tag_that_is_not_an_identifier_is_refused(self, subset):
        """Upstream names each instance after the tag, then evals that name.

        A tag carrying anything else makes every replayed call a syntax error --
        the ground truth's as much as the model's -- so both sides stay at the
        initial state, match, and the task is scored correct. A run tagged that
        way reports near-perfect accuracy having executed nothing.
        """
        task = subset["multi_turn_base_6"]

        with pytest.raises(ValueError, match="not a Python identifier"):
            benchmark.score(task, as_recorded(task), "has~a~tilde")

    def test_a_wrong_argument_is_caught(self, filesystem_task):
        """The property the identifier check exists to protect."""
        correct = as_recorded(filesystem_task)
        mutated = [[[call.replace("'", "'wrong", 1) if index == 0 else call
                     for index, call in enumerate(step)] for step in turn] for turn in correct]

        assert benchmark.score(filesystem_task, correct, benchmark.tag("arg", "correct"))["valid"]
        assert not benchmark.score(filesystem_task, mutated,
                                   benchmark.tag("arg", "mutated"))["valid"]
