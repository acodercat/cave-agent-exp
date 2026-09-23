"""The pipeline runs every stage, folds the expected table, and names what failed.

No model and no runtime tables: a fake agent and a fake runtime stand in, so what
is under test is the loop — how many agents run, what each is judged against, what
crosses between them, and which role is blamed when the end-to-end answer is
wrong. That last one is the reading the study's attribution table rests on.
"""

import asyncio
from collections import Counter
from types import SimpleNamespace

import pandas as pd
import pytest
from cave_agent import StopReason, TokenUsage

from core import pipeline_evaluator as pipeline
from cases.pipeline.stages import KEEP_LOWER_HALF
from core.pipeline import Answer, CHANNELS, FollowUp, PipelineCase, Middle
from core.pipeline_evaluator import PipelineSettings, run_hosted
from core.table_delivery import CellKind, Column, Size, TableTask


ROWS = [{"n": index} for index in range(8)]


def _task() -> TableTask:
    return TableTask(
        name="fake", title="Fake", data_sources=("fake",), financial_domain="banking_credit",
        query="Deliver {scope}.", output="the_table", row_noun="row", key=("n",),
        columns=(Column("n", CellKind.INTEGER, "a number"),),
        sizes=(Size("8", "eight rows", 8),),
        # A real load and build, because a TableTask is frozen: the expected rows
        # have to come from the task itself rather than be patched onto it.
        load=lambda: None, build=lambda source, **_: pd.DataFrame({"n": range(8)}),
    )


