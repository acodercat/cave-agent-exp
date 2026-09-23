"""What must hold of the two arms for a difference between them to mean anything.

None of these call a model. The claim being mechanised is the one R3 asks for:
the arms are given the same operations over the same state, and differ only in
how an action is expressed.
"""

import json

import pytest

from bfcl_multiturn import arms, benchmark, prompts


@pytest.fixture(scope="module")
def task():
    return next(t for t in benchmark.tasks() if t.involved_classes == ("GorillaFileSystem",))


@pytest.fixture
def built(task):
    """Both arms over their own instances of the same task."""
    def build(kind):
        instances = benchmark.instantiate(task)
        methods = benchmark.methods(instances)
        if kind == "cave":
            return arms.CaveArm(model=object(), methods=methods), instances
        settings = arms.Settings(model_id="unused")
        return arms.FunctionCallingArm(settings=settings, methods=methods,
                                       tool_documents=benchmark.tool_documents(task)), instances
    return build


class TestTheArmsAreMatched:
    def test_they_are_given_the_same_operations(self, built):
        cave, _ = built("cave")
        fc, _ = built("fc")

        assert [m.__name__ for m in cave.methods] == [m.__name__ for m in fc.methods]

    def test_the_tools_the_fc_arm_sends_are_the_benchmark_s_own(self, built, task):
        fc, _ = built("fc")

        sent = [tool["function"]["name"] for tool in fc._tools]
        assert sent == [tool["function"]["name"] for tool in benchmark.tool_documents(task)]
        assert sent == [method.__name__ for method in fc.methods]

    def test_the_tools_carry_nothing_a_definition_does_not_have(self, task):
        """`response` describes a return value; a type spelled `dict` is rejected."""
        import json

        for tool in benchmark.tool_documents(task):
            assert set(tool["function"]) == {"name", "description", "parameters"}
        assert '"dict"' not in json.dumps(benchmark.tool_documents(task))

    def test_both_are_told_the_same_task_and_constraint(self, built):
        """They differ on how to act, and on nothing else."""
        cave, _ = built("cave")
        fc, _ = built("fc")
        shared = prompts.SHARED.split("- Change anything")[0]

        assert shared in cave._agent.instructions
        assert shared in fc._history[0]["content"]
        assert "```python" in cave._agent.instructions      # the fenced arm's action
        assert "```python" not in fc._history[0]["content"]  # the provider enforces the other

    def test_each_arm_acts_on_its_own_state(self, built):
        """Two arms sharing instances would score each other's work."""
        _, first = built("cave")
        _, second = built("fc")

        assert first["GorillaFileSystem"] is not second["GorillaFileSystem"]

    def test_the_budget_is_the_same(self, built):
        cave, _ = built("cave")
        fc, _ = built("fc")

        assert cave.max_steps == fc.max_steps


class TestTheFcArmAnswersEveryCall:
    """An unanswered tool call makes the history unsendable, ending the task."""

    def call(self, name, arguments):
        return {"id": "c1", "function": {"name": name, "arguments": arguments}}

    def test_a_call_that_works(self, built):
        fc, instances = built("fc")

        answer = fc._dispatch(self.call("mkdir", json.dumps({"dir_name": "made"})))

        assert "error" not in answer
        assert "made" in str(instances["GorillaFileSystem"].ls())

    def test_a_tool_that_does_not_exist(self, built):
        fc, _ = built("fc")

        assert "no tool named" in fc._dispatch(self.call("nope", "{}"))

    def test_arguments_that_are_not_json(self, built):
        fc, _ = built("fc")

        assert "not JSON" in fc._dispatch(self.call("mkdir", "{dir_name: made"))

    def test_a_call_the_tool_itself_refuses(self, built):
        fc, _ = built("fc")

        answer = fc._dispatch(self.call("cd", json.dumps({"folder": "nowhere"})))

        assert answer                                  # answered, not raised

    def test_a_working_call_is_recorded_for_scoring(self, built):
        fc, _ = built("fc")

        fc._dispatch(self.call("mkdir", json.dumps({"dir_name": "made"})))

        assert fc._recorder.take_turn() == [["mkdir(dir_name='made')"]]


class TestSettings:
    def test_reasoning_is_stated_rather_than_left_to_a_default(self):
        assert arms.Settings(model_id="m").request()["extra_body"] == {"thinking": {"type": "disabled"}}

    def test_the_provider_is_named_because_litellm_needs_it(self):
        assert arms.Settings(model_id="m").request()["model"] == "openai/m"

    def test_a_gateway_that_cannot_take_it_can_be_told_so(self):
        assert "extra_body" not in arms.Settings(model_id="m", extra_body={}).request()


class TestTheFenceGuard:
    """A fenced turn that executed nothing is a missed turn, not a wrong answer."""

    class Response:
        def __init__(self, content, snippets=()):
            self.content, self.code_snippets = content, list(snippets)

    names = frozenset({"ls", "mkdir"})

    @pytest.mark.parametrize("content", [
        "<tool_call>\n<function=ls>\n</function>",
        "<function=mkdir>",
        "```\nls()\n```",
        "I will run ls() now.",
    ])
    def test_an_action_the_runtime_would_ignore(self, content):
        assert arms.unexecuted_call(self.Response(content), self.names)

    def test_a_turn_that_did_execute_is_left_alone(self):
        """Even when its prose names a function."""
        response = self.Response("I called ls() and here is what it said.", ["ls()"])

        assert not arms.unexecuted_call(response, self.names)

    def test_plain_prose_is_not_mistaken_for_an_action(self):
        assert not arms.unexecuted_call(self.Response("There is no such folder."), self.names)
