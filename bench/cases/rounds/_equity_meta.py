"""A table of bank equity beside its metadata, audited round by round.

The object is a tuple, and one of its halves is a dict: two things a plain JSON
round trip does not carry back on its own. Each round writes in both halves —
it marks one bank's equity as no longer reported, and records its own number in
the metadata — so the metadata ends up holding the chain's own trace. A list
reading ``[1, 2, 4]`` says an edit was skipped, ``[1, 2, 3, 3]`` that one was
made twice, ``[1, 2, 5]`` that a round worked from an older version.
"""

from __future__ import annotations

import pandas as pd

from cases.fidelity._structure_table_with_meta import TASK as EQUITY
from core.fidelity import ObjectTask
from core.pipeline import Answer, FollowUp
from core.rounds import Revision

# The bank each round marks, frozen because the ids are written into the rules.
WITHDRAWN = ("101738", "11640", "118736", "12142", "121642", "179335", "205243")
TRACE = "revisions"


def _withdraw(pair: tuple[pd.DataFrame, dict], index: int) -> tuple[pd.DataFrame, dict]:
    table, metadata = pair
    table = table.copy()
    table.loc[table["bank_rssd_id"].eq(WITHDRAWN[index - 1]), "total_equity"] = pd.NA
    metadata = {**metadata, TRACE: [*metadata.get(TRACE, []), index]}
    return (table, metadata)


def _ask(index: int) -> str:
    return (
        f"In the table, set total_equity to missing for the bank whose bank_rssd_id is "
        f"'{WITHDRAWN[index - 1]}', leaving the column able to hold missing values and every "
        f"other row as it is. In the metadata, append the integer {index} to the list under the "
        f"key '{TRACE}'; if that key is not there yet, add it with the list [{index}]. Leave the "
        "metadata's other keys and their values alone."
    )


REVISIONS = tuple(
    Revision(
        index=index, name=f"withdraw_{index}", ask=_ask(index),
        apply=(lambda pair, index=index: _withdraw(pair, index)),
        output=f"equity_{index}",
    )
    for index in range(1, len(WITHDRAWN) + 1)
)


def reported(pair: tuple[pd.DataFrame, dict]) -> tuple:
    table, metadata = pair
    factor = {"thousand USD": 1000}[metadata["units"]]
    return (int(table["total_equity"].dropna().sum()) * factor, len(metadata.get(TRACE, [])))


TASK = ObjectTask(
    name="rounds_equity_meta",
    title=EQUITY.title,
    group="rounds",
    kind=EQUITY.kind,
    data_sources=EQUITY.data_sources,
    ask=EQUITY.ask,
    output=EQUITY.output,
    describe=EQUITY.describe,
    build=EQUITY.build,
    follow_up=FollowUp(
        "Over the banks whose total_equity is still reported, what is total equity in dollars, "
        "converted from the units the metadata states? And how many revisions does the metadata "
        "record?",
        (
            Answer("reported_equity_usd", "the sum over the banks still reporting, in dollars", 0),
            Answer("revisions_recorded", "how many entries the metadata's revisions list holds", 0),
        ),
        reported,
    ),
    row_key=EQUITY.row_key,
)
