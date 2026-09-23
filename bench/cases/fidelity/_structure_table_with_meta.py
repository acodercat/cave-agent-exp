"""A table with its metadata beside it: Mississippi banks' equity, and what the numbers are in."""

from __future__ import annotations

import pandas as pd

from cases.fidelity._sources import REPORT_DATE, balance
from core.fidelity import TEXT_COLUMNS, Degradation, ObjectKind, ObjectTask
from core.pipeline import Answer, FollowUp

METADATA = {"units": "thousand USD", "as_of": REPORT_DATE, "source": "FFIEC call reports"}


def build(tables) -> tuple[pd.DataFrame, dict]:
    rows = balance(tables, "MS")
    table = pd.DataFrame({
        "bank_rssd_id": rows["bank_rssd_id"].astype("string"),
        "total_equity": rows["total_equity_thousand_usd"].astype("Int64"),
    })
    return (table, dict(METADATA))


def total_in_dollars(pair: tuple) -> tuple:
    table, metadata = pair
    factor = {"thousand USD": 1000}[metadata["units"]]
    return (int(table["total_equity"].sum()) * factor,)


TASK = ObjectTask(
    name="structure_table_with_meta",
    title="Bank equity with its units",
    group="structure",
    kind=ObjectKind.COMPOSITE,
    data_sources=("ffiec_call_reports_balance",),
    ask=(
        "From the FFIEC balance-sheet data as of 2024-12-31, take every bank in Mississippi, "
        "ordered by RSSD identifier ascending. Build a Python tuple of two elements: first a "
        "DataFrame with exactly the columns bank_rssd_id (as text) and total_equity (total "
        "equity as an integer column, pandas Int64, in the source's thousands of dollars); "
        "second a dict with exactly the keys 'units', 'as_of' and 'source', holding "
        "'thousand USD', '2024-12-31' and 'FFIEC call reports'."
        + " " + TEXT_COLUMNS
    ),
    output="equity",
    describe=(
        "A tuple (table, metadata): a DataFrame of Mississippi banks with columns bank_rssd_id "
        "and total_equity, and a dict with keys units, as_of and source."
    ),
    build=build,
    follow_up=FollowUp(
        "What is total equity over all these banks, in dollars — converting from the units the "
        "metadata states?",
        (Answer("total_equity_usd", "the sum in dollars, a whole number", 0),),
        total_in_dollars,
    ),
    row_key="bank_rssd_id",
    degradations={
        "metadata dropped": Degradation(lambda p: (p[0], {}), "[1].keys"),
        "units changed": Degradation(lambda p: (p[0], {**p[1], "units": "USD"}), "[1].units.value"),
    },
)
