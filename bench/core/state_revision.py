"""A state-revision task: the host changes the data between two turns.

A persistent runtime keeps whatever the agent derived in its first turn, under
every paradigm: a filtered table, a grouped summary, a ranking. When the host
then revises the data, the agent can answer its second turn from the revised
tables or from what it kept. The family measures how often it does the second,
and whether a word of warning changes that.

A task asks two questions over the same tables and revises them in between, and
is asked under each :class:`Condition`, one case each. The second turn's
validator records an answer as *stale* when every output equals the second
question's answer on the tables as they stood before the revision; an answer
that is wrong some other way is only wrong. A task whose revision leaves the
second answer unchanged is a negative control: nothing can be stale, and what
it measures is what re-reading the data costs.

A task may also withhold part of the data before the first turn, so a revision
can add rows as well as change and remove them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cache
from typing import Callable, Mapping

import pandas as pd
from cave_agent import Variable

from core.runtime_catalog import select_runtime_tables
from core.types import CaseMembers
from core.validation import ValidatorResult, turn_validator, validate_ordered_outputs
from core.written_cases import WrittenCase, case_spec, module_source, quoted, turn


FAMILY = "state_revision"
# The mark a second-turn verdict and each of its outputs carry when the answer is stale.
STALE = "stale"

Tables = Mapping[str, pd.DataFrame]
Revision = Callable[[Tables], dict[str, pd.DataFrame]]


class Condition(Enum):
    ANNOUNCED = "announced"       # the second turn says the data was revised
    UNANNOUNCED = "unannounced"   # only the system prompt says the host may revise it
    UNSTATED = "unstated"         # nothing says so: the risk itself


@dataclass(frozen=True)
class Output:
    name: str
    description: str
    decimals: int | None = None   # None compares exactly


@dataclass(frozen=True)
class Question:
    query: str
    outputs: tuple[Output, ...]
    answer: Callable[[Tables], tuple]   # the answer on the tables as they stand


@dataclass(frozen=True)
class RevisionTask:
    """Two questions over the same tables, with the host revising them in between.

    The tables are those ``data_sources`` declares, keyed by runtime name, which
    is what the evaluator hands a revision. ``withhold``, when given, is applied
    before the first turn and ``revise`` before the second; both return only the
    tables they change, and neither changes its input.
    """

    name: str
    title: str
    data_sources: tuple[str, ...]
    financial_domain: str
    first: Question
    second: Question
    announcement: str             # opens the second question under ANNOUNCED
    revise: Revision
    withhold: Revision | None = None
    changes_answer: bool = True   # False for a negative control

    def case_name(self, condition: Condition) -> str:
        return f"{self.name}_{condition.value}"

    @property
    def revisions(self) -> dict[int, Revision]:
        """What the host does to the data before each turn, by turn index."""
        return ({0: self.withhold} if self.withhold else {}) | {1: self.revise}

    def load(self) -> dict[str, pd.DataFrame]:
        """The declared tables as the catalog holds them."""
        return {table.name: table.loader() for table in select_runtime_tables(self.data_sources)}

    def tables(self, source: Tables | None = None) -> tuple[dict, dict]:
        """The tables as the first turn and as the second turn find them."""
        original = dict(self.load() if source is None else source)
        first = original | (self.withhold(original) if self.withhold else {})
        return first, first | self.revise(first)

    def answers(self, source: Tables | None = None) -> tuple[tuple, tuple, tuple]:
        """The first answer, the second answer, and the second answer before the revision."""
        first, second = self.tables(source)
        return self.first.answer(first), self.second.answer(second), self.second.answer(first)

    def members(self) -> CaseMembers:
        """The members every case of this task shares, whatever its condition."""
        answers = cache(self.answers)
        variables = [
            Variable(output.name, None, output.description)
            for question in (self.first, self.second) for output in question.outputs
        ]

        def check(question: Question, outputs: dict, expected: tuple):
            names = {output.name for output in question.outputs}
            return validate_ordered_outputs(
                outputs, [v for v in variables if v.name in names], list(expected),
                [output.decimals for output in question.outputs],
            )

        def validate_first(outputs: dict):
            return check(self.first, outputs, answers()[0])

        def validate_second(outputs: dict):
            _, expected, before = answers()
            verdict = check(self.second, outputs, expected)
            if self.changes_answer and check(self.second, outputs, before).success:
                detail = verdict.message
                verdict.message = f"{STALE}: answered from the data before the revision; {detail}"
                for result in verdict.variable_results.values():
                    result[STALE] = True
            return verdict

        def ground_truth() -> tuple:
            first, second, _ = answers()
            return (*first, *second)

        def validate(outputs: dict):
            verdicts = (validate_first(outputs), validate_second(outputs))
            return ValidatorResult(
                all(v.success for v in verdicts),
                "; ".join(v.message for v in verdicts),
                any(v.variables_not_set for v in verdicts),
                {name: item for v in verdicts for name, item in v.variable_results.items()},
            )

        return CaseMembers(variables, ground_truth, validate, {
            "validate_first": turn_validator(validate_first),
            "validate_second": turn_validator(validate_second),
        })

    def written_cases(self) -> list[WrittenCase]:
        """The case asking this task under each condition."""
        return [self._written_case(condition) for condition in Condition]

    def _written_case(self, condition: Condition) -> WrittenCase:
        name = self.case_name(condition)
        second = self.second.query
        if condition is Condition.ANNOUNCED:
            second = f"{self.announcement} {second}"
        warns = condition is not Condition.UNSTATED
        return WrittenCase(
            name=name,
            spec=case_spec(FAMILY, name, self.data_sources, [
                turn(self.first.query, "validate_first", [o.name for o in self.first.outputs]),
                turn(second, "validate_second", [o.name for o in self.second.outputs]),
            ]),
            module=module_source(
                f"{self.title}: {condition.value}.",
                f"The first question:\n\n{quoted(self.first.query)}\n\n"
                f"The second question, after the host revises the data:\n\n{quoted(second)}\n\n"
                "The revision, the answers and what counts as stale are in\n"
                f"cases/{FAMILY}/_{self.name}.py; the conditions differ only in what the\n"
                "agent is told.",
                f"from cases.{FAMILY}._{self.name} import TASK\n\n"
                "variables, ground_truth, validate, validators = TASK.members()\n"
                "revisions = TASK.revisions\n"
                f"warns_of_revisions = {warns}",
            ),
            financial_domain=self.financial_domain,
        )
