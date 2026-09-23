"""The rounds study: the chains' rules, what the host can tell apart, and the arms end to end.

Every rule is checked against the object it edits: that it is a pure function,
that no two stages leave the object in the same state, and that a skipped, a
repeated and a stale-input stage each show up somewhere the host can read. Then,
with scripted replies as :mod:`tests.test_fidelity` scripts them, a chain runs
through each arm and every hop's record is checked.
"""

import asyncio
import copy
import json
import re
import tempfile
from pathlib import Path

from cave_agent.models import LiteLLMModel
import pandas as pd
import pytest

from cases.rounds import DEPTHS, ROUNDS_CASES
from cases.rounds._control_branches import TASK as BRANCHES, REVISIONS as BRANCH_REVISIONS
from core.fidelity import INPUT_SLOT, RECEIVED, TOKEN_LIMIT, compare, serialized_tokens, to_jsonable
from core.orchestration import ARMS, describe_worker, worker_specs
from core.paradigms import table_paths
from core.pipeline_evaluator import PipelineSettings
from core.rounds import CARRIED, RoundsCase, align, cases
from core.rounds_evaluator import orchestrator_task, run_rounds
from core.runtime_catalog import select_runtime_tables
from tests.test_agents import ScriptedLiteLLM, fenced_reply, text_reply, tool_reply


DEEPEST = [case for case in ROUNDS_CASES if case.depth == max(DEPTHS)]
SETTINGS = PipelineSettings(step_budget=14, max_protocol_nudges=0, orchestrator_step_budget=24)


@pytest.fixture(scope="module")
def loaded():
    tables = {}
    for case in ROUNDS_CASES:
        for table in select_runtime_tables(case.data_sources):
            if table.name not in tables:
                tables[table.name] = table.loader()
    return tables


@pytest.fixture(scope="module", params=DEEPEST, ids=lambda case: case.task.name)
def chain(request, loaded):
    case = request.param
    return case, case.standards(loaded)


# ----- the rules ---------------------------------------------------------------

def test_every_rule_is_a_pure_function(chain):
    case, standards = chain
    for index, revision in enumerate(case.revisions):
        before = copy.deepcopy(standards[index])
        once, twice = revision.applied_to(standards[index]), revision.applied_to(standards[index])
        assert compare(standards[index], before, row_key=case.task.row_key).intact, revision.name
        assert compare(once, twice, row_key=case.task.row_key).intact, revision.name


def test_no_two_stages_leave_the_object_in_the_same_state(chain):
    """One assertion for a rule that is a no-op, idempotent, or undone by a later one."""
    case, standards = chain
    for i, one in enumerate(standards):
        for j, other in enumerate(standards):
            if i < j:
                assert not compare(one, other, row_key=case.task.row_key).intact, (i, j)


def test_a_skipped_stage_shows_as_the_version_before_it(chain):
    case, standards = chain
    for index, revision in enumerate(case.revisions, start=1):
        found = align(standards[index - 1], standards, standards, revision=revision,
                      row_key=case.task.row_key)
        assert found.as_of == index - 1


def test_a_stage_that_worked_from_an_older_version_is_named(chain):
    case, standards = chain
    for index, revision in enumerate(case.revisions, start=1):
        for older in range(index - 1):
            stale = revision.applied_to(standards[older])
            found = align(stale, standards, standards, revision=revision, row_key=case.task.row_key)
            assert found.as_of is None and found.edited_from == older, (index, older)


def test_a_repeated_stage_changes_the_object(chain):
    """So that a repeat is visible in the object as well as in the run record."""
    case, standards = chain
    for index, revision in enumerate(case.revisions, start=1):
        twice = revision.applied_to(standards[index])
        assert not compare(twice, standards[index], row_key=case.task.row_key).intact, index


def test_the_object_stays_small_at_every_stage(chain):
    case, standards = chain
    for index, standard in enumerate(standards):
        assert serialized_tokens(standard) <= TOKEN_LIMIT, (case.name, index)


def test_the_question_answers_differently_at_every_stage(chain):
    """The end-to-end answer must depend on the last hop, not only on the first."""
    case, standards = chain
    answers = [tuple(case.follow_up.compute(standard)) for standard in standards]
    assert len(set(answers)) == len(answers)


