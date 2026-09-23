"""The pipeline cases: a table crossing a pipeline of agents.

Every case is a delivery task the suite already has, asked at one size, followed
by the agents that hand its table on and a second question about what reaches the
end (:mod:`cases.pipeline.follow_ups`, :mod:`cases.pipeline.stages`). The cases are
enumerated here rather than written one file per case, and they are not
registered in ``benchmarks.json``: a pipeline is several agents and several
runtimes, which ``scripts.run`` has no shape for. ``scripts.run_pipeline`` runs
them.

Two case sets, because they answer different questions.

**The main study** (:data:`PIPELINE_CASES`) is three agents — retriever, narrower,
analyst — over all twenty-four tasks at three sizes. It asks what the channel
costs, with enough task clusters for the interval around that answer to mean
something. Three of each task's six sizes are used. The delivery study already
has the single-hop curve across all six on twenty of these tasks, and from 1,000
rows up the text arms are at zero there; a pipeline run at those sizes only
repeats that its first agent cannot deliver, at the study's highest cost per run
(one three-agent text pipeline at 1,000 rows was measured at 870 s), and shows
nothing about the seams. What a second hop can show that a single one cannot
lies where the single hop still worked, so the sizes kept are 250 and 500, on
either side of where a reply starts to strain, and 10, where every channel is
expected to pass. That smallest size is not padding: it is the control that shows
the pipeline, the middle rule and the follow-up questions are sound, so that a
text-arm failure at a larger size cannot be blamed on them.

**The depth probe** (:func:`depth_cases`) is the same first and last agents with
relays in between, run at two, three, four and five agents over a subset. Because
a relay hands on everything it was given, the table is the same size at every
crossing, so what changes between depths is only how many crossings there were.
That is the measurement a two-agent pipeline cannot make: whether a channel's
loss compounds with depth or is paid once.
"""

from __future__ import annotations

from dataclasses import replace

from cases.pipeline.follow_ups import FOLLOW_UPS
from cases.pipeline.stages import KEEP_LOWER_HALF, RELAY
from core.pipeline import PipelineCase


PIPELINE_SIZES = ("10", "250", "500")

PIPELINE_CASES: tuple[PipelineCase, ...] = tuple(
    PipelineCase(task=task, size=task.size(label), follow_up=follow_up, middles=(KEEP_LOWER_HALF,))
    for task, follow_up in FOLLOW_UPS
    for label in PIPELINE_SIZES
)


# The probe trades tasks for depths. Six clusters spread across the financial
# domains and across the two delivery families, at the two sizes that bracket
# where a reply starts to strain: below it every channel should be flat with
# depth, above it the text channel has somewhere to fall.
DEPTH_TASKS = (
    "branch_top_deposits",              # table_control, banking
    "market_quality_top_securities",    # table_control, capital markets
    "bank_capital_ratios",              # table_delivery, banking
    "holdings_value_changes",           # table_delivery, investment funds
    "county_sector_employment",         # table_delivery, macro
    "private_offerings",                # table_delivery, corporate reporting
)
DEPTH_SIZES = ("250", "1k")
DEPTH_AGENTS = (2, 3, 4, 5)


def depth_cases(agents: int) -> tuple[PipelineCase, ...]:
    """The probe's cases for a pipeline of ``agents`` agents, relays in between."""
    if agents < 2:
        raise ValueError("a pipeline needs at least a first and a last agent")
    chosen = [pair for pair in FOLLOW_UPS if pair[0].name in set(DEPTH_TASKS)]
    missing = set(DEPTH_TASKS) - {task.name for task, _ in chosen}
    if missing:
        raise ValueError(f"the depth probe names no such task: {sorted(missing)}")
    # Each relay hands on under its own name. A runtime refuses to register one
    # name twice, so a shared pipeline with two relays would raise before it ran;
    # and a record in which every stage assigned `relayed_table` could not say
    # which stage a table came from.
    relays = tuple(
        replace(RELAY, output=f"{RELAY.output}_{stage}")
        for stage in range(1, agents - 1)
    )
    return tuple(
        PipelineCase(
            task=task, size=task.size(label), follow_up=follow_up, middles=relays,
        )
        for task, follow_up in chosen
        for label in DEPTH_SIZES
    )
