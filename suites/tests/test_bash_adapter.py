"""Tests for the bash + filesystem adapter (paper Q3's third paradigm).

Local and deterministic: the venv builder and the model call are both stubbed,
so nothing here creates a venv or reaches the network. What is exercised for
real is the sandbox: commands run through `bash`, and the scenario-tool calls
the evaluator scores are read back from the trace file that `tools.py` writes.
"""

import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters import bash_adapter
from adapters.bash_adapter import (
    BashAgentFactory,
    BashAgentWrapper,
    _check_deny_list,
    _generate_tools_py,
    _signatures_block,
)


def sample_tool(city: str, days: int = 3) -> dict:
    """Get a weather forecast.

    Args:
        city: City name
        days: How many days ahead
    """
    return {"city": city, "days": days}


@pytest.fixture
def sandboxed(tmp_path, monkeypatch):
    """Point the adapter's venv and sandbox root at tmp_path.

    Isolation is switched off here: these tests exercise the adapter's own
    behaviour, and bwrap is unavailable inside some CI/dev sandboxes. The
    bwrap layer is covered by TestIsolation.
    """
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    monkeypatch.setattr(bash_adapter, "_ensure_uv_venv", lambda: venv)
    monkeypatch.setattr(bash_adapter, "_SANDBOX_ROOT", tmp_path / "sandboxes")
    monkeypatch.setattr(bash_adapter, "_isolation_enabled", lambda: False)
    return venv


def make_agent(**kwargs) -> BashAgentWrapper:
    model = SimpleNamespace(
        model_id="test-model", api_key="k", base_url=None, provider="openai",
        temperature=0.0, max_tokens=None, reasoning_effort=None, extra_body=None,
    )
    return BashAgentWrapper(model=model, functions=[sample_tool], **kwargs)


def tool_call(command: str, call_id: str = "c1") -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name="bash", arguments=json.dumps({"command": command})),
    )


def model_response(*, finish_reason: str, content: str = "", tool_calls=None) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason=finish_reason,
            message=SimpleNamespace(content=content, tool_calls=tool_calls),
        )],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def replies(monkeypatch, agent, responses):
    """Make the agent's model return `responses` in order."""
    queue = list(responses)

    async def fake_call():
        return queue.pop(0)

    monkeypatch.setattr(agent, "_call_model", fake_call)


