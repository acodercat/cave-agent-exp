"""What each paradigm is told, and that they are told the same thing elsewhere.

Local and deterministic: no model, no runtime tables.
"""

from itertools import combinations

import pandas as pd
import pytest
from cave_agent import Variable

import core.prompts as prompts
from core.paradigms import (
    CAVE, CAVE_REPLY, CODEBLOCK, CODEBLOCK_FILES, CODEBLOCK_VARIABLES, JSON_EXEC, PARADIGMS,
    DataAccess, Delivery,
)
from core.prompts import repair_nudge, system_instructions, turn_prompt
from core.runtime_catalog import RuntimeTable


OUTPUTS = [
    Variable("branch_count", None, "Store the number of branches as an integer."),
    Variable("branch_table", None, "Store a table with columns branch_id and deposits."),
]
TABLE = RuntimeTable(
    name="branches_df", labels=("fdic_sod",), loader=lambda: pd.DataFrame(),
    description="pandas DataFrame of FDIC branches. One row per branch.",
)
PATHS = {"branches_df": "/data/branches_df.parquet"}


def prompt_for(paradigm, **options):
    return system_instructions(
        paradigm=paradigm, tables=[TABLE], paths=PATHS, output_dir="/out", **options,
    )


# What each sentence of the template may depend on.
SENTENCE_AXES = {
    "data_access": ("data_access",),
    "first_step": ("data_access", "action"),
    "data_rule": ("data_access",),
    "action_rules": ("action", "delivery"),
    "outputs_missing": ("delivery",),
    "delivery": ("delivery",),
}


def test_every_sentence_of_the_template_declares_the_axes_it_follows():
    assert SENTENCE_AXES.keys() == prompts._slots(CAVE, "eager", [TABLE], PATHS, "/out").keys()


@pytest.mark.parametrize("sentence, axes", SENTENCE_AXES.items())
def test_paradigms_that_agree_on_a_sentences_axes_read_the_same_sentence(sentence, axes):
    """So two neighbouring paradigms are told apart only where their one axis differs."""
    def text(paradigm):
        return prompts._slots(paradigm, "eager", [TABLE], PATHS, "/out")[sentence]

    for first, second in combinations(PARADIGMS.values(), 2):
        if all(getattr(first, axis) is getattr(second, axis) for axis in axes):
            assert text(first) == text(second), (first.name, second.name)


def test_system_instructions_pin_the_runtime_execution_envelope():
    instructions = system_instructions("eager")
    assert "Only a Markdown ```python fence is executable" in instructions
    assert "XML/DSML tool markup" in instructions
    assert "code written without a fence" in instructions
    assert "no tool functions to call" in instructions
    assert "progress updates in Python comments" in instructions
    assert "standalone planning message" in instructions
    # The prompt shows the turn shape, and names the observed failure as the
    # counterexample: a prose-only "I'll start by inspecting" reply that ends
    # the run with nothing computed.
    assert "What a step looks like" in instructions
    assert "This is not a step" in instructions


def test_system_instructions_follow_the_injection_mode():
    eager = system_instructions("eager")
    lazy = system_instructions("lazy")
    assert "registered there as pandas DataFrames" in eager and "datasets" not in eager
    assert 'datasets.load("table_name")' in lazy and "Only the listed tables can be loaded" in lazy
    with pytest.raises(ValueError):
        system_instructions("streaming")


