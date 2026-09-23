"""Compare paradigms that answered the same cases, one study per paradigm.

    uv run python -m scripts.compare_paradigms --name x1-imported --set imported \\
        --study cave=x1-a-cave --repeats cave=3 \\
        --study codeblock=x1-a-codeblock --repeats codeblock=3

Writes ``experiments/comparisons/<name>/report.json``. Every definition below is
fixed before any study it reads is run; changing one is a change of protocol.

Units. A *task* is what a comparison resamples: an imported case is its own
task; the sizes of a table-delivery task are one task; the conditions of a
state-revision task are one task. Within a case, its runs and their turns are
averaged together; within a task, its cases. A task enters a comparison of two
paradigms with the cases both have scored, and its *stratum* (a size, a
condition) lets a comparison be repeated within one.

Outcomes, per scored turn:

* ``success`` (primary): the turn passes after at most the protocol repairs the
  study allowed — the repair arm's verdict when a repair was attempted, the
  first answer's otherwise.
* ``strict_success``: the first answer passes. In a conversation, a later turn
  follows the history as it actually was, repaired or not; this is not a run
  without repair.
* ``cell_accuracy`` (secondary, table-delivery turns only): the share of the
  table's non-key cells delivered right, after repairs as for ``success``. Each
  expected row delivered at least once contributes its cells once; the wrong
  cells and the cells of columns a row leaves out are taken off, repeats
  included; and the rest is divided by the cells of the larger of the expected
  and the delivered table, so a missing row, an extra row and a repeated row
  each cost their cells. A table not delivered scores 0. Unlike ``success``, a
  wrong cell costs only its own share of the table, which is what makes this
  precise enough to show two channels alike.
* ``stale`` (state-revision turns only): the second turn's answer is the one the
  data gave before the host revised it (:mod:`core.state_revision`). It is taken
  over conversations whose first turn passed, and not for a task whose revision
  changes no answer (a negative control, whose costs are read with ``--task``).
* ``source_reread`` (the same turns): the turn's code named the case's data
  again — a registered table by its variable, a file by its path, a handle by
  its load — rather than working on only what the first turn left behind. It is
  read from ``tables_referenced``, which the evaluator records per turn from the
  executed code, so it is a property of the run and not of this script.
* ``stale_after_reread`` (the same turns, where the code did name the data
  again): the answer is still the one from before the revision. This separates
  two ways of being stale. Reusing a derived result is one, and any persistent
  runtime allows it. Going back to the data and still answering from before the
  revision is another, and only a channel that hands over a *copy* allows it:
  the file on disk was replaced, but the DataFrame the first turn read from it
  was not. A registered table cannot fail this way, because naming it is what
  reaching the current data means. Read it per condition: under an announcement
  it is the residual risk of copy-based exchange.

Costs, per run, over every model call it made, repair arms included:

* ``estimated_tokens`` and ``estimated_completion_tokens`` (primary): one
  estimator applied to every call of every paradigm (see ``core.agents``). A
  provider's own count is not comparable across actions, because a fenced reply
  is read only to its first block, before the provider reports usage.
* ``model_calls``.

Attempts abandoned to an outage are not part of any run; their number and spend
are reported per paradigm.

A comparison of paradigm P against the reference R takes, for each shared task,
the difference P − R of the task means, and reports their mean with 90% and 95%
percentile intervals from a bootstrap that resamples tasks. For an outcome, P and
R are *equivalent* when the 90% interval lies inside its margin (two one-sided
tests at 5%), and *differ* when the 95% interval excludes zero; both, either or
neither may hold. The margins are fixed in :data:`OUTCOMES`: 0.10 for the success
outcomes, 0.02 for cell accuracy, and none for staleness, which is a risk to
measure rather than a quality to show alike. For a cost, the ratio of mean costs
P/R is reported with its 95% interval, and no equivalence is claimed.

Each paradigm's own mean of every outcome is reported overall and per stratum.
For state revision, whose question is also whether a warning helps, each
condition is contrasted within every paradigm with the one that says nothing of
revisions (:data:`BASELINE_STRATA`), paired by task and without a margin.

Missing runs. Every case of a paradigm is run as many times as its
``--repeats`` declares; paradigms may differ. A case with fewer scored
runs — a run failed after its retries and was not replaced, or a turn could not
be scored — is short of that many runs, and the primary analysis leaves them
out. The ``*_missing_as_failure`` outcomes count every turn of every missing run
as failed, which cannot flatter the paradigm that is short; staleness, defined
only for an answer, has no such variant. A case with more
scored runs than the protocol allows is an error.

Verdicts. A run is read only with a programmatic-verification verdict reached
against the current answer key (:mod:`core.answer_key`); a missing or stale one
is an error, and the study must be scored again before it is compared.

Tables. For table-delivery turns, row losses and cell errors are pooled per
paradigm and stratum, and cell errors are also broken down by the kind of cell
(:class:`core.table_delivery.CellKind`), each over the cells actually compared.

Studies are compared only when they share the model configuration and every run
setting except the paradigm and the injection mode, which only a paradigm that
registers its tables uses; within a study, the injection mode is fixed too.

Not counted in any cost: the model calls CaveAgent makes to summarise a history
it compacts, which it does not report. Runs that compacted are counted in
``loop_events``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import cache
import hashlib
import importlib
import json
from pathlib import Path
from statistics import fmean
from typing import Callable, Iterable

import numpy as np

from config import BENCHMARKS_JSON, EXPERIMENTS_DIR, PROJECT_ROOT
from core.answer_key import answer_key_fingerprint
from core.evaluator import load_specs
from core.state_revision import STALE, Condition
from core.results import (
    RUNS_DIR, atomic_write_json, iter_result_files, load_result, resolve_experiment,
    result_is_complete, utc_now, verification_path,
)
from core.types import conversations_of


SCHEMA = "cave-bench-paradigm-comparison-v1"
COMPARISONS_DIR = EXPERIMENTS_DIR / "comparisons"
BOOTSTRAP_DRAWS = 10_000
ALL_STRATA = "all"
# The run settings two studies must share to be compared; a study also fixes its injection.
SHARED_SETTINGS = ("max_protocol_nudges", "total_step_budget", "max_exec_output")
SIZE_ORDER = ("10", "100", "250", "500", "1k", "5k", "10k")


def _top_directory(spec: dict) -> str:
    return Path(spec["_path"]).relative_to(PROJECT_ROOT).parts[0]


# The stratum a set's other strata are contrasted with, within each paradigm: a
# state-revision condition against the one that says nothing of revisions, and a
# delivery size against the smallest one. The second is what the delivery study
# asks — a paradigm is not slow or wrong in the abstract, it is slower and wronger
# as the table it must hand over grows — and the contrast is paired by task, so it
# is the same question answered at two sizes rather than two sets of questions.
BASELINE_STRATA = {
    "state_revision": Condition.UNSTATED.value,
    "table_delivery": SIZE_ORDER[0],
    "table_control": SIZE_ORDER[0],
}

CASE_SETS: dict[str, Callable[[dict], bool]] = {
    "imported": lambda spec: _top_directory(spec) == "evals",
    "table_delivery": lambda spec: spec["task_family"] == "table_delivery",
    "table_control": lambda spec: spec["task_family"] == "table_control",
    "state_revision": lambda spec: spec["task_family"] == "state_revision",
}


@dataclass(frozen=True)
class Turn:
    paradigm: str
    case: str
    run_id: str
    success: bool
    strict_success: bool
    missing: bool = False
    stop_cause: str | None = None
    failure_type: str | None = None
    tables: dict = field(default_factory=dict)
    # Each defined only for the turns the module docstring names.
    cell_accuracy: float | None = None
    stale: bool | None = None
    source_reread: bool | None = None


@dataclass(frozen=True)
class Run:
    paradigm: str
    case: str
    run_id: str
    spent: dict
    loop_events: dict


@dataclass
class Study:
    """One paradigm's scored turns and runs, and what is missing from them."""

    paradigm: str
    turns: list[Turn] = field(default_factory=list)
    runs: list[Run] = field(default_factory=list)
    model: dict | None = None
    settings: dict = field(default_factory=dict)
    injection: str | None = None
    missing_runs: int = 0
    failed_attempts: list[dict] = field(default_factory=list)
    failed_runs: list[str] = field(default_factory=list)
    unscored_runs: list[str] = field(default_factory=list)


