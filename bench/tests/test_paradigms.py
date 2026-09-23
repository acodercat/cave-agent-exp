"""How each paradigm moves data and outputs across the host boundary.

Local and deterministic: no model, no runtime tables.
"""

import asyncio

import pandas as pd
import pytest
from cave_agent import Variable

import core.paradigms as paradigms
from core.paradigms import (
    CAVE, CAVE_REPLY, CODEBLOCK, CODEBLOCK_FILES, CODEBLOCK_VARIABLES, JSON_EXEC, PARADIGMS,
    Action, DataAccess, Delivery, collect_outputs, publish_revision, table_paths,
)
from core.runtime_catalog import RuntimeTable


OUTPUTS = [
    Variable("branch_count", None, "Store the number of branches as an integer."),
    Variable("branch_table", None, "Store a table with columns branch_id and deposits."),
]
TABLE = RuntimeTable(
    name="branches_df", labels=("fdic_sod",), loader=lambda: pd.DataFrame(),
    description="pandas DataFrame of FDIC branches. One row per branch.",
)


class Runtime:
    def __init__(self, values):
        self.values = values

    async def retrieve(self, name):
        return self.values[name]


def collect(paradigm, *, runtime=None, response="", output_dir=None):
    names = [output.name for output in OUTPUTS]
    return asyncio.run(collect_outputs(paradigm, runtime, response, names, output_dir))


PATHS = {"branches_df": "/data/branches_df.parquet"}


def named(value):
    """A readable test id: a paradigm by its name, anything else as it is."""
    return getattr(value, "name", value)


def having(**axes):
    """Every paradigm with the given axis values."""
    return [
        paradigm for paradigm in PARADIGMS.values()
        if all(getattr(paradigm, axis) is value for axis, value in axes.items())
    ]


class TestDesign:
    """Neighbouring paradigms differ in one axis, so a gap between them reads as its effect."""

    def test_the_fenced_paradigms_cross_the_two_boundaries_in_every_combination(self):
        grid = (CAVE, CAVE_REPLY, CODEBLOCK_VARIABLES, CODEBLOCK)
        assert {(p.data_access, p.delivery) for p in grid} == {
            (access, delivery)
            for access in DataAccess for delivery in (Delivery.VARIABLES, Delivery.REPLY)
        }
        assert {p.action for p in grid} == {Action.FENCED_CODE}

    @pytest.mark.parametrize("paradigm, neighbour, axis", [
        (CAVE, CAVE_REPLY, "delivery"),
        (CAVE, CODEBLOCK_VARIABLES, "data_access"),
        (CODEBLOCK, CAVE_REPLY, "data_access"),
        (CODEBLOCK, CODEBLOCK_VARIABLES, "delivery"),
        (CODEBLOCK, CODEBLOCK_FILES, "delivery"),
        (CODEBLOCK, JSON_EXEC, "action"),
    ], ids=named)
    def test_neighbours_differ_in_exactly_one_axis(self, paradigm, neighbour, axis):
        differing = [a for a in ("data_access", "action", "delivery")
                     if getattr(paradigm, a) is not getattr(neighbour, a)]
        assert differing == [axis]

    def test_every_paradigm_is_registered_under_its_name(self):
        assert all(name == paradigm.name for name, paradigm in PARADIGMS.items())
        axes = {(p.data_access, p.action, p.delivery) for p in PARADIGMS.values()}
        assert len(axes) == len(PARADIGMS)


class TestCollection:
    @pytest.mark.parametrize("paradigm", having(delivery=Delivery.VARIABLES), ids=named)
    def test_variable_delivery_retrieves_the_variables(self, paradigm):
        runtime = Runtime({"branch_count": 3, "branch_table": None})
        assert collect(paradigm, runtime=runtime) == {"branch_count": 3, "branch_table": None}

    @pytest.mark.parametrize("paradigm", having(delivery=Delivery.REPLY), ids=named)
    def test_reply_delivery_reads_the_last_json_block(self, paradigm):
        response = (
            'Draft:\n```json\n{"branch_count": 1}\n```\nFinal:\n'
            '```json\n{"branch_count": 3, "branch_table": [{"branch_id": "007"}]}\n```'
        )
        assert collect(paradigm, response=response) == {
            "branch_count": 3, "branch_table": [{"branch_id": "007"}],
        }

    @pytest.mark.parametrize("response", [
        "The count is 3.",                           # no block
        "```json\n{branch_count: 3}\n```",          # not JSON
        "```json\n[3]\n```",                        # not an object
    ])
    def test_an_unreadable_reply_records_nothing(self, response):
        assert collect(CODEBLOCK, response=response) == {
            "branch_count": None, "branch_table": None,
        }

    def test_a_missing_key_is_a_missing_output(self):
        outputs = collect(CODEBLOCK, response='```json\n{"branch_count": 3}\n```')
        assert outputs == {"branch_count": 3, "branch_table": None}

    def test_file_delivery_prefers_the_table_file_and_falls_back_to_the_reply(self, tmp_path):
        pd.DataFrame({"branch_id": ["007"], "deposits": [5]}).to_parquet(
            tmp_path / "branch_table.parquet"
        )
        outputs = collect(
            CODEBLOCK_FILES, response='```json\n{"branch_count": 1}\n```', output_dir=tmp_path,
        )
        assert outputs == {
            "branch_count": 1, "branch_table": [{"branch_id": "007", "deposits": 5}],
        }


class TestRevisions:
    """A host revision reaches the agent the way its paradigm reaches data."""

    REVISED = pd.DataFrame({"branch_id": ["b1"], "deposits": [99]})

    @pytest.mark.parametrize("paradigm", having(data_access=DataAccess.REGISTERED), ids=named)
    def test_a_registered_table_has_its_variable_rebound(self, paradigm):
        updates = {}
        runtime = type("R", (), {"update_variable": lambda self, n, v: updates.update({n: v})})()
        publish_revision(paradigm, runtime, {"branches_df": self.REVISED}, {})
        assert updates["branches_df"] is self.REVISED

    @pytest.mark.parametrize("paradigm", having(data_access=DataAccess.FILES), ids=named)
    def test_a_table_read_from_a_file_has_its_file_overwritten(self, paradigm, tmp_path):
        path = tmp_path / "branches_df.parquet"
        pd.DataFrame({"branch_id": ["b1"], "deposits": [1]}).to_parquet(path)
        publish_revision(paradigm, None, {"branches_df": self.REVISED}, {"branches_df": path})
        assert pd.read_parquet(path).equals(self.REVISED)

    def test_a_revising_case_gets_private_copies_of_its_table_files(self, tmp_path, monkeypatch):
        shared = tmp_path / "shared.parquet"
        self.REVISED.to_parquet(shared)
        monkeypatch.setattr(paradigms, "table_file", lambda table: shared)
        assert table_paths([TABLE], None) == {"branches_df": shared}
        private = table_paths([TABLE], tmp_path / "data")["branches_df"]
        assert private != shared and pd.read_parquet(private).equals(self.REVISED)
