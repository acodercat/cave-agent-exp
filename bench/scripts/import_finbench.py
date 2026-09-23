"""Import FinBench cases and runtime tables, keeping programmatic verification only.

    uv run python -m scripts.import_finbench \
        --source <path-to-FinBench> --commit 1c924e5

Cases are read from the given FinBench commit, never from its working tree, so
an import is reproducible from the commit id alone. A case is admitted when it
is a baseline (traps are diagnostics) and not easy (an easy case measures little
about an architecture). The selection rule reads only case metadata, never a
model result. Admitted case files are copied with the fields that exist only for
LLM judging removed: ``judge_reference`` and every turn's ``claims``. Validator
modules are copied unchanged.

The governed runtime tables are copied from FinBench's installed data release,
which is outside Git, as a whole layer: every ``runtime`` file the catalog
registers is checked against the catalog's size and SHA-256, and the catalog is
copied beside them. Copying the whole layer rather than the tables admitted
cases happen to name keeps every loader in ``core.runtime_catalog`` resolvable.

Re-running replaces ``evals/`` and the imported entries of ``benchmarks.json`` and
the case taxonomy, and recopies only the tables whose bytes differ. Cases written
here live under ``cases/``; their registry and taxonomy entries are kept as is.
The source commit, data release and exclusions are written to
``metadata/finbench_import.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from config import BENCHMARKS_JSON, CASE_TAXONOMY_PATH, DATASETS_DIR, EVALS_DIR, PROJECT_ROOT
from core.results import atomic_write_json, utc_now


IMPORT_RECORD = PROJECT_ROOT / "metadata" / "finbench_import.json"
SELECTION_RULE = "case_type == 'baseline' and difficulty != 'easy'"


def _git(source: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(source), *args], check=True, capture_output=True,
    ).stdout


def _read_json(source: Path, commit: str, path: str) -> Any:
    return json.loads(_git(source, "show", f"{commit}:{path}"))


def exclusion_reason(spec: dict[str, Any]) -> str | None:
    """Why a case is not admitted, or None when it is."""
    if spec.get("case_type") != "baseline":
        return f"case_type={spec.get('case_type')}"
    if spec.get("difficulty") == "easy":
        return "difficulty=easy"
    return None


def strip_judging_fields(spec: dict[str, Any]) -> dict[str, Any]:
    """The case without the fields only LLM judges read."""
    stripped = {
        key: value for key, value in spec.items() if key not in {"judge_reference", "claims"}
    }
    if "conversations" in stripped:
        stripped["conversations"] = [
            {**conversation, "turns": [
                {key: value for key, value in turn.items() if key != "claims"}
                for turn in conversation["turns"]
            ]}
            for conversation in stripped["conversations"]
        ]
    return stripped


def _local_entries(registry_path: Path, section: str) -> dict[str, str]:
    """Registry entries for cases written here, which an import must not touch."""
    if not registry_path.exists():
        return {}
    entries = json.loads(registry_path.read_text())[section]
    return {case_id: path for case_id, path in entries.items() if not path.startswith("evals/")}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_cases(source: Path, commit: str) -> tuple[list[str], dict[str, str]]:
    registry = _read_json(source, commit, "benchmarks.json")
    taxonomy = _read_json(source, commit, "metadata/case_taxonomy.json")
    admitted: dict[str, str] = {}
    excluded: dict[str, str] = {}
    cases: dict[str, tuple[dict[str, Any], bytes]] = {}
    for case_id, relative in sorted(registry["cases"].items()):
        spec = _read_json(source, commit, relative)
        reason = exclusion_reason(spec)
        if reason:
            excluded[case_id] = reason
            continue
        module = _git(source, "show", f"{commit}:{Path(relative).with_suffix('.py')}")
        cases[case_id] = (strip_judging_fields(spec), module)
        admitted[case_id] = relative

    if EVALS_DIR.exists():
        shutil.rmtree(EVALS_DIR)
    families = sorted({spec["task_family"] for spec, _ in cases.values()})
    for package in ["evals", *(f"evals/{family}" for family in families)]:
        (PROJECT_ROOT / package).mkdir(parents=True)
        (PROJECT_ROOT / package / "__init__.py").write_bytes(
            _git(source, "show", f"{commit}:{package}/__init__.py")
        )
    for case_id, (spec, module) in cases.items():
        family_dir = EVALS_DIR / spec["task_family"]
        (family_dir / f"{case_id}.json").write_text(
            json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
        (family_dir / f"{case_id}.py").write_bytes(module)

    local_cases = _local_entries(BENCHMARKS_JSON, "cases")
    local_taxonomy = (
        json.loads(CASE_TAXONOMY_PATH.read_text()) if CASE_TAXONOMY_PATH.exists() else {}
    )
    atomic_write_json(BENCHMARKS_JSON, {"schema_version": 2, "cases": admitted | local_cases})
    atomic_write_json(CASE_TAXONOMY_PATH, {
        "schema_version": taxonomy["schema_version"],
        "task_families": {
            family: definition
            for family, definition in local_taxonomy.get("task_families", {}).items()
            if family not in taxonomy["task_families"]
        } | {family: taxonomy["task_families"][family] for family in families},
        "financial_domains": taxonomy["financial_domains"],
        "cases": {case_id: taxonomy["cases"][case_id] for case_id in admitted} | {
            case_id: local_taxonomy["cases"][case_id] for case_id in local_cases
        },
    })
    return sorted(admitted), excluded


def import_runtime_tables(source: Path) -> dict[str, Any]:
    source_dir = source / "datasets" / "dataset_new"
    catalog = json.loads((source_dir / "catalog.json").read_text(encoding="utf-8"))
    copied = 0
    for table_id, table in sorted(catalog["tables"].items()):
        runtime = table["layers"]["runtime"]
        origin = source_dir / runtime["path"]
        if origin.stat().st_size != runtime["bytes"] or _sha256(origin) != runtime["sha256"]:
            raise ValueError(f"{table_id}: {origin} does not match the FinBench catalog")
        destination = DATASETS_DIR / runtime["path"]
        if destination.is_file() and _sha256(destination) == runtime["sha256"]:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin, destination)
        copied += 1
    shutil.copyfile(source_dir / "catalog.json", DATASETS_DIR / "catalog.json")
    return {
        "dataset_release": catalog["dataset_release"],
        "catalog_sha256": _sha256(source_dir / "catalog.json"),
        "tables": len(catalog["tables"]),
        "tables_copied": copied,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True, help="FinBench git root")
    parser.add_argument("--commit", required=True, help="FinBench commit to read cases from")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    commit = _git(source, "rev-parse", "--verify", f"{args.commit}^{{commit}}").decode().strip()
    admitted, excluded = import_cases(source, commit)
    data = import_runtime_tables(source)
    atomic_write_json(IMPORT_RECORD, {
        "imported_at": utc_now(),
        "source_commit": commit,
        "selection_rule": SELECTION_RULE,
        "admitted_cases": len(admitted),
        "excluded_cases": excluded,
        **data,
    })
    print(f"{len(admitted)} cases admitted, {len(excluded)} excluded: {excluded}")
    print(f"{data['tables']} runtime tables ({data['tables_copied']} copied) "
          f"from release {data['dataset_release']}")


if __name__ == "__main__":
    main()