def test_the_local_hour_column_keeps_agreeing_with_the_timestamps(loaded):
    """The events chain nudges start times; no nudge may carry a row into another hour."""
    case = next(case for case in DEEPEST if case.task.name == "rounds_tz_events")
    for standard in case.standards(loaded)[1:]:
        assert (standard["hour_local"] == standard["began_at"].dt.hour).all()


_TRANSPORT_WORDS = re.compile(
    r"\b(json|file|serializ|serialis|write out|written out|parquet|reply|print|joblib|pickle)",
    re.IGNORECASE,
)


def test_a_rule_says_what_to_change_and_nothing_about_sending_or_sources(chain):
    case, _ = chain
    sources = {name.lower() for name in case.data_sources}
    for revision in case.revisions:
        assert not _TRANSPORT_WORDS.search(revision.ask), revision.name
        assert not any(source in revision.ask.lower() for source in sources), revision.name


def test_the_depths_of_one_object_are_prefixes_of_one_chain():
    by_task = {}
    for case in ROUNDS_CASES:
        by_task.setdefault(case.task.name, []).append(case)
    for name, group in by_task.items():
        group.sort(key=lambda case: case.depth)
        assert [case.depth for case in group] == list(DEPTHS), name
        longest = group[-1].revisions
        for case in group:
            assert case.revisions == longest[: len(case.revisions)], name


def test_a_chain_whose_stages_share_an_output_name_is_refused():
    case = DEEPEST[0]
    clashing = tuple(
        revision if index else type(revision)(**{**revision.__dict__, "output": case.task.output})
        for index, revision in enumerate(case.revisions)
    )
    with pytest.raises(ValueError, match="one name"):
        RoundsCase(case.task, clashing)


def test_every_worker_of_a_chain_has_its_own_name_and_rule():
    case = next(case for case in DEEPEST if case.task.name == "rounds_control_branches")
    specs = worker_specs(case)
    assert [spec.name for spec in specs] == \
        ["producer", *(f"reviser_{k}" for k in range(1, 8)), "consumer"]
    assert len({spec.name for spec in specs}) == len(specs)
    for spec, revision in zip(specs[1:-1], case.revisions):
        assert revision.ask in spec.purpose
    cave = describe_worker(specs[3], ARMS["cave"], input_slot=INPUT_SLOT, noun="object")
    assert f"update_variable('{INPUT_SLOT}', obj)" in cave and "retrieve('branch_table_3')" in cave
    file = describe_worker(specs[3], ARMS["file"], Path("/w/reviser_3/branch_table_3.parquet"),
                           input_slot=INPUT_SLOT, noun="object")
    assert "writes the object it made to the file '/w/reviser_3/branch_table_3.parquet'" in file


def test_the_orchestrator_is_told_the_order_and_not_the_question():
    case = next(case for case in DEEPEST if case.task.name == "rounds_control_branches")
    task = orchestrator_task(case)
    assert "Each part works on the object the part before it produced" in task
    assert task.count("Next, to the object as the part before this one left it:") == 7
    assert case.follow_up.query not in task
    for revision in case.revisions:
        assert revision.ask in task


# ----- the arms, end to end -----------------------------------------------------

CASE = next(case for case in ROUNDS_CASES
            if case.task.name == "rounds_control_branches" and case.depth == 4)
FINAL = text_reply("Ran the producer, the revisers in order, then the consumer.")
_SOURCE = table_paths(select_runtime_tables(CASE.data_sources), None)["fdic_sod_branches_df"]
PRODUCER_CODE = (
    f"import pandas as pd\nbranches = pd.read_parquet('{_SOURCE}')\n"
    "day = branches[branches['report_date'] == '2024-06-30']\n"
    "ranked = day.sort_values(['branch_deposits_thousand_usd', 'branch_id'], ascending=[False, True]).head(10)\n"
    "branch_table = pd.DataFrame({\n"
    "    'branch_id': ranked['branch_id'].astype('string'),\n"
    "    'bank_name': ranked['bank_name'].astype('string'),\n"
    "    'branch_state': ranked['branch_state'].astype('string'),\n"
    "    'main_office_indicator': ranked['main_office_indicator'].astype('string'),\n"
    "    'branch_deposits_thousand_usd': ranked['branch_deposits_thousand_usd'].astype('Int64'),\n"
    "}).reset_index(drop=True)"
)


def _standards():
    tables = {table.name: table.loader() for table in select_runtime_tables(CASE.data_sources)}
    return CASE.standards(tables)


