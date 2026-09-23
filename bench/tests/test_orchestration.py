"""An orchestrator directs three scripted workers through each arm, end to end.

No live model: every agent's replies are scripted, in the order the agents make
requests. That order is, for each worker, the orchestrator's step that runs it
followed by that worker's own steps, then the orchestrator's final answer. So
the script encodes exactly the coordination the orchestrator is meant to
perform, and the test asks whether the machinery under it — the worker agents
as variables, the media, the judging — carries it through.
"""

import asyncio
import json
import tempfile
from pathlib import Path

from cave_agent.models import LiteLLMModel
import pytest

from core.errors import InfrastructureError

from cases.pipeline import PIPELINE_CASES, depth_cases
from core.pipeline import CHANNELS
from core.pipeline_evaluator import PipelineSettings
from core.orchestration import ARMS, INPUT_TABLE, Medium, describe_worker, worker_specs
from core.orchestration_evaluator import (
    HANDED_CHANNEL, PRODUCER, orchestrator_task, run_orchestration,
)
from core.prompts import orchestrator_instructions
from tests.test_agents import ScriptedLiteLLM, fenced_reply, text_reply, tool_reply


CASE = next(case for case in PIPELINE_CASES if case.name == "branch_top_deposits_10")
ROWS = CASE.expected_rows()
HALF = CASE.middles[0].select(CASE.task, ROWS)
ANSWERS = CASE.follow_up.compute(HALF)
ANSWER_CODE = (
    f"total_deposits_thousand_usd = {ANSWERS[0]}\n"
    f"distinct_state_count = {ANSWERS[1]}\n"
    f"main_office_count = {ANSWERS[2]}"
)
TABLE_JSON = json.dumps({"branch_table": ROWS})
HALF_JSON = json.dumps({"shortlisted_table": HALF})

# What a correct orchestrator writes in the cave arm: the calls its workers'
# descriptions name, as the library's own example has them.
CAVE_ORCHESTRATOR = [
    "await retriever.run('compute the table the task asks for, as branch_table')\n"
    "t = await retriever.runtime.retrieve('branch_table')\nprint(type(t).__name__, len(t))",
    f"narrower.runtime.update_variable('{INPUT_TABLE}', t)\n"
    "await narrower.run('keep the half that sorts first by branch_id, as shortlisted_table')\n"
    "h = await narrower.runtime.retrieve('shortlisted_table')\nprint(len(h))",
    f"analyst.runtime.update_variable('{INPUT_TABLE}', h)\n"
    "r = await analyst.run('answer the question about this table')\nprint(r.content[:40])",
]
# And in the text arms: only run, with the table written into the instruction.
TEXT_ORCHESTRATOR = [
    "r1 = await retriever.run('compute the table the task asks for, as branch_table')\n"
    "print(r1.content[-200:])",
    "r2 = await narrower.run('Keep the half of this table that sorts first by branch_id, "
    "as shortlisted_table. The table:\\n' + r1.content)\nprint(r2.content[-200:])",
    "r3 = await analyst.run('Answer the question about this table:\\n' + r2.content)\n"
    "print(r3.content[:40])",
]
FINAL = text_reply("Ran retriever, narrower, analyst; the analyst's answer stands.")


def _interleave(orchestrator, workers):
    """Every agent's replies, as the agents will request them."""
    replies = []
    for step, worker in zip(orchestrator, workers):
        replies += [fenced_reply(step)] + worker
    return replies + [FINAL]


def _run(arm: str, replies):
    model = LiteLLMModel(model_id="m", api_key="k", base_url="u", temperature=0.1)
    model._litellm = ScriptedLiteLLM(replies)
    with tempfile.TemporaryDirectory() as workdir:
        result = asyncio.run(run_orchestration(
            model, CASE, ARMS[arm], PipelineSettings(max_protocol_nudges=0), Path(workdir),
        ))
    return result, model._litellm


def _assert_clean_success(result, provider):
    assert result.success and result.ran_as_designed, result.workers
    assert result.ran == ["retriever", "narrower", "analyst"]
    assert result.repeated == [] and result.skipped == []
    assert [w["success"] for w in result.workers] == [True, True, True]
    assert not provider.replies, "every scripted reply was consumed"


