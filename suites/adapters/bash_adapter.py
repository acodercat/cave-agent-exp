"""Bash + filesystem agent adapter.

Single-tool JSON function calling: the LLM calls ``bash(command)``. The command
runs in a per-conversation sandbox with a uv-managed Python interpreter on PATH.
State persists by writing files to the sandbox; nothing else.

This is the paper's third Q3 paradigm (Table 7, "Bash (filesystem)"): filesystem
persistence against CaveAgent's runtime variables, through the same evaluator,
validators and token accounting.

Sandboxes are left on disk for inspection (`.bash_sandboxes/conv_*/`); sweep them
with `rm -rf .bash_sandboxes`. Both that directory and the `.bash_venv` the
sandboxes run under are gitignored.

SAFETY: every command runs under bubblewrap (`_isolation_argv`) — all namespaces
unshared, so there is no network and no view of the host's processes; a read-only
/usr and venv; and one writable path, the conversation's sandbox directory. The
project is not mounted beyond `evals/` and `core/`, so `models.toml` and its keys
do not exist inside. What the deny-list below still covers is only what isolation
cannot express: a fixed package set, and fork bombs. Isolation is required: if
bubblewrap is missing or blocked, the run fails rather than falling back to the
host, unless CAVE_BENCH_BASH_NO_SANDBOX=1 waives it.
"""

import inspect
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from litellm import acompletion

from adapters.litellm_adapter import LitellmModel
from core.agent import Agent, AgentFactory, AgentResponse, TokenUsage
from core.types import ToolCall

logger = logging.getLogger("Agent.BashAdapter")


# ---------------------------------------------------------------------------
# Sandbox / uv venv management
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Project-local paths so sandboxes survive across reboots and stay easy to
# inspect after a run. Both are .gitignored.
_UV_VENV_DIR = _PROJECT_ROOT / ".bash_venv"
_SANDBOX_ROOT = _PROJECT_ROOT / ".bash_sandboxes"
_SANDBOX_PREFIX = "conv_"
# Written only after dependencies install cleanly, and holding the list they
# were installed from.
_VENV_STAMP = _UV_VENV_DIR / "cave-bench-deps.json"


def _ensure_uv_venv() -> Path:
    """Create a uv-managed venv with the project's runtime dependencies installed.

    Idempotent: reuse the venv when the stamp says these exact dependencies are
    already in it. The stamp, rather than the interpreter's existence, is what
    marks it usable — an interrupted or failed install leaves a venv whose
    `bin/python` is there but whose packages are not, and a sandbox missing
    pandas scores as a string of model failures rather than as the broken
    environment it is.

    We install only `pyproject.toml`'s dependency list (not the project itself,
    which has a flat layout incompatible with setuptools auto-discovery). Local
    modules (cave-bench's own packages, scenario tools) are reached via
    PYTHONPATH.
    """
    pyproject = _PROJECT_ROOT / "pyproject.toml"
    deps = tomllib.loads(pyproject.read_text())["project"]["dependencies"]

    if _VENV_STAMP.exists():
        try:
            if json.loads(_VENV_STAMP.read_text()) == deps:
                return _UV_VENV_DIR
        except json.JSONDecodeError:
            pass  # unreadable stamp: rebuild
        logger.info("Bash venv is stale or incomplete; rebuilding")

    py = _UV_VENV_DIR / "bin" / "python"
    logger.info(f"Preparing the bash sandbox venv at {_UV_VENV_DIR} (~10-30s)")
    if not py.exists():
        _run_uv(["uv", "venv", str(_UV_VENV_DIR), "--python", "3.12"])
    _run_uv(["uv", "pip", "install", "--python", str(py), *deps])
    _VENV_STAMP.write_text(json.dumps(deps, indent=2))
    return _UV_VENV_DIR


