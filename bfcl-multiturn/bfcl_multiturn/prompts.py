"""What each arm is told, which differs only in how an action is expressed.

The shared part states the task and the one constraint the benchmark imposes:
state must be changed by calling the tools, because the benchmark scores a
conversation by replaying the calls it was told about onto fresh instances. An
agent that assigns to an attribute leaves nothing to replay and is scored wrong
for a reason that has nothing to do with its paradigm.

The differing part names the action. It has to be explicit for the fenced arm:
a model whose training favours tool-call markup will reach for it, and nothing
catches that -- a provider rejects a malformed JSON tool call and lets the model
try again, while a fenced block is a prompt convention, so unparsed code is sent
on as chat and the turn silently does nothing. This was observed here before it
was guarded: qwen3.8-flash answered the first smoke tasks in `<tool_call>` XML
and executed nothing.
"""

SHARED = """\
You are completing a task for a user.

- Change anything only by {acting}. Never assign to an object's attributes
  directly, and never re-implement what a function does.
- Read the state before you change it, rather than assuming it.
- Do only what the user asked for in their current message. Do not anticipate
  what they might ask next.
- When the request cannot be met with what you have, say so in plain text.
- When you have finished, reply in plain text describing what you did.
"""

#: The fenced arm. Names the markup a model is likely to reach for instead,
#: because an unparsed block is not an error here but a turn that did nothing.
CAVE = SHARED.format(acting="calling the provided functions") + """
Call functions only by writing Python inside a fenced block that opens with
```python and closes with ```, exactly like this:

```python
result = some_function(argument="value")
print(result)
```

Nothing else runs. Any other form -- a tool-calling token your training favours,
an XML-like <tool_call> or <function> tag, a bare indented snippet -- is not
executed: it is shown to the user as text, and you will be left waiting for a
result that never arrives.
"""

#: The JSON arm. The provider enforces the format, so nothing has to be said
#: about it; what remains is the shared task and constraint.
FC = SHARED.format(acting="calling the tools you have been given")

#: Sent when a fenced turn executed nothing but its reply looks like an attempted
#: call. Mirrors how the provider lets a JSON arm retry a rejected call, so
#: neither paradigm is penalised for a format slip the other is protected from.
FENCE_REMINDER = """\
Your last message was not executed. Only code inside a fenced ```python block
runs; anything else is shown to the user as text, which is what just happened,
so you have no results yet.

Send the same code again inside a ```python block, or, if no code is needed,
answer in plain words.
"""
