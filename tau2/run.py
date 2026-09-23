"""Run a tau2 domain with CaveAgent or with tau2's own function-calling baseline.

Keys come from the environment, never from a file or the command line.
TAU2_API_KEY reaches litellm through the environment too — tau2 copies llm_args
verbatim into its result file, so a key passed that way lands on disk. When the
agent sits on a different gateway from the user simulator, its key comes from
TAU2_AGENT_API_KEY and has to travel in llm_args; the redaction below scrubs it
once the run ends.

    TAU2_API_KEY=... uv run python run.py --domain telecom --num-tasks 2 \
        --model deepseek-v4-flash --base-url https://host/v1 --thinking disabled

Results land in results/<timestamp>_<domain>_<agent>_<model>.json, in tau2's own
simulation format.
"""

import argparse
import datetime
import json
import os
import signal
from pathlib import Path

# Importing tau2_cave first points tau2 at the right data directory.
import tau2_cave
import tau2_json_exec
from missing import missing_tasks
from tau2_cave import gemini
from redact import redact_api_key
from tau2.data_model.simulation import RunConfig
from tau2.run import run_domain

DEFAULT_SEED = 300          # tau2's own default, kept for run 1

# The arms whose action is Python run in a persistent runtime. They differ from
# each other only in how that code crosses the boundary — a fenced block or an
# execute_python call — and from llm_agent in having a runtime at all. Both build
# the model through cave-agent's LiteLLMModel, which takes a bare model id and
# the provider separately, where tau2's own agent wants "provider/model".
CODE_ARMS = {"cave_agent": tau2_cave, "json_exec_agent": tau2_json_exec}
ROOT = tau2_cave.ROOT
DATA_DIR = tau2_cave.DATA_DIR
RESULTS = ROOT / "results"


def file_slug(model: str) -> str:
    """A model id that can appear in a filename.

    Gateways name models with a vendor prefix — deepseek/deepseek-v3.2,
    moonshotai/kimi-k3 — and the slash would turn a result file into a path
    into a directory that does not exist.
    """
    return model.replace("/", "-")


# litellm providers this runner configures: OpenAI-compatible gateways, and
# Gemini's native API through tau2_cave.gemini.
THINKING_MODES = {"openai": ("enabled", "disabled"), gemini.PROVIDER: ("low", "medium", "high")}


def thinking_args(provider: str, mode: str) -> dict:
    """The request fields that set a model's reasoning.

    Stated on every request rather than left to the model: defaults differ from
    one model to the next — qwen3.8-flash reasons unless told not to,
    deepseek-v3.2 does not — and from one gateway to another. OpenAI-compatible
    gateways take an on/off switch; Gemini 3 always reasons and takes a level.
    """
    if mode not in THINKING_MODES[provider]:
        raise ValueError(f"thinking '{mode}' is not available on {provider}; "
                         f"choose from {', '.join(THINKING_MODES[provider])}")
    if provider == gemini.PROVIDER:
        # litellm withholds OpenAI parameters from a custom provider unless allowed.
        return {"reasoning_effort": mode, "allowed_openai_params": ["reasoning_effort"]}
    return {"extra_body": {"thinking": {"type": mode}}}


def number_simulations(path: Path, run: int, trials: int) -> None:
    """Record which run a sweep is, in the field tau2 already has for repeats.

    tau2 numbers repeats within one sweep as `trial`, starting at 0. Separate
    sweeps all start at 0 again, so run 2 would be indistinguishable from run 1
    once the files sit side by side — or worse, collide when merged. Shifting a
    sweep's trials by its run index keeps them apart and leaves a merged file
    looking exactly like a single sweep of the same size, which is what tau2's
    pass^k reads.
    """
    if run == 1:
        return
    results = json.loads(path.read_text())
    for simulation in results["simulations"]:
        simulation["trial"] += (run - 1) * trials
    path.write_text(json.dumps(results, indent=2))


