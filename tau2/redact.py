"""Scrub API keys from result files.

    uv run python redact.py results/            # every result file under a directory
    uv run python redact.py results/<run>.json  # or named files

tau2 records llm_args in its result file, and an agent on a second gateway has
to carry its key there. run.py scrubs its own file when it ends, but a process
that is killed never gets that far, so sweep.sh also calls this before and after
every attempt — a key left by any earlier kill is gone before the next run.
"""

import re
import sys
from pathlib import Path

_API_KEY = re.compile(r'("api_key"\s*:\s*")(?!<redacted>)([^"]+)(")')


def redact_api_key(path: Path) -> int:
    """Replace any api_key in a result file; returns how many were replaced."""
    text, count = _API_KEY.subn(r"\1<redacted>\3", path.read_text())
    if count:
        path.write_text(text)
    return count


def result_files(targets: list[Path]) -> list[Path]:
    """The .json files named, or found under the directories named."""
    files = []
    for target in targets:
        files.extend(sorted(target.rglob("*.json")) if target.is_dir() else [target])
    return files


def main() -> int:
    targets = [Path(arg) for arg in sys.argv[1:]] or [Path("results")]
    scrubbed = sum(bool(redact_api_key(path)) for path in result_files(targets))
    if scrubbed:
        print(f"redacted api keys in {scrubbed} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