def test_the_cave_arm_hands_the_table_as_an_object_through_the_worker_s_runtime():
    result, provider = _run("cave", _interleave(CAVE_ORCHESTRATOR, [
        [fenced_reply("import pandas as pd\nbranch_table = pd.DataFrame(" + json.dumps(ROWS) + ")"),
         text_reply("table done")],
        [fenced_reply(f"shortlisted_table = {INPUT_TABLE}.sort_values('branch_id')"
                      f".head(len({INPUT_TABLE}) // 2)"),
         text_reply("halved")],
        [fenced_reply(ANSWER_CODE), text_reply("answered")],
    ]))
    _assert_clean_success(result, provider)
    # The narrower's runtime described the object it was handed, as the hosted study's
    # study's described arm does: its system prompt names the row count.
    narrower_system = str(result.workers[1]["messages"][0].content)
    assert f"{len(ROWS)} rows" in narrower_system and "branch_id" in narrower_system


def test_the_text_arm_carries_the_table_inside_the_instruction():
    result, provider = _run("text", _interleave(TEXT_ORCHESTRATOR, [
        [fenced_reply("print('computing')"), text_reply("Here.\n```json\n" + TABLE_JSON + "\n```")],
        [fenced_reply("print('halving')"), text_reply("Halved.\n```json\n" + HALF_JSON + "\n```")],
        [fenced_reply(ANSWER_CODE), text_reply("answered")],
    ]))
    _assert_clean_success(result, provider)
    # The narrower's question carried the retriever's reply: the table crossed
    # as text, inside what the orchestrator wrote.
    narrower_query = next(str(m.content) for m in result.workers[1]["messages"]
                          if "user" in str(m.role).lower())
    assert TABLE_JSON in narrower_query


def test_the_json_arm_s_workers_act_through_tool_calls():
    result, provider = _run("json", _interleave(TEXT_ORCHESTRATOR, [
        [tool_reply("print('computing')"), text_reply("Here.\n```json\n" + TABLE_JSON + "\n```")],
        [tool_reply("print('halving')"), text_reply("Halved.\n```json\n" + HALF_JSON + "\n```")],
        [tool_reply(ANSWER_CODE), text_reply("answered")],
    ]))
    _assert_clean_success(result, provider)
    # The workers were sent the tool; the orchestrator, a fenced-code agent, was not.
    worker_requests = [r for r in provider.requests if "tools" in r]
    assert worker_requests and all("tools" not in r or r["tools"] for r in provider.requests)
    orchestrator_system = str(result.orchestrator["messages"][0].content)
    assert "fenced ```python code block" in orchestrator_system


def test_a_reply_table_is_read_under_the_orchestrator_s_name_for_it():
    """The orchestrator writes the instruction and may name the output as it likes.

    A worker that wrote its one table under another key delivered it all the
    same; the study measures the medium, not the orchestrator's naming.
    """
    renamed = json.dumps({"top_branches": ROWS})
    result, _ = _run("text", _interleave(TEXT_ORCHESTRATOR, [
        [fenced_reply("print('computing')"), text_reply("```json\n" + renamed + "\n```")],
        [fenced_reply("print('halving')"), text_reply("```json\n" + HALF_JSON + "\n```")],
        [fenced_reply(ANSWER_CODE), text_reply("answered")],
    ]))
    assert result.workers[0]["success"], result.workers[0]


def test_a_skipped_worker_is_recorded_beside_the_verdict_not_in_it():
    """The verdict is the answer; how the workers were directed is diagnosis.

    The scripted analyst produces the right numbers without a table. The run
    counts as a success, and the record says the retriever and narrower never
    ran, so a reader can see it for the guess it is — without the verdict
    charging an arm twice for one failure when a worker is retried.
    """
    replies = (
        [fenced_reply("r = await analyst.run('just answer')\nprint(r.content)")]
        + [fenced_reply(ANSWER_CODE), text_reply("guessed")]
        + [FINAL]
    )
    result, _ = _run("cave", replies)
    assert result.success
    assert result.ran == ["analyst"]
    assert not result.ran_as_designed
    assert result.skipped == ["retriever", "narrower"] and result.repeated == []
    assert result.failure is None


def test_runs_are_recorded_in_the_order_they_happened():
    """An orchestrator that runs the analyst first and then the retriever is not
    one that ran them in order with the names shuffled; the record keeps time."""
    replies = (
        [fenced_reply("await analyst.run('answer')")]
        + [fenced_reply(ANSWER_CODE), text_reply("answered")]
        + [fenced_reply("await retriever.run('go')")]
        + [fenced_reply("print(1)"), text_reply("first")]
        + [fenced_reply("await retriever.run('again')")]
        + [fenced_reply("print(2)"), text_reply("second")]
        + [FINAL]
    )
    result, _ = _run("cave", replies)
    assert result.ran == ["analyst", "retriever", "retriever"]
    assert not result.ran_as_designed
    assert result.repeated == ["retriever"] and result.skipped == ["narrower"]
    # Two model calls per run, code then answer: spent is summed over both runs.
    assert result.workers[0]["runs"] == 2 and result.workers[0]["steps"] == 4