def _spent(run: Run, *keys: str) -> float | None:
    return float(sum(run.spent.get(key, 0) for key in keys)) if run.spent else None


@dataclass(frozen=True)
class Outcome:
    value: Callable[[Turn], float | None]   # None where the outcome is not defined
    margin: float | None                     # of equivalence; None claims none
    counts_missing: bool                     # a missing run's turns count as failures


# Fixed before any study is run; see the module docstring.
OUTCOMES = {
    "success": Outcome(lambda turn: float(turn.success), 0.10, True),
    "strict_success": Outcome(lambda turn: float(turn.strict_success), 0.10, True),
    "cell_accuracy": Outcome(lambda turn: turn.cell_accuracy, 0.02, True),
    "stale": Outcome(lambda turn: None if turn.stale is None else float(turn.stale), None, False),
    "source_reread": Outcome(
        lambda turn: None if turn.source_reread is None else float(turn.source_reread),
        None, False),
    "stale_after_reread": Outcome(
        lambda turn: float(turn.stale) if turn.source_reread else None, None, False),
}
RUN_COSTS: dict[str, Callable[[Run], float | None]] = {
    "estimated_tokens": lambda run: _spent(
        run, "estimated_prompt_tokens", "estimated_completion_tokens"),
    "estimated_completion_tokens": lambda run: _spent(run, "estimated_completion_tokens"),
    "model_calls": lambda run: _spent(run, "model_calls"),
}


