"""Fidelity: whether an object that crossed between agents is still the object.

The pipeline study (:mod:`core.pipeline`) asks what it costs to move a table
between agents. This study asks what arrives. A **producer** builds an object
from the source data; a **consumer** is handed it and binds what it holds to
``received``; the host takes ``received`` from the consumer's runtime and
compares it with the object the producer was meant to build, property by
property — every column's dtype, every value, the timezone on a timestamp, the
categories a categorical declares, a model's predictions on held-out rows. The
result is a report, not a verdict: which properties survived, and by how much
the numbers moved.

Two reference points that no model touches sit beside the four arms. The host
serialises the true object through JSON and back, and through Parquet or
joblib and back, and runs the same comparator. Those floors are what the
*format* loses; what an arm loses beyond its floor is what the *model* lost
writing the object out and reading it back in. That distinction is the point:
a library's JSON round trip of a float is exact, and a model's is not.

Every object is small — a few thousand tokens serialised — so that what the
pipeline study measured, a reply that cannot hold the table, does not decide
this one. Two control objects, a plain dict and a ten-row table of plain
types, are expected to cross every arm intact; if the text arm loses them, the
study has a defect and not a finding.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import io
import json
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
import pandas as pd

from cave_agent import Variable

from core.pipeline import FollowUp
from core.validation import as_number


# How close a number must come to count as the same number. Nothing in this
# study computes anything from the object except the light question, so an
# arm that carried full precision and reread it should match to the last bit
# of a double; 1e-9 leaves room for a different summation order and nothing else.
VALUE_TOLERANCE = 1e-9
# A model rebuilt from its parameters predicts through a different sequence of
# floating-point operations than the original; 1e-6 relative is what that
# costs, and what a parameter written short of full precision exceeds.
PREDICTION_TOLERANCE = 1e-6


class ObjectKind(Enum):
    """What the object is, as the arms need to know it.

    The kind decides the file the file arm writes and reads, and the words
    every arm's contract uses for the object; the comparison itself dispatches
    on the true object's Python type and needs no kind.
    """

    TABLE = ("table", "parquet", "DataFrame.to_parquet", "pd.read_parquet")
    ARRAY = ("array", "npy", "np.save", "np.load")
    MODEL = ("model", "joblib", "joblib.dump", "joblib.load")
    COMPOSITE = ("composite", "pkl", "joblib.dump", "joblib.load")

    def __init__(self, label: str, extension: str, writer: str, loader: str):
        self.label = label
        self.extension = extension
        self.writer = writer
        self.loader = loader


@dataclass
class FidelityReport:
    """What survived the crossing, property by property."""

    properties: dict[str, bool] = field(default_factory=dict)
    max_rel_err: float | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def intact(self) -> bool:
        return all(self.properties.values())

    @property
    def lost(self) -> list[str]:
        return [name for name, kept in self.properties.items() if not kept]

    def as_dict(self) -> dict[str, Any]:
        return {
            "intact": self.intact, "lost": self.lost, "properties": self.properties,
            "max_rel_err": self.max_rel_err, "notes": self.notes,
        }


# ----- comparing ------------------------------------------------------------

def compare(
    received: Any, truth: Any, *, probes: Any = None, row_key: str | None = None,
) -> FidelityReport:
    """``received`` against ``truth``, dispatching on what the truth is.

    ``probes`` are the held-out rows a model is compared on. ``row_key`` names
    the column that identifies a table's rows, where one does: the rows are
    then matched on it and their order is not a property, as the table
    validator matches rows on a key — a producer that sorted identifiers as
    numbers where another sorted them as text made the same table. A
    composite is compared element by element under a path, so a report on a
    pair of a table and a dict says which part lost what.
    """
    report = FidelityReport()
    _compare(received, truth, "", report, probes, row_key, 0)
    return report


# Deeper than any object in the study; a received object nested past it, or
# one that refers to itself, is reported rather than descended into.
MAX_DEPTH = 12


def _compare(
    received: Any, truth: Any, path: str, report: FidelityReport, probes: Any, row_key: str | None,
    depth: int,
) -> None:
    """One object under ``path``: ``a.b[2].values`` names a property of the third element of b in a.

    ``received`` is whatever a consumer bound, and a comparison that raises on
    it — a hand-made stand-in for a fitted tree, say — is itself a finding,
    recorded as the property ``comparable`` and never an error of the host's.
    """
    at = (lambda name: f"{path}.{name}" if path else name)
    if depth > MAX_DEPTH:
        report.properties[at("comparable")] = False
        report.notes.append(f"{at('')}: nested deeper than {MAX_DEPTH}")
        return
    try:
        _compare_node(received, truth, at, path, report, probes, row_key, depth)
    except Exception as error:                      # noqa: BLE001 - anything the object does
        report.properties[at("comparable")] = False
        report.notes.append(f"{at('')}: comparison failed ({type(error).__name__}: {str(error)[:80]})")


def _compare_node(received, truth, at, path, report, probes, row_key, depth) -> None:
    if isinstance(truth, pd.DataFrame):
        _compare_table(received, truth, at, report, row_key)
    elif isinstance(truth, np.ndarray):
        _compare_array(received, truth, at, report)
    elif _is_estimator(truth):
        _compare_model(received, truth, at, report, probes)
    elif isinstance(truth, Mapping):
        _compare_mapping(received, truth, path, at, report, probes, row_key, depth)
    elif isinstance(truth, (list, tuple)):
        _compare_sequence(received, truth, path, at, report, probes, row_key, depth)
    else:
        report.properties[at("type")] = _scalar_family(received) == _scalar_family(truth)
        report.properties[at("value")] = _scalars_equal(received, truth, report)


def _is_estimator(value: Any) -> bool:
    try:
        from sklearn.base import BaseEstimator
    except ImportError:                             # pragma: no cover
        return False
    return isinstance(value, BaseEstimator)


def _compare_table(
    received: Any, truth: pd.DataFrame, at, report: FidelityReport, row_key: str | None,
) -> None:
    frame = received
    if not isinstance(frame, pd.DataFrame):
        # A consumer that held the rows as a list of dicts held the values but
        # not the object; the values are still compared, so the report says both.
        report.properties[at("is_dataframe")] = False
        try:
            frame = pd.DataFrame(frame)
        except Exception:                           # noqa: BLE001 - anything at all
            report.notes.append(f"{at('')}: not a table at all ({type(received).__name__})")
            return
    else:
        report.properties[at("is_dataframe")] = True
    if row_key in truth.columns and row_key in frame.columns and truth[row_key].is_unique:
        frame, truth = _aligned(frame, row_key), _aligned(truth, row_key)
    report.properties[at("rows")] = len(frame) == len(truth)
    report.properties[at("columns")] = list(frame.columns) == list(truth.columns)
    # The index is a property where the task gave the table one; a default
    # RangeIndex is what any construction leaves behind and is not compared.
    if not isinstance(truth.index, pd.RangeIndex) or truth.index.names != [None]:
        report.properties[at("index")] = (
            list(frame.index.names) == list(truth.index.names)
            and len(frame.index) == len(truth.index)
            and bool(frame.index.equals(truth.index))
        )
    for column in truth.columns:
        if column not in frame.columns:
            continue
        got, want = frame[column], truth[column]
        report.properties[at(f"dtype:{column}")] = _dtype_family(got.dtype) == _dtype_family(want.dtype)
        if isinstance(want.dtype, pd.DatetimeTZDtype):
            report.properties[at(f"tz:{column}")] = (
                isinstance(got.dtype, pd.DatetimeTZDtype) and str(got.dtype.tz) == str(want.dtype.tz)
            )
        if isinstance(want.dtype, pd.CategoricalDtype):
            got_categories = list(got.cat.categories) if isinstance(got.dtype, pd.CategoricalDtype) else None
            report.properties[at(f"categories:{column}")] = got_categories == list(want.cat.categories)
            report.properties[at(f"ordered:{column}")] = (
                isinstance(got.dtype, pd.CategoricalDtype) and bool(got.cat.ordered) == bool(want.cat.ordered)
            )
        if len(got) != len(want):
            report.properties[at(f"values:{column}")] = False
            continue
        got_na, want_na = got.isna().to_numpy(), want.isna().to_numpy()
        report.properties[at(f"na:{column}")] = bool((got_na == want_na).all())
        report.properties[at(f"values:{column}")] = _column_values_equal(
            got[~want_na], want[~want_na], report,
        )


def _aligned(frame: pd.DataFrame, row_key: str) -> pd.DataFrame:
    """The rows in the order of their key, as text, so two orderings of the same rows compare equal."""
    order = frame[row_key].astype(str).argsort(kind="stable")
    return frame.iloc[order].reset_index(drop=True)


def _dtype_family(dtype) -> str:
    """The family a dtype belongs to, so that Int64 and int64 read the same.

    A category is its own family, whatever it holds: T4's point is that the
    categorical survives. Object and string columns are one family, since a
    table rebuilt from records holds its text as object.
    """
    types = pd.api.types
    if isinstance(dtype, pd.CategoricalDtype):
        return "category"
    if types.is_datetime64_any_dtype(dtype):
        return "datetime"
    if types.is_bool_dtype(dtype):
        return "bool"
    if types.is_integer_dtype(dtype):
        return "int"
    if types.is_float_dtype(dtype):
        return "float"
    if types.is_string_dtype(dtype) or types.is_object_dtype(dtype):
        return "str"
    return str(dtype)


def _column_values_equal(got: pd.Series, want: pd.Series, report: FidelityReport) -> bool:
    family = _dtype_family(want.dtype)
    if family == "int":
        # Integers are exact: through float, 2**53 + 1 is 2**53, and a relative
        # tolerance would let a large count drift by one.
        numbers = [as_number(v) for v in got.to_numpy()]
        return all(n is not None and _whole(n) for n in numbers) and \
            [int(n) for n in numbers] == [int(v) for v in want.to_numpy()]
    if family == "float":
        numbers = [as_number(v) for v in got.to_numpy()]
        if any(n is None for n in numbers):
            return False
        return _record_rel_err(np.asarray(numbers, dtype=float), want.to_numpy(dtype=float), report)
    if family == "datetime":
        # A column that lost its zone is compared on the wall clock it kept,
        # so ``values`` says what the clock says and ``tz`` says the zone;
        # a column in another zone is compared as instants.
        try:
            g = pd.to_datetime(pd.Series(got.to_numpy()), errors="raise")
        except (TypeError, ValueError):
            return False
        aware = isinstance(want.dtype, pd.DatetimeTZDtype)
        if aware and g.dt.tz is None:
            w = want.dt.tz_localize(None)
        elif aware:
            g, w = g.dt.tz_convert("UTC"), want.dt.tz_convert("UTC")
        else:
            w = want
        return bool((g.to_numpy() == w.to_numpy()).all())
    if family == "bool":
        return [bool(v) if isinstance(v, (bool, np.bool_)) else None for v in got] == [bool(v) for v in want]
    # text, identifiers, categories: exact, as text
    return [None if v is None else str(v) for v in got.astype(object)] == \
        [str(v) for v in want.astype(object)]


def _whole(number) -> bool:
    return isinstance(number, (int, np.integer)) or float(number).is_integer()


def _record_rel_err(got: np.ndarray, want: np.ndarray, report: FidelityReport) -> bool:
    if got.shape != want.shape:
        return False
    scale = np.maximum(np.abs(want), 1e-300)
    err = float(np.max(np.abs(got - want) / scale)) if want.size else 0.0
    report.max_rel_err = err if report.max_rel_err is None else max(report.max_rel_err, err)
    return err <= VALUE_TOLERANCE


def _compare_array(received: Any, truth: np.ndarray, at, report: FidelityReport) -> None:
    array = received
    if not isinstance(array, np.ndarray):
        report.properties[at("is_ndarray")] = False
        try:
            array = np.asarray(array)
        except (TypeError, ValueError):
            report.notes.append(f"{at('')}: not an array ({type(received).__name__})")
            return
    else:
        report.properties[at("is_ndarray")] = True
    report.properties[at("shape")] = array.shape == truth.shape
    # Exact: float32 holds a float64's value only by accident of the value.
    report.properties[at("dtype")] = array.dtype == truth.dtype
    report.properties[at("values")] = array.shape == truth.shape and _record_rel_err(
        array.astype(float), truth.astype(float), report,
    )


# The fitted state compared is what the model's function is made of: its
# float parameters and arrays, its integer arrays (a tree's nodes, a
# classifier's classes), and its nested estimators. Left out are what the fit
# left behind rather than what it produced — integer counts (features seen,
# samples seen, rank), the solver's iteration count, feature names remembered
# only when fitted on a DataFrame — and values derived from others: the SVD's
# singular values, a tree's feature importances, a scaler's variance (its
# transform uses ``scale_``). A model rebuilt from its parameters has the first
# kind and not the second, and it is the same function.
_NOT_STATE = ("n_iter_", "feature_names_in_", "singular_", "feature_importances_", "var_")
_TREE_ARRAYS = ("feature", "threshold", "children_left", "children_right", "value")


def _compare_model(received: Any, truth: Any, at, report: FidelityReport, probes: Any) -> None:
    """A fitted estimator: its class, its hyperparameters, its fitted state, what it predicts.

    The state is every fitted attribute (a trailing underscore) that holds a
    float, an array or another estimator, less what ``_NOT_STATE`` explains;
    a tree's is the arrays of its nodes; a pipeline's is its steps, each
    compared as an estimator. Predictions on the probes are compared besides,
    so a model rebuilt some other way that behaves the same is seen to.
    """
    report.properties[at("type")] = type(received) is type(truth)
    report.properties[at("params")] = _params(received) == _params(truth)
    for name, want in _fitted_state(truth).items():
        got = getattr(received, name, None)
        under = (lambda inner, name=name: at(f"{name}.{inner}"))
        if _is_estimator(want):
            # The probes are the whole model's; a nested estimator is compared on its state.
            _compare_model(got, want, under, report, None)
        elif name == "tree_":
            for array in _TREE_ARRAYS:
                report.properties[under(array)] = got is not None and _arrays_equal(
                    getattr(got, array, None), getattr(want, array), report,
                )
        elif isinstance(want, np.ndarray) and want.dtype.kind in "iufb":
            report.properties[at(name)] = _arrays_equal(got, want, report)
        elif isinstance(want, np.ndarray):
            report.properties[at(name)] = got is not None and \
                [str(v) for v in np.asarray(got).ravel()] == [str(v) for v in want.ravel()]
        else:
            report.properties[at(name)] = _scalars_equal(got, want, report)
    steps = getattr(truth, "steps", None)
    if steps is not None:
        got_steps = dict(getattr(received, "steps", None) or [])
        report.properties[at("steps")] = list(got_steps) == [name for name, _ in steps]
        for name, step in steps:
            _compare_model(got_steps.get(name), step, lambda inner, name=name: at(f"steps.{name}.{inner}"),
                           report, None)
    if probes is not None:
        _compare_predictions(received, truth, at, report, probes)


def _fitted_state(model: Any) -> dict[str, Any]:
    state = {}
    for name in dir(model):
        if not name.endswith("_") or name.startswith("_") or name in _NOT_STATE or name == "steps":
            continue
        try:
            value = getattr(model, name)
        except Exception:                           # noqa: BLE001 - a property may refuse
            continue
        if _is_estimator(value) or name == "tree_" or isinstance(value, np.ndarray) or \
                isinstance(value, (float, np.floating)):
            state[name] = value
    return state


def _params(model: Any) -> dict[str, Any]:
    """The hyperparameters, with a callable named and nested estimators left to their own comparison."""
    try:
        params = model.get_params(deep=False)
    except Exception:                               # noqa: BLE001 - not an estimator
        return {}
    plain = {}
    for name, value in params.items():
        if _holds_estimator(value):
            continue
        plain[name] = getattr(value, "__name__", value) if callable(value) else value
    return plain


def _arrays_equal(got: Any, want: np.ndarray, report: FidelityReport) -> bool:
    if got is None:
        return False
    try:
        got = np.asarray(got)
    except Exception:                               # noqa: BLE001
        return False
    if got.shape != want.shape:
        return False
    if want.dtype.kind in "iub":
        return bool((got == want).all())
    return _record_rel_err(got.astype(float), want.astype(float), report)


def _compare_predictions(received, truth, at, report: FidelityReport, probes) -> None:
    """What the models say of the probes: labels exactly, probabilities and values within tolerance."""
    try:
        want = np.asarray(truth.predict(probes))
        got = np.asarray(received.predict(probes))
        if want.dtype.kind in "iub" or want.dtype.kind in "OSU":
            ok = got.shape == want.shape and bool((got == want).all())
        else:
            ok = got.shape == want.shape and _within(got, want, np.maximum(np.abs(want), 1e-300), report)
        report.properties[at("predicts")] = bool(ok)
    except Exception as error:                      # noqa: BLE001 - a rebuilt model may fail any way
        report.properties[at("predicts")] = False
        report.notes.append(f"{at('')}: predict failed ({type(error).__name__}: {str(error)[:80]})")
    if hasattr(truth, "predict_proba"):
        try:
            want = np.asarray(truth.predict_proba(probes), dtype=float)
            got = np.asarray(received.predict_proba(probes), dtype=float)
            # In [0, 1], so compared as it stands.
            report.properties[at("predicts_proba")] = got.shape == want.shape and \
                _within(got, want, np.ones_like(want), report)
        except Exception as error:                  # noqa: BLE001
            report.properties[at("predicts_proba")] = False
            report.notes.append(f"{at('')}: predict_proba failed ({type(error).__name__})")


def _within(got: np.ndarray, want: np.ndarray, scale: np.ndarray, report: FidelityReport) -> bool:
    err = float(np.max(np.abs(got.astype(float) - want) / scale)) if want.size else 0.0
    report.max_rel_err = err if report.max_rel_err is None else max(report.max_rel_err, err)
    return err <= PREDICTION_TOLERANCE


def _compare_mapping(
    received, truth: Mapping, path: str, at, report: FidelityReport, probes, row_key, depth,
) -> None:
    if not isinstance(received, Mapping):
        report.properties[at("is_mapping")] = False
        return
    report.properties[at("keys")] = list(received.keys()) == list(truth.keys())
    for key, value in truth.items():
        if key in received:
            _compare(received[key], value, at(str(key)), report, probes, row_key, depth + 1)
        else:
            report.properties[at(f"{key}.present")] = False


def _compare_sequence(
    received, truth: Sequence, path: str, at, report: FidelityReport, probes, row_key, depth,
) -> None:
    if not isinstance(received, (list, tuple)):
        report.properties[at("is_sequence")] = False
        return
    report.properties[at("type")] = type(received) is type(truth)
    report.properties[at("length")] = len(received) == len(truth)
    for index, value in enumerate(truth):
        if index < len(received):
            _compare(received[index], value, f"{path}[{index}]", report, probes, row_key, depth + 1)


def _scalar_family(value: Any) -> str:
    """bool, int, float, str, none or other: what a plain value is, whoever's numeric type holds it."""
    if isinstance(value, (bool, np.bool_)):
        return "bool"
    if isinstance(value, (int, np.integer)):
        return "int"
    if isinstance(value, (float, np.floating)):
        return "float"
    if isinstance(value, str):
        return "str"
    return "none" if value is None else type(value).__name__


