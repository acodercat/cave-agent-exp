"""What the agent is told: the system prompt, a turn's question and the repair nudge.

It also holds the text an agent loop adds as it runs — the tool a tool-calling
agent is offered, what it is told about a call it cannot run, and the sentence
that closes every execution result — so that this module remains the one place
to read everything a model was told.

One template serves every paradigm. Its slots follow the paradigm — how the
data is reached, how a step runs code, the worked first step, what may be read
and written, how outputs are delivered and what those outputs are called — and
everything else is common text. Which paradigm gets which sentence is decided here and nowhere
else, so two paradigms can be compared knowing exactly what they were told
differently.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from cave_agent import Variable

from core.datastore import HANDLE_NAME
from core.paradigms import CAVE, INJECTION_MODES, Action, DataAccess, Delivery, Paradigm
from core.runtime_catalog import RuntimeTable


TOOL_NAME = "execute_python"

# What a handed agent calls the table it was given, in the channels that carry no
# variable: nothing named it upstream, so the study names it. Where a variable
# does cross, it keeps the name its producer gave it, which is what a shared
# runtime would have shown anyway; the caller passes that name in.
HANDED_TABLE = "delivered_table"
# What the runtime calls the previous agent's reply, in the one channel that
# binds that reply as a string beside quoting it.
HANDED_REPLY = "handed_reply"
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "Run Python code in the persistent session and return what it prints. "
            "Variables, imports and results persist between calls."
        ),
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "The Python code to run."}},
            "required": ["code"],
        },
    },
}

# The answer to a call that cannot run, in place of its execution result.
UNKNOWN_TOOL = f"There is no tool named {{name}}; the only tool is {TOOL_NAME}. Nothing was run."
MALFORMED_ARGUMENTS = (
    "The tool arguments were not a JSON object with a `code` string; nothing was run."
)

# CaveAgent closes every execution result with a sentence naming the next move.
# Its own is written for one action format and one delivery: "provide the next
# code block" is wrong for a tool call, and "your final answer in plain text"
# contradicts a paradigm whose answer must end in a JSON block. Every paradigm
# reads the same sentence in the terms of its own action.
UPSTREAM_NEXT_STEP = (
    "If more operations are needed, provide the next code block. "
    "Otherwise, provide your final answer in plain text."
)
NEXT_STEP = {
    Action.FENCED_CODE: (
        "If more operations are needed, provide the next code block. "
        "Otherwise, give your final answer."
    ),
    Action.TOOL_CALL: (
        f"If more operations are needed, call `{TOOL_NAME}` again. "
        "Otherwise, give your final answer."
    ),
}

# What closes an execution result once every output the turn asked for has been
# assigned. The runtime knows this and the model does not: an assignment is a
# line of code like any other, where writing a file is a visible act of
# delivery, and an agent that assigned its last output was seen to spend its
# remaining steps re-typing the variable's name. Only the arm that opts in
# reads this sentence; the frozen studies read NEXT_STEP unconditionally.
OUTPUTS_ASSIGNED = (
    "Every required output ({names}) is now assigned in the runtime. "
    "Nothing further needs to run: give your final answer."
)


_REGISTERED_ACCESS = {
    "eager": (
        "The data is registered there as pandas DataFrames that the runtime\n"
        "describes; it is not in this text. Write and execute Python to inspect,\n"
        "filter and calculate from those DataFrames."
    ),
    "lazy": (
        f"The data is reachable through the registered `{HANDLE_NAME}` handle, whose\n"
        f"description lists this task's tables; it is not in this text. Call\n"
        f"`{HANDLE_NAME}.load(name)` to obtain a table as a pandas DataFrame and\n"
        f"`{HANDLE_NAME}.describe(name)` for its columns, units and caveats, then\n"
        "write and execute Python to inspect, filter and calculate from those\n"
        "DataFrames. Only the listed tables can be loaded."
    ),
}

_FILE_ACCESS = (
    "The data is in the Parquet files listed below; it is not in this text, and\n"
    "no table is registered in the runtime. Load a file with\n"
    "`pd.read_parquet(path)`, then write and execute Python to inspect, filter\n"
    "and calculate from it. Only these files may be read.\n{listing}"
)

_ACTION_RULES = {
    Action.FENCED_CODE: (
        "- Each analysis step is exactly one fenced ```python code block with nothing\n"
        "  after it. The environment runs that block and returns its real output; then\n"
        "  either issue one further block or, once {outputs_ready},\n"
        "  give the final answer.\n"
        "- Only a Markdown ```python fence is executable. Code inside provider-specific\n"
        "  tags, special tokens, XML/DSML tool markup or other model-native envelopes is\n"
        "  treated as prose and will not run, and so is code written without a fence.\n"
        "  There are no tool functions to call: the fence is the only way to run code."
    ),
    Action.TOOL_CALL: (
        f"- Each analysis step is exactly one call to the `{TOOL_NAME}` tool, whose\n"
        "  `code` argument is the Python to run. The environment runs it and returns its\n"
        "  real output; then either make one further call\n"
        "  or, once {outputs_ready}, give the final answer.\n"
        f"- Only code passed to `{TOOL_NAME}` runs. Code written in your reply, whether\n"
        "  fenced, tagged or bare, is treated as prose and will not run: the tool is the\n"
        "  only way to run code."
    ),
}

_HOW_TO_RUN_CODE = {
    Action.FENCED_CODE: (
        "Only a fenced ```python block is executed; code without the fence, in a tool "
        "call or in any other markup is read as prose. Send the code again as one "
        "```python block with nothing after it."
    ),
    Action.TOOL_CALL: (
        f"Only code passed to the `{TOOL_NAME}` tool is executed; code written in the "
        f"reply is read as prose. Call `{TOOL_NAME}` with the code."
    ),
}

_ORIENT = "# Orient before filtering: the columns, periods and units in play\n"
_INSPECT = "print(table_df.columns.tolist())\nprint(table_df.head())"

# What a turn's outputs are called where they are assigned, and where they are
# written into the reply or a file.
_OUTPUTS_READY = {
    Delivery.VARIABLES: "every required variable is assigned",
    Delivery.REPLY: "every required output is ready",
    Delivery.FILES: "every required output is ready",
}
_OUTPUTS_MISSING = {
    Delivery.VARIABLES: "every output variable still unassigned",
    Delivery.REPLY: "every required output still missing",
    Delivery.FILES: "every required output still missing",
}

# The worked first step per way of reaching the data: what its placeholder stands
# for, and the code. `_first_step` shows that code in the paradigm's action format.
_REGISTERED_FIRST_STEP = {
    "eager": (
        "table_df stands for whichever registered DataFrame\nthe question needs",
        _ORIENT + _INSPECT,
    ),
    "lazy": (
        "\"table_name\" stands for whichever listed table\nthe question needs",
        _ORIENT
        + f"print({HANDLE_NAME}.describe(\"table_name\"))\n"
        + f"table_df = {HANDLE_NAME}.load(\"table_name\")\n"
        + _INSPECT,
    ),
}
_FILE_FIRST_STEP = (
    "the path stands for whichever listed file the\nquestion needs",
    _ORIENT
    + "import pandas as pd\n"
    + "table_df = pd.read_parquet(\"/path/to/table.parquet\")\n"
    + _INSPECT,
)

_DATA_RULE = {
    DataAccess.REGISTERED: (
        "- Use only the data the runtime registers. Do not access files, the network,\n"
        "  benchmark modules or validator code."
    ),
    DataAccess.FILES: (
        "- Read only the listed files and write only where this prompt tells you to.\n"
        "  Do not access the network, benchmark modules or validator code."
    ),
}

_REVISION_WARNING = (
    "\n- The host may revise the data between turns. Base each turn's answer on the\n"
    "  data as it stands in that turn."
)

_ASSIGN_VARIABLES = (
    "- Assign every required output variable in the runtime; printing a value does\n"
    "  not record it."
)

_ANSWER_IN_REPLY = (
    "- End your final answer with exactly one fenced ```json block holding a single\n"
    "  object whose keys are the required output names. A table output is a list of\n"
    "  row objects keyed by column name; a missing value is null. An output absent\n"
    "  from that block is not recorded, however clearly the text above it states it."
)

# The common text tells every paradigm not to print whole tables. A table that
# must be written into the reply is the exception: the model can only copy what
# it has seen, so forbidding the print would force it to invent the rows.
_PRINT_THE_DELIVERED_TABLE = (
    "\n- A table you deliver in that block is the one exception to printing small\n"
    "  samples: print it in full first, for instance with\n"
    "  `print(table.to_json(orient=\"records\"))`, and copy the printed rows exactly.\n"
    "  Never write a row you have not printed."
)

_TABLES_AS_FILES = (
    "- Deliver a table output by writing it to {output_dir}/<output name>.parquet\n"
    "  with `DataFrame.to_parquet`. Every other output goes in the final answer: end\n"
    "  it with exactly one fenced ```json block holding a single object whose keys\n"
    "  are those outputs' names; a missing value is null. An output that is neither\n"
    "  written as a file nor in that block is not recorded, however clearly the text\n"
    "  above it states it."
)

# ----- delivering an object that need not be a table (core.fidelity) ---------
#
# The fidelity study's producer builds an object — a table, an array, a fitted
# model, a structure of several — and delivers it the way its arm delivers a
# table. Where that is a reply or a file, the table rule does not say what to do
# with the rest, so these say it; the variables rule needs no variant, an
# assignment being the same for any object.

_OBJECT_IN_REPLY = (
    "\n- An output that is not a table — an array, a fitted model, a structure of\n"
    "  several parts — is a JSON object holding everything needed to rebuild it\n"
    "  exactly: its type, and every attribute, dtype and parameter it carries,\n"
    "  written at full precision."
)

_PRINT_THE_DELIVERED_OBJECT = (
    "\n- What you deliver in that block is the one exception to printing small\n"
    "  samples: print it in full first — a table with\n"
    "  `print(table.to_json(orient=\"records\", double_precision=15))`, anything\n"
    "  else attribute by attribute at full precision — and copy the printed values\n"
    "  exactly. Never write a value you have not printed."
)

_OBJECT_AS_FILE = (
    "- Deliver the object output by writing it to {path} with {writer}. Every\n"
    "  other output goes in the final answer: end it with exactly one fenced\n"
    "  ```json block holding a single object whose keys are those outputs' names;\n"
    "  a missing value is null. An output that is neither written as a file nor in\n"
    "  that block is not recorded, however clearly the text above it states it."
)


def object_delivery(delivers: Delivery, *, path: Path | None = None, writer: str | None = None) -> str:
    """The delivery rule for an agent whose output is an object of any kind.

    ``path`` and ``writer`` — the file to write and the call that writes that
    kind of object — are the file delivery's; the other two need nothing.
    """
    if delivers is Delivery.VARIABLES:
        return _ASSIGN_VARIABLES
    if delivers is Delivery.REPLY:
        return _ANSWER_IN_REPLY + _OBJECT_IN_REPLY + _PRINT_THE_DELIVERED_OBJECT
    return _OBJECT_AS_FILE.format(path=path, writer=writer)


_SYSTEM_INSTRUCTIONS_TEMPLATE = """
You are a financial data-analysis agent operating in a persistent Jupyter-like
Python runtime. {data_access}