# -- tasks -------------------------------------------------------------------------

@dataclass(frozen=True)
class CaseTask:
    task: str
    stratum: str | None
    # A table-delivery case's non-key columns and their cell kinds.
    columns: dict[str, str] = field(default_factory=dict)
    # A state-revision case whose revision changes the second answer.
    measures_staleness: bool = False


def task_of(spec: dict) -> CaseTask:
    if spec["task_family"] in ("table_delivery", "table_control"):
        from importlib import import_module

        task, size = import_module(f"cases.{spec['task_family']}").task_and_size(spec["name"])
        columns = {
            column.name: column.kind.value for column in task.columns
            if column.name not in task.key
        }
        return CaseTask(task.name, size.label, columns)
    if spec["task_family"] == "state_revision":
        from cases.state_revision import tasks

        name, _, condition = spec["name"].rpartition("_")
        task = {task.name: task for task in tasks()}[name]
        return CaseTask(name, condition, measures_staleness=task.changes_answer)
    return CaseTask(spec["name"], None)


# -- reading a study ---------------------------------------------------------------

def load_study(
    paradigm: str, experiment: Path, specs: dict[str, dict], tasks: dict[str, CaseTask],
    *, repeats: int,
) -> Study:
    study = Study(paradigm)
    scored_runs: Counter[str] = Counter()
    for case, path in iter_result_files(experiment, set(specs)):
        payload = load_result(path)
        settings = payload.get("run", {})
        if settings.get("paradigm") != paradigm:
            raise ValueError(
                f"{path}: a run of {settings.get('paradigm')!r} in a study of {paradigm!r}")
        _adopt_configuration(study, payload, path)
        study.failed_attempts.extend(settings.get("failed_attempts", []))
        turns = (
            _scored_turns(paradigm, tasks[case], payload, _current_verdicts(path, specs[case]))
            if result_is_complete(payload, specs[case]) else None
        )
        if turns is None:
            study.unscored_runs.append(str(path))
            continue
        scored_runs[case] += 1
        study.turns.extend(turns)
        loop_events = _total(
            conversation.get("loop_events", {}) for conversation in payload["conversations"])
        study.runs.append(Run(
            paradigm, case, settings["run_id"], payload.get("spent", {}), dict(loop_events),
        ))
    for path in sorted((experiment / RUNS_DIR).glob("*/*/*/error.json")):
        if path.parents[2].name in specs:
            study.failed_runs.append(str(path))
            study.failed_attempts.extend(json.loads(path.read_text()).get("failed_attempts", []))
    for case, spec in specs.items():
        if scored_runs[case] > repeats:
            raise ValueError(
                f"{paradigm}: {case} has {scored_runs[case]} scored runs, the protocol {repeats}")
        missing = repeats - scored_runs[case]
        study.missing_runs += missing
        study.turns.extend(
            Turn(paradigm, case, f"missing-{index}", False, False, missing=True,
                 cell_accuracy=0.0 if tasks[case].columns else None)
            for index in range(missing)
            for conversation in conversations_of(spec) for _ in conversation.turns
        )
    return study


