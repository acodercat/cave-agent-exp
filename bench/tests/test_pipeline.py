"""The pipeline family's arms differ on one axis, and its cases are well formed.

If the three channels differed in anything but the channel, a difference between
arms would be a difference between paradigms and the study would measure nothing.
That, and what the second agent is told, is settled here without the runtime
tables. Whether the scorer separates is settled in ``test_pipeline_cases.py``,
which needs them.
"""

from pathlib import Path

import pytest
from cave_agent import Variable
from cave_agent.runtime import IPythonRuntime


from cases.pipeline import (
    DEPTH_AGENTS, DEPTH_SIZES, DEPTH_TASKS, PIPELINE_CASES, PIPELINE_SIZES, depth_cases,
)
from cases.pipeline.follow_ups import FOLLOW_UPS
from cases.pipeline.stages import KEEP_LOWER_HALF, RELAY
from core.evaluator import TurnResult
from core.pipeline import (
    ADDRESS_ARMS, CARRY_ARMS, CHANNELS, DELIVERY_ARMS, DESCRIBE_ARMS, SIGNAL_ARMS, Carry,
    Channel, cases_by_name,
)
from core.pipeline_evaluator import as_it_ended
from core.paradigms import Action, DataAccess, Delivery
from core.prompts import (
    HANDED_REPLY, HANDED_TABLE, QUOTED_REPLY, describe_handed_frame,
    handed_agent_instructions, system_instructions,
)
from core.table_delivery import CellKind, Column, Size, TableTask


# ----- the arms differ on one axis ------------------------------------------

def test_the_delivery_arms_differ_in_delivery_alone():
    """object / file / text: a difference between them is a difference in channel."""
    producers = [CHANNELS[name].producer for name in DELIVERY_ARMS]
    assert {producer.data_access for producer in producers} == {DataAccess.FILES}
    assert {producer.action for producer in producers} == {Action.FENCED_CODE}
    assert len({producer.delivery for producer in producers}) == len(producers)
    assert {CHANNELS[name].carry for name in DELIVERY_ARMS} != {Carry.SHARE}


def test_the_carry_arms_are_produced_identically_and_differ_in_the_carry_alone():
    """object / shared: the same paradigm, and only the host's move differs."""
    object_arm, shared_arm = (CHANNELS[name] for name in CARRY_ARMS)
    assert object_arm.producer is shared_arm.producer
    assert object_arm.carry is not shared_arm.carry
    assert shared_arm.shares_runtime
    assert not object_arm.shares_runtime


def test_the_address_arms_are_produced_identically_and_differ_in_addressability_alone():
    """text / text_bound: the same paradigm, the same quoted reply; one also binds it."""
    text, bound = (CHANNELS[name] for name in ADDRESS_ARMS)
    assert text.producer is bound.producer
    assert text.carry is Carry.REPLY and bound.carry is Carry.REPLY_BOUND
    plain = handed_agent_instructions("text", delivers=Delivery.VARIABLES)
    with_binding = handed_agent_instructions("text_bound", delivers=Delivery.VARIABLES)
    # The same three sentences about the table, then one more about the binding.
    shared_opening = "Another agent has computed a table and its reply is quoted at the head of"
    assert shared_opening in plain and shared_opening in with_binding
    assert HANDED_REPLY in with_binding and HANDED_REPLY not in plain
    assert "retyping the rows" in with_binding


def test_only_the_shared_channel_shares_a_runtime():
    assert [name for name, c in CHANNELS.items() if c.shares_runtime] == ["shared"]


def test_every_channel_names_itself_and_is_reachable_by_that_name():
    for name, channel in CHANNELS.items():
        assert isinstance(channel, Channel)
        assert channel.name == name


def test_every_channel_has_something_to_tell_its_second_agent():
    """The prompts are keyed by channel name; a new channel must bring its text."""
    for name in CHANNELS:
        for delivers in Delivery:
            assert handed_agent_instructions(
                name, delivers=delivers, path=Path("/tmp/table.parquet"),
                output_dir=Path("/tmp/out"),
            )