class TestVenvBuild:
    """The venv is reused only when its stamp matches the current dependencies."""

    @pytest.fixture
    def venv(self, tmp_path, monkeypatch):
        root = tmp_path / ".bash_venv"
        monkeypatch.setattr(bash_adapter, "_UV_VENV_DIR", root)
        monkeypatch.setattr(bash_adapter, "_VENV_STAMP", root / "cave-bench-deps.json")
        monkeypatch.setattr(bash_adapter, "_PROJECT_ROOT", tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["pandas>=2.2.3"]\n')

        commands = []

        def fake_run_uv(command):
            commands.append(command[1])          # "venv" or "pip"
            (root / "bin").mkdir(parents=True, exist_ok=True)
            (root / "bin" / "python").touch()

        monkeypatch.setattr(bash_adapter, "_run_uv", fake_run_uv)
        return root, commands

    def test_builds_once_then_reuses(self, venv):
        root, commands = venv
        bash_adapter._ensure_uv_venv()
        bash_adapter._ensure_uv_venv()
        assert commands == ["venv", "pip"]

    def test_failed_install_is_not_treated_as_ready(self, venv, monkeypatch):
        """An interpreter without packages must not pass for a usable venv."""
        root, commands = venv

        def install_fails_once(command):
            commands.append(command[1])
            (root / "bin").mkdir(parents=True, exist_ok=True)
            (root / "bin" / "python").touch()
            if command[1] == "pip" and commands.count("pip") == 1:
                raise RuntimeError("uv pip install failed (exit 1)")

        monkeypatch.setattr(bash_adapter, "_run_uv", install_fails_once)

        with pytest.raises(RuntimeError):
            bash_adapter._ensure_uv_venv()
        assert not bash_adapter._VENV_STAMP.exists()  # bin/python alone is not enough

        bash_adapter._ensure_uv_venv()                # a later run retries the install
        assert commands.count("pip") == 2
        assert bash_adapter._VENV_STAMP.exists()

    def test_changed_dependencies_rebuild(self, venv, tmp_path):
        root, commands = venv
        bash_adapter._ensure_uv_venv()
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["pandas>=2.2.3", "numpy>=2.0"]\n')
        bash_adapter._ensure_uv_venv()
        assert commands == ["venv", "pip", "pip"]    # venv kept, packages reinstalled


class TestIsolation:
    """Commands are wrapped in bwrap, and a machine that cannot isolate fails loudly."""

    def test_argv_unshares_everything_and_writes_only_the_sandbox(self, tmp_path):
        argv = bash_adapter._isolation_argv(tmp_path / "conv_1", tmp_path / "venv")

        assert Path(argv[0]).name == "bwrap"      # resolved to wherever it is installed
        assert "--unshare-all" in argv                       # includes the network namespace
        assert "--die-with-parent" in argv
        writable = [argv[i + 2] for i, a in enumerate(argv) if a == "--bind"]
        assert writable == [str(tmp_path / "conv_1")]

    def test_project_is_mounted_only_where_tools_py_needs_it(self, tmp_path):
        """The model must not be able to read models.toml, which holds API keys."""
        argv = bash_adapter._isolation_argv(tmp_path / "conv_1", tmp_path / "venv")
        mounted = {argv[i + 1] for i, a in enumerate(argv) if a in ("--ro-bind", "--bind")}

        assert str(bash_adapter._PROJECT_ROOT / "evals") in mounted
        assert str(bash_adapter._PROJECT_ROOT / "core") in mounted
        assert str(bash_adapter._PROJECT_ROOT) not in mounted

    def test_interpreter_tree_is_mounted(self, tmp_path):
        """A venv's `python` is a symlink; without its target tree there is no python."""
        interpreter = tmp_path / "pythons" / "cpython-3.12.13" / "bin" / "python3.12"
        interpreter.parent.mkdir(parents=True)
        interpreter.touch()
        (tmp_path / "pythons" / "cpython-3.12").symlink_to(interpreter.parent.parent)
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        # through the version alias, as uv writes it
        (venv / "bin" / "python").symlink_to(
            tmp_path / "pythons" / "cpython-3.12" / "bin" / "python3.12")

        argv = bash_adapter._isolation_argv(tmp_path / "conv_1", venv)
        mounted = {argv[i + 1] for i, a in enumerate(argv) if a == "--ro-bind"}

        # the directory holding both the alias and the resolved install
        assert str(tmp_path / "pythons") in mounted

    def test_system_interpreter_needs_no_extra_mount(self, tmp_path):
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "bin" / "python").symlink_to("/usr/bin/python3")
        assert bash_adapter._interpreter_root(venv) is None

    def test_command_runs_under_bwrap(self, tmp_path, monkeypatch):
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        monkeypatch.setattr(bash_adapter, "_ensure_uv_venv", lambda: venv)
        monkeypatch.setattr(bash_adapter, "_SANDBOX_ROOT", tmp_path / "sandboxes")
        monkeypatch.setattr(bash_adapter, "_isolation_enabled", lambda: True)
        agent = make_agent()

        seen = {}

        def fake_run(argv, **kwargs):
            seen["argv"] = argv
            return SimpleNamespace(stdout="", stderr="", returncode=0)

        monkeypatch.setattr(bash_adapter.subprocess, "run", fake_run)
        agent._execute_bash("ls")

        assert Path(seen["argv"][0]).name == "bwrap"
        assert seen["argv"][-3:] == ["bash", "-c", "ls"]

    def test_missing_bubblewrap_is_an_error(self, monkeypatch):
        monkeypatch.delenv(bash_adapter._NO_SANDBOX_ENV, raising=False)
        monkeypatch.setattr(bash_adapter, "_isolation_error", lambda: "bubblewrap is not installed")

        with pytest.raises(RuntimeError, match="bubblewrap"):
            bash_adapter._isolation_enabled()

    def test_isolation_can_be_waived_explicitly(self, monkeypatch):
        monkeypatch.setenv(bash_adapter._NO_SANDBOX_ENV, "1")
        assert bash_adapter._isolation_enabled() is False