def _run_uv(command: List[str]) -> None:
    """Run a uv command, raising with its stderr if it fails.

    `check=True` alone reports only an exit status, which leaves a failed
    sandbox build (a yanked release, an offline index, a resolution conflict)
    with no way to tell what went wrong.
    """
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command[:3])} failed (exit {result.returncode}):\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


# ---------------------------------------------------------------------------
# Isolation: every command runs under bubblewrap
# ---------------------------------------------------------------------------

# Escape hatch for a machine where unprivileged user namespaces are unavailable.
# Opting out runs model-written shell commands directly on the host.
_NO_SANDBOX_ENV = "CAVE_BENCH_BASH_NO_SANDBOX"


def _isolation_argv(sandbox: Path, venv: Path) -> List[str]:
    """The bwrap prefix that a sandbox command runs under.

    Namespaces are all unshared, so the command gets a network namespace with no
    interfaces — egress is impossible at the kernel level rather than filtered by
    a regex. The filesystem is assembled rather than inherited: a read-only /usr
    (plus the merged-/usr symlinks), the venv, and only the two package
    directories `tools.py` imports. Nothing else of the project exists inside, so
    `models.toml` and its keys are out of reach. The conversation's sandbox
    directory is the single writable path besides /tmp.
    """
    argv = [
        # Resolved here, against our PATH: the command itself runs with the
        # scrubbed PATH of _build_env, and exec looks a bare name up in the
        # child's PATH — which misses a bwrap installed outside /usr/bin.
        shutil.which("bwrap") or "bwrap",
        "--die-with-parent",
        "--unshare-all",                                  # net, pid, ipc, uts, cgroup, user
        "--new-session",                                  # no terminal-injection back at us
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/etc", "/etc",
        "--symlink", "usr/bin", "/bin",
        "--symlink", "usr/lib", "/lib",
        "--symlink", "usr/lib64", "/lib64",
        "--symlink", "usr/sbin", "/sbin",
        "--ro-bind", str(venv), str(venv),
        "--ro-bind", str(_PROJECT_ROOT / "evals"), str(_PROJECT_ROOT / "evals"),
        "--ro-bind", str(_PROJECT_ROOT / "core"), str(_PROJECT_ROOT / "core"),
        "--bind", str(sandbox), str(sandbox),
        "--chdir", str(sandbox),
    ]
    interpreter = _interpreter_root(venv)
    if interpreter:
        argv += ["--ro-bind", str(interpreter), str(interpreter)]
    return argv


def _interpreter_root(venv: Path) -> Optional[Path]:
    """The directory holding the interpreter the venv's `python` points into.

    uv installs its own CPython under ~/.local/share/uv/python/, and a venv's
    `bin/python` is only a symlink into it — through a version alias that is
    itself a symlink (`cpython-3.12-…` -> `cpython-3.12.13-…`). Mounting the
    directory that holds both keeps the whole chain resolvable inside the
    sandbox; mounting just the resolved install directory leaves `python` as a
    dangling symlink, i.e. "command not found". None when the venv uses the
    system interpreter, which /usr already covers.
    """
    real = (venv / "bin" / "python").resolve()
    if not real.exists() or real.is_relative_to("/usr"):
        return None
    return real.parent.parent.parent


@lru_cache(maxsize=1)
def _isolation_error() -> Optional[str]:
    """Why commands cannot be isolated on this machine, or None when they can.

    Probed once by actually running bwrap: having the binary is not enough, since
    Ubuntu 24.04+ confines unprivileged user namespaces to an AppArmor profile
    that denies the capabilities bwrap needs.
    """
    if shutil.which("bwrap") is None:
        return "bubblewrap is not installed (apt install bubblewrap)"
    with tempfile.TemporaryDirectory() as probe_dir:
        probe = subprocess.run(
            [*_isolation_argv(Path(probe_dir), _UV_VENV_DIR), "/bin/true"],
            capture_output=True, text=True,
        )
    if probe.returncode != 0:
        return f"bwrap cannot create a sandbox here: {probe.stderr.strip()}"
    return None


