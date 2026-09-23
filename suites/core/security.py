"""Advisory security checker for the Python agent runtime.

CaveAgent solves benchmarks by writing and executing Python, so model-generated
code runs in-process. These static rules restrict the most dangerous operations
before execution. They are defense in depth, NOT a sandbox: a determined agent
can evade any static check, so evaluations should also run inside an OS or
container boundary.

Adapted from a sibling harness's `core/security.py`, with two deliberate differences:

- `open` is NOT in FORBIDDEN_FUNCTIONS. `FunctionRule` matches on the callee's
  bare name, so it cannot distinguish `open("/etc/passwd")` from `blinds.open()`
  — and the smart-home suite models blinds, windows and doors with an `open()`
  method (`evals/smart_home/types.py`). Including it would fail every smart-home
  scenario on legitimate device control. Reading files is therefore reachable
  here; the container boundary is what closes it.
- The SQL RegexRules are dropped. the sibling harness validates against live PostgreSQL;
  this repo has no database, so those patterns could only produce false
  positives on ordinary prose or variable names.
"""

from cave_agent import SecurityChecker, ImportRule, FunctionRule, AttributeRule

# Imports that would let generated code reach the filesystem, the network, or
# the interpreter's internals.
FORBIDDEN_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "pathlib",
    "socket", "urllib", "http", "ctypes", "gc",
    "csv", "multiprocessing", "threading",
}

# Callables that permit arbitrary execution or interpreter introspection.
# NOTE: `open` is intentionally absent — see the module docstring.
FORBIDDEN_FUNCTIONS = {
    "exec", "compile", "input", "raw_input",
    "exit", "quit", "__import__", "globals", "locals",
    "breakpoint", "eval",
}

# Attributes that expose interpreter internals and allow sandbox escape.
FORBIDDEN_ATTRIBUTES = {
    "__globals__", "__locals__", "__code__", "__closure__",
    "__defaults__", "__dict__", "__class__", "__bases__",
    "__mro__", "__subclasses__", "__import__", "__builtins__",
}


def create_security_checker() -> SecurityChecker:
    """Build the checker applied to every block of model-generated code."""
    return SecurityChecker([
        ImportRule(FORBIDDEN_IMPORTS),
        FunctionRule(FORBIDDEN_FUNCTIONS),
        AttributeRule(FORBIDDEN_ATTRIBUTES),
    ])


# Shared by the runtime adapter.
security_checker = create_security_checker()