def _adopt_configuration(study: Study, payload: dict, path: Path) -> None:
    run = payload.get("run", {})
    configuration = (
        payload.get("model", {}), {key: run.get(key) for key in SHARED_SETTINGS},
        run.get("injection"),
    )
    if study.model is None:
        study.model, study.settings, study.injection = configuration
    elif configuration != (study.model, study.settings, study.injection):
        raise ValueError(f"{path}: model or run settings differ from the study's other runs")


@cache
def _answer_key(module_name: str) -> str:
    return answer_key_fingerprint(importlib.import_module(module_name))


def _current_verdicts(path: Path, spec: dict) -> dict[tuple[str, int], dict]:
    """The run's per-turn verdicts, refused unless reached against today's answer key."""
    verification = verification_path(path)
    if not verification.exists():
        raise ValueError(f"{path}: no verdict; score the study before comparing it")
    payload = json.loads(verification.read_text())
    if payload.get("validator", {}).get("fingerprint") != _answer_key(spec["module"]):
        raise ValueError(f"{path}: the verdict predates the answer key; score the study again")
    return {
        (conversation["id"], turn["turn"]): turn
        for conversation in payload.get("conversations", [])
        for turn in conversation.get("turns", [])
    }


def _scored_turns(
    paradigm: str, case_task: CaseTask, payload: dict, verdicts: dict[tuple[str, int], dict],
) -> list[Turn] | None:
    """The run's turns with their verdicts, or None when a turn was refused a verdict."""
    case, run_id = payload["case"], payload["run"]["run_id"]
    turns = []
    for conversation in payload["conversations"]:
        for number, stored in enumerate(conversation["turns"], start=1):
            verdict = verdicts.get((conversation["id"], number), {})
            first = verdict.get("programmatic_verification")
            if verdict.get("status") != "scored" or not isinstance(first, dict):
                return None
            repaired = verdict.get("protocol_repair_verification")
            final = repaired if isinstance(repaired, dict) else first
            items = final.get("variable_verification", {}).get("items", {})
            tables = {
                name: item["table"] for name, item in items.items()
                if isinstance(item, dict) and item.get("table")
            }
            accuracy = stale = reread = None
            if case_task.columns:
                # Every output of such a turn is a table; one not delivered scores 0.
                accuracy = fmean(cell_accuracy(tables.get(name)) for name in stored["stores"])
            if case_task.measures_staleness and number == 2 and turns[-1].success:
                stale = bool(items) and all(
                    isinstance(item, dict) and item.get(STALE) for item in items.values())
                # What the executed code named, as the evaluator recorded it.
                repair = stored.get("protocol_repair")
                named = (repair or stored).get("tables_referenced", [])
                reread = bool(named)
            turns.append(Turn(
                paradigm, case, run_id,
                success=bool(final["success"]), strict_success=bool(first["success"]),
                stop_cause=stored.get("stop_cause"), failure_type=final.get("failure_type"),
                tables=tables, cell_accuracy=accuracy, stale=stale, source_reread=reread,
            ))
    return turns


def cell_accuracy(table: dict | None) -> float:
    """The share of a delivered table's non-key cells that are right (module docstring).

    Every table-delivery task has a non-key column and every size a row, which
    ``tests/test_table_delivery.py`` holds, so the denominator is never zero.
    """
    if not table:
        return 0.0
    errors = table["cell_errors"]
    width = len(errors)
    # A repeated row adds no right cells: it cannot stand in for a missing one.
    delivered_once = table["rows_expected"] - table["rows_missing"]
    wrong = sum(errors.values()) + sum(table["columns_absent"].get(column, 0) for column in errors)
    cells = max(table["rows_expected"], table["rows_delivered"]) * width
    return max(0.0, delivered_once * width - wrong) / cells


# -- statistics --------------------------------------------------------------------

def task_means(
    observations: Iterable[tuple[str, str, float]], tasks: dict[str, CaseTask],
) -> dict[str, dict[str, float]]:
    """Task → case → mean of that case's (case, run, value) observations."""
    by_case: dict[str, list[float]] = defaultdict(list)
    for case, _, value in observations:
        by_case[case].append(value)
    by_task: dict[str, dict[str, float]] = defaultdict(dict)
    for case, values in by_case.items():
        by_task[tasks[case].task][case] = fmean(values)
    return dict(by_task)