HALVE = Middle(
    "narrower", lambda task: "Halve it.",
    lambda task, rows: rows[: len(rows) // 2], "half_table",
)
RELAY = Middle("relay", lambda task: "Pass it on.", lambda task, rows: list(rows),
               "relayed_table")
FOLLOW_UP = FollowUp(
    query="How many rows?", answers=(Answer("row_count", "How many rows.", decimals=0),),
    compute=lambda rows: (len(rows),),
)


def _case(middles) -> PipelineCase:
    task = _task()
    return PipelineCase(task=task, size=task.sizes[0], follow_up=FOLLOW_UP, middles=middles)


@pytest.fixture
def pipeline_env(monkeypatch):
    """A pipeline whose agents assign whatever the recipe for their stage says."""
    seen = []

    class FakeRuntime:
        def __init__(self, *, functions, variables, types, security_checker):
            self.values = {variable.name: variable.value for variable in variables}

        def inject_variable(self, variable):
            self.values[variable.name] = variable.value

        async def retrieve(self, name):
            return self.values.get(name)

    class FakeAgent:
        def __init__(self, model, *, runtime, max_steps, **kwargs):
            self.runtime, self.max_steps = runtime, max_steps
            self.messages = []
            self.loop_events, self.spent = Counter(), Counter()
            self.stop_cause = None

        async def run(self, prompt):
            # The real agent reads the name out of its prompt. This one takes the
            # most recently bound value instead, which is the same variable: a
            # shared runtime still holds everything the earlier agents left, and
            # the newest of those is the one the prompt names.
            visible = [
                (key, value) for key, value in self.runtime.values.items()
                if value is not None
            ]
            handed = visible[-1] if visible else None
            rows = handed[1] if handed else None
            name, value = model_recipe.pop(0)
            seen.append(SimpleNamespace(
                prompt=prompt, handed=rows, handed_named=handed,
                assigned=name, runtime=self.runtime,
            ))
            self.runtime.values[name] = value(rows)
            return SimpleNamespace(
                stop_reason=StopReason.COMPLETED, content="done", steps=1,
                usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
                elapsed=0.1, code_snippets=["x = 1"],
            )

    model_recipe: list = []
    monkeypatch.setattr(pipeline, "IPythonRuntime", FakeRuntime)
    monkeypatch.setattr(pipeline, "FencedCodeAgent", FakeAgent)
    monkeypatch.setattr(pipeline, "select_runtime_tables", lambda _: [])
    monkeypatch.setattr(pipeline, "table_paths", lambda *_: {})
    return SimpleNamespace(recipe=model_recipe, seen=seen)


def _run(case, pipeline_env, recipe, tmp_path):
    """Run the whole pipeline, as the repository's other async tests do."""
    pipeline_env.recipe[:] = recipe
    return asyncio.run(run_hosted(
        None, case, CHANNELS["object"], PipelineSettings(max_protocol_nudges=0), tmp_path,
    ))


def test_a_three_agent_pipeline_runs_three_agents(pipeline_env, tmp_path):
    case = _case((HALVE,))
    result = _run(case, pipeline_env, [
        ("the_table", lambda handed: list(ROWS)),
        ("half_table", lambda handed: handed[:4]),
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    assert result.agents == 3
    assert [stage.role for stage in result.stages] == ["retriever", "narrower", "analyst"]
    assert result.success
    assert result.first_contract_failure is None
    assert result.first_unfaithful is None


def test_each_stage_is_handed_what_the_stage_before_it_assigned(pipeline_env, tmp_path):
    case = _case((HALVE,))
    _run(case, pipeline_env, [
        ("the_table", lambda handed: list(ROWS)),
        ("half_table", lambda handed: handed[:4]),
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    handed = [call.handed for call in pipeline_env.seen]
    assert handed[0] is None                 # the first agent reads the source tables
    assert handed[1] == ROWS                 # the narrower gets all eight
    assert handed[2] == ROWS[:4]             # the analyst gets the four it kept


def test_a_relay_pipeline_crosses_the_channel_once_per_seam(pipeline_env, tmp_path):
    case = _case((RELAY, RELAY, RELAY))
    result = _run(case, pipeline_env, [
        ("the_table", lambda handed: list(ROWS)),
        *[("relayed_table", lambda handed: handed)] * 3,
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    assert result.agents == 5
    assert result.success
    assert [stage.delivered_rows for stage in result.stages] == [8, 8, 8, 8, None]
    assert all(stage.crossing for stage in result.stages[:-1])
    assert result.stages[-1].crossing is None


def test_the_middle_agent_is_judged_against_the_table_it_should_have_handed_on(
    pipeline_env, tmp_path,
):
    """A narrower that passes everything through has not narrowed."""
    case = _case((HALVE,))
    result = _run(case, pipeline_env, [
        ("the_table", lambda handed: list(ROWS)),
        ("half_table", lambda handed: handed),       # keeps all eight
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    assert [stage.success for stage in result.stages] == [True, False, False]
    assert result.first_contract_failure == "narrower"
    assert result.first_unfaithful == "narrower"


def test_a_stage_that_hands_nothing_on_stops_the_pipeline(pipeline_env, tmp_path):
    case = _case((HALVE,))
    result = _run(case, pipeline_env, [
        ("nothing_at_all", lambda handed: list(ROWS)),
        ("half_table", lambda handed: handed[:4]),
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    assert len(result.stages) == 1
    assert result.first_contract_failure == "retriever_handed_nothing_on"
    assert not result.success
    assert pipeline_env.recipe, "the later agents must not have run"


def test_a_wrong_table_faithfully_handed_on_is_blamed_on_the_stage_that_made_it(
    pipeline_env, tmp_path,
):
    case = _case((HALVE,))
    result = _run(case, pipeline_env, [
        ("the_table", lambda handed: ROWS[:6]),      # the first agent is short
        ("half_table", lambda handed: handed[:3]),   # the narrower halves what it got
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    assert not result.success
    assert result.first_contract_failure == "retriever"
    assert result.first_unfaithful == "retriever"
    # The narrower did its own job on what it was given, and the record says so.
    assert result.stages[1].faithful is True


# ----- sharing a runtime ------------------------------------------------------

def test_a_shared_channel_runs_every_agent_in_one_runtime(pipeline_env, tmp_path):
    case = _case((HALVE,))
    pipeline_env.recipe[:] = [
        ("the_table", lambda handed: list(ROWS)),
        ("half_table", lambda handed: handed[:4]),
        ("row_count", lambda handed: len(handed)),
    ]
    result = asyncio.run(run_hosted(
        None, case, CHANNELS["shared"], PipelineSettings(max_protocol_nudges=0), tmp_path,
    ))
    assert result.success
    assert len({id(call.runtime) for call in pipeline_env.seen}) == 1
    assert all(stage.crossing["carried"] == "share" for stage in result.stages[:-1])


def test_an_injecting_channel_gives_every_agent_its_own_runtime(pipeline_env, tmp_path):
    case = _case((HALVE,))
    result = _run(case, pipeline_env, [
        ("the_table", lambda handed: list(ROWS)),
        ("half_table", lambda handed: handed[:4]),
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    assert result.success
    assert len({id(call.runtime) for call in pipeline_env.seen}) == 3
    assert all(stage.crossing["carried"] == "inject" for stage in result.stages[:-1])


def test_a_shared_channel_hands_the_table_on_under_its_own_name(pipeline_env, tmp_path):
    """Nothing renamed it, so the next agent looks for what the producer called it."""
    case = _case(())
    pipeline_env.recipe[:] = [
        ("the_table", lambda handed: list(ROWS)),
        ("row_count", lambda handed: len(handed)),
    ]
    asyncio.run(run_hosted(
        None, case, CHANNELS["shared"], PipelineSettings(max_protocol_nudges=0), tmp_path,
    ))
    # The second agent reads the producer's own binding out of the shared namespace.
    assert pipeline_env.seen[1].handed_named == ("the_table", ROWS)


def test_a_later_stage_that_repairs_a_bad_table_is_not_blamed_and_the_real_culprit_is(
    pipeline_env, tmp_path,
):
    """The reviewer's counter-example.

    The first agent spoils one row at the end; the narrower keeps the front half,
    so the spoilt row never reaches the analyst; the analyst is handed exactly the
    right table and still answers wrong. Against the reference the first stage
    failed first, but the cause of the wrong answer is the analyst. Both readings
    are recorded, and neither is called the other.
    """
    case = _case((HALVE,))
    spoilt = list(ROWS[:-1]) + [{"n": 99}]
    result = _run(case, pipeline_env, [
        ("the_table", lambda handed: spoilt),
        ("half_table", lambda handed: handed[:4]),      # drops the spoilt row
        ("row_count", lambda handed: len(handed) + 1),  # wrong, on a right table
    ], tmp_path)
    assert [stage.success for stage in result.stages] == [False, True, False]
    assert result.first_contract_failure == "retriever"
    assert [stage.faithful for stage in result.stages] == [None, True, False]
    assert result.first_unfaithful == "analyst"


def test_a_faithful_stage_handed_a_wrong_table_is_recorded_as_faithful(
    pipeline_env, tmp_path,
):
    case = _case((HALVE,))
    result = _run(case, pipeline_env, [
        ("the_table", lambda handed: ROWS[:6]),
        ("half_table", lambda handed: handed[:3]),
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    assert [stage.faithful for stage in result.stages] == [None, True, True]
    assert result.first_unfaithful == "retriever"


def test_a_malformed_handed_table_leaves_faithfulness_unknown_rather_than_crashing(
    pipeline_env, tmp_path,
):
    """A text-channel upstream can hand on rows without the key column.

    The study's real middle rule sorts by that key, so it cannot even be applied
    to such rows; the faithfulness of the stage that received them is then
    unknown, not false, and the run must record that rather than abort.
    """
    case = _case((KEEP_LOWER_HALF,))
    result = _run(case, pipeline_env, [
        ("the_table", lambda handed: [{"not_n": 1}, {"not_n": 2}]),
        ("shortlisted_table", lambda handed: handed[:1]),
        ("row_count", lambda handed: len(handed)),
    ], tmp_path)
    assert not result.success
    assert result.stages[1].faithful is None
    assert result.first_contract_failure == "retriever"
    assert result.first_unfaithful == "retriever"


def test_the_bound_text_channel_hands_the_reply_on_as_a_string_and_quotes_it(
    pipeline_env, tmp_path,
):
    """Both carriers at once, and the record confirms each from the next stage."""
    case = _case(())
    pipeline_env.recipe[:] = [
        ("the_table", lambda handed: list(ROWS)),
        ("row_count", lambda handed: 8),
    ]
    result = asyncio.run(run_hosted(
        None, case, CHANNELS["text_bound"], PipelineSettings(max_protocol_nudges=0), tmp_path,
    ))
    crossing = result.stages[0].crossing
    assert crossing["carried"] == "reply_bound"
    assert crossing["quoted_in_prompt"] is True
    assert crossing["same_reply_bound_in_next_runtime"] is True
    # The next agent's runtime held the reply as a string, under the study's name.
    assert isinstance(pipeline_env.seen[1].runtime.values.get("handed_reply"), str)


def test_the_plain_text_channel_binds_nothing(pipeline_env, tmp_path):
    case = _case(())
    pipeline_env.recipe[:] = [
        ("the_table", lambda handed: list(ROWS)),
        ("row_count", lambda handed: 8),
    ]
    result = asyncio.run(run_hosted(
        None, case, CHANNELS["text"], PipelineSettings(max_protocol_nudges=0), tmp_path,
    ))
    assert result.stages[0].crossing["carried"] == "reply"
    assert "handed_reply" not in pipeline_env.seen[1].runtime.values


def test_the_signalled_channel_builds_signalling_agents_and_tells_each_its_outputs(
    pipeline_env, tmp_path, monkeypatch,
):
    """Each stage's agent watches the names that stage must assign, and no others."""
    from core import pipeline_evaluator as pipeline
    built = []

    def spy(model, runtime, instructions, settings, channel, outputs=()):
        agent = pipeline.FencedCodeAgent(model, runtime=runtime, max_steps=settings.step_budget)
        built.append((channel.signals, tuple(outputs)))
        return agent
    monkeypatch.setattr(pipeline, "_agent", spy)
    case = _case((HALVE,))
    _run_with_channel = lambda ch: asyncio.run(run_hosted(
        None, case, CHANNELS[ch], PipelineSettings(max_protocol_nudges=0), tmp_path))
    pipeline_env.recipe[:] = [
        ("the_table", lambda handed: list(ROWS)),
        ("half_table", lambda handed: handed[:4]),
        ("row_count", lambda handed: len(handed)),
    ]
    _run_with_channel("object_signalled")
    assert built == [(True, ("the_table",)), (True, ("half_table",)), (True, ("row_count",))]
    built.clear()
    pipeline_env.recipe[:] = [
        ("the_table", lambda handed: list(ROWS)),
        ("half_table", lambda handed: handed[:4]),
        ("row_count", lambda handed: len(handed)),
    ]
    _run_with_channel("object_described")
    assert [signals for signals, _ in built] == [False, False, False]