def _revise(index: int, source: str, case=None) -> str:
    """A reviser's code: keep what it was handed, edit a copy, hand the copy on."""
    revision = (case or CASE).revisions[index - 1]
    return (
        f"{CARRIED} = {source}\n"
        f"{revision.output} = {CARRIED}.copy()\n"
        f"chosen = {revision.output}['branch_id'] == '{BRANCH_REVISIONS[index - 1].ask.split(chr(39))[1]}'\n"
        f"{revision.output}.loc[chosen, 'branch_deposits_thousand_usd'] += {index}\n"
        f"{revision.output}.loc[chosen, 'main_office_indicator'] = 'R{index}'"
    )


def _consume(source: str) -> str:
    return (
        f"{RECEIVED} = {source}\n"
        f"total_deposits_thousand_usd = int({RECEIVED}['branch_deposits_thousand_usd'].sum())\n"
        f"corrected_branches = int({RECEIVED}['main_office_indicator'].str.startswith('R').sum())"
    )


def _run(arm: str, replies, workdir: Path, case=CASE):
    model = LiteLLMModel(model_id="m", api_key="k", base_url="u", temperature=0.1)
    model._litellm = ScriptedLiteLLM(replies)
    result = asyncio.run(run_rounds(model, case, ARMS[arm], SETTINGS, workdir))
    return result, model._litellm


def _cave_script(worker_codes, *, sources=None):
    """The orchestrator's cave-arm steps, and each worker's own two replies."""
    names = ["producer", *(f"reviser_{k}" for k in range(1, len(CASE.revisions) + 1)), "consumer"]
    outputs = [CASE.task.output, *(r.output for r in CASE.revisions), RECEIVED]
    sources = sources or {}
    replies = []
    for index, (name, output, code) in enumerate(zip(names, outputs, worker_codes)):
        step = ""
        if index:
            held = sources.get(index, f"obj{index - 1}")
            step = f"{name}.runtime.update_variable('{INPUT_SLOT}', {held})\n"
        step += f"await {name}.run('do your part')\n"
        if name != "consumer":
            step += f"obj{index} = await {name}.runtime.retrieve('{output}')\nprint(type(obj{index}).__name__)"
        else:
            step += "print('done')"
        replies += [fenced_reply(step), fenced_reply(code), text_reply("done")]
    return replies + [FINAL]


def test_the_cave_arm_carries_the_object_through_every_hop():
    standards = _standards()
    codes = [PRODUCER_CODE] + [_revise(k, INPUT_SLOT) for k in range(1, 4)] + [_consume(INPUT_SLOT)]
    with tempfile.TemporaryDirectory() as workdir:
        result, provider = _run("cave", _cave_script(codes), Path(workdir))
    assert result.success and result.depth == 4 and not provider.replies
    assert result.ran == ["producer", "reviser_1", "reviser_2", "reviser_3", "consumer"]
    assert result.chain == [0, 1, 2, 3, 3], result.chain
    for hop in result.hops[1:]:
        assert hop["carried"] and hop["applied"], hop
        assert hop["edited"] is not False
    assert result.workers[-1]["answered"] and result.workers[-1]["received_bound"]
    assert result.elapsed_s >= 0 and result.host_observations > 0
    assert compare(standards[-1], standards[-1], row_key=CASE.task.row_key).intact


def test_a_downstream_agent_editing_in_place_does_not_rewrite_what_the_host_saw():
    """The cave arm hands on a reference; every record is a copy taken when the run returned."""
    in_place = [PRODUCER_CODE]
    for index in range(1, 4):
        revision = CASE.revisions[index - 1]
        branch = BRANCH_REVISIONS[index - 1].ask.split("'")[1]
        in_place.append(
            f"{CARRIED} = {INPUT_SLOT}.copy()\n"
            f"{revision.output} = {INPUT_SLOT}\n"
            f"chosen = {revision.output}['branch_id'] == '{branch}'\n"
            f"{revision.output}.loc[chosen, 'branch_deposits_thousand_usd'] += {index}\n"
            f"{revision.output}.loc[chosen, 'main_office_indicator'] = 'R{index}'"
        )
    in_place.append(_consume(INPUT_SLOT))
    with tempfile.TemporaryDirectory() as workdir:
        result, _ = _run("cave", _cave_script(in_place), Path(workdir))
    assert result.chain == [0, 1, 2, 3, 3], result.chain
    assert all(hop["applied"] for hop in result.hops), [hop["lost"] for hop in result.hops]


