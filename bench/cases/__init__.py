"""Cases written for this benchmark; ``evals`` holds the ones imported from FinBench.

A family whose cases are generated keeps each task in a ``_<task>.py`` module
that defines ``TASK``; ``scripts.build_cases`` writes the cases from them.
"""

from importlib import import_module
from pathlib import Path


GENERATED_FAMILIES = ("table_delivery", "table_control")


def tasks_in(family: str) -> tuple:
    """The ``TASK`` of every task module in a family, in name order."""
    package = import_module(f"{__name__}.{family}")
    names = sorted(path.stem for path in Path(package.__file__).parent.glob("_[a-z]*.py"))
    return tuple(import_module(f"{package.__name__}.{name}").TASK for name in names)