def _scalars_equal(received: Any, truth: Any, report: FidelityReport) -> bool:
    if isinstance(truth, bool):
        return isinstance(received, (bool, np.bool_)) and bool(received) is truth
    if isinstance(truth, (int, np.integer)):
        got = as_number(received)
        return got is not None and _whole(got) and int(got) == int(truth)
    if isinstance(truth, (float, np.floating)):
        got = as_number(received)
        if got is None:
            return False
        want = float(truth)
        err = abs(float(got) - want) / max(abs(want), 1e-300)
        report.max_rel_err = err if report.max_rel_err is None else max(report.max_rel_err, err)
        return err <= VALUE_TOLERANCE
    if truth is None:
        return received is None
    return received == truth


# ----- the reference points -------------------------------------------------

def to_jsonable(value: Any) -> Any:
    """The plainest JSON form of an object: tables as records, arrays as lists."""
    if isinstance(value, pd.DataFrame):
        frame = value.reset_index() if not isinstance(value.index, pd.RangeIndex) or \
            value.index.names != [None] else value
        return json.loads(frame.to_json(orient="records", date_format="iso", double_precision=15))
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Mapping):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def from_jsonable(data: Any, like: Any) -> Any:
    """The plainest reconstruction of ``data`` in the shape of ``like``.

    A table comes back as ``pd.DataFrame(records)`` and an array as
    ``np.asarray(list)``: what a careful reader does with no more than the JSON.
    Types the format does not carry — a timezone, a categorical, an integer
    with a missing value, a tuple — are not guessed back; that is the floor.
    ``like`` says only where a table or an array stands.
    """
    if isinstance(like, pd.DataFrame):
        return pd.DataFrame(data)
    if isinstance(like, np.ndarray):
        return np.asarray(data)
    if isinstance(like, Mapping) and isinstance(data, Mapping):
        return {k: from_jsonable(data.get(str(k)), v) for k, v in like.items()}
    if isinstance(like, (list, tuple)) and isinstance(data, list):
        return [from_jsonable(d, v) for d, v in zip(data, like)]
    return data


