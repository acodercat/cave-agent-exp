"""A table of storm events with local start times, retagged and nudged round by round.

The object's fragile property is the timezone on ``began_at``: the question at
the end converts to UTC, so a chain that drops the zone answers it wrong even
when every value it holds is the one it was given. Each round retags two rows
and moves their start times on by its own number of minutes, so no round is a
no-op and no round undoes another.
"""

from __future__ import annotations

import pandas as pd

from cases.fidelity._type_tz_datetime import TASK as EVENTS
from core.fidelity import ObjectTask
from core.pipeline import Answer, FollowUp
from core.rounds import Revision

# The rows each round retags, in the order the built table holds them. Frozen
# here rather than read off the data: the ids are written into the rule's text,
# which is part of what tells one experiment from another.
RETAGGED = (
    ("1211973", "1211976"), ("1215149", "1215150"), ("1215285", "1218183"),
    ("1219278", "1219281"), ("1219282", "1219283"), ("1219284", "1219285"),
    ("1219286", "1219287"),
)
LABEL = "Reviewed-{index}"
HOUR_COLUMN = "hour_local"


def _first_round(table: pd.DataFrame) -> pd.DataFrame:
    table = table.copy()
    table[HOUR_COLUMN] = table["began_at"].dt.hour.astype("int64")
    return _retag(table, 1)


def _retag(table: pd.DataFrame, index: int) -> pd.DataFrame:
    table = table.copy()
    chosen = table["event_id"].isin(RETAGGED[index - 1])
    table.loc[chosen, "event_type"] = LABEL.format(index=index)
    table.loc[chosen, "began_at"] = table.loc[chosen, "began_at"] + pd.Timedelta(minutes=index)
    return table


def _ask(index: int) -> str:
    pair = RETAGGED[index - 1]
    rows = (
        f"In the two rows whose event_id is '{pair[0]}' or '{pair[1]}', set event_type to "
        f"'{LABEL.format(index=index)}' and move began_at on by exactly {index} minute"
        f"{'s' if index > 1 else ''}, keeping the timezone it carries."
    )
    if index == 1:
        return (
            f"Add one column, hour_local, holding the hour of began_at as that timestamp's own "
            f"timezone reads it, as an integer column. Then {rows[0].lower()}{rows[1:]} "
            "Leave hour_local as you first computed it. Change nothing else."
        )
    return f"{rows} Leave hour_local and every other row and column exactly as they are."


REVISIONS = tuple(
    Revision(
        index=index, name=f"retag_{index}", ask=_ask(index),
        apply=(_first_round if index == 1 else (lambda table, index=index: _retag(table, index))),
        output=f"events_{index}",
    )
    for index in range(1, len(RETAGGED) + 1)
)


def reviewed(table: pd.DataFrame) -> tuple:
    chosen = table.loc[table["event_type"].str.startswith("Reviewed-")]
    utc = chosen["began_at"].dt.tz_convert("UTC")
    return (len(chosen), int((utc.dt.hour * 60 + utc.dt.minute).sum()))


TASK = ObjectTask(
    name="rounds_tz_events",
    title=EVENTS.title,
    group="rounds",
    kind=EVENTS.kind,
    data_sources=EVENTS.data_sources,
    ask=EVENTS.ask,
    output=EVENTS.output,
    describe=EVENTS.describe,
    build=EVENTS.build,
    follow_up=FollowUp(
        "How many events have an event_type beginning 'Reviewed-', and what do their start "
        "times come to when each is converted to UTC and read as hour times sixty plus minute, "
        "summed over those events?",
        (
            Answer("reviewed_events", "how many events are tagged as reviewed", 0),
            Answer("reviewed_utc_minutes", "the sum of hour*60 + minute, in UTC, over those events", 0),
        ),
        reviewed,
    ),
    row_key=EVENTS.row_key,
)