def test_a_hop_that_read_an_earlier_version_is_named_by_what_it_edited_from():
    codes = [PRODUCER_CODE] + [_revise(k, INPUT_SLOT) for k in range(1, 4)] + [_consume(INPUT_SLOT)]
    with tempfile.TemporaryDirectory() as workdir:
        # reviser_3 is handed the producer's object instead of reviser_2's.
        result, _ = _run("cave", _cave_script(codes, sources={3: "obj0"}), Path(workdir))
    third = result.hops[3]
    assert third["carried"] is False and third["edited"] is True
    assert third["in_as_of"] == 0 and third["edited_from"] == 0 and third["applied"] is False
    assert result.failure == "reviser_3" and not result.success


def test_a_skipped_edit_leaves_the_object_at_the_version_before_it():
    codes = [PRODUCER_CODE] + [_revise(k, INPUT_SLOT) for k in range(1, 4)] + [_consume(INPUT_SLOT)]
    # reviser_2 hands on what it was given, unchanged.
    codes[2] = f"{CARRIED} = {INPUT_SLOT}\n{CASE.revisions[1].output} = {INPUT_SLOT}"
    with tempfile.TemporaryDirectory() as workdir:
        result, _ = _run("cave", _cave_script(codes), Path(workdir))
    second = result.hops[2]
    assert second["carried"] is True and second["edited"] is False and second["applied"] is False
    assert result.chain[2] == 1


def test_the_text_arm_carries_the_object_in_the_instruction_at_every_hop():
    standards = _standards()
    names = ["producer", "reviser_1", "reviser_2", "reviser_3", "consumer"]
    outputs = [CASE.task.output, *(r.output for r in CASE.revisions)]
    replies = []
    for index, name in enumerate(names):
        if index:
            step = (f"r{index} = await {name}.run('Here is the object:\\n' + r{index - 1}.content)\n"
                    f"print(r{index}.content[:40])")
        else:
            step = f"r0 = await {name}.run('build it')\nprint(r0.content[-200:])"
        rebuilt = repr(to_jsonable(standards[min(index, len(standards) - 1)]))
        if name == "consumer":
            code = (f"import pandas as pd\n{RECEIVED} = pd.DataFrame({rebuilt})\n"
                    f"total_deposits_thousand_usd = int({RECEIVED}['branch_deposits_thousand_usd'].sum())\n"
                    f"corrected_branches = int({RECEIVED}['main_office_indicator'].str.startswith('R').sum())")
            reply = text_reply("Answered.")
        else:
            name_of = outputs[index]
            code = (f"import pandas as pd\n{name_of} = pd.DataFrame({rebuilt})"
                    + (f"\n{CARRIED} = {name_of}.copy()" if index else ""))
            reply = text_reply("Here.\n```json\n"
                               + json.dumps({name_of: to_jsonable(standards[index])}) + "\n```")
        replies += [fenced_reply(step), fenced_reply(code), reply]
    with tempfile.TemporaryDirectory() as workdir:
        result, provider = _run("text", replies + [FINAL], Path(workdir))
    assert result.success and not provider.replies, [hop["lost"] for hop in result.hops]
    assert result.chain == [0, 1, 2, 3, 3]
    assert all(hop["encoded"] for hop in result.hops[:-1])


def test_the_file_arm_gives_every_hop_its_own_file():
    standards = _standards()
    names = ["producer", "reviser_1", "reviser_2", "reviser_3", "consumer"]
    outputs = [CASE.task.output, *(r.output for r in CASE.revisions)]
    with tempfile.TemporaryDirectory() as workdir:
        paths = [Path(workdir) / name / f"{output}.parquet" for name, output in zip(names, outputs)]
        replies = []
        for index, name in enumerate(names):
            step = (f"r{index} = await {name}.run('work from {paths[index - 1]}')\nprint('ok')"
                    if index else f"r0 = await {name}.run('build it')\nprint('ok')")
            rebuilt = repr(to_jsonable(standards[min(index, len(standards) - 1)]))
            if name == "consumer":
                code = (f"import pandas as pd\n{RECEIVED} = pd.read_parquet('{paths[index - 1]}')\n"
                        f"total_deposits_thousand_usd = int({RECEIVED}['branch_deposits_thousand_usd'].sum())\n"
                        f"corrected_branches = int({RECEIVED}['main_office_indicator'].str.startswith('R').sum())")
            else:
                code = (f"import pandas as pd\n{outputs[index]} = pd.DataFrame({rebuilt})\n"
                        + (f"{CARRIED} = pd.read_parquet('{paths[index - 1]}')\n" if index else "")
                        + f"{outputs[index]}.to_parquet('{paths[index]}')")
            replies += [fenced_reply(step), fenced_reply(code), text_reply("done")]
        result, provider = _run("file", replies + [FINAL], Path(workdir))
    assert result.success and not provider.replies, [hop["lost"] for hop in result.hops]
    assert result.chain == [0, 1, 2, 3, 3]
    assert str(paths[0]) in result.orchestrator["messages"][0].content


