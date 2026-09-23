from pathlib import Path

import pytest

from config import DATASETS_DIR


RUNTIME_TEST_FILES = {
    "test_cases.py",
    "test_dataset.py",
    "test_pipeline_cases.py",
    "test_rounds.py",
    "test_intermediate_rounding.py",
    "test_near_miss_probes.py",
    "test_orchestration.py",
    "test_table_control_cases.py",
    "test_table_delivery_cases.py",
}


def pytest_ignore_collect(collection_path, config):
    """Without the tables, do not import the test files that load them at import time."""
    if collection_path.name in RUNTIME_TEST_FILES and not (DATASETS_DIR / "catalog.json").is_file():
        return True
    return None


def pytest_collection_modifyitems(config, items):
    """Mark, and skip without the data, the tests that read the runtime tables.

    The tables are imported by ``scripts.import_finbench`` and are not in Git, so
    a code-only checkout still runs every test that does not need them.
    """
    runtime_materialized = (DATASETS_DIR / "catalog.json").is_file()
    for item in items:
        if Path(item.path).name not in RUNTIME_TEST_FILES:
            continue
        item.add_marker(pytest.mark.runtime_data)
        if not runtime_materialized:
            item.add_marker(pytest.mark.skip(
                reason="runtime tables are not imported; run scripts.import_finbench"
            ))
