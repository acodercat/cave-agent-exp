"""Parquet copies of the runtime tables, for paradigms that read data from files.

Parquet keeps what the catalog's storage contract promises — identifiers stay
strings with their leading zeros, integer columns with gaps stay integers — so a
paradigm that loads a file starts from the same table an injected DataFrame
holds. Each copy is written once, on first use, beside the runtime tables, in a
directory named for the data release it was written from: a re-import that
changes any table starts a fresh set of copies instead of serving stale ones.
"""

from __future__ import annotations

from pathlib import Path
import tempfile

from config import DATASETS_DIR
from core.dataset_layers import catalog_digest
from core.runtime_catalog import RuntimeTable


TABLE_FILES_DIR = DATASETS_DIR.parent / "table_files"


def table_file_name(table_name: str) -> str:
    """The name of a table's file: its runtime name, so code that reads it names it."""
    return f"{table_name}.parquet"


def table_file(table: RuntimeTable) -> Path:
    """The table's Parquet copy for the current data release, written on first use."""
    directory = TABLE_FILES_DIR / catalog_digest()[:16]
    path = directory / table_file_name(table.name)
    if not path.is_file():
        directory.mkdir(parents=True, exist_ok=True)
        # Written under a temporary name and renamed, so a concurrent case never
        # reads a half-written file.
        with tempfile.NamedTemporaryFile(
            dir=directory, suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            table.loader().to_parquet(temporary_path, index=False)
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)
    return path