def write_object(value: Any, kind: ObjectKind, path: Path) -> None:
    """Write an object the way the file arm's producer is told to."""
    if kind is ObjectKind.TABLE:
        value.to_parquet(path)
    elif kind is ObjectKind.ARRAY:
        np.save(path, value)
    else:
        import joblib
        joblib.dump(value, path)


def read_object(kind: ObjectKind, path: Path) -> Any:
    """Read it back the way the file arm's consumer is told to."""
    if kind is ObjectKind.TABLE:
        return pd.read_parquet(path)
    if kind is ObjectKind.ARRAY:
        return np.load(path)
    import joblib
    return joblib.load(path)


def format_floors(
    kind: ObjectKind, truth: Any, *, probes: Any = None, row_key: str | None = None,
) -> dict[str, FidelityReport]:
    """The comparator on the object after each format's round trip, with no model in between."""
    floors: dict[str, FidelityReport] = {}
    if kind is not ObjectKind.MODEL and not _holds_estimator(truth):
        data = json.loads(json.dumps(to_jsonable(truth)))
        floors["json"] = compare(from_jsonable(data, truth), truth, probes=probes, row_key=row_key)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / f"object.{kind.extension}"
        write_object(truth, kind, path)
        floors["file"] = compare(read_object(kind, path), truth, probes=probes, row_key=row_key)
    return floors