def test_a_worker_run_again_remembers_nothing_of_its_first_run():
    """CaveAgent.run appends to history; here each run starts a fresh conversation.

    Otherwise a text-arm worker retried would still hold the table it was sent
    the first time, and a retry would be cheaper in that arm than in the cave
    arm, where the object is in the runtime either way.
    """
    replies = (
        [fenced_reply("await retriever.run('first instruction')")]
        + [fenced_reply("print(1)"), text_reply("first")]
        + [fenced_reply("await retriever.run('second instruction')")]
        + [fenced_reply("print(2)"), text_reply("second")]
        + [FINAL]
    )
    result, provider = _run("text", replies)
    # The worker's second-run requests to the model carried no trace of its
    # first run. (The orchestrator's own history names both runs; it is not
    # the worker, and is left out by its system prompt.)
    worker_requests = [r for r in provider.requests
                       if "orchestrator of a team" not in str(r["messages"][0].get("content"))]
    second_run_requests = [r for r in worker_requests
                           if any("second instruction" in str(m.get("content")) for m in r["messages"])]
    assert second_run_requests
    for request in second_run_requests:
        texts = [str(m.get("content")) for m in request["messages"]]
        assert not any("first instruction" in t or "print(1)" in t for t in texts)
    # Both runs are in the transcript, each opening with the system prompt.
    transcript = result.workers[0]["messages"]
    assert sum("system" in str(m.role).lower() for m in transcript) == 2


def test_the_first_wrong_worker_is_named_when_the_answer_is_wrong():
    """The narrower halves wrongly and the analyst, answering from that, is wrong too."""
    result, _ = _run("cave", _interleave(CAVE_ORCHESTRATOR, [
        [fenced_reply("import pandas as pd\nbranch_table = pd.DataFrame(" + json.dumps(ROWS) + ")"),
         text_reply("done")],
        [fenced_reply(f"shortlisted_table = {INPUT_TABLE}.head(1)"), text_reply("oops")],
        [fenced_reply("total_deposits_thousand_usd = 1\ndistinct_state_count = 1\n"
                      "main_office_count = 1"), text_reply("answered")],
    ]))
    assert result.ran_as_designed
    assert [w["success"] for w in result.workers] == [True, False, False]
    assert not result.success
    assert result.failure == "narrower"


def test_every_worker_reads_its_output_contract_beside_the_instruction():
    """The orchestrator writes the instruction; the host appends what the worker owes.

    Without this a live retriever computed the right table and assigned it to
    a name of its own, and a text-arm worker had no key to write its table
    under. The contract is the same one every agent in the suite reads.
    """
    for arm, orchestrator, step in (("cave", CAVE_ORCHESTRATOR, fenced_reply),
                                    ("json", TEXT_ORCHESTRATOR, tool_reply)):
        result, _ = _run(arm, _interleave(orchestrator, [
            [step("print(1)"), text_reply("```json\n" + TABLE_JSON + "\n```")],
            [step("print(2)"), text_reply("```json\n" + HALF_JSON + "\n```")],
            [step("print(3)"), text_reply("done")],
        ]))
        owed = ("branch_table", "shortlisted_table", "total_deposits_thousand_usd")
        for worker, name in zip(result.workers, owed):
            query = next(str(m.content) for m in worker["messages"] if "user" in str(m.role).lower())
            assert "Required outputs for this turn" in query, (arm, worker["name"])
            assert f"- {name}:" in query, (arm, worker["name"], name)
            assert query.index("Required outputs") > 0     # after the instruction


def test_the_orchestrator_prompt_is_one_text_whatever_the_arm():
    """The arm lives in the workers' descriptions, which the runtime lists.

    The orchestrator's own prompt takes no arm, so it cannot differ between
    arms; and it names no medium — how a table is stored or moved is said only
    where the library's example says it, in each worker variable's description.
    """
    text = orchestrator_instructions()
    own = text[: text.index("Executing code:")].lower()
    for word in ("parquet", "update_variable", "retrieve(", "json", ".content", "dataframe"):
        assert word not in own, f"the orchestrator's own text must not name {word}"
    assert "the runtime describes each below" in own