class TestDenyList:
    """Only what isolation cannot express: fixed packages, and fork bombs."""

    @pytest.mark.parametrize("command", [
        "pip install requests",
        "pip3 install requests",
        "uv pip install pandas",
        "uv add pandas",
        "apt-get install jq",
        "npm install lodash",
        ":(){ :|:& };:",
    ])
    def test_forbidden(self, command):
        assert _check_deny_list(command) is not None

    @pytest.mark.parametrize("command", [
        "python -c 'import tools; print(tools.sample_tool(\"Paris\"))'",
        "cat summary.json",
        "ls -la",
        "echo hi > note.txt",
        # all of these the sandbox itself answers for; blocking them only cost
        # the baseline a turn
        "python -c 'import json' 2>/dev/null",
        "ls ~/.ssh",
        "curl https://example.com",
        "sudo rm -f /etc/hosts",
        "rm -rf /usr",
        "shutdown now",
        "chown me file.txt",
    ])
    def test_allowed(self, command):
        assert _check_deny_list(command) is None

    def test_blocked_command_is_not_executed(self, sandboxed):
        agent = make_agent()
        result = agent._execute_bash("pip install requests")
        assert result.startswith("[blocked]")


class TestSandbox:
    def test_command_runs_in_the_sandbox(self, sandboxed):
        agent = make_agent()
        assert agent._execute_bash("pwd").strip() == str(agent._sandbox)

    def test_files_persist_across_commands(self, sandboxed):
        agent = make_agent()
        agent._execute_bash("echo saved > state.txt")
        assert "saved" in agent._execute_bash("cat state.txt")

    def test_failure_reports_stderr_and_exit_code(self, sandboxed):
        agent = make_agent()
        result = agent._execute_bash("ls /definitely/not/here")
        assert "[stderr]" in result and "[exit " in result

    def test_timeout_is_reported(self, sandboxed):
        agent = make_agent(bash_timeout=1)
        assert agent._execute_bash("sleep 5").startswith("[timeout")

    def test_long_output_is_truncated(self, sandboxed):
        agent = make_agent()
        result = agent._execute_bash("python3 -c \"print('x' * 20000)\"")
        assert "[...truncated" in result

    def test_each_agent_gets_its_own_sandbox(self, sandboxed):
        first, second = make_agent(), make_agent()
        assert first._sandbox != second._sandbox