def paired_difference(
    reference: dict[str, dict[str, float]], other: dict[str, dict[str, float]],
    *, label: str, margin: float | None = None, ratio: bool = False,
) -> dict:
    """``other`` − ``reference`` over shared tasks, each on the cases both have.

    With a ``margin``, whether the two are equivalent within it and whether they
    differ; with ``ratio``, the ratio of their means, as for a cost.
    """
    reference_means, other_means = [], []
    for task in sorted(reference.keys() & other.keys()):
        cases = sorted(reference[task].keys() & other[task].keys())
        if cases:
            reference_means.append(fmean(reference[task][case] for case in cases))
            other_means.append(fmean(other[task][case] for case in cases))
    report: dict = {"tasks": len(reference_means)}
    if not reference_means:
        return report
    before, after = np.asarray(reference_means), np.asarray(other_means)
    draws = bootstrap_indices(len(before), label)
    differences = (after - before)[draws].mean(axis=1)
    report |= {
        "mean_difference": float((after - before).mean()),
        "ci90": interval(differences, 90),
        "ci95": interval(differences, 95),
    }
    (low90, high90), (low95, high95) = report["ci90"], report["ci95"]
    report["differs_from_zero"] = low95 > 0 or high95 < 0
    if margin is not None:
        report |= {
            "margin": margin, "equivalent_within_margin": -margin <= low90 and high90 <= margin,
        }
    if ratio and before.sum() > 0:
        ratios = after[draws].sum(axis=1) / before[draws].sum(axis=1)
        report |= {"ratio": float(after.sum() / before.sum()), "ratio_ci95": interval(ratios, 95)}
    return report


def mean_over_tasks(by_task: dict[str, dict[str, float]], *, label: str) -> dict:
    """One paradigm's mean over its tasks, with a 95% task-bootstrap interval."""
    values = np.asarray([fmean(cases.values()) for cases in by_task.values()])
    if not len(values):
        return {"tasks": 0}
    draws = bootstrap_indices(len(values), label)
    return {
        "tasks": len(values), "mean": float(values.mean()),
        "ci95": interval(values[draws].mean(axis=1), 95),
    }


def bootstrap_indices(size: int, label: str) -> np.ndarray:
    """Task indices for every draw, seeded by what is being estimated."""
    seed = int(hashlib.sha256(label.encode()).hexdigest()[:16], 16)
    return np.random.default_rng(seed).integers(0, size, size=(BOOTSTRAP_DRAWS, size))


def interval(draws: np.ndarray, level: int) -> list[float]:
    tail = (100 - level) / 2
    low, high = np.percentile(draws, [tail, 100 - tail])
    return [float(low), float(high)]


# -- the comparison ----------------------------------------------------------------

def compare(
    studies: dict[str, Study], tasks: dict[str, CaseTask], *, reference: str,
    baseline_stratum: str | None = None,
) -> dict:
    """Each paradigm against the reference, overall and within each stratum.

    With a ``baseline_stratum``, also each other stratum against it within every
    paradigm, as :data:`BASELINE_STRATA` sets for a case set.
    """
    if reference not in studies:
        raise ValueError(f"the reference paradigm {reference!r} has no study")
    shapes = {
        json.dumps({"model": study.model, "settings": study.settings}, sort_keys=True)
        for study in studies.values() if study.model is not None
    }
    if len(shapes) > 1:
        raise ValueError(f"the studies differ in model or settings: {sorted(shapes)}")
    answered = {turn.case for study in studies.values() for turn in study.turns}
    strata = [ALL_STRATA] + sorted(
        {tasks[case].stratum for case in answered if tasks[case].stratum is not None},
        key=lambda stratum: (SIZE_ORDER.index(stratum) if stratum in SIZE_ORDER else 99, stratum),
    )
    shared = json.loads(next(iter(shapes), '{"model": null, "settings": {}}'))
    report = {
        "reference": reference, "bootstrap_draws": BOOTSTRAP_DRAWS,
        "margins": {name: outcome.margin for name, outcome in OUTCOMES.items()},
        "model": shared["model"], "settings": shared["settings"],
        "paradigms": {
            name: _paradigm_report(study, tasks, strata) for name, study in studies.items()
        },
        "comparisons": {
            name: {
                stratum: _pairwise(studies[reference], study, tasks, stratum)
                for stratum in strata
            }
            for name, study in studies.items() if name != reference
        },
    }
    if baseline_stratum is not None:
        report["baseline_stratum"] = baseline_stratum
        report["contrasts"] = {
            name: {
                stratum: _contrast(study, tasks, stratum, baseline_stratum)
                for stratum in strata if stratum not in {ALL_STRATA, baseline_stratum}
            }
            for name, study in studies.items()
        }
    return report