def _isolation_enabled() -> bool:
    """Whether commands are wrapped in bwrap.

    Raises when isolation is unavailable and has not been explicitly waived, so
    a broken setup fails before a sweep spends money rather than quietly running
    model-written commands on the host.
    """
    if os.environ.get(_NO_SANDBOX_ENV) == "1":
        logger.warning(
            f"{_NO_SANDBOX_ENV}=1: bash commands run on the host without isolation"
        )
        return False
    problem = _isolation_error()
    if problem:
        raise RuntimeError(
            f"The bash paradigm needs bubblewrap to isolate model-written commands, but "
            f"{problem}. Install it, or set {_NO_SANDBOX_ENV}=1 to run without isolation "
            f"(only on a machine you are willing to hand to a model)."
        )
    return True


# ---------------------------------------------------------------------------
# Deny-list: what isolation cannot express
# ---------------------------------------------------------------------------
#
# Only two things are left here. Everything the sandbox already makes impossible
# — network egress, privilege escalation, writes outside the sandbox, reading
# host files — was removed once commands started running under bwrap: those
# patterns bought nothing and cost the baseline real turns, since a word like
# `ssh` or a redirect like `2>/dev/null` matched them and came back "[blocked]".

_DENY_PATTERNS: List[re.Pattern] = [re.compile(p) for p in (
    # Not a safety rule but an experiment-design one: every paradigm must run
    # against the same fixed set of packages, and the system prompt says so.
    r"\bpip[0-9]*\s+install\b",
    r"\buv\s+pip\s+install\b",
    r"\buv\s+(add|sync|tool\s+install|run\s+--with)\b",
    r"\bconda\s+install\b",
    r"\bpoetry\s+(add|install)\b",
    r"\b(apt|apt-get|yum|dnf|pacman|zypper)\b",
    r"\bbrew\s+install\b",
    r"\b(npm|pnpm|yarn)\s+(install|i|add)\b",
    r"\bcargo\s+install\b",

    # Resource exhaustion is the one risk the namespaces do not bound: the
    # sandbox dies with its parent and at the timeout, but until then a fork
    # bomb burns host CPU and memory.
    r":\s*\(\s*\)\s*\{[^}]*\}\s*;\s*:",
)]


def _check_deny_list(command: str) -> Optional[str]:
    """Return a human-readable reason if the command is forbidden, else None."""
    for pat in _DENY_PATTERNS:
        m = pat.search(command)
        if m:
            return f"command blocked: matches forbidden pattern `{m.group(0)}`"
    return None


# ---------------------------------------------------------------------------
# tools.py generation: wrap each scenario tool with a call logger.
# ---------------------------------------------------------------------------

_TOOLS_PY_TEMPLATE = '''\
"""Auto-generated wrapper module — do not edit.

Each scenario tool is re-exported with a thin logger that appends one JSONL
record per call to $CAVE_BASH_TRACE. The original implementation is reused
verbatim, so behaviour is identical to CaveAgent / JSON FC paradigms.
"""
import json
import os
import uuid
import inspect

_TRACE = os.environ["CAVE_BASH_TRACE"]

# Imports of the original functions
{imports}

_originals = {{
{originals_dict}
}}


def _log_call(name, args, kwargs):
    sig = inspect.signature(_originals[name])
    try:
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        arg_dict = dict(bound.arguments)
    except TypeError:
        arg_dict = {{"_args": list(args), "_kwargs": dict(kwargs)}}
    rec = {{
        "function": name,
        "arguments": arg_dict,
        "call_id": uuid.uuid4().hex[:8],
    }}
    with open(_TRACE, "a") as f:
        f.write(json.dumps(rec, default=str) + "\\n")
        f.flush()


def _make(name):
    orig = _originals[name]
    def wrapper(*args, **kwargs):
        _log_call(name, args, kwargs)
        return orig(*args, **kwargs)
    wrapper.__name__ = name
    wrapper.__doc__ = orig.__doc__
    wrapper.__signature__ = inspect.signature(orig)
    return wrapper


{wrapper_assigns}
'''


