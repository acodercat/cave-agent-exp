"""Tests for keeping API keys out of result files."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from redact import redact_api_key, result_files

KEY = "sk-" + "x" * 40


def write(path: Path, api_key: str) -> Path:
    path.write_text(json.dumps({"info": {"agent_info": {"llm_args": {"api_key": api_key}}}}))
    return path


def test_a_key_is_replaced(tmp_path):
    path = write(tmp_path / "run.json", KEY)

    assert redact_api_key(path) == 1
    assert KEY not in path.read_text()
    assert "<redacted>" in path.read_text()


def test_an_already_redacted_file_is_left_alone(tmp_path):
    path = write(tmp_path / "run.json", "<redacted>")
    before = path.stat().st_mtime_ns

    assert redact_api_key(path) == 0
    assert path.stat().st_mtime_ns == before


def test_directories_are_searched_recursively(tmp_path):
    (tmp_path / "superseded").mkdir()
    write(tmp_path / "a.json", KEY)
    write(tmp_path / "superseded" / "b.json", KEY)

    assert {p.name for p in result_files([tmp_path])} == {"a.json", "b.json"}


def test_a_stopped_run_still_scrubs_its_file(tmp_path):
    """SIGTERM is what stopping a sweep sends; cleanup has to survive it.

    Python's default for SIGTERM skips `finally`, which is how killed runs used
    to leave a plaintext key on disk.
    """
    path = write(tmp_path / "run.json", KEY)
    project = Path(__file__).resolve().parents[1]
    script = (
        "import signal, sys, time\n"
        f"sys.path.insert(0, {str(project)!r})\n"
        "from pathlib import Path\n"
        "from run import _exit_on_sigterm\n"
        "from redact import redact_api_key\n"
        "signal.signal(signal.SIGTERM, _exit_on_sigterm)\n"
        "try:\n"
        "    print('ready', flush=True); time.sleep(60)\n"
        "finally:\n"
        f"    redact_api_key(Path({str(path)!r}))\n"
    )
    proc = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True,
                            env={k: v for k, v in os.environ.items()})
    assert proc.stdout.readline().strip() == "ready"
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=30)

    assert KEY not in path.read_text()