Executing code:
{action_rules}
  Never merely say that you will inspect the data: inspect it in code, and put
  progress updates in Python comments, never in a standalone planning message.
- Never predict or invent execution output. Conclude only from results the
  environment actually returned.
- The session is continuous: variables, imports and intermediate results persist
  across blocks and can be referenced directly. Reuse them instead of
  recomputing.
- Keep each block compact. Print only small filtered samples or aggregates,
  never whole tables, and do not plot.
{data_rule}

What a step looks like. {first_step}

This is not a step. It runs nothing, and because it contains no code the run
ends here with {outputs_missing}:

I'll start by inspecting the available data to understand the structure.

Analysing:
- Determine the relevant records and their financial meaning from the question
  and the data. Rows with similar labels are not interchangeable: confirm
  period, unit, scope and filing before treating values as comparable.
- Convert units only when the requested output requires it.

Answering:
{delivery}
- The final answer states each result together with the basis it rests on and
  the limits of what it establishes, in plain financial language without
  internal DataFrame or column names. Cover everything the question asks and
  nothing decorative.
"""


def _data_access(paradigm: Paradigm, injection: str, tables, paths) -> str:
    if paradigm.data_access is DataAccess.REGISTERED:
        return _REGISTERED_ACCESS[injection]
    listing = "\n".join(f"- {paths[table.name]}\n  {table.description}" for table in tables)
    return _FILE_ACCESS.format(listing=listing)


_FENCED_FIRST_STEP = (
    "A complete first response is only this — one fence,\n"
    "nothing before or after it ({stands_for}):\n\n```python\n{code}\n```"
)


def _first_step(paradigm: Paradigm, injection: str) -> str:
    """The worked first step: the same code, shown in the paradigm's action format."""
    if paradigm.data_access is DataAccess.REGISTERED:
        stand_in, code = _REGISTERED_FIRST_STEP[injection]
    else:
        stand_in, code = _FILE_FIRST_STEP
    return _worked_step(paradigm.action, stand_in, code)