def test_worker_descriptions_state_the_arm_s_calls_and_nothing_else_differs():
    """The arm is the API a description states; what the worker is for is shared."""
    specs = worker_specs(CASE)
    cave = [describe_worker(spec, ARMS["cave"]) for spec in specs]
    text = [describe_worker(spec, ARMS["text"]) for spec in specs]
    assert describe_worker(specs[1], ARMS["json"]) == text[1], "text and json expose the same API"
    assert f"narrower.runtime.update_variable('{INPUT_TABLE}', table) — a plain call, not awaited" in cave[1]
    assert "await narrower.runtime.retrieve('shortlisted_table')" in cave[1]
    assert "runtime" not in text[1].split("Use it from code")[1].split("It cannot reach")[0]
    assert "written out in full" in text[1] and "written out in full" not in text[0]
    for cave_text, text_text in zip(cave, text):
        assert cave_text.split(" Use it from code")[0] == text_text.split(" Use it from code")[0]


def test_the_task_names_no_worker_and_asks_the_hosted_study_s_three_things():
    task = orchestrator_task(CASE)
    for name in ("retriever", "narrower", "analyst"):
        assert name not in task.lower()
    assert CASE.producer_query() in task
    assert CASE.middles[0].query(CASE.task) in task
    assert CASE.follow_up.query in task


def test_the_cave_arm_s_workers_read_the_hosted_study_s_object_prompt():
    """One family of agents: a cave worker is the hosted study's object-arm agent."""
    assert HANDED_CHANNEL[Medium.CAVE] in CHANNELS
    assert PRODUCER[Medium.CAVE] is CHANNELS["object"].producer
    assert PRODUCER[Medium.TEXT] is CHANNELS["text"].producer


def test_a_list_of_rows_from_upstream_is_accepted_by_the_next_worker_s_slot():
    """The contract allows a table as a list of row dicts; the slot must too.

    A slot typed DataFrame refused the list at update_variable and set the
    orchestrator a conversion the medium does not ask for.
    """
    orchestrator = [
        "await retriever.run('compute the table, as branch_table')\n"
        "t = await retriever.runtime.retrieve('branch_table')\nprint(type(t).__name__)",
        f"narrower.runtime.update_variable('{INPUT_TABLE}', t)\n"
        "await narrower.run('keep the half that sorts first, as shortlisted_table')\n"
        "h = await narrower.runtime.retrieve('shortlisted_table')\nprint(len(h))",
        f"analyst.runtime.update_variable('{INPUT_TABLE}', h)\n"
        "await analyst.run('answer')\nprint('ok')",
    ]
    result, provider = _run("cave", _interleave(orchestrator, [
        [fenced_reply("branch_table = " + json.dumps(ROWS)), text_reply("as rows")],
        [fenced_reply(f"import pandas as pd\nshortlisted_table = pd.DataFrame({INPUT_TABLE})"
                      f".sort_values('branch_id').head(len({INPUT_TABLE}) // 2)"),
         text_reply("halved")],
        [fenced_reply(ANSWER_CODE), text_reply("answered")],
    ]))
    _assert_clean_success(result, provider)


def test_a_downstream_worker_mutating_the_shared_object_does_not_change_the_upstream_verdict():
    """The cave arm hands the object itself on; each worker is judged on what it delivered.

    The narrower here shrinks the very frame the retriever made, in place. The
    retriever's verdict is taken when it returned, so it still stands.
    """
    result, _ = _run("cave", _interleave(CAVE_ORCHESTRATOR, [
        [fenced_reply("import pandas as pd\nbranch_table = pd.DataFrame(" + json.dumps(ROWS) + ")"),
         text_reply("done")],
        [fenced_reply(f"{INPUT_TABLE}.sort_values('branch_id', inplace=True)\n"
                      f"{INPUT_TABLE}.drop({INPUT_TABLE}.index[len({INPUT_TABLE}) // 2:], inplace=True)\n"
                      f"shortlisted_table = {INPUT_TABLE}"),
         text_reply("halved in place")],
        [fenced_reply(ANSWER_CODE), text_reply("answered")],
    ]))
    assert result.success
    assert [w["success"] for w in result.workers] == [True, True, True], result.workers
    assert result.workers[0]["rows"] == len(ROWS) and result.workers[1]["rows"] == len(HALF)


def test_a_provider_failure_inside_a_worker_is_an_outage_not_a_wrong_answer():
    """The delivery study's rule: a model error the conversation did not cause is retried.

    The provider fails on the worker's request. Left alone, the worker would
    stop with model_error, the orchestrator would carry on, and the run would
    be stored as a wrong answer that no rerun ever replaces.
    """

    class FailsOnTheWorker(ScriptedLiteLLM):
        async def acompletion(self, **request):
            if "orchestrator of a team" not in str(request["messages"][0].get("content")):
                raise ValueError("gateway rejected the request")
            return await super().acompletion(**request)

    # The orchestrator's script runs to a clean final answer, so the only way
    # this run can end as an outage is the worker's failure being surfaced.
    model = LiteLLMModel(model_id="m", api_key="k", base_url="u", temperature=0.1)
    model._litellm = FailsOnTheWorker([
        fenced_reply("await retriever.run('go')"),
        fenced_reply("print('carrying on regardless')"),
        FINAL,
    ])
    with tempfile.TemporaryDirectory() as workdir:
        with pytest.raises(InfrastructureError):
            asyncio.run(run_orchestration(
                model, CASE, ARMS["cave"], PipelineSettings(max_protocol_nudges=0), Path(workdir),
            ))


