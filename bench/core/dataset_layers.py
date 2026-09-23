"""Read the governed runtime tables.

Each table is a gzipped CSV under ``datasets/dataset_new/<source>/runtime/``,
registered in ``catalog.json`` with its path and a storage type per column. The
tables are built upstream in FinBench and imported here by
``scripts.import_finbench``; this module only reads them back with the dtypes the
catalog records, so an identifier with leading zeros stays a string and an
integer column with gaps stays an integer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from config import DATASETS_DIR


CATALOG_PATH = DATASETS_DIR / "catalog.json"

_PANDAS_DTYPES = {
    "string": "string",
    "category": "category",
    "integer": "Int64",
    "number": "Float64",
    "boolean": "boolean",
}


def load_catalog(catalog_path: Path = CATALOG_PATH) -> dict[str, Any]:
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def catalog_digest(catalog_path: Path = CATALOG_PATH) -> str:
    """The identity of the imported data release.

    The catalog records every runtime table's checksum, so its digest changes
    whenever any table does: anything derived from the tables can be keyed on
    it and cannot outlive the data it was derived from.
    """
    return hashlib.sha256(catalog_path.read_bytes()).hexdigest()


def load_runtime_table(
    table_id: str, *, datasets_dir: Path = DATASETS_DIR,
    catalog_path: Path | None = None,
) -> pd.DataFrame:
    """Load one governed runtime table using its recorded storage contract."""
    catalog = load_catalog(catalog_path or datasets_dir / "catalog.json")
    try:
        metadata = catalog["tables"][table_id]
    except KeyError as error:
        raise KeyError(f"unknown governed runtime table: {table_id}") from error
    dtype_map = {
        column["name"]: _PANDAS_DTYPES[column["storage_type"]]
        for column in metadata["columns"]
    }
    return pd.read_csv(
        datasets_dir / metadata["layers"]["runtime"]["path"],
        dtype=dtype_map, keep_default_na=False, na_values=[""], low_memory=False,
    )