def _worked_step(action: Action, stands_for: str, code: str) -> str:
    if action is Action.FENCED_CODE:
        return _FENCED_FIRST_STEP.format(stands_for=stands_for, code=code)
    indented = "\n".join(f"    {line}" for line in code.splitlines())
    return (
        "A complete first response is only this — one call,\n"
        f"nothing before or after it ({stands_for}), running this code:\n\n{indented}"
    )


def _delivery(paradigm: Paradigm, output_dir: Path | None) -> str:
    if paradigm.delivery is Delivery.VARIABLES:
        return _ASSIGN_VARIABLES
    if paradigm.delivery is Delivery.REPLY:
        return _ANSWER_IN_REPLY + _PRINT_THE_DELIVERED_TABLE
    return _TABLES_AS_FILES.format(output_dir=output_dir)


def system_instructions(
    injection: str = "eager", *, paradigm: Paradigm = CAVE,
    tables: Sequence[RuntimeTable] = (), paths: Mapping[str, Path] | None = None,
    output_dir: Path | None = None, warn_of_revisions: bool = False,
    delivery: str | None = None,
) -> str:
    """The agent's system prompt for one paradigm.

    ``injection`` applies when the runtime registers the data: ``"eager"`` as
    loaded DataFrames, ``"lazy"`` as one handle that loads a table on request.
    ``paths`` are where a paradigm that reads files reads them, and
    ``output_dir`` where a paradigm that delivers files writes them.
    ``warn_of_revisions`` adds, for every paradigm alike, that the host may
    revise the data between turns. ``delivery`` replaces the delivery rule with
    :func:`object_delivery`'s, for an agent whose output need not be a table.
    """
    if injection not in INJECTION_MODES:
        raise ValueError(f"injection must be one of {INJECTION_MODES}, got {injection!r}")
    slots = _slots(paradigm, injection, tables, paths or {}, output_dir)
    if warn_of_revisions:
        slots["data_rule"] += _REVISION_WARNING
    if delivery is not None:
        slots["delivery"] = delivery
    return _SYSTEM_INSTRUCTIONS_TEMPLATE.format(**slots)