def _outcome_means(
    turns: Iterable[Turn], tasks: dict[str, CaseTask], outcome: Outcome, stratum: str,
    *, with_missing: bool = False,
) -> dict[str, dict[str, float]]:
    """Task → case → mean of the outcome over the stratum's turns where it is defined."""
    return task_means(
        ((t.case, t.run_id, observed) for t in turns
         if (stratum == ALL_STRATA or tasks[t.case].stratum == stratum)
         and (with_missing or not t.missing) and (observed := outcome.value(t)) is not None),
        tasks,
    )


def _pairwise(reference: Study, other: Study, tasks, stratum: str) -> dict:
    label = f"{reference.paradigm}:{other.paradigm}:{stratum}"
    report = {}
    for name, outcome in OUTCOMES.items():
        variants = {"": False}
        if outcome.counts_missing:
            variants["_missing_as_failure"] = True
        for suffix, with_missing in variants.items():
            reference_means, other_means = (
                _outcome_means(study.turns, tasks, outcome, stratum, with_missing=with_missing)
                for study in (reference, other)
            )
            if reference_means or other_means:
                report[name + suffix] = paired_difference(
                    reference_means, other_means, label=f"{label}:{name}{suffix}",
                    margin=outcome.margin,
                )
    for cost, value in RUN_COSTS.items():
        reference_means, other_means = (
            task_means(
                ((run.case, run.run_id, spent) for run in study.runs
                 if (stratum == ALL_STRATA or tasks[run.case].stratum == stratum)
                 and (spent := value(run)) is not None),
                tasks,
            )
            for study in (reference, other)
        )
        report[cost] = paired_difference(
            reference_means, other_means, label=f"{label}:{cost}", ratio=True,
        )
    return report


def _contrast(study: Study, tasks: dict[str, CaseTask], stratum: str, baseline: str) -> dict:
    """``stratum`` − ``baseline`` within one paradigm, paired by task.

    A task has one case in each stratum, so its cases are paired through the task.
    """
    def per_task(outcome: Outcome, stratum: str) -> dict[str, dict[str, float]]:
        return {
            task: {"": fmean(cases.values())}
            for task, cases in _outcome_means(study.turns, tasks, outcome, stratum).items()
        }

    report = {}
    for name, outcome in OUTCOMES.items():
        stratum_means, baseline_means = per_task(outcome, stratum), per_task(outcome, baseline)
        if stratum_means or baseline_means:
            report[name] = paired_difference(
                baseline_means, stratum_means,
                label=f"{study.paradigm}:{stratum}-{baseline}:{name}",
            )
    return report


def _paradigm_report(study: Study, tasks: dict[str, CaseTask], strata: list[str]) -> dict:
    scored = [turn for turn in study.turns if not turn.missing]
    failed_spent = _total(attempt.get("spent", {}) for attempt in study.failed_attempts)
    return {
        "injection": study.injection,
        "scored_runs": len(study.runs), "scored_turns": len(scored),
        "missing_runs": study.missing_runs, "failed_runs": len(study.failed_runs),
        "unscored_runs": len(study.unscored_runs),
        "failed_attempts": len(study.failed_attempts), "failed_attempts_spent": dict(failed_spent),
        "outcomes": {
            stratum: {
                name: mean_over_tasks(by_task, label=f"{study.paradigm}:{stratum}:{name}")
                for name, outcome in OUTCOMES.items()
                if (by_task := _outcome_means(scored, tasks, outcome, stratum))
            }
            for stratum in strata
        },
        "failure_types": dict(Counter(turn.failure_type for turn in scored if turn.failure_type)),
        "stop_causes": dict(Counter(turn.stop_cause for turn in scored if turn.stop_cause)),
        "loop_events": dict(_total(run.loop_events for run in study.runs)),
        "tables": table_losses(scored, tasks),
    }


