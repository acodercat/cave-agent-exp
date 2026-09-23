"""Identify the answer key a verdict was reached against.

A stored verdict is only as current as the code and data that produced it. A
case module can be three lines that hand over to a task defined elsewhere, and
its answer key is computed by data loaders over the imported tables, so the
fingerprint follows the module's imports through every project source it runs
and adds the data release. Programmatic verification scores a run again when
the fingerprint it recorded differs; a comparison refuses to read such a verdict.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path

from config import PROJECT_ROOT
from core.dataset_layers import CATALOG_PATH, catalog_digest


VENV_DIR = PROJECT_ROOT / ".venv"


def local_sources(module) -> list[Path]:
    """The project source files a module runs, following its imports.

    Imports are read from the source rather than from ``sys.modules``, which
    also holds whatever the caller itself imported.
    """
    sources: dict[str, Path] = {}
    pending = [module.__name__]
    while pending:
        name = pending.pop()
        if name in sources:
            continue
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            continue
        origin = Path(spec.origin) if spec and spec.origin else None
        if (origin is None or not origin.is_file() or not origin.is_relative_to(PROJECT_ROOT)
                or VENV_DIR in origin.parents):
            continue
        sources[name] = origin
        for node in ast.walk(ast.parse(origin.read_text())):
            if isinstance(node, ast.Import):
                pending.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                # ``from package import name`` may import a submodule.
                pending.append(node.module)
                pending.extend(f"{node.module}.{alias.name}" for alias in node.names)
    return sorted(sources.values())


def answer_key_fingerprint(module) -> str:
    """A digest of every project source the case module runs, and of the data release."""
    digest = hashlib.sha256()
    for path in local_sources(module):
        digest.update(str(path.relative_to(PROJECT_ROOT)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    if CATALOG_PATH.is_file():
        digest.update(catalog_digest().encode())
    return digest.hexdigest()[:20]