class TestToolsModule:
    def test_generated_module_wraps_scenario_tools(self):
        source = _generate_tools_py([sample_tool])
        assert "from tests.test_bash_adapter import sample_tool as _orig_sample_tool" in source
        assert 'sample_tool = _make("sample_tool")' in source

    def test_non_functions_are_skipped(self):
        assert "_orig_" not in _generate_tools_py([dict])

    def test_signatures_block_includes_docstring(self):
        block = _signatures_block([sample_tool])
        assert "### sample_tool(city: str, days: int = 3) -> dict" in block
        assert "Get a weather forecast." in block

    def test_signatures_block_without_tools(self):
        assert _signatures_block([]) == "  (no scenario tools)"

    def test_tool_calls_are_recovered_from_the_trace(self, sandboxed):
        """The model only calls `bash`; the evaluator scores the tools that ran.

        The tool lives in a module written into the sandbox (which is on the
        sandbox PYTHONPATH), so the subprocess needs nothing but the stdlib.
        """
        agent = make_agent()
        (agent._sandbox / "local_tools.py").write_text(
            "def forecast(city: str, days: int = 3) -> dict:\n"
            "    return {'city': city, 'days': days}\n"
        )
        spec = importlib.util.spec_from_file_location(
            "local_tools", agent._sandbox / "local_tools.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        (agent._sandbox / "tools.py").write_text(_generate_tools_py([module.forecast]))

        offset = agent._trace_size()
        output = agent._execute_bash(
            "python3 -c \"import tools; tools.forecast('Paris', days=5)\""
        )

        assert "Traceback" not in output
        calls = agent._new_calls_since(offset)
        assert [(c.function, c.arguments) for c in calls] == [
            ("forecast", {"city": "Paris", "days": 5})
        ]


class TestRunLoop:
    def test_answer_without_a_tool_call(self, sandboxed, monkeypatch):
        agent = make_agent()
        replies(monkeypatch, agent, [model_response(finish_reason="stop", content="42")])

        response = asyncio.run(agent.run("What is the answer?"))

        assert response.content == "42"
        assert response.stop_reason == "completed"
        assert response.steps == 1
        assert response.token_usage.total_tokens == 15
        assert response.elapsed > 0

    def test_bash_call_then_answer(self, sandboxed, monkeypatch):
        agent = make_agent()
        replies(monkeypatch, agent, [
            model_response(finish_reason="tool_calls",
                           tool_calls=[tool_call("echo 7 > seven.txt")]),
            model_response(finish_reason="stop", content="wrote it"),
        ])

        response = asyncio.run(agent.run("Save seven."))

        assert response.content == "wrote it"
        assert response.steps == 2
        assert response.code_snippets == ["echo 7 > seven.txt"]
        assert response.token_usage.total_tokens == 30      # accumulated over both calls
        assert (agent._sandbox / "seven.txt").exists()
        assert [m["role"] for m in agent.messages] == [
            "system", "user", "assistant", "tool", "assistant"
        ]

    def test_max_steps_stops_the_loop(self, sandboxed, monkeypatch):
        agent = make_agent(max_steps=2)
        replies(monkeypatch, agent, [
            model_response(finish_reason="tool_calls", tool_calls=[tool_call("echo a")]),
            model_response(finish_reason="tool_calls", tool_calls=[tool_call("echo b")]),
        ])

        response = asyncio.run(agent.run("Loop forever."))

        assert response.stop_reason == "max_steps"
        assert response.steps == 2

    def test_model_failure_is_reported_not_raised(self, sandboxed, monkeypatch):
        agent = make_agent()

        async def boom():
            raise RuntimeError("api down")

        monkeypatch.setattr(agent, "_call_model", boom)
        response = asyncio.run(agent.run("Anything."))

        assert response.stop_reason == "model_error"
        assert "api down" in response.content

    def test_unknown_tool_and_empty_command_are_rejected(self, sandboxed, monkeypatch):
        agent = make_agent()
        unknown = SimpleNamespace(
            id="c1", function=SimpleNamespace(name="python", arguments="{}"))
        empty = SimpleNamespace(
            id="c2", function=SimpleNamespace(name="bash", arguments=json.dumps({"command": "  "})))
        replies(monkeypatch, agent, [
            model_response(finish_reason="tool_calls", tool_calls=[unknown, empty]),
            model_response(finish_reason="stop", content="done"),
        ])

        asyncio.run(agent.run("Try bad calls."))

        tool_messages = [m["content"] for m in agent.messages if m["role"] == "tool"]
        assert tool_messages == ["[error] unknown tool 'python'", "[error] empty command"]


class TestFactory:
    def test_creates_agents_and_ignores_runtime_state(self, sandboxed):
        """variables/types are ignored by design — this baseline has no runtime."""
        factory = BashAgentFactory(model=SimpleNamespace(
            model_id="m", api_key="k", base_url=None, provider="openai",
            temperature=0.0, max_tokens=None, reasoning_effort=None, extra_body=None,
        ))
        agent = factory.create_agent(
            functions=[sample_tool], variables=["ignored"], types=["ignored"],
            description="Do the thing.",
        )
        assert isinstance(agent, BashAgentWrapper)
        assert agent.runtime is None
        assert "Do the thing." in agent.messages[0]["content"]