def table_losses(turns: Iterable[Turn], tasks: dict[str, CaseTask]) -> dict:
    """Row losses and cell errors of the delivered tables, pooled per stratum.

    A cell error rate is the errors over the cells compared: each matched row
    contributes one cell for every non-key column, of its column's kind.
    """
    pooled: dict[str, Counter] = defaultdict(Counter)
    for turn in turns:
        columns = tasks[turn.case].columns
        for table in turn.tables.values():
            totals = pooled[str(tasks[turn.case].stratum)]
            totals["tables"] += 1
            for key in ("rows_expected", "rows_matched", "rows_missing", "rows_unexpected",
                        "rows_repeated"):
                totals[key] += table.get(key, 0)
            for column, errors in table.get("cell_errors", {}).items():
                kind = columns.get(column, "unclassified")
                totals[f"errors:{kind}"] += errors
                totals[f"compared:{kind}"] += table.get("rows_matched", 0)
    report = {}
    for stratum, totals in sorted(pooled.items()):
        kinds = sorted(key.split(":", 1)[1] for key in totals if key.startswith("compared:"))
        compared = sum(totals[f"compared:{kind}"] for kind in kinds)
        report[stratum] = {
            **{key: totals[key] for key in (
                "tables", "rows_expected", "rows_matched", "rows_missing", "rows_unexpected",
                "rows_repeated")},
            "row_miss_rate": _rate(totals["rows_missing"], totals["rows_expected"]),
            "cell_error_rate": _rate(sum(totals[f"errors:{kind}"] for kind in kinds), compared),
            "cell_error_rate_by_kind": {
                kind: _rate(totals[f"errors:{kind}"], totals[f"compared:{kind}"]) for kind in kinds
            },
        }
    return report


def _total(counts: Iterable[dict]) -> Counter:
    return sum((Counter(item) for item in counts), Counter())


def _rate(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


# -- entry point -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--name", required=True, help="comparison id under experiments/comparisons/")
    parser.add_argument("--set", choices=sorted(CASE_SETS), required=True, dest="case_set")
    parser.add_argument("--study", action="append", required=True, metavar="PARADIGM=STUDY")
    parser.add_argument(
        "--repeats", action="append", required=True, metavar="PARADIGM=N",
        help="runs per case the protocol sets for the paradigm")
    parser.add_argument("--reference", default="cave")
    parser.add_argument(
        "--task", action="append", default=[], dest="only_tasks",
        help="compare only this task's cases (repeatable), such as a negative control")
    args = parser.parse_args()

    in_set = CASE_SETS[args.case_set]
    specs = {spec["name"]: spec for spec in load_specs(BENCHMARKS_JSON) if in_set(spec)}
    tasks = {name: task_of(spec) for name, spec in specs.items()}
    if args.only_tasks:
        unknown = set(args.only_tasks) - {task.task for task in tasks.values()}
        if unknown:
            raise ValueError(f"no such task in the set: {sorted(unknown)}")
        tasks = {name: task for name, task in tasks.items() if task.task in args.only_tasks}
        specs = {name: specs[name] for name in tasks}
    named = dict(item.split("=", 1) for item in args.study)
    repeats = {paradigm: int(n) for paradigm, n in (item.split("=", 1) for item in args.repeats)}
    if repeats.keys() != named.keys():
        raise ValueError("give --repeats for each paradigm with a --study, and only those")
    studies = {
        paradigm: load_study(
            paradigm, resolve_experiment(study), specs, tasks, repeats=repeats[paradigm])
        for paradigm, study in named.items()
    }
    report = {
        "schema": SCHEMA, "generated_at": utc_now(), "case_set": args.case_set,
        "repeats": repeats, "studies": named, "tasks": sorted(args.only_tasks) or "all",
        **compare(
            studies, tasks, reference=args.reference,
            baseline_stratum=BASELINE_STRATA.get(args.case_set),
        ),
    }
    output = COMPARISONS_DIR / args.name / "report.json"
    atomic_write_json(output, report)
    print(output)


if __name__ == "__main__":
    main()