def _exit_on_sigterm(signum, frame) -> None:
    """Turn SIGTERM into an exception, so cleanup runs when a run is stopped.

    Python's default for SIGTERM ends the process without unwinding, which skips
    the redaction below; stopping a sweep sends exactly that signal.
    """
    raise SystemExit(128 + signum)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--domain", default="telecom", help="tau2 domain (default: telecom)")
    parser.add_argument("--agent",
                        choices=["cave_agent", "json_exec_agent", "llm_agent"],
                        default="cave_agent",
                        help="cave_agent (fenced Python in a persistent runtime), "
                             "json_exec_agent (the same runtime, reached by an "
                             "execute_python JSON call) or llm_agent (tau2's own JSON "
                             "function calling, no runtime)")
    parser.add_argument("--model", required=True,
                        help="model id; names the results file and, unless --api-model "
                             "says otherwise, the model requested")
    parser.add_argument("--api-model", default=None,
                        help="the name the endpoint serves --model under, when it has its own")
    parser.add_argument("--base-url", default=None,
                        help="custom endpoint for both agent and user")
    parser.add_argument("--thinking", required=True,
                        choices=sorted({m for modes in THINKING_MODES.values() for m in modes}),
                        help="the agent's reasoning: enabled/disabled on OpenAI-compatible "
                             "gateways, low/medium/high on genai (Gemini); required, since "
                             "models disagree on the default")
    parser.add_argument("--user-thinking", default=None,
                        help="the user simulator's reasoning (default: --thinking)")
    parser.add_argument("--provider", choices=sorted(THINKING_MODES), default="openai",
                        help="litellm provider for the agent's model (default: openai)")
    parser.add_argument("--user-provider", choices=sorted(THINKING_MODES), default=None,
                        help="litellm provider for the user simulator (default: --provider)")
    parser.add_argument("--user-model", default=None,
                        help="user simulator model (default: --model). Hold it fixed across "
                             "a comparison: the simulator decides how hard the domain is")
    parser.add_argument("--user-base-url", default=None,
                        help="endpoint for the user simulator (default: --base-url)")
    parser.add_argument("--tasks", nargs="+", default=None,
                        help="task ids to run (default: the whole split)")
    parser.add_argument("--num-tasks", type=int, default=None,
                        help="run only the first N tasks of the split")
    parser.add_argument("--resume", type=Path, default=None,
                        help="run only the tasks missing from this results file, "
                             "for a sweep the gateway cut short; merge.py folds the two together")
    parser.add_argument("--task-split", default="base",
                        help="task split: base (the benchmark's 114 telecom tasks), "
                             "small, test, train or full (default: base)")
    parser.add_argument("--trials", type=int, default=1,
                        help="repeats within this one sweep, as tau2 counts them")
    parser.add_argument("--run", type=int, default=1,
                        help="which run of a repeated experiment this is (n>1); "
                             "names the file and numbers its simulations")
    parser.add_argument("--seed", type=int, default=None,
                        help="tau2's base seed (default: 300 + run - 1, so repeated runs "
                             "of one experiment do not sample identically)")
    parser.add_argument("--temperature", type=float, default=0.2,
                        help="agent sampling temperature (default: 0.2)")
    parser.add_argument("--user-temperature", type=float, default=0.0,
                        help="user simulator temperature (default: 0.0, as tau2 ships)")
    parser.add_argument("--max-steps", type=int, default=200,
                        help="orchestrator step budget (tau2's own default)")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--request-timeout", type=float, default=300,
                        help="seconds before one model request is abandoned and retried "
                             "(default: 300; litellm's own default is 6000)")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, _exit_on_sigterm)

    # The user simulator's key goes through <PROVIDER>_API_KEY, which litellm
    # falls back to, so it never enters llm_args nor the result file.
    api_key = os.environ["TAU2_API_KEY"]
    user_provider = args.user_provider or args.provider
    try:
        agent_thinking = thinking_args(args.provider, args.thinking)
        user_thinking = thinking_args(user_provider, args.user_thinking or args.thinking)
    except ValueError as error:
        parser.error(str(error))
    if gemini.PROVIDER in (args.provider, user_provider):
        gemini.register()
    os.environ[f"{user_provider.upper()}_API_KEY"] = api_key
    os.environ[f"{args.provider.upper()}_API_KEY"] = api_key
    agent_key = os.environ.get("TAU2_AGENT_API_KEY", api_key)
    user_model = args.user_model or args.model
    # litellm waits 100 minutes on a stalled request by default, and a stall is
    # not an error its retries act on — one hung call held a sweep for 55
    # minutes. The same bound goes to agent and simulator, both paradigms.
    llm_args = {"temperature": args.temperature, "timeout": args.request_timeout,
                **agent_thinking}
    if args.base_url:
        llm_args["base_url"] = args.base_url
    # The user simulator is configured apart from the agent: it is the other half
    # of the experiment, held fixed while the agent under test changes.
    user_args = {"temperature": args.user_temperature, "timeout": args.request_timeout,
                 **user_thinking}
    if args.user_base_url or args.base_url:
        user_args["base_url"] = args.user_base_url or args.base_url

    if agent_key != api_key:
        # A second gateway needs its own key, and only llm_args reaches the
        # agent's call. It is redacted from the result file after the run.
        llm_args["api_key"] = agent_key

    requested_model = args.api_model or args.model
    if args.agent in CODE_ARMS:
        CODE_ARMS[args.agent].register()
        agent_model = requested_model            # cave-agent's LiteLLMModel takes the bare id
        llm_args["custom_llm_provider"] = args.provider
    else:
        agent_model = f"{args.provider}/{requested_model}"

    task_ids = args.tasks
    if args.resume:
        task_ids = missing_tasks(args.resume, args.domain, args.task_split)
        if not task_ids:
            print(f"{args.resume.name} is already complete")
            return
        print(f"resuming {args.resume.name}: {len(task_ids)} task(s) left")

    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    name = f"{stamp}_{args.domain}_{args.agent}_{file_slug(args.model)}_run{args.run}"

    config = RunConfig(
        domain=args.domain,
        task_split_name=args.task_split,
        task_ids=task_ids,
        num_tasks=args.num_tasks,
        agent=args.agent,
        llm_agent=agent_model,
        llm_args_agent=llm_args,
        user="user_simulator",
        llm_user=f"{user_provider}/{user_model}",
        llm_args_user=user_args,
        num_trials=args.trials,
        # tau2 derives each trial's LLM seed from this one. Runs launched as
        # separate processes would otherwise all derive the same seed from the
        # same default and, on a gateway that honours `seed`, repeat themselves.
        seed=args.seed if args.seed is not None else DEFAULT_SEED + args.run - 1,
        max_steps=args.max_steps,
        max_errors=10,
        # tau2 resolves save_to under DATA_DIR/simulations; point it back here
        save_to=os.path.relpath(RESULTS / name, DATA_DIR / "simulations"),
        max_concurrency=args.concurrency,
        log_level="INFO",
        enforce_communication_protocol=False,
    )
    out = RESULTS / f"{name}.json"
    try:
        results = run_domain(config)
    finally:
        # Even a run that dies partway leaves a file behind; scrub it either way.
        if out.exists():
            redact_api_key(out)
            number_simulations(out, args.run, args.trials)
    solved = sum(
        1 for simulation in results.simulations
        if simulation.reward_info and simulation.reward_info.reward == 1
    )
    total = len(results.simulations)
    print(f"\n{args.agent} on {args.domain}: {solved}/{total} solved "
          f"({100 * solved / total:.1f}%) -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