def test_the_second_agent_is_told_where_its_table_is_and_nowhere_else():
    """Each channel names its own carrier, and none offers a way round it."""
    prompts = {
        name: handed_agent_instructions(
            name, delivers=Delivery.VARIABLES, path=Path("/tmp/handed.parquet"))
        for name in CHANNELS
    }
    assert f"`{HANDED_TABLE}`, a pandas DataFrame" in prompts["object"]
    assert "same runtime as the agent before you" in prompts["shared"]
    assert "/tmp/handed.parquet" in prompts["file"]
    assert "quoted at the head of" in prompts["text"]
    assert "quoted at the head of" in prompts["text_bound"]
    for name, prompt in prompts.items():
        assert "Use only the table you were handed" in prompt, name
    assert "{reply}" in QUOTED_REPLY


def _from(prompt: str, opens: str) -> str:
    return prompt[prompt.index(opens):]


def _between(prompt: str, opens: str, closes: str) -> str:
    return prompt[prompt.index(opens):prompt.index(closes)]


def test_the_second_agent_runs_code_by_the_same_rules_as_every_other_agent():
    """The executing-code rules and everything after the question are shared text.

    Three slots are the second agent's own: where its table is, the first step
    that opens it, and the rule about what it may read — it has been handed one
    table, not given a list of files. The rest must be the text a fenced-code
    agent delivering variables reads in the delivery study, so a difference
    between channels cannot be a difference in how they were told to run code.
    """
    handed = handed_agent_instructions("object", delivers=Delivery.VARIABLES)
    reference = system_instructions("eager", paradigm=CHANNELS["object"].producer)
    rules = "Executing code:"
    data_rule = "- Read only the listed files"
    assert _between(handed, rules, "- Use only the table you were handed") == \
        _between(reference, rules, data_rule)
    assert _from(handed, "Analysing:") == _from(reference, "Analysing:")


# ----- the cases -------------------------------------------------------------

def test_every_case_is_named_once():
    by_name = cases_by_name(PIPELINE_CASES)
    assert len(by_name) == len(PIPELINE_CASES)


def test_every_task_is_asked_at_every_size_the_study_uses():
    assert len(PIPELINE_CASES) == len(FOLLOW_UPS) * len(PIPELINE_SIZES)
    assert {case.size.label for case in PIPELINE_CASES} == set(PIPELINE_SIZES)


def test_every_task_offers_the_sizes_the_study_asks_for():
    """A task whose sizes were relabelled would silently drop out of the study."""
    for task, _ in FOLLOW_UPS:
        assert set(PIPELINE_SIZES) <= {size.label for size in task.sizes}, task.name


def test_no_two_tasks_are_the_same_task():
    assert len({task.name for task, _ in FOLLOW_UPS}) == len(FOLLOW_UPS)


def test_a_follow_up_asks_only_for_values_that_are_exact():
    """A decimal answer would drift between a channel carrying full precision
    and one carrying rounded text, which is not what the study measures."""
    for _, follow_up in FOLLOW_UPS:
        for answer in follow_up.answers:
            assert answer.decimals in (None, 0), answer.name


def test_a_follow_up_never_asks_for_a_value_it_did_not_declare():
    for _, follow_up in FOLLOW_UPS:
        assert len(follow_up.stores) == len(set(follow_up.stores))
        assert follow_up.stores == [variable.name for variable in follow_up.variables]


def test_the_first_stage_is_always_a_delivery_task_of_the_suite():
    """The first question is never written for this study; it is one the suite has.

    Which of the two families it comes from matters to how a size is read — the
    control family varies the delivered volume alone, the delivery family widens
    the scope as well — so the study keeps both and the analysis says which.
    """
    for task, _ in FOLLOW_UPS:
        assert isinstance(task, TableTask)
        assert task.family in ("table_control", "table_delivery"), task.name


def test_the_task_with_a_recorded_scoring_defect_is_left_out():
    """market_growth_drawdown's reference has a rounding tie, so it is left out."""
    assert "market_growth_drawdown" not in {task.name for task, _ in FOLLOW_UPS}


# ----- a turn is read as it ended ---------------------------------------------

def _turn(*, success: bool, response: str, outputs: dict, repair: dict | None) -> TurnResult:
    return TurnResult(
        turn=1, query="", stores=list(outputs), success=success, failure_type=None,
        response=response, outputs=outputs, validation_message="", variables_not_set=False,
        steps=1, prompt_tokens=0, completion_tokens=0, total_tokens=0, elapsed=0.0,
        stop_reason="completed", executed_code=True, code_snippets=[], protocol_nudges=0,
        protocol_repair=repair,
    )


