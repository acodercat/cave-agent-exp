"""The paradigms an ablation compares, and what crosses the host-runtime boundary.

Every paradigm runs the same agent loop over the same persistent Python runtime,
reads the same table descriptions and is judged by the same validators. A
paradigm fixes three things and nothing else:

* how the data reaches the agent (:class:`DataAccess`),
* how the agent runs code (:class:`Action`),
* how its outputs reach the host (:class:`Delivery`).

With code written as fenced blocks, the two crossings of the boundary form a
grid, so the effect of each is read with the other held fixed:

==================  ==========================  ==========================
data in             outputs as variables        outputs in a JSON block
==================  ==========================  ==========================
registered tables   ``cave``                    ``cave_reply``
Parquet files       ``codeblock_variables``     ``codeblock``
==================  ==========================  ==========================

Two more paradigms each change one thing from ``codeblock``:

``codeblock_files``
    A table output may be delivered as a Parquet file.

``json_exec``
    Code is the argument of an ``execute_python`` tool call, not a fenced block.

What each paradigm is *told* is in :mod:`core.prompts`; this module is what the
host *does*.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import inspect
import json
from pathlib import Path
import re
import shutil
from typing import Any, Mapping, Sequence

import pandas as pd

from core.runtime_catalog import RuntimeTable
from core.table_files import table_file
from core.validation import as_records


class DataAccess(Enum):
    REGISTERED = "registered"   # the runtime registers the tables as variables
    FILES = "files"             # the agent loads Parquet files


class Action(Enum):
    FENCED_CODE = "fenced_code"   # a ```python block in the reply
    TOOL_CALL = "tool_call"       # the `code` argument of a JSON tool call


class Delivery(Enum):
    VARIABLES = "variables"   # registered output variables the agent assigns
    REPLY = "reply"           # one JSON block at the end of the final reply
    FILES = "files"           # tables as Parquet files, the rest as REPLY


@dataclass(frozen=True)
class Paradigm:
    name: str
    data_access: DataAccess
    action: Action
    delivery: Delivery


CAVE = Paradigm("cave", DataAccess.REGISTERED, Action.FENCED_CODE, Delivery.VARIABLES)
CAVE_REPLY = Paradigm("cave_reply", DataAccess.REGISTERED, Action.FENCED_CODE, Delivery.REPLY)
CODEBLOCK_VARIABLES = Paradigm(
    "codeblock_variables", DataAccess.FILES, Action.FENCED_CODE, Delivery.VARIABLES,
)
CODEBLOCK = Paradigm("codeblock", DataAccess.FILES, Action.FENCED_CODE, Delivery.REPLY)
CODEBLOCK_FILES = Paradigm(
    "codeblock_files", DataAccess.FILES, Action.FENCED_CODE, Delivery.FILES,
)
JSON_EXEC = Paradigm("json_exec", DataAccess.FILES, Action.TOOL_CALL, Delivery.REPLY)
PARADIGMS = {
    paradigm.name: paradigm
    for paradigm in (CAVE, CAVE_REPLY, CODEBLOCK_VARIABLES, CODEBLOCK, CODEBLOCK_FILES, JSON_EXEC)
}

# How a paradigm whose tables are registered registers them: as loaded
# DataFrames, or as one handle that loads a table on request.
INJECTION_MODES = ("eager", "lazy")

_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)


def table_paths(tables: Sequence[RuntimeTable], private_dir: Path | None) -> dict[str, Path]:
    """The file each table is read from, when the agent reads its data from files.

    Tables are shared, read-only copies unless the case revises its data between
    turns; then each conversation gets private copies the host can overwrite.
    """
    paths = {table.name: table_file(table) for table in tables}
    if private_dir is None:
        return paths
    private_dir.mkdir(parents=True, exist_ok=True)
    return {
        name: Path(shutil.copyfile(path, private_dir / path.name))
        for name, path in paths.items()
    }


def publish_revision(
    paradigm: Paradigm, runtime, revised: Mapping[str, pd.DataFrame],
    paths: Mapping[str, Path],
) -> None:
    """Make the host's revised tables the data the agent's next turn reaches.

    A registered table's variable is rebound to the revised table; a table read
    from a file has its file overwritten. Either way, whatever the agent derived
    from the earlier data is still in its runtime, unrevised.
    """
    for name, frame in revised.items():
        if paradigm.data_access is DataAccess.FILES:
            frame.to_parquet(paths[name], index=False)
        else:
            runtime.update_variable(name, frame)


def reply_outputs(response: str) -> dict[str, Any]:
    """The object in the reply's last ```json block; empty when there is none.

    The last block is the answer, so a draft block earlier in the reply does not
    count. Read strictly otherwise: a block that is not valid JSON, or not an
    object, records nothing, exactly as an unassigned variable records nothing.
    The one liberty is Python's reader's own, the NaN token, which is a missing
    value here as it is in a DataFrame (see ``as_records``).
    """
    blocks = _JSON_BLOCK.findall(response or "")
    if not blocks:
        return {}
    try:
        parsed = json.loads(blocks[-1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def collect_outputs(
    paradigm: Paradigm, runtime, response: str, names: Sequence[str],
    output_dir: Path | None,
) -> dict[str, Any]:
    """This turn's outputs as the host receives them; None where one is missing."""
    if paradigm.delivery is Delivery.VARIABLES:
        values = {}
        for name in names:
            value = runtime.retrieve(name)
            values[name] = await value if inspect.isawaitable(value) else value
    else:
        replied = reply_outputs(response)
        values = {name: replied.get(name) for name in names}
        if paradigm.delivery is Delivery.FILES:
            for name in names:
                path = output_dir / f"{name}.parquet"
                if path.is_file():
                    values[name] = pd.read_parquet(path)
    return {name: as_records(value) for name, value in values.items()}