def test_the_json_arm_s_workers_act_through_tool_calls():
    standards = _standards()
    names = ["producer", "reviser_1", "reviser_2", "reviser_3", "consumer"]
    outputs = [CASE.task.output, *(r.output for r in CASE.revisions)]
    replies = []
    for index, name in enumerate(names):
        step = (f"r{index} = await {name}.run('Here is the object:\\n' + r{index - 1}.content)\nprint('ok')"
                if index else f"r0 = await {name}.run('build it')\nprint('ok')")
        rebuilt = repr(to_jsonable(standards[min(index, len(standards) - 1)]))
        if name == "consumer":
            code = (f"import pandas as pd\n{RECEIVED} = pd.DataFrame({rebuilt})\n"
                    f"total_deposits_thousand_usd = int({RECEIVED}['branch_deposits_thousand_usd'].sum())\n"
                    f"corrected_branches = int({RECEIVED}['main_office_indicator'].str.startswith('R').sum())")
            reply = text_reply("Answered.")
        else:
            code = (f"import pandas as pd\n{outputs[index]} = pd.DataFrame({rebuilt})"
                    + (f"\n{CARRIED} = {outputs[index]}.copy()" if index else ""))
            reply = text_reply("Here.\n```json\n"
                               + json.dumps({outputs[index]: to_jsonable(standards[index])}) + "\n```")
        replies += [fenced_reply(step), tool_reply(code), reply]
    with tempfile.TemporaryDirectory() as workdir:
        result, provider = _run("json", replies + [FINAL], Path(workdir))
    assert result.chain == [0, 1, 2, 3, 3], [hop["lost"] for hop in result.hops]
    assert [r for r in provider.requests if r.get("tools")]


def test_a_chain_of_eight_hops_registers_every_name_once():
    """Nine workers and nine outputs share the orchestrator's runtime in the cave arm."""
    deepest = next(case for case in DEEPEST if case.task.name == "rounds_control_branches")
    codes = [PRODUCER_CODE] + [_revise(k, INPUT_SLOT, deepest) for k in range(1, 8)] \
        + [_consume(INPUT_SLOT)]
    names = ["producer", *(f"reviser_{k}" for k in range(1, 8)), "consumer"]
    outputs = [deepest.task.output, *(r.output for r in deepest.revisions), RECEIVED]
    replies = []
    for index, (name, output, code) in enumerate(zip(names, outputs, codes)):
        step = "" if not index else f"{name}.runtime.update_variable('{INPUT_SLOT}', obj{index - 1})\n"
        step += f"await {name}.run('do your part')\n"
        step += (f"obj{index} = await {name}.runtime.retrieve('{output}')\nprint('ok')"
                 if name != "consumer" else "print('done')")
        replies += [fenced_reply(step), fenced_reply(code), text_reply("done")]
    with tempfile.TemporaryDirectory() as workdir:
        result, provider = _run("cave", replies + [FINAL], Path(workdir), case=deepest)
    assert result.depth == 8 and result.success, [hop["lost"] for hop in result.hops]
    assert result.chain == [*range(8), 7] and not provider.replies
    assert len(result.workers) == 9


