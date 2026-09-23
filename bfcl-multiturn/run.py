"""Run one paradigm over BFCL's stateful multi-turn subset.

    BFCL_API_KEY=<key> uv run python run.py --arm cave --model qwen3.8-flash \
        --base-url "$GATEWAY/v1" --run 1

One task is one conversation: the arm is given the task's own API instances and
its user messages in order, and the calls it made are scored by the benchmark
against the state its ground truth reaches. Results stream to
``results/<arm>_<model>_run<n>.json`` as each task finishes, so an interrupted
run keeps what it had and a rerun skips what is already there.

A task that raises is recorded as an error rather than as a failure, and does not
stop the run: a provider outage and a wrong answer must not look alike when the
numbers are read. A task that stops making progress is given ``--task-timeout``
and then recorded the same way -- litellm retries a gateway error inside its own
call, so without a deadline one task can hold a run open indefinitely, and a
campaign waiting on that run stalls with it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path

from cave_agent import LiteLLMModel

from bfcl_multiturn import arms, benchmark, results
from bfcl_multiturn.fidelity import unrecorded_change

RESULTS = Path(__file__).resolve().parent / "results"


def settings_for(options) -> arms.Settings:
    key = os.environ.get("BFCL_API_KEY")
    if not key:
        raise SystemExit("BFCL_API_KEY is not set")
    extra = {} if options.thinking == "unset" else {"thinking": {"type": options.thinking}}
    return arms.Settings(model_id=options.api_model or options.model, provider=options.provider,
                         base_url=options.base_url, api_key=key,
                         temperature=options.temperature, extra_body=extra)


def build(kind: str, task: benchmark.Task, options):
    """One arm, over one task's own instances, and those instances."""
    instances = benchmark.instantiate(task)
    methods = benchmark.methods(instances)
    if kind == "cave":
        settings = settings_for(options)
        # cave-agent's model takes the bare id and is told the provider separately.
        model = LiteLLMModel(model_id=settings.model_id, base_url=settings.base_url,
                             api_key=settings.api_key, temperature=settings.temperature,
                             custom_llm_provider=settings.provider,
                             **({"extra_body": settings.extra_body} if settings.extra_body else {}))
        return arms.CaveArm(model=model, methods=methods, max_steps=options.max_steps), instances
    arm = arms.FunctionCallingArm(settings=settings_for(options), methods=methods,
                                  tool_documents=benchmark.tool_documents(task),
                                  max_steps=options.max_steps)
    return arm, instances


async def one_task(task: benchmark.Task, options) -> dict:
    """A whole conversation, and the benchmark's verdict on it."""
    started = time.monotonic()
    arm, instances = build(options.arm, task, options)
    tag = benchmark.tag(options.arm, f"run{options.run}", task.id)
    turns, calls_per_turn = [], []
    for index, messages in enumerate(task.turns):
        # A turn's messages are the user's; the benchmark ships them as a list,
        # which is one message for every task of this subset.
        result = await arm.turn("\n".join(messages))
        turn = {"turn": index, "reply": result.reply, "stop_reason": result.stop_reason,
                "model_steps": result.model_steps, "calls": result.steps}
        if result.repaired:
            turn["repaired"] = True
        if result.code:
            turn["code"] = list(result.code)
        turns.append(turn)
        calls_per_turn.append(result.steps or [[]])

    # Whether the record accounts for the state the agent actually reached. A
    # verdict on a record that does not is a verdict on the wrong trajectory, so
    # it is reported rather than scored.
    missed = unrecorded_change(task, instances, calls_per_turn, tag)

    verdict = benchmark.score(task, calls_per_turn, tag)
    row = {"id": task.id, "valid": verdict["valid"], "error_type": verdict.get("error_type"),
           "turns": turns, "elapsed": round(time.monotonic() - started, 1),
           "involved_classes": list(task.involved_classes)}
    if missed:
        row["unrecorded_change"] = missed
    return row


