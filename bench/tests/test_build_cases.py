"""The generated families' case files and registry entries are those their tasks write."""

from scripts.build_cases import build


def test_the_written_case_files_match_their_tasks():
    assert build(check=True) == []