def test_a_reviser_that_bound_the_wrong_kind_of_object_is_a_finding_not_a_crash():
    codes = [PRODUCER_CODE] + [_revise(k, INPUT_SLOT) for k in range(1, 4)] + [_consume(INPUT_SLOT)]
    # reviser_2 hands on records where a table was due; the rule cannot take them.
    codes[2] = (f"{CARRIED} = {INPUT_SLOT}\n"
                f"{CASE.revisions[1].output} = {INPUT_SLOT}.to_dict('records')")
    with tempfile.TemporaryDirectory() as workdir:
        result, _ = _run("cave", _cave_script(codes), Path(workdir))
    second, third = result.hops[2], result.hops[3]
    # The crossing was clean — the host saw the object arrive — and the edit was not.
    assert second["carried"] is True and second["input_seen"] == "host"
    assert second["edited"] is False and second["applied"] is False
    # The next reviser was handed records: its edit cannot be judged, and is not called wrong.
    assert third["edited"] is None and third["applied"] is False
    assert not result.success and result.failure == "reviser_2"
    assert [hop["after"] for hop in result.hops] == [None, "producer", "reviser_1", "reviser_2", "reviser_3"]


def test_where_the_host_sees_the_input_itself_an_agent_cannot_rewrite_the_evidence():
    """The cave arm's crossing is read from the runtime, before the worker runs.

    An agent that binds what it was handed and then edits a part they share —
    a dict's ``copy`` is shallow — leaves its own variable holding something
    that was never handed to anyone. The host's snapshot is taken first.
    """
    codes = [PRODUCER_CODE]
    for index in range(1, 4):
        revision = CASE.revisions[index - 1]
        branch = BRANCH_REVISIONS[index - 1].ask.split("'")[1]
        codes.append(
            f"{CARRIED} = {INPUT_SLOT}\n"                    # the same object, not a copy
            f"{revision.output} = {INPUT_SLOT}.copy()\n"
            f"chosen = {revision.output}['branch_id'] == '{branch}'\n"
            f"{revision.output}.loc[chosen, 'branch_deposits_thousand_usd'] += {index}\n"
            f"{revision.output}.loc[chosen, 'main_office_indicator'] = 'R{index}'\n"
            f"{CARRIED} = {revision.output}"                  # and now it holds its own output
        )
    codes.append(_consume(INPUT_SLOT))
    with tempfile.TemporaryDirectory() as workdir:
        result, _ = _run("cave", _cave_script(codes), Path(workdir))
    assert result.success and result.chain == [0, 1, 2, 3, 3]
    for hop in result.hops[1:-1]:
        assert hop["input_seen"] == "host" and hop["carried"] and hop["edited"], hop


def test_a_reviser_in_the_arms_without_a_slot_is_read_from_what_it_bound():
    """There the host has no view of its own, so the agent's variable is the evidence."""
    standards = _standards()
    names = ["producer", "reviser_1", "reviser_2", "reviser_3", "consumer"]
    outputs = [CASE.task.output, *(r.output for r in CASE.revisions)]
    replies = []
    for index, name in enumerate(names):
        step = (f"r{index} = await {name}.run('Here is the object:\\n' + r{index - 1}.content)\nprint('ok')"
                if index else f"r0 = await {name}.run('build it')\nprint('ok')")
        rebuilt = repr(to_jsonable(standards[min(index, len(standards) - 1)]))
        if name == "consumer":
            code = (f"import pandas as pd\n{RECEIVED} = pd.DataFrame({rebuilt})\n"
                    f"total_deposits_thousand_usd = int({RECEIVED}['branch_deposits_thousand_usd'].sum())\n"
                    f"corrected_branches = int({RECEIVED}['main_office_indicator'].str.startswith('R').sum())")
            reply = text_reply("Answered.")
        else:
            # reviser_2 binds its input only after editing: the crossing goes unobserved.
            late = index == 2
            code = (f"import pandas as pd\n{outputs[index]} = pd.DataFrame({rebuilt})"
                    + (f"\n{CARRIED} = {outputs[index]}" if late else
                       f"\n{CARRIED} = pd.DataFrame({repr(to_jsonable(standards[index - 1]))})"
                       if index else ""))
            reply = text_reply("Here.\n```json\n"
                               + json.dumps({outputs[index]: to_jsonable(standards[index])}) + "\n```")
        replies += [fenced_reply(step), fenced_reply(code), reply]
    with tempfile.TemporaryDirectory() as workdir:
        result, _ = _run("text", replies + [FINAL], Path(workdir))
    assert [hop["input_seen"] for hop in result.hops[1:]] == ["agent"] * 4
    assert result.hops[1]["carried"] is True
    second = result.hops[2]
    assert second["observed_late"] and second["carried"] is None and second["edited"] is None
    assert second["applied"] and result.success