def already_scored(path: Path) -> dict[str, dict]:
    """The tasks a rerun should keep, from a file it is resuming.

    A task that errored is not a result -- the gateway refused it or dropped the
    connection, which says nothing about the paradigm -- so it is left out and
    run again. A task that was scored is kept whether it passed or failed.
    """
    if not path.exists():
        return {}
    return {row["id"]: row for row in results.read(path)["tasks"]
            if row.get("error") is None}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", choices=sorted(arms.ARMS), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--provider", default="openai",
                        help="litellm provider for the endpoint; the gateways speak OpenAI's API, "
                             "and 'genai' reaches Gemini through its own SDK")
    parser.add_argument("--api-model",
                        help="the id the endpoint serves, when it differs from the paper's label "
                             "(deepseek-v4-flash is deployed as deepseek-v4-flash-0731)")
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--thinking", choices=("disabled", "enabled", "unset"), required=True,
                        help="stated on every request; 'unset' sends nothing")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--task-timeout", type=float, default=900,
                        help="seconds one task may take before it is recorded as timed out; "
                             "0 waits forever")
    parser.add_argument("--limit", type=int, help="first N tasks, for a smoke run")
    parser.add_argument("--out", type=Path)
    options = parser.parse_args()

    if options.provider == "genai":
        # Imported here, and only for this provider: registering rewrites
        # litellm's provider map, which nothing else in a run should touch.
        from bfcl_multiturn import gemini

        gemini.register()

    name = options.out or RESULTS / f"{options.arm}_{options.model.replace('/', '-')}_run{options.run}.json"
    name.parent.mkdir(parents=True, exist_ok=True)
    done = already_scored(name)
    if done:
        retrying = len(json.loads(name.read_text())["tasks"]) - len(done)
        print(f"{len(done)} task(s) already scored in {name.name}"
              + (f", {retrying} errored and will be retried" if retrying else ""), file=sys.stderr)

    todo = [task for task in benchmark.tasks()[:options.limit] if task.id not in done]
    print(f"{len(todo)} task(s) to run, {options.concurrency} at a time", file=sys.stderr)

    # SIGTERM has to leave the file valid, so it raises rather than killing the
    # process between a task finishing and its result being written.
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))

    header = {"arm": options.arm, "model": options.model, "run": options.run,
              "api_model": options.api_model or options.model,
              "base_url": options.base_url, "provider": options.provider,
              "temperature": options.temperature,
              "thinking": options.thinking, "max_steps": options.max_steps,
              "category": benchmark.CATEGORY}
    limit = asyncio.Semaphore(options.concurrency)
    collected = dict(done)

    def save() -> None:
        ordered = [collected[task.id] for task in benchmark.tasks() if task.id in collected]
        scored = [row for row in ordered if row.get("error") is None]
        payload = {**header, "tasks": ordered}
        payload["solved"] = results.solved(payload)
        payload["scored"] = len(scored)
        payload["errored"] = len(ordered) - len(scored)
        payload["unaccounted"] = sum(1 for row in ordered if row.get("unrecorded_change"))
        name.write_text(json.dumps(payload, indent=1))

    async def guarded(task):
        async with limit:
            try:
                if options.task_timeout:
                    return await asyncio.wait_for(one_task(task, options),
                                                  timeout=options.task_timeout)
                return await one_task(task, options)
            except TimeoutError:
                # Not a wrong answer but an unfinished one, recorded so the run
                # can end and a rerun can try it again.
                return {"id": task.id, "valid": False,
                        "error": f"TimeoutError: no result within {options.task_timeout:.0f}s"}
            except Exception as error:      # an outage must not read as a wrong answer
                return {"id": task.id, "valid": False, "error": f"{type(error).__name__}: {error}"}

    try:
        for finished in asyncio.as_completed([guarded(task) for task in todo]):
            row = await finished
            collected[row["id"]] = row
            save()
            mark = "err" if row.get("error") else ("ok " if row["valid"] else "   ")
            note = row.get("error") or row.get("error_type") or ""
            if row.get("unrecorded_change"):
                note = f"UNACCOUNTED {row['unrecorded_change']}  {note}"
            print(f"  {mark} {row['id']}  {note}"[:130], file=sys.stderr)
    finally:
        save()
        scored = [row for row in collected.values() if row.get("error") is None]
        solved = sum(results.counts_as_solved(row) for row in scored)
        errored = len(collected) - len(scored)
        rate = f"{100 * solved / len(scored):.1f}%" if scored else "n/a"
        unaccounted = sum(1 for row in collected.values() if row.get("unrecorded_change"))
        print(f"\n{solved}/{len(scored)} = {rate}"
              + (f", {errored} errored" if errored else "")
              + (f", {unaccounted} counted as failed on an incomplete record" if unaccounted else "")
              + f" -> {name}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
