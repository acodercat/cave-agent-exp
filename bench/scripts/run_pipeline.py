"""Run the multi-agent pipeline: one arm per invocation, resumable by repeat count.

    uv run python -m scripts.run_pipeline --model <name> --channel object \
        --experiment x2-pipeline-v1-object --repeats 3 --concurrency 6

With ``--study orchestrated`` the same cases are run the other way round: one
orchestrator agent is handed the workers as objects and directs them itself
(:mod:`core.orchestration`), and ``--channel`` names the medium the orchestrator
and workers exchange state through. The pool, the resume rule and the record
are shared, because what differs is who coordinates, not how a study is run.
``--study rounds`` hands one object along a chain of agents that each edit it
and judges every hop (:mod:`core.rounds`).

One channel per invocation because the arms are compared to each other and a
process per arm is what the delivery study's drivers already do: an arm that has
to be killed takes only its own runs with it.

``--repeats`` is the number of runs each case should end with, and a case that
already has that many is skipped, so re-running this after a batch was killed
asks only for what is missing and can never push a case past its repeats. That
is the same guarantee the shell drivers get by asking which cases are short,
made part of the driver because a pipeline has no registry to ask.

A stored run counts towards that number only if it was made under the same
configuration: channel, pipeline depth, roles, step budget, nudges and output
cap. A run made with a different budget is a different experiment, and skipping
over it would quietly mix the two in one study directory. Each run also records
the commit and the working-tree state it ran from, because the delivery study
could not afterwards say which of its runs had seen a change made mid-study.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from config import EXPERIMENTS_DIR, MODELS_TOML
from cases.pipeline import DEPTH_AGENTS, PIPELINE_CASES, depth_cases
from cases.rounds import ROUNDS_CASES
from core.errors import BenchmarkSpecificationError, InfrastructureError
from core.fidelity import FidelityCase
from core.rounds import RoundsCase
from core.rounds_evaluator import run_rounds
from core.models import load_model
from core.orchestration import ARMS as ORCHESTRATION_ARMS
from core.orchestration_evaluator import PRODUCER, run_orchestration
from core.pipeline import CHANNELS, PipelineCase, cases_by_name
from core.pipeline_evaluator import PipelineSettings, run_hosted
from core.results import (
    RUNS_DIR, atomic_write_json, new_run_id, sanitize_component, utc_now,
)
from core.transcripts import write_transcript


PIPELINE_FILE = "pipeline.json"
PIPELINE_SCHEMA = "cave-bench-pipeline-v3"
# The longest one pipeline may take while the event loop is running. In the
# orchestrated study a worker's whole loop runs inside one cell of the
# orchestrator's runtime, and an in-process runtime cannot be interrupted
# (cave_agent.runtime.protocol.PreemptibleRuntime says so). This guard catches
# a pipeline that stalls while awaiting — a model stream that never ends, a
# worker loop that never returns — and abandons it as an outage of the case.
# It cannot catch generated code that never yields to the loop: a CPU-bound
# cell blocks the timer along with everything else. For that, the process runs
# under a CPU-time limit, which the kernel enforces, and the driver script
# restarts it; the run in flight is lost and the resume rule picks the case up
# again.
#
# A pipeline that runs past the guard is stored as a failed run of the case,
# not retried: the study's rule is that a run which cannot finish within the
# budget is a failure, and retrying it would spend three guards' worth of time
# on a case already known to be the slowest. The record carries ``timed_out``
# so a table can tell it from a wrong answer. The guard was two hours while the
# arms were filled the first time; the remaining text and json runs are the
# slowest cases, and an hour is the budget they get.
PIPELINE_TIMEOUT_S = 60 * 60
# An outage is the endpoint's, not the case's; a case that fails this many times
# in a row is reported rather than retried forever.
MAX_ATTEMPTS = 3
# When every running case fails at once the endpoint is down, not the cases.
# Retrying then spends each case's attempts on the same refused connection: two
# smoke pipelines abandoned three attempts each in 160 s against a vLLM that
# had crashed. So the pool pauses and probes the endpoint until it answers.
OUTAGE_PROBE_SECONDS = 30
OUTAGE_GIVE_UP_SECONDS = 3600


def code_fingerprint() -> dict:
    """The commit this process runs from, and whether the tree matched it.

    Best effort: a checkout without git records that it could not say. A dirty
    tree is recorded as such rather than refused, because a study is sometimes
    run from a tree with an uncommitted fix; the point is that the record says
    so instead of leaving it to be reconstructed from timestamps.
    """
    root = Path(__file__).resolve().parent.parent
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": bool(dirty)}


def run_configuration(
    case: PipelineCase | FidelityCase | RoundsCase, channel, settings: PipelineSettings,
    study: str = "hosted", protocol: Protocol | None = None,
) -> dict:
    """What a stored run must have been made under to count as one of this study's.

    ``protocol`` is required by the orchestrated and fidelity studies and unused
    by the hosted one. A fidelity case has no sizes and no middle agents; what
    it asks of the producer is part of its questions.

    The questions are part of it. A follow-up that was reworded, or a middle
    agent's rule that was changed, makes a different experiment of the same
    case name, and a run under the old wording must not count towards the new
    one — nor be overwritten: it is ignored and reported, as any mismatch is.
    """
    if isinstance(case, RoundsCase):
        # Every rule's text, so a reworded edit is a different experiment even
        # at the same depth, which ``agents`` and ``roles`` alone would not say.
        asked = [case.task.ask, *(revision.ask for revision in case.revisions)]
    elif isinstance(case, FidelityCase):
        asked = [case.task.ask]
    else:
        asked = [middle.query(case.task) for middle in case.middles]
    questions = hashlib.sha256("\0".join([
        case.follow_up.query, *asked,
        *(answer.description for answer in case.follow_up.answers),
    ]).encode()).hexdigest()[:16]
    # The pipeline study's runs were stored before there was a second study, so
    # its configuration carries no "study" key: adding one would unmatch every
    # run already on disk. The orchestrated study names itself, and also pins
    # the model's protocol (temperature, max_tokens, thinking) and the commit
    # its code ran from: a run made under another max_tokens, or by code since
    # changed, is a run of a different experiment and is ignored rather than
    # counted towards this one's repeats.
    if study == "hosted":
        configuration = {}
    elif protocol is None:
        raise ValueError(f"the {study} study's runs are keyed on a Protocol")
    else:
        configuration = {"study": study, "model": protocol.model, "code": protocol.commit}
    return configuration | {
        "channel": channel.name,
        "producer_paradigm": _producer_name(channel, study),
        "agents": case.agents,
        "roles": list(case.roles),
        "step_budget": settings.step_budget,
        **({"orchestrator_step_budget": settings.orchestrator_steps} if study == "rounds" else {}),
        "max_protocol_nudges": settings.max_protocol_nudges,
        "max_exec_output": settings.max_exec_output,
        **({"depth": case.depth} if isinstance(case, RoundsCase) else
           {"group": case.task.group} if isinstance(case, FidelityCase) else
           {"size": case.size.label}),
        "task": case.task.name,
        "questions": questions,
    }


@dataclass(frozen=True)
class Protocol:
    """What the orchestrated study's resume key pins besides the case and the arm.

    The model's settings that make two runs comparable, and the commit the code
    ran from; read once when an arm starts, so every run of one invocation is
    keyed alike even if the tree changes while it runs.
    """

    model: dict
    commit: str | None

    @classmethod
    def of(cls, cfg, begun_at: str | None = None) -> Protocol:
        public = _public_model(cfg)
        return cls(
            model={key: public.get(key) for key in ("model_id", "temperature", "max_tokens", "thinking")},
            commit=_study_commit(begun_at),
        )


# What decides how a run behaves: the agents, prompts, cases and judges, the
# settings module, and the pinned dependencies. The driver is not among them.
_RUN_DETERMINING_PATHS = ("core", "cases", "config.py", "pyproject.toml", "uv.lock")


def _study_commit(begun_at: str | None) -> str | None:
    """The commit a study's runs are keyed on: HEAD, or the one it was begun at.

    A study keyed on HEAD alone is orphaned by any commit made while it runs —
    a one-line change to a log message left sixty-seven stored runs ignored. So
    a study may be continued under the commit it began at, but only when nothing
    that determines a run has changed since; otherwise the runs would not be
    runs of one experiment, and this refuses.
    """
    head = code_fingerprint()["commit"]
    if begun_at is None:
        return head
    root = Path(__file__).resolve().parent.parent
    begun = subprocess.run(
        ["git", "-C", str(root), "rev-parse", begun_at], capture_output=True, text=True, check=True,
    ).stdout.strip()
    changed = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", begun, "HEAD", "--", *_RUN_DETERMINING_PATHS],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    dirty = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no", "--",
         *_RUN_DETERMINING_PATHS],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    if changed or dirty:
        raise SystemExit(
            f"cannot continue the study begun at {begun[:7]}: changed since: {sorted(set(changed + dirty))}"
        )
    return begun


def _producer_name(channel, study: str) -> str:
    """The paradigm the first agent runs under, in either study."""
    if study in ("orchestrated", "fidelity", "rounds"):
        return PRODUCER[channel.medium].name
    return channel.producer.name


def case_directory(experiment_dir: Path, case_name: str, api_model: str) -> Path:
    return (
        experiment_dir / RUNS_DIR / sanitize_component(case_name)
        / sanitize_component(api_model)
    )


def stored_runs(
    experiment_dir: Path, case: PipelineCase, api_model: str, configuration: dict,
) -> int:
    """How many stored runs of this case were made under this configuration.

    A run under another configuration is neither counted nor touched: it is
    someone else's study, and the mismatch is reported so it is not silent.
    """
    directory = case_directory(experiment_dir, case.name, api_model)
    matching = 0
    for path in directory.glob(f"*/{PIPELINE_FILE}"):
        try:
            stored = json.loads(path.read_text()).get("settings", {})
        except (OSError, json.JSONDecodeError):
            continue
        if stored == configuration:
            matching += 1
        else:
            differing = sorted(k for k in configuration if stored.get(k) != configuration[k])
            print(f"IGNORE {path.parent.name} for {case.name}: differs in {differing}", flush=True)
    return matching


def cases_short_of(
    cases: list[PipelineCase], experiment_dir: Path, api_model: str, repeats: int,
    channel, settings: PipelineSettings, study: str = "hosted",
    protocol: Protocol | None = None,
) -> list[PipelineCase]:
    return [
        case for case in cases
        if stored_runs(
            experiment_dir, case, api_model,
            run_configuration(case, channel, settings, study, protocol),
        ) < repeats
    ]


def _public_model(cfg) -> dict:
    if hasattr(cfg, "public_fingerprint"):
        return cfg.public_fingerprint()
    return {"name": cfg.name, "model_id": cfg.api_model, "base_url": cfg.base_url}


async def _run_and_write(
    model, cfg, case: PipelineCase, channel, settings: PipelineSettings,
    experiment_dir: Path, run_id: str, study: str = "hosted",
    protocol: Protocol | None = None,
) -> bool:
    """Run one case under one channel or medium and store it. Returns the verdict."""
    # A worker's Parquet output lives here and is read by the next agent while
    # the directory exists, so it is removed only once the whole run is over.
    with tempfile.TemporaryDirectory(prefix="cave-bench-pipeline-") as workdir:
        run = {"hosted": run_hosted, "orchestrated": run_orchestration,
               "rounds": run_rounds}[study]
        try:
            result = await asyncio.wait_for(
                run(model, case, channel, settings, Path(workdir)), PIPELINE_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            result = None
    path = case_directory(experiment_dir, case.name, cfg.api_model) / run_id / PIPELINE_FILE
    stamp = {
        "schema": PIPELINE_SCHEMA, "written_at": utc_now(), "model": _public_model(cfg),
        "code": code_fingerprint(),
        "settings": run_configuration(case, channel, settings, study, protocol),
    }
    if result is None:
        atomic_write_json(path, {
            **stamp, "case": case.name, "channel": channel.name, "success": False,
            "timed_out": True, "timeout_s": PIPELINE_TIMEOUT_S,
        })
        print(f"TIMEOUT {case.name} after {PIPELINE_TIMEOUT_S // 60} minutes; stored as failed", flush=True)
        return False
    # One transcript per agent, written before the record that cites them, so a
    # crash can only leave an unreferenced transcript and never a dangling cite.
    record = result.as_dict()
    transcripts = path.parent / "transcripts"
    if study != "hosted":
        write_transcript(transcripts / "orchestrator.jsonl", record["orchestrator"].pop("messages"))
        record["orchestrator"]["transcript"] = "transcripts/orchestrator.jsonl"
        for worker in record["workers"]:
            write_transcript(transcripts / f"{worker['name']}.jsonl", worker.pop("messages"))
            worker["transcript"] = f"transcripts/{worker['name']}.jsonl"
    else:
        for index, stage in enumerate(result.stages):
            name = f"stage{index}_{stage.role}"
            write_transcript(transcripts / f"{name}.jsonl", stage.messages)
            record["stages"][index]["transcript"] = f"transcripts/{name}.jsonl"
    atomic_write_json(path, {**stamp, **record})
    return result.success


async def _wait_for_endpoint(model) -> None:
    """Block until the model's endpoint answers, or give up after an hour.

    A pipeline's attempts are for a case that fails on its own; an endpoint
    that is down fails every case, and should cost none of them anything.
    """
    import httpx

    base = getattr(model, "base_url", None) or getattr(model, "kwargs", {}).get("base_url")
    if not base:
        return
    url = str(base).rstrip("/") + "/models"
    waited = 0
    while waited < OUTAGE_GIVE_UP_SECONDS:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if (await client.get(url)).status_code < 500:
                    return
        except Exception:
            pass
        if waited == 0:
            print(f"OUTAGE endpoint {url} not answering; pausing until it does", flush=True)
        await asyncio.sleep(OUTAGE_PROBE_SECONDS)
        waited += OUTAGE_PROBE_SECONDS
    raise SystemExit(f"endpoint {url} did not come back within {OUTAGE_GIVE_UP_SECONDS}s")


async def run_channel(
    model, cfg, cases: list[PipelineCase], channel, settings: PipelineSettings,
    experiment_dir: Path, concurrency: int, repeats: int, study: str = "hosted",
    begun_at: str | None = None,
) -> dict:
    """Bring every case up to ``repeats`` stored runs, one pass at a time.

    A pass asks only for the cases still short of that pass's count, so a case
    whose run was abandoned is picked up by the next pass rather than repeated
    immediately — which would spend the attempts on whichever case is unwell
    while the rest of the study waits.
    """
    totals = {"run": 0, "passed": 0, "abandoned": 0}
    protocol = Protocol.of(cfg, begun_at)
    for wanted in range(1, repeats + 1):
        pending = deque(
            (case, 0) for case in cases_short_of(
                cases, experiment_dir, cfg.api_model, wanted, channel, settings, study, protocol,
            )
        )
        running: dict[asyncio.Task, tuple[PipelineCase, int]] = {}
        while pending or running:
            while pending and len(running) < concurrency:
                case, attempts = pending.popleft()
                task = asyncio.create_task(_run_and_write(
                    model, cfg, case, channel, settings, experiment_dir, new_run_id(), study,
                    protocol,
                ))
                running[task] = (case, attempts)
                print(
                    f"START {case.name} channel={channel.name} attempt={attempts + 1} "
                    f"active={len(running)} pending={len(pending)}",
                    flush=True,
                )
            done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                case, attempts = running.pop(task)
                try:
                    success = task.result()
                except BenchmarkSpecificationError:
                    # A defect in the case reproduces on every attempt. Stop and
                    # let the traceback name the case that has to be fixed.
                    for other in running:
                        other.cancel()
                    raise
                except InfrastructureError as error:
                    connection_refused = "Connect call failed" in str(error) or \
                        "Connection error" in str(error)
                    if connection_refused:
                        # Not this case's fault, nor any other running case's:
                        # put them all back unchanged — the one that reported it
                        # and every one still in flight or finishing in this
                        # batch — and wait for the endpoint before starting
                        # anything else.
                        pending.appendleft((case, attempts))
                        unfinished = [other for other in running if not other.done()]
                        for other in unfinished:
                            other.cancel()
                            pending.appendleft(running.pop(other))
                        await asyncio.gather(*unfinished, return_exceptions=True)
                        # A task that had already finished keeps its result; the
                        # next wait returns it at once.
                        await _wait_for_endpoint(model)
                        break
                    if attempts + 1 < MAX_ATTEMPTS:
                        pending.append((case, attempts + 1))
                        print(f"RETRY {case.name} after {type(error).__name__}: "
                              f"{str(error)[:160]}", flush=True)
                    else:
                        totals["abandoned"] += 1
                        print(f"ABANDON {case.name} after {MAX_ATTEMPTS} attempts: {error}",
                              flush=True)
                    continue
                totals["run"] += 1
                totals["passed"] += bool(success)
                print(
                    f"DONE {case.name} {'PASS' if success else 'FAIL'} "
                    f"completed={totals['run']} active={len(running)}",
                    flush=True,
                )
        print(f"PASS {wanted}/{repeats} complete for channel {channel.name}", flush=True)
    return totals


def _selected(
    study: str, pipeline: str, agents: int, case_names: list[str] | None,
    sizes: list[str] | None,
) -> list[PipelineCase | FidelityCase]:
    if study == "rounds":
        available = ROUNDS_CASES
    else:
        available = PIPELINE_CASES if pipeline == "main" else depth_cases(agents)
    by_name = cases_by_name(available)
    if case_names:
        unknown = sorted(set(case_names) - set(by_name))
        if unknown:
            raise SystemExit(f"unknown pipeline case(s): {unknown}")
        chosen = [by_name[name] for name in case_names]
    else:
        chosen = list(available)
    if sizes and study == "rounds":
        raise SystemExit(f"the {study} cases have no sizes")
    if sizes:
        chosen = [case for case in chosen if case.size.label in set(sizes)]
        if not chosen:
            raise SystemExit(f"no pipeline case is asked at size(s) {sizes}")
    return chosen


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--study", choices=("hosted", "orchestrated", "rounds"), default="hosted",
        help="hosted: the host runs the pipeline and moves each table. orchestrated: "
             "an orchestrator agent directs the workers itself; --channel is the medium. "
             "rounds: "
             "one object handed on and edited several times (cases/rounds).",
    )
    parser.add_argument(
        "--channel", required=True,
        help="hosted: a channel from core/pipeline.py. orchestrated: a medium from "
             "core/orchestration.py (cave, text, json, file).",
    )
    parser.add_argument(
        "--pipeline", choices=("main", "depth"), default="main",
        help="main: retriever, narrower, analyst over every task. depth: the probe, "
             "with relays in between and --agents deciding how many.",
    )
    parser.add_argument(
        "--agents", type=int, default=3,
        help=f"Agents in the pipeline; the depth probe uses {list(DEPTH_AGENTS)}. "
             "Ignored by --pipeline main, which is always three.",
    )
    parser.add_argument("--case", nargs="*", dest="case_names")
    parser.add_argument(
        "--size", nargs="*", dest="sizes",
        help="Limit to these delivery volumes, e.g. --size 10 100.",
    )
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument(
        "--repeats", type=int, default=1,
        help="Runs each case should end with; cases already at that many are skipped.",
    )
    parser.add_argument(
        "--step-budget", type=int, default=14,
        help="Maximum steps per agent, the same for both; default: 14.",
    )
    parser.add_argument(
        "--orchestrator-step-budget", type=int, default=None,
        help="The orchestrator's own step budget (rounds study); default: the workers'.",
    )
    parser.add_argument("--protocol-nudges", type=int, choices=(0, 1, 2), default=1)
    parser.add_argument(
        "--max-exec-output", type=int, default=100000,
        help="Characters of execution output shown to an agent per step; default: 100000.",
    )
    parser.add_argument("--experiment", required=True, help="Study id under experiments/.")
    parser.add_argument(
        "--begun-at", metavar="COMMIT",
        help="Continue an orchestrated study begun at this commit. Refused if anything "
             "that determines a run (core/, cases/, config, dependencies) changed since.",
    )
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 32:
        raise SystemExit("concurrency must be between 1 and 32")
    if not 1 <= args.repeats <= 10:
        raise SystemExit("repeats must be between 1 and 10")

    cases = _selected(args.study, args.pipeline, args.agents, args.case_names, args.sizes)
    arms = CHANNELS if args.study == "hosted" else ORCHESTRATION_ARMS
    if args.channel not in arms:
        raise SystemExit(f"--channel must be one of {sorted(arms)} for --study {args.study}")
    channel = arms[args.channel]
    settings = PipelineSettings(
        step_budget=args.step_budget,
        max_protocol_nudges=args.protocol_nudges,
        max_exec_output=args.max_exec_output,
        orchestrator_step_budget=args.orchestrator_step_budget,
    )
    model, cfg = load_model(MODELS_TOML, args.model)
    experiment_dir = EXPERIMENTS_DIR / sanitize_component(args.experiment)
    if args.study != "hosted" and args.protocol_nudges:
        # An orchestrated study has no host between a worker and its judge to
        # nudge a turn that ran no code; a recorded nudge count would be a
        # setting nothing applied.
        raise SystemExit(f"--study {args.study} applies no protocol nudges; pass --protocol-nudges 0")
    started = datetime.now()
    print(
        f"EXPERIMENT {experiment_dir} STUDY {args.study} CHANNEL {channel.name} "
        f"MODEL {cfg.api_model} PIPELINE {args.pipeline} AGENTS {cases[0].agents} "
        f"CASES {len(cases)} REPEATS {args.repeats}",
        flush=True,
    )
    totals = await run_channel(
        model, cfg, cases, channel, settings, experiment_dir,
        args.concurrency, args.repeats, args.study, args.begun_at,
    )
    elapsed = (datetime.now() - started).total_seconds()
    print(
        f"SUMMARY {totals} elapsed={elapsed:.0f}s "
        f"end_to_end={totals['passed']}/{max(totals['run'], 1)}",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
