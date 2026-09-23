"""A timezone-aware timestamp column: Texas storm events of October 2024."""

from __future__ import annotations

import pandas as pd

from core.fidelity import TEXT_COLUMNS, Degradation, ObjectKind, ObjectTask
from core.pipeline import Answer, FollowUp

STATE, MONTH, ZONE = "TX", "2024-10", "America/Chicago"


def build(tables) -> pd.DataFrame:
    events = tables["noaa_storm_event_details_df"]
    rows = events.loc[events["state_usps"].eq(STATE) & events["begin_datetime"].str.startswith(MONTH)]
    rows = rows.sort_values("event_id")
    return pd.DataFrame({
        "event_id": rows["event_id"].astype("string"),
        "event_type": rows["event_type"].astype("string"),
        "began_at": pd.to_datetime(rows["begin_datetime"]).dt.tz_localize(ZONE),
    }).reset_index(drop=True)


def overnight(table: pd.DataFrame) -> tuple:
    hour = table["began_at"].dt.tz_convert("UTC").dt.hour
    return (int(((hour >= 3) & (hour < 11)).sum()),)


TASK = ObjectTask(
    name="type_tz_datetime",
    title="Storm events with local start times",
    group="type",
    kind=ObjectKind.TABLE,
    data_sources=("noaa_storm_events",),
    ask=(
        "From the NOAA storm event details, take every event in Texas whose begin time "
        "falls in October 2024, ordered by event identifier ascending. Build a DataFrame "
        "with exactly these columns: event_id (the identifier, as text), event_type (as "
        "the source gives it, as text), and began_at, the begin time as a timezone-aware "
        "timestamp: the source's begin_datetime is local Central time with no zone "
        "attached, so localize it to America/Chicago rather than converting it."
        + " " + TEXT_COLUMNS
    ),
    output="events",
    describe=(
        "A DataFrame of Texas storm events of October 2024 with columns event_id, "
        "event_type and began_at, where began_at is a timestamp localized to America/Chicago."
    ),
    build=build,
    follow_up=FollowUp(
        "How many of these events began between 03:00 and 11:00 UTC (from 03:00 inclusive "
        "to 11:00 exclusive)?",
        (Answer("events_03_to_11_utc", "that count, a whole number", 0),),
        overnight,
    ),
    row_key="event_id",
    degradations={
        "zone dropped": Degradation(
            lambda t: t.assign(began_at=t["began_at"].dt.tz_localize(None)), "tz:began_at", felt=False,
        ),
        "converted to UTC": Degradation(
            lambda t: t.assign(began_at=t["began_at"].dt.tz_convert("UTC")), "tz:began_at", felt=False,
        ),
    },
)