def test_a_turn_that_was_never_nudged_is_read_from_its_first_pass():
    turn = _turn(success=True, response="first", outputs={"t": [1]}, repair=None)
    assert as_it_ended(turn) == (True, "first", {"t": [1]})


def test_a_nudged_turn_is_read_from_where_it_ended():
    """The delivery study's headline does this, and the reply that crosses must too."""
    turn = _turn(
        success=False, response="I will inspect the data.", outputs={"t": None},
        repair={"attempted": True, "success": True, "response": "final", "outputs": {"t": [1]}},
    )
    assert as_it_ended(turn) == (True, "final", {"t": [1]})


def test_a_repair_that_was_not_attempted_changes_nothing():
    turn = _turn(
        success=True, response="first", outputs={"t": [1]},
        repair={"attempted": False, "success": True, "response": "first", "outputs": {"t": [1]}},
    )
    assert as_it_ended(turn) == (True, "first", {"t": [1]})


# ----- the pipeline -----------------------------------------------------------

def test_the_main_study_puts_one_narrower_between_the_two():
    for case in PIPELINE_CASES:
        assert case.middles == (KEEP_LOWER_HALF,)
        assert case.agents == 3
        assert case.roles == ("retriever", "narrower", "analyst")


def test_the_depth_probe_lengthens_the_pipeline_with_relays_alone():
    for agents in DEPTH_AGENTS:
        cases = depth_cases(agents)
        assert cases, agents
        for case in cases:
            assert case.agents == agents
            # Every middle is a relay; they differ only in the name each hands on
            # under, which a runtime requires them to.
            assert len(case.middles) == agents - 2
            for middle in case.middles:
                assert middle.role == RELAY.role
                assert middle.select is RELAY.select
                assert middle.ask is RELAY.ask
            assert case.task.name in set(DEPTH_TASKS)
            assert case.size.label in set(DEPTH_SIZES)


def test_a_pipeline_needs_a_first_and_a_last_agent():
    with pytest.raises(ValueError):
        depth_cases(1)


def test_a_relay_holds_the_table_the_same_size_at_every_crossing():
    """The probe varies depth alone, so the payload must not vary with it."""
    rows = [{"a": index} for index in range(10)]
    for agents in DEPTH_AGENTS:
        case = depth_cases(agents)[0]
        tables = case.expected_tables(rows)
        assert len(tables) == agents - 1
        assert all(table == rows for table in tables)


def _ordering_task(key=("k",)):
    return TableTask(
        name="fake", title="Fake", data_sources=("fake",), financial_domain="banking_credit",
        query="Deliver {scope}.", output="t", row_noun="row", key=key,
        columns=tuple(Column(column, CellKind.IDENTIFIER, column) for column in key),
        sizes=(Size("4", "four", 4),), load=lambda: None, build=lambda source, **_: None,
    )


def test_the_narrower_keeps_the_half_that_sorts_first_by_key():
    task = _ordering_task()
    rows = [{"k": "d"}, {"k": "a"}, {"k": "c"}, {"k": "b"}]
    assert KEEP_LOWER_HALF.select(task, rows) == [{"k": "a"}, {"k": "b"}]


def test_the_narrower_gives_the_same_answer_whatever_order_it_received():
    """The defect this replaced: a faithful middle agent scored wrong for the
    order the first agent happened to deliver in, which validate_table ignores."""
    task = _ordering_task()
    rows = [{"k": letter} for letter in "abcd"]
    wanted = KEEP_LOWER_HALF.select(task, rows)
    for shuffled in ([rows[i] for i in order] for order in
                     ((3, 1, 0, 2), (2, 3, 1, 0), (1, 0, 3, 2))):
        assert KEEP_LOWER_HALF.select(task, shuffled) == wanted


def test_the_narrower_takes_the_smaller_half_of_an_odd_table():
    task = _ordering_task()
    rows = [{"k": letter} for letter in "abcdefg"]
    assert KEEP_LOWER_HALF.select(task, rows) == [{"k": "a"}, {"k": "b"}, {"k": "c"}]
    assert KEEP_LOWER_HALF.select(task, [{"k": "a"}]) == []


def test_the_narrower_question_names_every_key_column():
    for columns in (("a",), ("a", "b"), ("a", "b", "c")):
        question = KEEP_LOWER_HALF.query(_ordering_task(columns))
        for column in columns:
            assert f"`{column}`" in question, (columns, column)