def _holds_estimator(value: Any) -> bool:
    if _is_estimator(value):
        return True
    if isinstance(value, Mapping):
        return any(_holds_estimator(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_holds_estimator(v) for v in value)
    return False


def serialized_tokens(value: Any) -> int:
    """How big the object is as text, in the study's token estimate (chars / 4)."""
    if _holds_estimator(value):
        import joblib
        buffer = io.BytesIO()
        joblib.dump(value, buffer)
        return len(buffer.getvalue()) // 4
    return len(json.dumps(to_jsonable(value), default=str)) // 4


# ----- the study's cases ----------------------------------------------------

@dataclass(frozen=True)
class Degradation:
    """One thing that could happen to the object, and the property it should cost.

    ``felt`` is whether the task's light question, asked of the degraded
    object, comes out wrong: a test requires it where it is claimed. A loss the
    question feels is one with a consequence downstream; a loss it does not
    feel — an integer column read back as floats — is still a loss of the
    object, and the report records it either way.
    """

    apply: Callable[[Any], Any]
    loses: str        # the property the report must mark False
    felt: bool = True


@dataclass(frozen=True)
class ObjectTask:
    """One object the producer builds and the consumer is handed.

    ``ask`` is the producer's whole instruction about the object. It says what
    the object is and nothing about how it will travel — a test greps it for
    the words a channel would use — so the four arms' producers are asked the
    same thing. ``build`` makes the true object from the loaded source tables,
    keyed by their runtime names. ``describe`` is what every contract calls
    the object. ``follow_up`` is the light question the consumer answers from
    it, whose ``compute`` takes the true object; ``probes`` are held-out rows
    a model is compared on; ``row_key`` the column that identifies the rows of
    a table in the object, where one does. ``degradations`` are the ways this
    object can lose fidelity: a test applies each and requires the comparator
    to notice.
    """

    name: str
    title: str
    group: str                                  # type | precision | structure | model | control
    kind: ObjectKind
    data_sources: tuple[str, ...]
    ask: str
    output: str
    describe: str
    build: Callable[[dict[str, pd.DataFrame]], Any]
    follow_up: FollowUp
    degradations: Mapping[str, Degradation] = field(default_factory=dict)
    probes: Callable[[dict[str, pd.DataFrame]], pd.DataFrame] | None = None
    row_key: str | None = None

    @property
    def variable(self) -> Variable:
        return Variable(self.output, None, f"{self.describe} {KEEP_BOUND}")


# The producer keeps the object it built under its output's name in its own
# runtime, in every arm, whatever the arm's delivery rule — a reply, a file,
# the variable itself. The host reads it there before anything crosses, so a
# producer that built the wrong object is told apart from a crossing that
# lost it.
KEEP_BOUND = (
    "Whatever else the delivery rules say, also keep the finished object bound under "
    "this name in your runtime."
)

# The consumer's first output: the object as it holds it. The host reads it
# from the consumer's runtime in every arm, which is the measurement. Its
# description says what the object is, as the task defines it, in every arm
# alike: in the cave arm the runtime describes the handed object anyway, and a
# consumer told nothing in the text arm held a table as the list of records
# the orchestrator had called it.
RECEIVED = "received"
RECEIVED_DESCRIPTION = (
    "The object you were handed — {describe} — exactly as you hold it after loading "
    "or rebuilding it: the same type, dtypes and values, changed in nothing."
)
# What the consumer finds its input under, in the arm that hands it an object.
INPUT_SLOT = "delivered"
HANDED_OBJECT_DESCRIPTION = "The object the producer agent was asked to build, exactly as it built it."

# Every object is this small, serialised, so that volume — what the pipeline
# study measured — does not decide fidelity.
TOKEN_LIMIT = 3000

# Said by every task whose object holds a table with text columns. Several
# source columns are stored as pandas categoricals, so "as text" alone leaves
# the producer a choice the study does not mean to measure: a producer that
# carried a category through unchanged differed from one that wrote a string
# column, and in the arms where the host can see the object that difference
# read as a loss. The sentence fixes what the column holds — Python strings,
# in a string or object column, which the comparator reads as one family —
# and says nothing about how the object travels.
TEXT_COLUMNS = "Any column called text here holds plain strings (a pandas string or object column, not a categorical)."


@dataclass(frozen=True)
class FidelityCase:
    """A task as the orchestrated pipeline runs it: producer, then consumer."""

    task: ObjectTask

    @property
    def name(self) -> str:
        return self.task.name

    @property
    def data_sources(self) -> tuple[str, ...]:
        return self.task.data_sources

    @property
    def follow_up(self) -> FollowUp:
        return self.task.follow_up

    @property
    def roles(self) -> tuple[str, str]:
        return ("producer", "consumer")

    @property
    def agents(self) -> int:
        return 2

    @property
    def consumer_variables(self) -> list[Variable]:
        describe = self.task.describe.rstrip(".")
        described = RECEIVED_DESCRIPTION.format(describe=describe[0].lower() + describe[1:])
        return [Variable(RECEIVED, None, described), *self.follow_up.variables]

    def truth(self, tables: Mapping[str, pd.DataFrame]) -> Any:
        return self.task.build(tables)

    def probes(self, tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame | None:
        return self.task.probes(tables) if self.task.probes else None