def _generate_tools_py(functions: List[Callable]) -> str:
    """Build the tools.py source for the given scenario functions.

    Only real Python functions defined in user code are wrapped — typing
    aliases and re-exported builtins are filtered out defensively.
    """
    real = [
        f for f in functions
        if (inspect.isfunction(f) or inspect.ismethod(f))
        and getattr(f, "__module__", "").split(".")[0] not in {"typing", "builtins"}
    ]
    imports = []
    originals_lines = []
    wrapper_lines = []
    for f in real:
        name = f.__name__
        module = f.__module__
        imports.append(f"from {module} import {name} as _orig_{name}")
        originals_lines.append(f'    "{name}": _orig_{name},')
        wrapper_lines.append(f'{name} = _make("{name}")')
    return _TOOLS_PY_TEMPLATE.format(
        imports="\n".join(imports),
        originals_dict="\n".join(originals_lines),
        wrapper_assigns="\n".join(wrapper_lines),
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
You are an agent that completes tasks by running shell commands. You have one
tool: `bash(command)`.

ENVIRONMENT
- Sandbox dir: every command runs in a fresh-per-conversation working directory.
  This is your only writable area. The dir starts empty except for `tools.py`
  (the Python module that exposes scenario tools) and `_calls.jsonl` (a trace
  file — don't touch it).
- Files you write to the working dir persist across `bash` calls within the
  conversation.
- `python` resolves to a managed virtualenv (NOT the system Python). Standard
  library is available; the scenario's tools are exposed as `import tools`.
- 30-second timeout per command. Network is disabled.

YOU MAY
- Execute Python code: `python -c "..."` or `python script.py`.
- Read files anywhere you have permission: `cat`, `head`, `tail`, `less`,
  `grep`, `find`, `wc`, `ls` — for inspecting your sandbox or the system.
- Use any stdlib (`json`, `pickle`, `os`, `sys`, `math`, `datetime`,
  `collections`, `re`, `csv`, `pathlib`, ...).
- Use these third-party packages already installed in the venv:
    pandas, numpy
  (no other 3rd-party packages — see `python -c "import X"` to test).
- Pipe and redirect: `echo ... > file`, `cat a | python -c '...'`,
  `python script.py > out.txt`.
- Write/modify/delete files **inside the working directory**.

YOU MUST NOT
- Install any package — `pip install`, `uv pip install`, `uv add`, `apt`,
  `apt-get`, `npm`, `cargo`, `brew`, `conda` are all blocked. Your environment
  is fixed; work with what's there.
- Make network calls — `curl`, `wget`, `nc`, `ssh`, `scp`, `telnet`, `ftp`,
  Python sockets, etc. are all blocked.
- Run `sudo`, `su`, `chmod 7??`, `chown`, or otherwise escalate privileges.
- Write to system paths (`/etc`, `/usr`, `/bin`, `/sbin`, `/dev`, `/proc`,
  `/sys`, `/boot`, `/lib`, `/root`).
- Execute fork bombs, `shutdown`, `reboot`, or destructive `rm -rf` outside
  `/tmp`.

Violating commands are blocked at the bash layer before they run, and the
return value will start with "[blocked]".

AVAILABLE SCENARIO TOOLS (callable as members of the `tools` module):
{tool_signatures}

CALLING TOOLS — each `python` invocation is a fresh process, so Python
variables defined in one `python -c` do NOT survive into the next.

⚠️ STATE MANAGEMENT — READ THIS CAREFULLY ⚠️

You MUST persist tool results to files when you need them in later steps.
Echoing large results to stdout and trusting them to "stay in your context"
is fragile and wastes tokens — your context is finite, large outputs get
truncated, and re-fetching from the conversation history is expensive.

Workflow you SHOULD follow:

    Step 1 — fetch + persist (don't print full payload, just confirm):
        python -c "import json, tools;
                   data = tools.get_sensor_data(...);
                   json.dump(data, open('sensor_a.json','w'));
                   print('saved sensor_a.json,', len(data['readings']), 'readings')"

    Step 2 — load + compute (NEVER paste data back through the prompt):
        python -c "import json;
                   d = json.load(open('sensor_a.json'));
                   avg = sum(r['value'] for r in d['readings']) / len(d['readings']);
                   json.dump({{'avg': avg}}, open('summary.json','w'));
                   print('avg saved:', avg)"

    Step 3 — read the small summary and answer:
        cat summary.json

Anti-patterns (DON'T do these):
- ❌ python -c "import tools; print(json.dumps(tools.X(...)))"  ← dumps full
     payload back through the prompt; bypasses persistence; expensive
- ❌ Calling `tools.X()` again in a later step to "re-fetch" data you already
     have — read the file you saved.

For larger objects (DataFrames, ndarrays) use pickle:
    python -c "import pickle, pandas as pd; df = ...; pickle.dump(df, open('df.pkl','wb'))"
    python -c "import pickle; df = pickle.load(open('df.pkl','rb')); print(df.head())"

Inspect saved state at any time: `ls -la`, `cat <file>`, `head <file>`.

TASK
{task_description}

When you have enough information, return a concise final answer in plain text
(no tool call). Don't dump files into the answer unless the user asked.
"""


def _signatures_block(functions: List[Callable]) -> str:
    """Render full signatures + docstrings, matching what CaveAgent exposes.

    CaveAgent injects functions as runtime objects, so the LLM has access to
    `help(f)` (full docstring with parameter constraints, return shape,
    examples, raises). For paradigm fairness the bash agent must see the same.
    """
    if not functions:
        return "  (no scenario tools)"
    blocks = []
    for f in functions:
        try:
            sig = str(inspect.signature(f))
        except (ValueError, TypeError):
            sig = "(...)"
        doc = inspect.getdoc(f) or ""
        header = f"### {f.__name__}{sig}"
        blocks.append(f"{header}\n{doc}" if doc else header)
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# The bash tool schema (single tool exposed via JSON FC)
# ---------------------------------------------------------------------------

_BASH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Execute a shell command in a persistent sandbox directory. "
            "Use `python -c '...'` to run Python. Files persist across calls. "
            "30s timeout. No network. No package installs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command. Restrict to Python execution and file IO.",
                },
            },
            "required": ["command"],
        },
    },
}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class BashAgentWrapper(Agent):
    """LLM agent that operates exclusively through a single `bash(command)` tool."""

    def __init__(
        self,
        model: LitellmModel,
        functions: List[Callable],
        max_steps: int = 20,        # match LitellmAgentFactory default
        description: Optional[str] = None,
        bash_timeout: int = 30,
    ):
        """Initialize the bash agent.

        Args:
            model: The LiteLLM model configuration
            functions: Scenario tools, exposed inside the sandbox as `tools.py`
            max_steps: Maximum number of steps (API calls) per run
            description: Task description for the system prompt
            bash_timeout: Per-command timeout in seconds
        """
        self._model = model
        self._max_steps = max_steps
        self._bash_timeout = bash_timeout
        self._functions = functions

        self._venv = _ensure_uv_venv()
        self._isolate = _isolation_enabled()
        _SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
        self._sandbox = Path(tempfile.mkdtemp(prefix=_SANDBOX_PREFIX, dir=_SANDBOX_ROOT))
        self._trace_file = self._sandbox / "_calls.jsonl"
        self._trace_file.touch()
        (self._sandbox / "tools.py").write_text(_generate_tools_py(functions))

        sys_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            tool_signatures=_signatures_block(functions),
            task_description=(description or "").strip() or "(see user query)",
        )
        self._messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]

        self._executed_commands: List[str] = []  # reported as code_snippets

    @property
    def runtime(self) -> Optional[Any]:
        return None  # by design — this paradigm has no runtime

    @property
    def messages(self) -> List[Dict[str, Any]]:
        """The conversation history, for the transcript written beside results."""
        return self._messages

    # ----- bash execution ---------------------------------------------------

    def _build_env(self) -> Dict[str, str]:
        bin_dir = self._venv / "bin"
        return {
            "PATH": f"{bin_dir}:/usr/local/bin:/usr/bin:/bin",
            "PYTHONPATH": f"{self._sandbox}:{_PROJECT_ROOT}",
            "VIRTUAL_ENV": str(self._venv),
            "HOME": str(self._sandbox),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONUNBUFFERED": "1",
            "CAVE_BASH_TRACE": str(self._trace_file),
        }

    def _execute_bash(self, command: str) -> str:
        """Run a command inside the sandbox and return formatted stdout/stderr."""
        self._executed_commands.append(command)  # reported whether or not it runs
        blocked = _check_deny_list(command)
        if blocked:
            return f"[blocked]\n{blocked}"

        argv = ["bash", "-c", command]
        if self._isolate:
            argv = [*_isolation_argv(self._sandbox, self._venv), *argv]

        try:
            result = subprocess.run(
                argv,
                cwd=str(self._sandbox),
                capture_output=True,
                timeout=self._bash_timeout,
                text=True,
                env=self._build_env(),
            )
        except subprocess.TimeoutExpired:
            return f"[timeout after {self._bash_timeout}s]"
        except Exception as e:
            return f"[exec error] {type(e).__name__}: {e}"

        out = self._truncate(result.stdout, 8192)
        err = self._truncate(result.stderr, 2048)
        parts = []
        if out:
            parts.append(out)
        if err:
            parts.append(f"[stderr]\n{err}")
        if result.returncode != 0:
            parts.append(f"[exit {result.returncode}]")
        return "\n".join(parts) if parts else "[no output]"

    @staticmethod
    def _truncate(s: str, limit: int) -> str:
        if len(s) <= limit:
            return s
        return s[:limit] + f"\n[...truncated {len(s) - limit} bytes]"

    # ----- tool-call extraction --------------------------------------------

    def _trace_size(self) -> int:
        try:
            return self._trace_file.stat().st_size
        except OSError:
            return 0

    def _new_calls_since(self, byte_offset: int) -> List[ToolCall]:
        """Read scenario-tool calls appended to the trace since a byte offset.

        The model only ever calls `bash`; the calls the evaluator scores are the
        scenario tools invoked by the Python it runs, which `tools.py` logs.
        """
        if not self._trace_file.exists():
            return []
        with open(self._trace_file, "rb") as f:
            f.seek(byte_offset)
            tail = f.read().decode("utf-8", errors="replace")
        calls: List[ToolCall] = []
        for line in tail.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                calls.append(ToolCall(
                    function=rec["function"],
                    arguments=rec.get("arguments", {}),
                    call_id=rec.get("call_id", ""),
                ))
            except (json.JSONDecodeError, KeyError):
                continue
        return calls

    # ----- model interaction -----------------------------------------------

    async def _call_model(self) -> Any:
        """Make an API call to the model.

        Mirrors `LitellmAgentWrapper._call_model` so the bash and JSON-FC
        paradigms see identical model behaviour (same provider routing, same
        parallel_tool_calls, same per-model knobs from the registry).
        """
        extra_params = {}
        if self._model.max_tokens is not None:
            extra_params["max_tokens"] = self._model.max_tokens
        if self._model.reasoning_effort:
            extra_params["reasoning_effort"] = self._model.reasoning_effort
        if self._model.extra_body:
            extra_params["extra_body"] = self._model.extra_body

        return await acompletion(
            model=self._model.model_id,
            api_key=self._model.api_key,
            base_url=self._model.base_url,
            custom_llm_provider=self._model.provider,
            tools=[_BASH_TOOL_SCHEMA],
            parallel_tool_calls=True,
            tool_choice="auto",
            messages=self._messages,
            temperature=self._model.temperature,
            **extra_params
        )

    @staticmethod
    def _extract_token_usage(response: Any) -> TokenUsage:
        usage = getattr(response, "usage", None)
        if not usage:
            return TokenUsage()
        return TokenUsage(
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
        )

    def _run_bash_tool_call(self, tool_call: Any) -> str:
        """Execute one `bash` tool call from the model, returning its output."""
        if tool_call.function.name != "bash":
            return f"[error] unknown tool '{tool_call.function.name}'"
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse arguments: {tool_call.function.arguments}")
            arguments = {}
        command = (arguments.get("command") or "").strip()
        if not command:
            return "[error] empty command"
        return self._execute_bash(command)

    # ----- main loop --------------------------------------------------------

    async def run(self, query: str) -> AgentResponse:
        """Run the agent with a query, looping until it answers without a tool call."""
        self._messages.append({"role": "user", "content": query})

        token_usage = TokenUsage()
        steps = 0
        trace_offset = self._trace_size()
        started = time.monotonic()

        def respond(content: str, stop_reason: str) -> AgentResponse:
            return AgentResponse(
                content=content,
                tool_calls=self._new_calls_since(trace_offset),
                steps=steps,
                code_snippets=list(self._executed_commands),
                token_usage=token_usage,
                elapsed=time.monotonic() - started,
                stop_reason=stop_reason,
            )

        while steps < self._max_steps:
            steps += 1

            try:
                response = await self._call_model()
            except Exception as e:
                logger.error(f"BashAgent model call failed: {e}")
                return respond(f"Error: {e}", "model_error")

            token_usage = token_usage + self._extract_token_usage(response)
            choice = response.choices[0]
            assistant_message = choice.message

            if choice.finish_reason == "tool_calls" and assistant_message.tool_calls:
                self._messages.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                for tool_call in assistant_message.tool_calls:
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": self._run_bash_tool_call(tool_call),
                    })

                continue

            # Model returned a final response (no tool calls)
            content = assistant_message.content or ""
            self._messages.append({"role": "assistant", "content": content})
            return respond(content, "completed")

        logger.warning(f"Max steps ({self._max_steps}) reached")
        return respond("Max steps reached without final response", "max_steps")


class BashAgentFactory(AgentFactory):
    """Factory for the bash + filesystem agent paradigm."""

    def __init__(self, model: LitellmModel, max_steps: int = 20, bash_timeout: int = 30):
        """Initialize the factory with a model configuration.

        Args:
            model: The LiteLLM model configuration
            max_steps: Maximum steps per agent run (default: 20)
            bash_timeout: Per-command timeout in seconds (default: 30)
        """
        self.model = model
        self.max_steps = max_steps
        self.bash_timeout = bash_timeout
        # Build the venv and check isolation now, so a broken setup fails before
        # the first conversation rather than partway through a sweep.
        _ensure_uv_venv()
        _isolation_enabled()

    def create_agent(
        self,
        functions: List[Callable],
        variables: Optional[List[Any]] = None,
        types: Optional[List[Any]] = None,
        description: Optional[str] = None,
    ) -> BashAgentWrapper:
        """Create a bash agent with the specified functions.

        `variables` and `types` are ignored by design: the point of this
        baseline is "no runtime injection" — whatever the agent wants to keep
        across turns, it has to write to the filesystem.
        """
        return BashAgentWrapper(
            model=self.model,
            functions=functions,
            max_steps=self.max_steps,
            description=description,
            bash_timeout=self.bash_timeout,
        )