def test_the_main_study_hands_the_last_agent_half_of_the_first_table():
    case = PIPELINE_CASES[0]
    key = case.task.key[0]
    rows = [{key: f"{index:03d}"} for index in range(100)]
    tables = case.expected_tables(rows)
    assert [len(table) for table in tables] == [100, 50]


def test_a_variable_that_crosses_keeps_the_name_its_producer_gave_it():
    """So object and shared differ in the carry and not in what to look for."""
    for name in CARRY_ARMS:
        prompt = handed_agent_instructions(
            name, delivers=Delivery.VARIABLES, table="branch_table")
        assert "`branch_table`" in prompt, name
        assert HANDED_TABLE not in prompt, name


def test_a_middle_agent_is_told_to_hand_a_table_on_and_the_last_one_is_not():
    """A middle agent delivers on the channel; only the last assigns answers."""
    for channel in CHANNELS:
        middle = handed_agent_instructions(
            channel, delivers=Delivery.FILES, output_dir=Path("/tmp/out"),
            path=Path("/tmp/in.parquet"),
        )
        last = handed_agent_instructions(
            channel, delivers=Delivery.VARIABLES, path=Path("/tmp/in.parquet"),
        )
        assert "/tmp/out/<output name>.parquet" in middle, channel
        assert "Assign every required output variable" in last, channel
        assert "Assign every required output variable" not in middle, channel


def test_no_two_stages_of_a_pipeline_hand_on_under_the_same_name():
    """A runtime refuses one name twice, so a shared pipeline would raise.

    The fake runtime the pipeline tests drive is a dict and accepts a duplicate,
    which is why this is checked against the real one's rule rather than through
    a run.
    """
    for agents in DEPTH_AGENTS:
        for case in depth_cases(agents):
            outputs = [case.task.output, *(middle.output for middle in case.middles)]
            assert len(set(outputs)) == len(outputs), (agents, outputs)
    for case in PIPELINE_CASES:
        outputs = [case.task.output, *(middle.output for middle in case.middles)]
        assert len(set(outputs)) == len(outputs), outputs


def test_the_real_runtime_refuses_a_name_it_already_holds():
    """The rule the test above exists for, stated against the runtime itself."""
    runtime = IPythonRuntime(functions=[], variables=[], types=[])
    runtime.inject_variable(Variable("relayed_table", None, "first"))
    with pytest.raises(ValueError):
        runtime.inject_variable(Variable("relayed_table", None, "second"))


def test_the_describe_arms_are_injected_identically_and_differ_in_the_description_alone():
    """object / object_described: same paradigm, same prompt; only the variable's
    own description differs, and that is the runtime's to write."""
    plain, described = (CHANNELS[name] for name in DESCRIBE_ARMS)
    assert plain.producer is described.producer
    assert plain.carry is Carry.INJECT and described.carry is Carry.INJECT_DESCRIBED
    assert handed_agent_instructions("object", delivers=Delivery.VARIABLES, table="t") == \
        handed_agent_instructions("object_described", delivers=Delivery.VARIABLES, table="t")


def test_a_described_frame_states_its_rows_and_every_column_s_dtype():
    import pandas as pd
    frame = pd.DataFrame({"code": pd.Series(["01", "02"], dtype="string"), "n": [1, 2]})
    text = describe_handed_frame("A table.", frame)
    assert text.startswith("A table. ")
    assert "2 rows" in text
    assert "code: string" in text and "n: int64" in text
    # No sample values: the description must not grow with the table.
    assert "01" not in text


def test_describing_something_that_is_not_a_frame_changes_nothing():
    assert describe_handed_frame("A table.", [{"a": 1}]) == "A table."


def test_the_signal_arms_are_injected_and_described_identically_and_differ_in_the_signal_alone():
    described, signalled = (CHANNELS[name] for name in SIGNAL_ARMS)
    assert described.producer is signalled.producer
    assert described.describes and signalled.describes
    assert signalled.signals and not described.signals
    assert handed_agent_instructions("object_described", delivers=Delivery.VARIABLES, table="t") == \
        handed_agent_instructions("object_signalled", delivers=Delivery.VARIABLES, table="t")


def test_only_the_signalled_channel_signals():
    assert [name for name, c in CHANNELS.items() if c.signals] == ["object_signalled"]
