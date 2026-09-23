"""Write the cases of every generated family from its tasks.

A generated family defines each task once (``cases/<family>/_<task>.py``), and the
task says what each of its cases is (:class:`core.written_cases.WrittenCase`).
This script writes each case's JSON spec and module and registers it, and is the
only writer of those files. ``--check`` writes nothing and fails if any is stale.

    uv run python -m scripts.build_cases
"""

from __future__ import annotations

import argparse
import json
from importlib import import_module
from pathlib import Path
import sys

from cases import GENERATED_FAMILIES
from config import BENCHMARKS_JSON, CASE_TAXONOMY_PATH, CASES_DIR, PROJECT_ROOT
from core.written_cases import WrittenCase


def written_cases(family: str) -> list[WrittenCase]:
    tasks = import_module(f"cases.{family}").tasks()
    return [case for task in tasks for case in task.written_cases()]


def _json(document: dict) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _case_files(family: str, cases: list[WrittenCase]) -> dict[Path, str]:
    directory = CASES_DIR / family
    return {
        path: text
        for case in cases
        for path, text in (
            (directory / f"{case.name}.json", _json(case.spec)),
            (directory / f"{case.name}.py", case.module),
        )
    }


def _registries(cases_by_family: dict[str, list[WrittenCase]]) -> dict[Path, str]:
    """Both registries with the generated families' entries replaced and the rest kept."""
    prefixes = tuple(f"{CASES_DIR.name}/{family}/" for family in cases_by_family)
    written = {
        case.name: (f"{CASES_DIR.name}/{family}/{case.name}.json", case.financial_domain)
        for family, cases in cases_by_family.items() for case in cases
    }
    registry = json.loads(BENCHMARKS_JSON.read_text())
    replaced = {name for name, path in registry["cases"].items() if path.startswith(prefixes)}
    registry["cases"] = {
        name: path for name, path in registry["cases"].items() if name not in replaced
    } | {name: path for name, (path, _) in written.items()}
    taxonomy = json.loads(CASE_TAXONOMY_PATH.read_text())
    taxonomy["cases"] = {
        name: entry for name, entry in taxonomy["cases"].items() if name not in replaced
    } | {name: {"financial_domains": [domain]} for name, (_, domain) in written.items()}
    return {BENCHMARKS_JSON: _json(registry), CASE_TAXONOMY_PATH: _json(taxonomy)}


def build(*, check: bool) -> list[Path]:
    """Bring the written files in line with the tasks; return the ones that differed."""
    cases_by_family = {family: written_cases(family) for family in GENERATED_FAMILIES}
    wanted: dict[Path, str] = {}
    present: set[Path] = set()
    for family, cases in cases_by_family.items():
        wanted |= _case_files(family, cases)
        present |= {
            path for path in (CASES_DIR / family).iterdir()
            if path.suffix in {".json", ".py"} and not path.name.startswith("_")
        }
    orphans = sorted(present - wanted.keys())
    wanted |= _registries(cases_by_family)
    stale = [path for path, text in wanted.items()
             if not path.exists() or path.read_text() != text]
    if not check:
        for path in stale:
            path.write_text(wanted[path])
        for path in orphans:
            path.unlink()
    return stale + orphans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="write nothing; fail if stale")
    args = parser.parse_args()
    changed = build(check=args.check)
    for path in changed:
        print(("stale: " if args.check else "wrote: ") + str(path.relative_to(PROJECT_ROOT)))
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
