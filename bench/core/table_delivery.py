"""A table-delivery task: one question asked at several sizes of answer.

The table-delivery family measures what it costs to get a table out of the
runtime. A task fixes the question, the columns and the arithmetic, and varies
the scope the question covers — a county, a state, several states — so the
delivered table grows from about ten rows to about ten thousand. Scope changes
can also change the population, missingness and time-series baseline: these are
end-to-end workload sizes, not a pure intervention on delivery length. Each
size is its own case; this module is what those cases share.

The same machinery writes the delivery-control family (``cases/table_control``),
where every size runs the same computation over the same rows and differs only
in how many of its rows the question asks for. There the delivered volume is an
intervention, at the cost of a less natural question. A task says which family
it belongs to, and what its sizes vary.

A task's columns carry a :class:`CellKind`, so a study can report where a
delivery channel loses cells by kind of cell — a zero-padded code, a long
decimal, a missing value — and not only by column name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cache
import textwrap
from typing import Any, Callable, Mapping

import pandas as pd
from cave_agent import Variable

from core.types import CaseMembers
from core.validation import as_records, turn_validator, validate_table
from core.written_cases import WrittenCase, case_spec, module_source, quoted, turn


FAMILY = "table_delivery"


class CellKind(Enum):
    IDENTIFIER = "identifier"                  # text compared exactly
    PADDED_IDENTIFIER = "padded_identifier"    # an identifier that may begin with zeros
    TEXT = "text"                              # a name or label, compared exactly
    DATE = "date"                              # ISO text, compared exactly
    INTEGER = "integer"                        # compared as a number, with no tolerance
    DECIMAL = "decimal"                        # compared to the column's decimals


@dataclass(frozen=True)
class Column:
    name: str
    kind: CellKind
    description: str
    decimals: int | None = None    # DECIMAL only
    nullable: bool = False         # some expected cells are missing

    def __post_init__(self):
        if (self.kind is CellKind.DECIMAL) != (self.decimals is not None):
            raise ValueError(f"{self.name}: decimals are given for DECIMAL columns only")


@dataclass(frozen=True)
class Size:
    label: str                    # "10", "100", "250", "500", "1k", then "10k" or "5k"
    scope: str                    # how the question names what it covers
    rows: int                     # the rows the answer holds, verified by test
    params: Mapping[str, Any] = field(default_factory=dict)


def changing(**changes: Callable[[Any], Any]) -> Callable[[list[dict]], list[dict]]:
    """A near miss that rewrites the named columns of every row.

    ``changing(share=lambda share: share * 100)`` is the answer with the share
    given as a percentage. A missing cell stays missing.
    """
    def change(rows: list[dict]) -> list[dict]:
        return [
            row | {name: rewrite(row[name]) for name, rewrite in changes.items()
                   if row[name] is not None}
            for row in rows
        ]
    return change


@dataclass(frozen=True)
class TableTask:
    """One table-delivery question and the sizes it is asked at.

    ``load`` reads the source tables; ``build`` turns them and one size's
    ``params`` into the expected table, with exactly ``columns``. They are
    separate so a test can load once and build every size.
    The validator must reject two sorts of plausible wrong answer: ``near_misses``
    rewrite the expected rows (a share given as a percentage), and
    ``misreadings`` are other builds of the same signature (a share taken of the
    wrong total), for errors that cannot be made from the delivered rows alone.
    """

    name: str
    title: str                    # "Flood claim payments", as a case's docstring opens
    data_sources: tuple[str, ...]
    financial_domain: str
    query: str                    # a template with one {scope} field
    output: str
    row_noun: str                 # "branch", as in "one row per branch"
    key: tuple[str, ...]
    columns: tuple[Column, ...]
    sizes: tuple[Size, ...]
    load: Callable[[], Any]
    build: Callable[..., pd.DataFrame]
    near_misses: Mapping[str, Callable[[list[dict]], list[dict]]] = field(default_factory=dict)
    misreadings: Mapping[str, Callable[..., pd.DataFrame]] = field(default_factory=dict)
    family: str = FAMILY
    # What a case module's docstring says its sizes vary, in one clause.
    sizes_vary: str = "the sizes differ in scope only"

    def size(self, label: str) -> Size:
        for size in self.sizes:
            if size.label == label:
                return size
        raise KeyError(f"{self.name} is not asked at size {label!r}")

    def case_name(self, size: Size) -> str:
        return f"{self.name}_{size.label}"

    @property
    def variable(self) -> Variable:
        columns = ", ".join(f"{column.name} ({column.description})" for column in self.columns)
        return Variable(
            self.output, None,
            f"Store a table with one row per {self.row_noun} and exactly these columns, "
            f"named as given: {columns}.",
        )

    def expected_rows(
        self, size: Size, source: Any = None, *, build: Callable[..., pd.DataFrame] | None = None,
    ) -> list[dict]:
        """The answer at one size, as the plain rows every paradigm is stored as.

        ``build`` replaces the task's own, to see what a misreading would deliver.
        """
        build = build or self.build
        frame = build(self.load() if source is None else source, **size.params).copy()
        names = [column.name for column in self.columns]
        if list(frame.columns) != names:
            raise ValueError(f"{self.name}: built {list(frame.columns)}, declared {names}")
        for column in self.columns:
            if column.kind is CellKind.DECIMAL:
                frame[column.name] = frame[column.name].astype("Float64").round(column.decimals)
            elif column.kind is CellKind.INTEGER:
                frame[column.name] = frame[column.name].astype("Int64")
            else:
                frame[column.name] = frame[column.name].astype("string")
        return as_records(frame)

    def check(self, delivered: Any, expected: list[dict]):
        """The verdict on a delivered table, given the expected rows."""
        # An integer is compared as a number with no tolerance, not as a Python
        # int: pandas holds an integer column with a missing cell as floats, so
        # 5.0 for 5 says nothing about the channel that delivered it.
        decimals = {
            column.name: 0 if column.kind is CellKind.INTEGER else column.decimals
            for column in self.columns
        }
        return validate_table(
            self.variable, delivered, expected, key=self.key, decimals=decimals,
        )

    def members(self, label: str) -> CaseMembers:
        """The members of the case that asks this task at one size."""
        size = self.size(label)
        expected = cache(lambda: self.expected_rows(size))

        def ground_truth() -> tuple:
            return (expected(),)

        def validate(outputs: dict):
            return self.check(outputs.get(self.output), expected())

        return CaseMembers(
            [self.variable], ground_truth, validate, {"validate": turn_validator(validate)},
        )

    def written_cases(self) -> list[WrittenCase]:
        """The case asking this task at each of its sizes."""
        return [self._written_case(size) for size in self.sizes]

    def _written_case(self, size: Size) -> WrittenCase:
        name = self.case_name(size)
        query = self.query.format(scope=size.scope)
        return WrittenCase(
            name=name,
            spec=case_spec(self.family, name, self.data_sources, [
                turn(query, "validate", [self.output]),
            ]),
            module=module_source(
                f"{self.title}, size {size.label}: a table of {size.rows:,} rows.",
                f"The question:\n\n{quoted(query)}\n\n" + textwrap.fill(
                    "The columns, the arithmetic and the wrong answers the validator must "
                    f"reject are in cases/{self.family}/_{self.name}.py; {self.sizes_vary}.",
                    width=84,
                ),
                f"from cases.{self.family}._{self.name} import TASK\n\n"
                f'variables, ground_truth, validate, validators = TASK.members("{size.label}")',
            ),
            financial_domain=self.financial_domain,
        )
