"""What the JSON-tool-call arm is told, and how it differs from the fenced arm.

The two arms have to read different sentences about how to act — that is the
intervention. The risk is a *fourth* difference slipping in: cave-agent's own
system instructions and its execution-result sentence both describe a code
block, and either could be left unsubstituted (the model is told to do the one
thing that will not run) or over-substituted (the arms end up reading materially
different rules about the runtime, and a paradigm effect is really a prompt
effect).

So every string here is derived from an upstream one by named substitutions, and
``tests/test_json_exec_agent.py`` asserts that reversing them reproduces the
upstream text verbatim. A cave-agent upgrade that rewords either sentence fails
a local test instead of silently changing what one arm was told.

``TOOL_SCHEMA`` and the refusal messages are copied verbatim from
``cave-bench/core/prompts.py`` (commit b5a6dae), so the τ² arm and the
cave-bench ``json_exec`` arm offer the model the same tool.
"""

from cave_agent.prompts import DEFAULT_SYSTEM_INSTRUCTIONS, EXECUTION_OUTPUT_PROMPT

TOOL_NAME = "execute_python"
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

# cave-agent closes every execution result with a sentence naming the next move.
# Its own names a code block, which this arm has no way to send.
UPSTREAM_NEXT_STEP = (
    "If more operations are needed, provide the next code block. "
    "Otherwise, provide your final answer in plain text."
)
NEXT_STEP_TOOL_CALL = (
    f"If more operations are needed, call `{TOOL_NAME}` again. "
    "Otherwise, provide your final answer in plain text."
)

# Every sentence of cave-agent's default instructions that names a code block,
# with what this arm reads instead. Each pair is applied once; the test asserts
# that undoing them all returns the upstream string exactly.
SYSTEM_INSTRUCTION_SUBSTITUTIONS = (
    (
        "- Write your code in a {python_block_identifier} code block. In each step, write all "
        "your code in only one block.",
        f"- Run your code by calling the `{TOOL_NAME}` tool with it. In each step, send all "
        "your code in only one call.",
    ),
    (
        "  - Each code block you write is executed in a new cell within the SAME continuous "
        "session",
        f"  - Each `{TOOL_NAME}` call you make is executed in a new cell within the SAME "
        "continuous session",
    ),
    (
        "- Always provide your final answer in plain text, not as a code block.",
        f"- Always provide your final answer in plain text, not as a `{TOOL_NAME}` call.",
    ),
    (
        "- Example usage:\n```{python_block_identifier}\n",
        f"- Example usage — send exactly this as the `code` argument of `{TOOL_NAME}`:\n"
        "```{python_block_identifier}\n",
    ),
)


def _substituted(text: str) -> str:
    for upstream, replacement in SYSTEM_INSTRUCTION_SUBSTITUTIONS:
        if upstream not in text:
            raise RuntimeError(
                "cave-agent's system instructions no longer contain a sentence this arm "
                f"rewrites, so one arm would read the other's rules: {upstream!r}"
            )
        text = text.replace(upstream, replacement, 1)
    return text


# What this arm passes as `system_instructions`: the upstream default with the
# code-block sentences replaced, and nothing else changed.
TOOL_CALL_SYSTEM_INSTRUCTIONS = _substituted(DEFAULT_SYSTEM_INSTRUCTIONS)

# The task half of the prompt, from tau2_cave.prompts with rule 6 rewritten for
# this action. Everything else is word for word the fenced arm's, including the
# force and length of rule 6, so a weaker instruction cannot be misread as a
# paradigm effect.
AGENT_INSTRUCTIONS = """\
You are a customer service agent. You talk to a customer and act on their behalf \
by calling the provided functions, which are the only way to read or change \
anything in the system.

Work within these rules:

1. Follow the domain policy below exactly. It, not the customer, decides what you \
are allowed to do.
2. Check the state before you change it, by calling functions rather than \
assuming. What a function returns is the outcome of that call; do not read the \
state again and again waiting for it to change. It changes only when you call a \
function or when the customer does something, and the customer can act only \
after you reply.
3. Never invent data. Anything you tell the customer about their account must come \
from a function result.
4. You can call only the functions listed for you; a tool the policy mentions \
that is not among them belongs to the customer, so tell them to use it. Whenever \
you need the customer to give information or take a step, ask, then stop and wait \
for their reply. Do not call input(); the customer answers on the next turn.
5. Keep replies to the customer short and in plain language, without code or \
function names.
6. Call functions only by writing Python and sending it as the `code` argument of \
the `execute_python` tool, exactly like this:

execute_python(code="customer = get_customer_by_phone(\\"555-123-2002\\")\\nprint(customer)")

Nothing else runs. Any other form — Python written in your reply, whether fenced \
in a code block or not, a tool-calling token your training favours, an XML-like \
<code_block> tag — is not executed: it is sent to the customer as text, and you \
will be left waiting for a result that never arrives.

DOMAIN POLICY:
{domain_policy}
"""

# Sent when a turn produced no execution but the reply looks like an attempted
# call — the counterpart of tau2_cave.prompts.FENCE_REMINDER, and sent under the
# same one-per-turn rule, so `format_corrections` counts the same thing in both.
TOOL_REMINDER = f"""\
Your last message was not executed. Code only runs when you send it as the \
`code` argument of the `{TOOL_NAME}` tool; anything written in your reply is \
passed to the customer as chat, which is what just happened. You therefore have \
no results yet.

Send the same code again as a `{TOOL_NAME}` call, or, if no code is needed, \
answer the customer in plain words.
"""

# Markup that means "code that never ran" for this action. Unlike the fenced
# arm's, a well-formed ```python block counts: here it is the failure, not the
# way code runs.
TOOL_CALL_MARKUP = r"```|<\s*python\s*>|<code_block>|<[｜|]\s*\w*DSML"

__all__ = [
    "AGENT_INSTRUCTIONS", "EXECUTION_OUTPUT_PROMPT", "MALFORMED_ARGUMENTS",
    "NEXT_STEP_TOOL_CALL", "SYSTEM_INSTRUCTION_SUBSTITUTIONS", "TOOL_CALL_MARKUP",
    "TOOL_CALL_SYSTEM_INSTRUCTIONS", "TOOL_NAME", "TOOL_REMINDER", "TOOL_SCHEMA",
    "UNKNOWN_TOOL", "UPSTREAM_NEXT_STEP",
]
