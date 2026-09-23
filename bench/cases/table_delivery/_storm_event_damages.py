"""Storm event damages, asked at six sizes.

Each NOAA storm event that began in 2024 in the scope: what it was, where, when
it began, how long it lasted, and the property and crop damage reported. The
scopes run from the District of Columbia (28 events) to Texas with Oklahoma and
Arkansas (10,428).

Event types and county or forecast-zone names are free text with slashes,
brackets and full stops, and the beginning is a timestamp. The two damage
figures are unreported for about three events in ten (3,104 and 3,110 of the
10,428), and an unreported figure is missing, not zero. Giving the duration in
minutes, the beginning without its time, or the names in title case, produces a
different table.

Decimals are compared at 0.6 x 10^-N for the N decimals the column declares;
every other cell is exact, and a cell expected missing must be missing.
"""

import pandas as pd

from core.data import load_expansion_table
from core.table_delivery import CellKind, Column, Size, TableTask, changing


def load():
    events = load_expansion_table("noaa_storm_events")
    return events.loc[events["begin_datetime"].str.startswith("2024")]


def build(events, *, states):
    rows = events.loc[events["state_usps"].isin(states)]
    duration = pd.to_datetime(rows["end_datetime"]) - pd.to_datetime(rows["begin_datetime"])
    return rows.assign(duration_hours=duration.dt.total_seconds() / 3600)[[
        "event_id", "event_type", "county_zone_name", "begin_datetime", "duration_hours",
        "property_damage_usd", "crop_damage_usd",
    ]]


TASK = TableTask(
    name="storm_event_damages",
    title="Storm event damages",
    data_sources=("noaa_storm_events",),
    financial_domain="insurance_disaster",
    query=(
        "Compile the 2024 storm record for {scope} from the NOAA storm events data, taking "
        "events by the date they began. For each event: its identifier, the event type, the "
        "county or forecast zone name, the beginning timestamp as the source writes it, the "
        "duration in hours, and the reported property damage and crop damage. Damage is "
        "often not reported; leave those cells missing rather than zero."
    ),
    output="event_table",
    row_noun="event",
    key=("event_id",),
    columns=(
        Column("event_id", CellKind.IDENTIFIER, "text, exactly as in the source"),
        Column("event_type", CellKind.TEXT, "text, exactly as in the source"),
        Column("county_zone_name", CellKind.TEXT, "text, exactly as in the source"),
        Column("begin_datetime", CellKind.DATE, "text, ISO YYYY-MM-DDTHH:MM:SS as in the source"),
        Column("duration_hours", CellKind.DECIMAL,
               "hours from beginning to end, rounded to 4 decimals", decimals=4),
        Column("property_damage_usd", CellKind.DECIMAL,
               "USD, rounded to 2 decimals, missing where the source reports none",
               decimals=2, nullable=True),
        Column("crop_damage_usd", CellKind.DECIMAL,
               "USD, rounded to 2 decimals, missing where the source reports none",
               decimals=2, nullable=True),
    ),
    sizes=(
        Size("10", "the District of Columbia", 28, {"states": ("DC",)}),
        Size("100", "Delaware", 83, {"states": ("DE",)}),
        Size("250", "New Hampshire", 263, {"states": ("NH",)}),
        Size("500", "Maine", 495, {"states": ("ME",)}),
        Size("1k", "New Mexico", 1068, {"states": ("NM",)}),
        Size("10k", "Texas, Oklahoma and Arkansas", 10428, {"states": ("TX", "OK", "AR")}),
    ),
    load=load,
    build=build,
    near_misses={
        "duration in minutes": changing(duration_hours=lambda hours: hours * 60),
        "beginning as a date without its time": changing(begin_datetime=lambda when: when[:10]),
        "names in title case": changing(county_zone_name=str.title),
    },
)