class TestPrompts:
    def test_every_turn_states_the_contract_its_output_variables_carry(self):
        prompt = turn_prompt("How many branches?", OUTPUTS)
        assert prompt.startswith("How many branches?\n\nRequired outputs for this turn:")
        for output in OUTPUTS:
            assert f"- {output.name}: {output.description}" in prompt

    def test_file_paradigms_list_each_table_with_its_full_description(self):
        instructions = system_instructions(paradigm=CODEBLOCK, tables=[TABLE], paths=PATHS)
        assert "/data/branches_df.parquet" in instructions
        assert TABLE.description in instructions
        assert "pd.read_parquet" in instructions
        assert "Use only the data the runtime registers" not in instructions

    def test_only_the_paradigms_own_sentences_change(self):
        """With the paradigm's own sentences blanked, the prompts are one text."""
        blanks = {"data_access": "<data>", "action_rules": "<action>", "first_step": "<step>",
                  "data_rule": "<rule>", "delivery": "<delivery>",
                  "outputs_missing": "<missing>"}
        skeleton = prompts._SYSTEM_INSTRUCTIONS_TEMPLATE.format(**blanks)
        fixed = [line for line in skeleton.splitlines() if "<" not in line]
        for paradigm in PARADIGMS.values():
            lines = prompt_for(paradigm).splitlines()
            assert all(line in lines for line in fixed), paradigm.name

    @pytest.mark.parametrize("paradigm", PARADIGMS.values(), ids=lambda p: p.name)
    def test_outputs_are_called_variables_only_where_they_are_variables(self, paradigm):
        text = prompt_for(paradigm)
        if paradigm.delivery is Delivery.VARIABLES:
            assert "every required variable is assigned" in text
            assert "every output variable still unassigned" in text
        else:
            assert "every required output is ready" in text
            assert "every required output still missing" in text
            assert "output variable" not in text

    @pytest.mark.parametrize("paradigm", PARADIGMS.values(), ids=lambda p: p.name)
    def test_the_data_is_said_to_arrive_the_way_it_does(self, paradigm):
        text = prompt_for(paradigm)
        reads_files = paradigm.data_access is DataAccess.FILES
        assert ("pd.read_parquet" in text) is reads_files
        assert ("Use only the data the runtime registers" in text) is not reads_files
        # Outputs may be registered even when no table is.
        assert "nothing is registered" not in text

    def test_file_delivery_names_the_output_directory(self, tmp_path):
        instructions = system_instructions(
            paradigm=CODEBLOCK_FILES, tables=[TABLE], paths=PATHS, output_dir=tmp_path,
        )
        assert f"{tmp_path}/<output name>.parquet" in instructions
        assert "```json block" in instructions
        # A table that leaves as a file never has to be printed to be copied.
        assert "print it in full first" not in instructions


class TestActionFormat:
    """`json_exec` differs from `codeblock` only in how code is said to run."""

    def test_the_tool_paradigm_never_shows_a_fence_as_the_way_to_run_code(self):
        text = system_instructions(paradigm=JSON_EXEC, tables=[TABLE], paths=PATHS)
        assert "one call to the `execute_python` tool" in text
        assert "```python" not in text
        assert 'table_df = pd.read_parquet("/path/to/table.parquet")' in text

    def test_codeblock_and_json_exec_share_data_access_and_delivery(self):
        fenced = system_instructions(paradigm=CODEBLOCK, tables=[TABLE], paths=PATHS)
        called = system_instructions(paradigm=JSON_EXEC, tables=[TABLE], paths=PATHS)
        for shared in ("/data/branches_df.parquet", "```json block", "print it in full first"):
            assert shared in fenced and shared in called

    def test_the_repair_nudge_names_the_paradigms_own_way_to_run_code(self):
        assert "```python" in repair_nudge(CODEBLOCK, ["a", "b"])
        tool = repair_nudge(JSON_EXEC, ["a", "b"])
        assert "`execute_python`" in tool and "```python" not in tool
        assert "a, b" in tool


def test_reply_delivery_lets_the_model_print_the_table_it_must_copy():
    """Without this the shared "never print whole tables" rule forces invention."""
    reply = system_instructions(paradigm=CODEBLOCK, tables=[TABLE], paths=PATHS)
    assert "print it in full first" in reply and "Never write a row you have not printed" in reply
    assert "print it in full first" not in system_instructions("eager")
    assert "print it in full first" in prompt_for(CAVE_REPLY)
    assert "print it in full first" not in prompt_for(CODEBLOCK_VARIABLES)


@pytest.mark.parametrize("paradigm", PARADIGMS.values(), ids=lambda p: p.name)
def test_every_paradigm_is_warned_alike_that_the_host_revises_data(paradigm):
    told = prompt_for(paradigm, warn_of_revisions=True)
    assert "The host may revise the data between turns" in told
    assert "may revise" not in prompt_for(paradigm)