def _slots(
    paradigm: Paradigm, injection: str, tables: Sequence[RuntimeTable],
    paths: Mapping[str, Path], output_dir: Path | None,
) -> dict[str, str]:
    """The template's paradigm sentences, each from its own axes.

    What a sentence may depend on is part of the design, and
    ``tests/test_prompts.py`` holds it: two paradigms that agree on a sentence's
    axes read the same sentence.
    """
    return {
        "data_access": _data_access(paradigm, injection, tables, paths),
        "action_rules": _ACTION_RULES[paradigm.action].format(
            outputs_ready=_OUTPUTS_READY[paradigm.delivery],
        ),
        "first_step": _first_step(paradigm, injection),
        "data_rule": _DATA_RULE[paradigm.data_access],
        "outputs_missing": _OUTPUTS_MISSING[paradigm.delivery],
        "delivery": _delivery(paradigm, output_dir),
    }


# ----- the second agent of a pipeline (core.pipeline) ---------------------------
#
# What it is told about where its table is, and how to open it. One entry per
# channel, keyed by the channel's name; a test pins that every channel has one.

_HANDED_ACCESS = {
    "object": (
        "Another agent has computed a table and it is registered in your runtime\n"
        "as `{table}`, a pandas DataFrame; it is not in this text. Write and\n"
        "execute Python to inspect and calculate from it. It is the only data you\n"
        "have: there are no files to read and nothing else is registered."
    ),
    "shared": (
        "You are working in the same runtime as the agent before you, and what it\n"
        "registered is still there — the table it computed is `{table}`, a pandas\n"
        "DataFrame, and the runtime describes it above along with anything else it\n"
        "left. None of it is in this text. Write and execute Python to inspect and\n"
        "calculate from it. There are no files to read."
    ),
    "file": (
        "Another agent has computed a table and written it to the Parquet file\n"
        "named below; it is not in this text, and nothing is registered in your\n"
        "runtime. Load it with `pd.read_parquet(path)`, then write and execute\n"
        "Python to inspect and calculate from it. It is the only file you may read.\n"
        "\n- {path}"
    ),
    "text": (
        "Another agent has computed a table and its reply is quoted at the head of\n"
        "the question below; that reply is the only place the table exists. Nothing\n"
        "is registered in your runtime and there are no files to read. Put the rows\n"
        "into Python yourself, then write and execute code to calculate from them."
    ),
    # The same first three sentences as "text", so the two arms are told the same
    # thing about the table; the fourth is the one thing that differs.
    # The orchestrated study's text arms: the table reaches the worker inside the
    # instruction an orchestrator agent wrote, wherever in it the orchestrator put it.
    "instruction": (
        "The orchestrator directing you has put everything you need into the\n"
        "instruction below, including any table, written out as text; that text is\n"
        "the only place the table exists. No data is registered in your runtime and\n"
        "there are no files to read. Put the rows into Python yourself, then write\n"
        "and execute code to calculate from them."
    ),
    # The orchestrated study's file arm: the orchestrator names the file to read.
    "instruction_file": (
        "The orchestrator directing you names, in the instruction below, the Parquet\n"
        "file holding the table you are to work from; the table is not in this text,\n"
        "and no data is registered in your runtime. Load it with\n"
        "`pd.read_parquet(path)`, then write and execute Python to inspect and\n"
        "calculate from it. It is the only file you may read."
    ),
    # The fidelity study's consumer (core.fidelity): the same three channels,
    # for an object that need not be a table. What kind of object it is, the
    # runtime's description (object) or the instruction (the others) says.
    "object_any": (
        "Another agent has built an object and it is registered in your runtime as\n"
        "`{table}`; the runtime describes it above, and it is not in this text.\n"
        "Write and execute Python to inspect it and work from it. It is the only\n"
        "data you have: there are no files to read and nothing else is registered."
    ),
    "instruction_object": (
        "The orchestrator directing you has put everything you need into the\n"
        "instruction below, including the object you are to work from, written out\n"
        "as text; that text is the only place the object exists. No data is\n"
        "registered in your runtime and there are no files to read. Rebuild the\n"
        "object in Python yourself, exactly as described — its type, its dtypes,\n"
        "its parameters — then write and execute code to work from it."
    ),
    "instruction_file_object": (
        "The orchestrator directing you names, in the instruction below, the file\n"
        "holding the object you are to work from; the object is not in this text,\n"
        "and no data is registered in your runtime. Load it with `{loader}(path)`,\n"
        "then write and execute Python to inspect it and work from it. It is the\n"
        "only file you may read."
    ),
    "text_bound": (
        "Another agent has computed a table and its reply is quoted at the head of\n"
        "the question below; that reply is the only place the table exists. Nothing\n"
        "else is registered in your runtime and there are no files to read. That\n"
        f"same reply is also bound in your runtime as the string `{HANDED_REPLY}`, so\n"
        "you can parse the table out of it in code instead of retyping the rows."
    ),
}

