"""What a persistent runtime costs to start, to hold, and to hand objects across.

R3 #7 asks for the deployment costs a persistent interpreter brings — start-up,
latency, peak memory, throughput — and says token counts alone do not establish
efficiency. None of that needs a model: it is a property of the runtime and of
the channel a result crosses on, so this measures it directly and deterministically.

    uv run python -m scripts.measure_runtime_cost --out experiments/runtime_cost

Two runtimes are measured, because they are different deployments of the same
framework and the paper must not describe them as one:

* ``in_process`` (:class:`~cave_agent.runtime.IPythonRuntime`): the runtime runs
  in the host process, so an injected object is the host's own object.
* ``kernel`` (:class:`~cave_agent.runtime.IPyKernelRuntime`): the runtime is a
  subprocess, so a crash cannot take the host down and a runaway cell can really
  be interrupted — and every object that crosses is copied through dill.

Beside them two channels that carry a result without a runtime object, as the
delivery study's baselines do: a parquet file on disk, and JSON text of the kind
a reply block holds. Sizes are row counts of the same frame, so the four are
measured on identical data.

Each timing is the median of repeated trials after a warm-up, reported with the
spread; memory is the resident-set increase of the host process and of the
kernel subprocess where there is one. The machine's other load is the limit on
how finely these can be read, so the run records what else was running.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from contextlib import suppress
from itertools import count
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import psutil
from cave_agent.runtime import IPyKernelRuntime, IPythonRuntime
from cave_agent.runtime.primitives import Variable

from core.results import atomic_write_json, utc_now
from core.security import SECURITY_CHECKER


# The delivery study's own sizes, and one beyond them to show where the curve goes.
ROW_COUNTS = (10, 1_000, 10_000, 100_000)
TRIALS = 5
WARM_UPS = 1


def sample_frame(rows: int) -> pd.DataFrame:
    """A frame shaped like a delivered table: identifiers, text, integers, decimals."""
    return pd.DataFrame({
        "identifier": [f"{index:08d}" for index in range(rows)],
        "name": [f"Entity number {index}" for index in range(rows)],
        "count": range(rows),
        "ratio": [index / 7 for index in range(rows)],
    })


def _median_seconds(measure: Callable[[], Any]) -> dict:
    for _ in range(WARM_UPS):
        measure()
    timings = []
    for _ in range(TRIALS):
        started = time.perf_counter()
        measure()
        timings.append(time.perf_counter() - started)
    return {
        "median_ms": round(statistics.median(timings) * 1000, 3),
        "min_ms": round(min(timings) * 1000, 3),
        "max_ms": round(max(timings) * 1000, 3),
        "trials": TRIALS,
    }


async def _release(runtime) -> None:
    """Give a runtime back, where there is something to give back.

    Only the kernel runtime owns anything outside the process; the in-process one
    is reclaimed with its references. Calling stop() on it would raise, and
    swallowing that would leave this reading as if a teardown had happened.
    """
    stop = getattr(runtime, "stop", None)
    if stop is not None:
        with suppress(Exception):
            await stop()


def _rss_mb(process: psutil.Process) -> float:
    return round(process.memory_info().rss / 1024 / 1024, 1)


def _kernel_rss_mb(process: psutil.Process) -> float:
    return round(sum(child.memory_info().rss for child in process.children(recursive=True))
                 / 1024 / 1024, 1)


async def _start_up(make_runtime: Callable[[], Any]) -> dict:
    """Time from constructing a runtime to its first executed statement."""
    async def once():
        runtime = make_runtime()
        await runtime.execute("1")
        await _release(runtime)

    timings = []
    for _ in range(WARM_UPS + TRIALS):
        started = time.perf_counter()
        await once()
        timings.append(time.perf_counter() - started)
    warm = timings[WARM_UPS:]
    return {
        "median_ms": round(statistics.median(warm) * 1000, 3),
        "min_ms": round(min(warm) * 1000, 3),
        "max_ms": round(max(warm) * 1000, 3),
        "trials": TRIALS,
    }


async def _crossing(make_runtime, frame: pd.DataFrame, host: psutil.Process) -> dict:
    """Inject a frame, run one statement over it, and retrieve a frame back."""
    runtime = make_runtime()
    await runtime.execute("1")                       # pay start-up before timing

    # A name can be claimed once, so each trial hands the frame over under a
    # fresh one — which is also what a turn does when it delivers another table.
    names = count()

    def inject_once():
        runtime.inject_variable(Variable(f"table_{next(names)}", frame, "A delivered table."))

    # What one crossing costs in memory, measured around one crossing alone:
    # the timing loop below repeats it, so measuring across that loop would
    # report the cost of six tables as the cost of one.
    before_host, before_kernel = _rss_mb(host), _kernel_rss_mb(host)
    inject_once()
    held = {"host_rss_mb": round(_rss_mb(host) - before_host, 1),
            "kernel_rss_mb": round(_kernel_rss_mb(host) - before_kernel, 1)}

    inject = await asyncio.to_thread(_median_seconds, inject_once)
    held_name = f"table_{next(names) - 1}"
    step = await _timed_await(lambda: runtime.execute(f"rows = len({held_name})"))
    retrieve = await _timed_await(lambda: runtime.retrieve(held_name))
    round_trip = await _timed_await(
        lambda: runtime.execute(f"total = {held_name}['count'].sum()"))

    await _release(runtime)
    return {"inject": inject, "execute_over_it": step, "retrieve": retrieve,
            "compute": round_trip, "resident_increase_one_table": held}


async def _timed_await(call: Callable[[], Any]) -> dict:
    for _ in range(WARM_UPS):
        await call()
    timings = []
    for _ in range(TRIALS):
        started = time.perf_counter()
        await call()
        timings.append(time.perf_counter() - started)
    return {
        "median_ms": round(statistics.median(timings) * 1000, 3),
        "min_ms": round(min(timings) * 1000, 3),
        "max_ms": round(max(timings) * 1000, 3),
        "trials": TRIALS,
    }


def _file_channel(frame: pd.DataFrame, workdir: Path) -> dict:
    """What a parquet file costs to write and to read back."""
    path = workdir / "table.parquet"
    write = _median_seconds(lambda: frame.to_parquet(path, index=False))
    read = _median_seconds(lambda: pd.read_parquet(path))
    return {"write": write, "read": read, "bytes": path.stat().st_size}


def _text_channel(frame: pd.DataFrame) -> dict:
    """What the same table costs as the JSON a reply block would carry."""
    encode = _median_seconds(lambda: frame.to_json(orient="records"))
    payload = frame.to_json(orient="records")
    decode = _median_seconds(lambda: json.loads(payload))
    return {"encode": encode, "decode": decode, "bytes": len(payload.encode()),
            # A table crossing as text also costs context: at roughly four
            # characters per token, this is what the reply would spend.
            "approx_tokens": len(payload) // 4}


async def _throughput(make_runtime) -> dict:
    """Executions per second of a trivial statement, once the runtime is warm."""
    runtime = make_runtime()
    await runtime.execute("1")
    started = time.perf_counter()
    executions = 50
    for index in range(executions):
        await runtime.execute(f"x = {index}")
    elapsed = time.perf_counter() - started
    await _release(runtime)
    return {"executions": executions, "seconds": round(elapsed, 3),
            "per_second": round(executions / elapsed, 1)}


async def _growth(make_runtime, host: psutil.Process, turns: int = 20) -> dict:
    """Resident memory after each of many turns, to show what a session accrues."""
    runtime = make_runtime()
    await runtime.execute("1")
    baseline_host, baseline_kernel = _rss_mb(host), _kernel_rss_mb(host)
    frame = sample_frame(10_000)
    points = []
    for turn in range(1, turns + 1):
        runtime.inject_variable(Variable(f"table_{turn}", frame.copy(), "A turn's table."))
        await runtime.execute(f"kept_{turn} = table_{turn}['count'].sum()")
        if turn % 5 == 0:
            points.append({"turn": turn,
                           "host_rss_mb": _rss_mb(host) - baseline_host,
                           "kernel_rss_mb": _kernel_rss_mb(host) - baseline_kernel})
    await _release(runtime)
    return {"turns": turns, "table_rows": 10_000, "points": points}


def _runtime_makers():
    return {
        "in_process": lambda: IPythonRuntime(
            functions=[], variables=[], types=[], security_checker=SECURITY_CHECKER),
        "kernel": lambda: IPyKernelRuntime(
            functions=[], variables=[], types=[], security_checker=SECURITY_CHECKER),
    }


async def measure(workdir: Path) -> dict:
    host = psutil.Process(os.getpid())
    makers = _runtime_makers()
    report: dict = {
        "measured_at": utc_now(),
        "machine": {"cpu_count": os.cpu_count(),
                    "load_average": [round(value, 2) for value in os.getloadavg()],
                    "other_python_processes": sum(
                        1 for p in psutil.process_iter(["name"])
                        if p.info["name"] and "python" in p.info["name"])},
        "start_up": {}, "throughput": {}, "crossing": {}, "growth": {}, "channels": {},
    }
    for name, maker in makers.items():
        report["start_up"][name] = await _start_up(maker)
        report["throughput"][name] = await _throughput(maker)
        report["growth"][name] = await _growth(maker, host)

    for rows in ROW_COUNTS:
        frame = sample_frame(rows)
        by_channel = {name: await _crossing(maker, frame, host) for name, maker in makers.items()}
        by_channel["parquet_file"] = _file_channel(frame, workdir)
        by_channel["reply_json"] = _text_channel(frame)
        report["crossing"][str(rows)] = by_channel
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path, help="directory for the report")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = asyncio.run(measure(args.out))
    path = args.out / "runtime_cost.json"
    atomic_write_json(path, report)
    print(path)
    for rows, channels in report["crossing"].items():
        line = [f"{rows:>7} rows"]
        for name in ("in_process", "kernel"):
            crossing = channels[name]
            line.append(f"{name} inject {crossing['inject']['median_ms']:.2f}ms "
                        f"retrieve {crossing['retrieve']['median_ms']:.2f}ms")
        line.append(f"parquet {channels['parquet_file']['write']['median_ms']:.2f}ms")
        line.append(f"json {channels['reply_json']['encode']['median_ms']:.2f}ms "
                    f"(~{channels['reply_json']['approx_tokens']:,} tokens)")
        print(" | ".join(line))


if __name__ == "__main__":
    main()