def test_a_reviser_in_the_file_arm_is_allowed_to_write_its_file():
    from core.paradigms import Delivery
    from core.prompts import handed_agent_instructions, object_delivery
    told = handed_agent_instructions(
        "instruction_file_object", delivers=Delivery.FILES, table=INPUT_SLOT,
        loader="pd.read_parquet", extension="parquet",
        delivery=object_delivery(Delivery.FILES, path=Path("/w/reviser_2/x.parquet"), writer="`w`"),
    )
    assert "write nothing but the output file" in told and "/w/reviser_2/x.parquet" in told
    assert "write nothing to disk" not in told


def test_the_consumer_is_not_told_a_description_the_chain_has_outgrown():
    """The edits add columns and keys; a consumer told how the object began rebuilt it that way."""
    shallow = next(case for case in ROUNDS_CASES if case.depth == 1)
    deep = next(case for case in DEEPEST if case.task.name == shallow.task.name)
    assert shallow.task.describe.rstrip(".")[1:] in shallow.consumer_variables[0].description
    told = deep.consumer_variables[0].description
    assert shallow.task.describe.rstrip(".")[1:] not in told
    assert "bind what reached you" in told and "7 rounds of changes" in told


def test_the_stage_before_is_not_an_earlier_version():
    """Only what a stage before the last one produced counts as reading an old object."""
    case = next(case for case in DEEPEST if case.task.name == "rounds_control_branches")
    tables = {t.name: t.loader() for t in select_runtime_tables(case.data_sources)}
    standards = case.standards(tables)
    key = case.task.row_key
    # A reviser at stage 3 handed what stage 2 produced: the ordinary case.
    ordinary = align(standards[2], standards, standards, row_key=key, older_than=2)
    assert ordinary.matches_output_of is None and ordinary.as_of == 2
    # Handed what stage 1 produced instead: an earlier version.
    stale = align(standards[1], standards, standards, row_key=key, older_than=2)
    assert stale.matches_output_of == 1
    # And its output, the rule applied to that older object, names where it came from.
    edited = align(case.revisions[2].applied_to(standards[1]), standards, standards,
                   revision=case.revisions[2], row_key=key, older_than=2)
    assert edited.as_of is None and edited.edited_from == 1


def test_a_payload_that_cannot_be_read_back_is_a_finding_not_a_crash():
    """The weakest model delivered a dict of scalars where a table was due."""
    from core.rounds_evaluator import _Judge
    case = next(c for c in ROUNDS_CASES if c.task.name == "rounds_control_branches" and c.depth == 1)
    judge = _Judge(case, ARMS["text"], [pd.DataFrame({"a": [1]})])
    assert judge._as_delivered({"a": 1, "b": 2}, pd.DataFrame({"a": [1]})) == {"a": 1, "b": 2}


def test_a_case_set_refuses_a_depth_its_chain_cannot_reach():
    case = DEEPEST[0]
    with pytest.raises(ValueError, match="revisions"):
        cases(case.task, case.revisions, (12,))


def test_the_control_object_survives_a_json_round_trip_at_every_stage(loaded):
    """What the control measures is the chain, not the format: its object has no fragile type."""
    from core.fidelity import ObjectKind, format_floors
    case = next(case for case in DEEPEST if case.task.name == "rounds_control_branches")
    for standard in case.standards(loaded):
        floors = format_floors(ObjectKind.TABLE, standard, row_key=BRANCHES.row_key)
        assert floors["json"].intact and floors["file"].intact


def test_the_events_chain_loses_its_question_when_the_zone_goes(loaded):
    """The end question is what a chain that dropped the timezone cannot answer."""
    case = next(case for case in DEEPEST if case.task.name == "rounds_tz_events")
    standard = case.standards(loaded)[-1]
    right = case.follow_up.compute(standard)
    # A consumer holding naive local times cannot convert at all; one that read
    # them back as if they were UTC answers a different question.
    naive = standard.assign(began_at=standard["began_at"].dt.tz_localize(None))
    with pytest.raises(TypeError):
        case.follow_up.compute(naive)
    as_utc = naive.assign(began_at=naive["began_at"].dt.tz_localize("UTC"))
    assert isinstance(as_utc, pd.DataFrame) and case.follow_up.compute(as_utc) != right