def test_spent_is_the_suite_s_unified_count_not_the_provider_total():
    result, _ = _run("cave", _interleave(CAVE_ORCHESTRATOR, [
        [fenced_reply("import pandas as pd\nbranch_table = pd.DataFrame(" + json.dumps(ROWS) + ")"),
         text_reply("done")],
        [fenced_reply(f"shortlisted_table = {INPUT_TABLE}.head(len({INPUT_TABLE}) // 2)"),
         text_reply("halved")],
        [fenced_reply(ANSWER_CODE), text_reply("answered")],
    ]))
    for record in [result.orchestrator, *result.workers]:
        spent = record["spent"]
        assert {"model_calls", "prompt_tokens", "completion_tokens",
                "estimated_prompt_tokens", "estimated_completion_tokens"} <= set(spent)
        assert spent["model_calls"] == record["steps"]


def test_depth_pipelines_give_each_relay_its_own_name_and_rule():
    case = depth_cases(4)[0]
    specs = worker_specs(case)
    names = [s.name for s in specs]
    assert len(names) == len(set(names)) == 4
    for spec in specs[1:-1]:
        assert spec.role == "relay"
        assert case.middles[0].query(case.task) in spec.purpose     # its own rule
        assert "half" not in spec.purpose.lower()


def test_the_file_arm_carries_the_table_as_a_parquet_path_in_the_instruction():
    """A worker writes its table where its description says; the orchestrator names that path on."""
    specs = worker_specs(CASE)
    described = describe_worker(specs[0], ARMS["file"], Path("/work/retriever/branch_table.parquet"))
    assert "'/work/retriever/branch_table.parquet'" in described and "runtime" not in described
    # A handed worker's description frames the instruction as the text arms' does:
    # everything it needs, the path among it — not the path alone.
    handed_file = describe_worker(specs[1], ARMS["file"], Path("/work/narrower/out.parquet"))
    handed_text = describe_worker(specs[1], ARMS["text"])
    frame = "everything it needs must be in the instruction you send, including"
    assert frame in handed_file and frame in handed_text

    orchestrator = [
        "r1 = await retriever.run('compute the table the task asks for')\nprint('ok')",
        "await narrower.run('Keep the half that sorts first by branch_id. Read: ' + RETRIEVED)\nprint('ok')",
        "r3 = await analyst.run('Answer the question. Read: ' + NARROWED)\nprint(r3.content[:20])",
    ]
    model = LiteLLMModel(model_id="m", api_key="k", base_url="u", temperature=0.1)
    with tempfile.TemporaryDirectory() as workdir:
        retrieved = f"{workdir}/retriever/branch_table.parquet"
        narrowed = f"{workdir}/narrower/shortlisted_table.parquet"
        steps = [step.replace("RETRIEVED", repr(retrieved)).replace("NARROWED", repr(narrowed))
                 for step in orchestrator]
        model._litellm = ScriptedLiteLLM(_interleave(steps, [
            [fenced_reply(f"import pandas as pd\npd.DataFrame({json.dumps(ROWS)})"
                          f".to_parquet({retrieved!r}, index=False)"), text_reply("written")],
            [fenced_reply(f"import pandas as pd\nt = pd.read_parquet({retrieved!r})\n"
                          f"t.sort_values('branch_id').head(len(t) // 2).to_parquet({narrowed!r}, index=False)"),
             text_reply("halved")],
            [fenced_reply(ANSWER_CODE), text_reply("answered")],
        ]))
        result = asyncio.run(run_orchestration(
            model, CASE, ARMS["file"], PipelineSettings(max_protocol_nudges=0), Path(workdir),
        ))
    _assert_clean_success(result, model._litellm)
    # The narrower was told the path, and its prompt said a file is where its table is.
    narrower = result.workers[1]["messages"]
    assert "Parquet" in str(narrower[0].content) and "no data is registered" in str(narrower[0].content)
    assert retrieved in next(str(m.content) for m in narrower if "user" in str(m.role).lower())
    # The orchestrator's description of the retriever named that very path.
    assert retrieved in str(result.orchestrator["messages"][0].content)