_HANDED_ORIENT = "# Orient before calculating: the columns, dtypes and row count in play\n"
_HANDED_OBJECT_ORIENT = "# Orient before working: what the object is, and what it holds\n"
_LOOK_AT_THE_OBJECT = (
    "print(type({table}))\n"
    "print({table}.dtypes if hasattr({table}, \"dtypes\") else repr({table})[:2000])"
)
OBJECT_CHANNELS = ("object_any", "instruction_object", "instruction_file_object")
_LOOK_AT_THE_TABLE = (
    "print({table}.dtypes)\n"
    "print(len({table}))\n"
    "print({table}.head())"
)
_HANDED_FIRST_STEP = {
    "object": ("nothing stands in: this is the code", _LOOK_AT_THE_TABLE),
    "shared": ("nothing stands in: this is the code", _LOOK_AT_THE_TABLE),
    "file": (
        "the path stands for the file named above",
        "import pandas as pd\n"
        "{table} = pd.read_parquet(\"/path/to/table.parquet\")\n" + _LOOK_AT_THE_TABLE,
    ),
    "text": (
        "the rows stand for the quoted table's own",
        "import pandas as pd\n"
        "{table} = pd.DataFrame([\n"
        "    # every row of the quoted table, copied exactly\n"
        "])\n"
        "print(len({table}))",
    ),
    "instruction_file": (
        "the path stands for the file the instruction names",
        "import pandas as pd\n"
        "{table} = pd.read_parquet(\"/path/to/table.parquet\")\n" + _LOOK_AT_THE_TABLE,
    ),
    "instruction": (
        "the rows stand for the table's own",
        "import pandas as pd\n"
        "{table} = pd.DataFrame([\n"
        "    # every row of the table in the instruction, copied exactly\n"
        "])\n"
        "print(len({table}))",
    ),
    "object_any": ("nothing stands in: this is the code", _LOOK_AT_THE_OBJECT),
    "instruction_object": (
        "the ellipsis stands for the object's own contents",
        "import numpy as np\n"
        "import pandas as pd\n"
        "{table} = ...  # the object in the instruction, rebuilt exactly as described\n"
        + _LOOK_AT_THE_OBJECT,
    ),
    "instruction_file_object": (
        "the path stands for the file the instruction names",
        "import joblib\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "{table} = {loader}(\"/path/to/object.{extension}\")\n" + _LOOK_AT_THE_OBJECT,
    ),
    "text_bound": (
        "nothing stands in: this is the code",
        "import json, re\n"
        "import pandas as pd\n"
        f"block = re.findall(r\"```json\\s*\\n(.*?)```\", {HANDED_REPLY}, re.DOTALL)[-1]\n"
        "delivered = json.loads(block)\n"
        "print(list(delivered))          # the output names the reply delivered\n"
        "{table} = pd.DataFrame(next(v for v in delivered.values() if isinstance(v, list)))\n"
        "print(len({table}))",
    ),
}

# How the second agent's question opens when the table reached it as text. The
# markers say where the quotation ends, because a reply cut off mid-table would
# otherwise run into the question.
QUOTED_REPLY = (
    "Another agent was asked for a table. This was its entire reply, between the\n"
    "markers:\n\n<<<REPLY\n{reply}\nREPLY>>>\n\n"
)

# Two of them: a handed agent that delivers its own table as a file is told where
# to write it, so it cannot also be told to write nothing. Only that clause
# differs — what may be read is the same rule in both.
_HANDED_DATA_RULE = {
    False: (
        "- Use only the table you were handed, and write nothing to disk. Do not\n"
        "  access the network, benchmark modules or validator code, and do not go\n"
        "  looking for the source data it was computed from."
    ),
    True: (
        "- Use only the table you were handed, and write nothing but the output file\n"
        "  this prompt names. Do not access the network, benchmark modules or\n"
        "  validator code, and do not go looking for the source data it was computed\n"
        "  from."
    ),
}

# Two, as for tables: an agent handed an object that hands its own on as a
# file is told where it may write, not to write nothing.
_HANDED_OBJECT_DATA_RULE = {
    False: (
        "- Use only the object you were handed, and write nothing to disk. Do not\n"
        "  access the network, benchmark modules or validator code, and do not go\n"
        "  looking for the source data it was built from."
    ),
    True: (
        "- Use only the object you were handed, and write nothing but the output file\n"
        "  this prompt names. Do not access the network, benchmark modules or\n"
        "  validator code, and do not go looking for the source data it was built\n"
        "  from."
    ),
}


# ----- the orchestrator of a multi-agent case (core.orchestration) -------------
#
# One text for every arm. The orchestrator is told that the workers are agent
# objects in its runtime and that each one's description says how to use it;
# what that description says is the arm's medium, and it is stated where the
# library's own multi-agent example states it, in the variable's description. So
# the arms differ in what the runtime describes and in nothing this text says.

ORCHESTRATOR_ACCESS = (
    "You are the orchestrator of a team of worker agents, and you complete the task\n"
    "by directing them. The workers are agent objects registered in your runtime;\n"
    "the runtime describes each below, with what it is for and exactly how to use\n"
    "it from code. None of the task's data is in this text or registered with you\n"
    "directly: only the workers can compute anything.\n"
    "\n"
    "Each worker's conversation starts afresh every time you run it: what you send\n"
    "to `run` is the whole of its instruction, so say what it is to do and pass on\n"
    "what it needs. What one worker produces, another may need: carry it across\n"
    "yourself, the way its description says. Decide which workers to run, in what\n"
    "order, and what to tell each one."
)

ORCHESTRATOR_FIRST_STEP = (
    "A complete first response is only this — one fence,\n"
    "nothing before or after it (`first_worker` stands for whichever worker the\n"
    "task needs first; its description says what to ask it for):\n\n"
    "```python\n"
    "# Run the first worker, then look at what it said before going on\n"
    "result = await first_worker.run(\"the instruction\")\n"
    "print(result.content[:2000])\n"
    "```"
)

ORCHESTRATOR_DATA_RULE = (
    "- Work only through the workers. Do not read files, the network, benchmark\n"
    "  modules or validator code, and do not compute the task's answer yourself:\n"
    "  the {answerer} worker is who answers, and its answer is what counts."
)


def orchestrator_instructions(answerer: str = "analyst") -> str:
    """The orchestrator's system prompt, the same in every arm.

    The workers are not listed here: the runtime lists them, under the
    ``<variables>`` heading of the agent's own prompt, each with the description
    :func:`core.orchestration.describe_worker` gives it. Every slot but the
    three named above is the text every fenced-code agent in the suite reads.
    ``answerer`` is the worker whose answer counts: the pipeline cases' analyst,
    the fidelity cases' consumer.
    """
    return _SYSTEM_INSTRUCTIONS_TEMPLATE.format(
        data_access=ORCHESTRATOR_ACCESS,
        action_rules=_ACTION_RULES[Action.FENCED_CODE].format(
            outputs_ready=f"the {answerer} has answered",
        ),
        first_step=ORCHESTRATOR_FIRST_STEP,
        data_rule=ORCHESTRATOR_DATA_RULE.format(answerer=answerer),
        outputs_missing="the task undone",
        delivery=(
            f"- When the {answerer} has answered, give your final answer: say which workers\n"
            f"  you ran, in what order, and repeat the {answerer}'s answer."
        ),
    )


def describe_handed_frame(description: str, frame) -> str:
    """A handed table's description with what the runtime can read off it.

    The runtime holds the object, so its shape and column dtypes cost nothing
    to state; a file or a quoted reply obliges the model to look for itself,
    and an agent handed a ready object without this often did not look. What is
    stated is exactly what ``DataFrame.dtypes`` and ``len`` would print — no
    sample values, so the description is the same size whatever the table.
    """
    try:
        columns = "; ".join(f"{name}: {dtype}" for name, dtype in frame.dtypes.items())
        shape = f"{len(frame)} rows"
    except AttributeError:
        return description
    return f"{description} It has {shape} and these columns (name: dtype): {columns}."


def describe_handed_object(description: str, value) -> str:
    """A handed object's description with what the runtime can read off it.

    As :func:`describe_handed_frame` for a table; for anything else, the
    object's type, and for a mapping its keys, a sequence its length, an array
    its shape and dtype — again what one line of code would print, and never
    the values.
    """
    if hasattr(value, "dtypes") and hasattr(value, "columns"):
        return describe_handed_frame(description, value)
    if isinstance(value, dict):
        held = f"a dict with keys {list(value)}"
    elif isinstance(value, (list, tuple)):
        held = f"a {type(value).__name__} of {len(value)} elements"
    elif hasattr(value, "shape") and hasattr(value, "dtype"):
        held = f"a {type(value).__name__} of shape {tuple(value.shape)} and dtype {value.dtype}"
    else:
        held = f"an object of type {type(value).__name__}"
    return f"{description} It is {held}."


def handed_agent_instructions(
    channel: str, *, delivers: Delivery, table: str = HANDED_TABLE,
    path: Path | None = None, output_dir: Path | None = None,
    action: Action = Action.FENCED_CODE, loader: str | None = None,
    extension: str | None = None, delivery: str | None = None,
) -> str:
    """The system prompt for an agent handed a table by the agent before it.

    Every agent in a pipeline but the first reads one of these. Three
    slots are the channel's — where the table is, the worked first step that
    opens it, and the rule about what may be read, since it has been handed one
    table rather than given a list of files — and ``delivers`` picks the same
    sentence about handing something on that the delivery study uses, because a
    middle agent hands on a table exactly as the first one does. The rest is the
    text every fenced-code agent in the suite reads, so a difference between
    channels cannot be a difference in how the agents were told to run code.
    ``action`` is that format; the pipeline study's agents all use the fenced
    one, and the orchestration study's json workers the tool call, shown the
    same worked first step as :func:`system_instructions` shows it. The
    ``OBJECT_CHANNELS`` hand an object of any kind; ``loader`` and
    ``extension`` are how the file one is opened. ``delivery`` replaces the
    rule about handing something on, for an agent whose output need not be a
    table (:func:`object_delivery`).
    """
    # The described arm differs from the object arm in the runtime's own
    # description of the variable, not in anything said here.
    channel = "object" if channel in ("object_described", "object_signalled") else channel
    stands_for, code = _HANDED_FIRST_STEP[channel]
    handed_object = channel in OBJECT_CHANNELS
    orient = _HANDED_OBJECT_ORIENT if handed_object else _HANDED_ORIENT
    slots = {"path": path, "table": table, "loader": loader, "extension": extension}
    return _SYSTEM_INSTRUCTIONS_TEMPLATE.format(
        data_access=_HANDED_ACCESS[channel].format(**slots),
        action_rules=_ACTION_RULES[action].format(outputs_ready=_OUTPUTS_READY[delivers]),
        first_step=_worked_step(action, stands_for, (orient + code).format(**slots)),
        data_rule=(_HANDED_OBJECT_DATA_RULE if handed_object else _HANDED_DATA_RULE)[
            delivers is Delivery.FILES
        ],
        outputs_missing=_OUTPUTS_MISSING[delivers],
        delivery=delivery if delivery is not None else
        _delivery(Paradigm("handed", DataAccess.FILES, action, delivers), output_dir),
    )


def turn_prompt(query: str, outputs: Sequence[Variable]) -> str:
    """The turn's question followed by its output contract, the same for every paradigm.

    A paradigm that delivers outputs as variables also has the runtime describe
    each registered output variable, in the system prompt. Leaving the contract
    there alone would have one paradigm read it far from the question and
    another beside it, and a pilot showed that difference, not the delivery
    channel, deciding whether outputs were delivered at all. So every paradigm
    reads the same names and descriptions in the same place.
    """
    contract = "\n".join(f"- {output.name}: {output.description}" for output in outputs)
    return f"{query}\n\nRequired outputs for this turn:\n{contract}"


def consumer_turn(instruction: str, question: str, outputs: Sequence[Variable]) -> str:
    """The fidelity consumer's turn: the orchestrator's instruction, then the host's question.

    The question is not in the orchestrator's task, so the orchestrator cannot
    answer it upstream or hand on only the part of the object it would take;
    its job is the object, whole, and the host asks the question of whoever
    holds it.
    """
    return turn_prompt(f"{instruction}\n\nThe question about this object: {question}", outputs)


def reviser_turn(instruction: str, keep_as: Variable, outputs: Sequence[Variable]) -> str:
    """A reviser's turn: the orchestrator's instruction, and the host's one standing rule.

    The host reads the object the agent was handed from ``keep_as``, in every
    arm alike, so that a hop's crossing is evidence rather than an inference
    from the object after it was edited. Without it a reviser that edits what
    it was handed in place leaves the host nothing to compare: the "object as
    it arrived" would be the object as it was changed.
    """
    return turn_prompt(
        f"{instruction}\n\nBefore you change anything, bind the object exactly as you were "
        f"given it to `{keep_as.name}` and leave it unchanged — make your changes on a copy. "
        f"It is not something you hand on; it stays in your runtime.",
        outputs,
    )


def repair_nudge(paradigm: Paradigm, missing: Sequence[str]) -> str:
    """What a turn that ran no code is told, once, before it is scored."""
    return (
        "Your previous response ran no code, so the required outputs "
        f"{', '.join(missing)} are still missing. {_HOW_TO_RUN_CODE[paradigm.action]}"
    )
