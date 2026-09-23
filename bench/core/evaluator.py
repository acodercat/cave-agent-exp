from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
import tempfile

from cave_agent import StopReason
from cave_agent.runtime import IPythonRuntime

from config import CASE_TAXONOMY_PATH
from core.agents import FencedCodeAgent, ToolCallAgent
from core.datastore import HANDLE_NAME, datastore_variable
from core.errors import BenchmarkSpecificationError, InfrastructureError
from core.paradigms import (
    CAVE, INJECTION_MODES, Action, DataAccess, Delivery, Paradigm, collect_outputs,
    publish_revision, table_paths,
)
from core.prompts import repair_nudge, system_instructions, turn_prompt
from core.results import (
    RESULT_SCHEMA, atomic_write_json, unserializable_outputs, utc_now,
)
from core.runtime_catalog import runtime_variables, select_runtime_tables
from core.security import SECURITY_CHECKER
from core.table_files import table_file_name
from core.transcripts import messages_of
from core.types import Conversation, Turn, conversations_of


@dataclass(frozen=True)
class RunSettings:
    """How a case is run. One study holds these fixed across its cases."""

    max_protocol_nudges: int = 0
    total_step_budget: int = 14
    injection: str = "lazy"
    paradigm: Paradigm = CAVE
    max_exec_output: int = 10000

    def __post_init__(self):
        if not 0 <= self.max_protocol_nudges <= 2:
            raise ValueError("max_protocol_nudges must be between 0 and 2")
        if self.total_step_budget < 1:
            raise ValueError("total_step_budget must be at least 1")
        if self.injection not in INJECTION_MODES:
            raise ValueError(
                f"injection must be one of {INJECTION_MODES}, got {self.injection!r}"
            )


@dataclass
class TurnResult:
    """One turn's trajectory and the verdict on the outputs it asked for."""

    turn: int
    query: str
    stores: list[str]
    success: bool
    failure_type: str | None
    response: str
    outputs: dict
    validation_message: str
    variables_not_set: bool
    steps: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    elapsed: float
    stop_reason: str
    executed_code: bool
    code_snippets: list[str]
    protocol_nudges: int
    protocol_repair: dict | None
    # Outputs the result file can only store as a repr. Post-hoc verification
    # refuses these instead of scoring the text a lossless run never saw.
    outputs_unserializable: list = field(default_factory=list)
    # What the agent loop did in the turn's first pass that its totals hide:
    # model calls whose usage the provider reported or the agent estimated,
    # replies resumed after an output cut, compactions; and what those calls
    # cost, recorded and estimated alike (see core.agents). The repair arm
    # records its own. Empty on older runs.
    loop_events: dict = field(default_factory=dict)
    spent: dict = field(default_factory=dict)
    # Why the first pass ended in a model error the conversation caused, when it
    # did: a reply still cut off at the output limit, or a history past the
    # context window. The turn is scored as it stands.
    stop_cause: str | None = None
    # Which registered tables the executed code named, and which it never did.
    # Diagnostic only: a turn is not failed for leaving a table untouched.
    tables_referenced: list = field(default_factory=list)
    tables_unreferenced: list = field(default_factory=list)
    # A digest of the storage contract the agent was shown for this turn's
    # outputs. The query guard in post-hoc verification exists because an answer
    # to a different question is not evidence about this validator; the same is
    # true of an answer to a different storage contract, and the Variable
    # description is where this suite puts precision, unit, format and any
    # closed token vocabulary. Empty on runs written before 2026-09-07, which
    # verification then scores as it always did.
    output_contract: str = ""


@dataclass
class ConversationResult:
    id: str
    turns: list[TurnResult]
    # Everything the conversation's agent did and spent, repair arms included:
    # the basis of a run's cost.
    loop_events: dict = field(default_factory=dict)
    spent: dict = field(default_factory=dict)
    transcript: str | None = None
    # Kept in memory until the runner writes the separate JSONL artefact.
    messages: list = field(default_factory=list, repr=False)


@dataclass
class CaseResult:
    name: str
    conversations: list[ConversationResult]

    @property
    def turns(self) -> list[TurnResult]:
        return [turn for item in self.conversations for turn in item.turns]

    def spent(self) -> dict:
        """Every model call the case made, repair arms included, summed over conversations."""
        return dict(_spent_by(self.conversations))

    def cost(self) -> dict:
        """Summed from the turns, so it can never disagree with them."""
        totals = {
            key: sum(getattr(turn, key) for turn in self.turns)
            for key in ("steps", "prompt_tokens", "completion_tokens",
                        "total_tokens", "elapsed")
        }
        return {"turns": len(self.turns), **totals}


def _spent_by(conversations: list[ConversationResult]) -> Counter:
    return sum((Counter(conversation.spent) for conversation in conversations), Counter())


class _ResolvedTurnRuntime:
    """Expose one awaited output snapshot through the validator interface.

    Cave runtime retrieval is asynchronous, while case validators are deliberately
    synchronous and are replayed later from stored outputs.  The evaluator already
    awaits every requested variable before validation, so validators must read that
    exact snapshot instead of starting a second, un-awaited live-runtime lookup.
    """

    def __init__(self, outputs: dict):
        self._outputs = outputs

    def retrieve(self, name: str):
        return self._outputs[name]


def referenced_names(code_snippets: list[str], names: list[str]) -> list[str]:
    """Which of the case's tables the executed code actually names.

    An agent that answers a two-source question after only ever naming one table
    either found a shortcut the case did not intend or was handed a source it
    does not need, and neither shows up in a pass/fail verdict. This is the
    FinBench form of a tool-call record: the tables reach the agent as
    DataFrames or files rather than callables, so what is worth recovering is
    which of them the code referred to — by variable, by the handle that loads
    it, or by its file.

    Read from the executed snippets, so it reports a *reference*, not a read: a
    name inside dead code counts, and a value reached some other way does not.
    That is weaker than interception but costs the run nothing and cannot change
    what the agent sees. Diagnostic only; no channel scores on it.
    """
    wanted = set(names)
    seen: set[str] = set()
    for snippet in code_snippets:
        try:
            tree = ast.parse(snippet)
        except SyntaxError:
            # The runtime rejected this block, but naming a table is still
            # evidence of intent, so fall back to a word-boundary scan.
            seen.update(
                name for name in wanted
                if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", snippet)
            )
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in wanted:
                seen.add(node.id)
            elif (table := _handle_argument(node)) in wanted:
                # Under lazy injection a table is named as the string argument
                # of datasets.load(...) or datasets.describe(...).
                seen.add(table)
            elif (table := _file_argument(node)) in wanted:
                # A table read from a file is named by its file's path. A bare
                # table name in any other string, or in a comment, is not a
                # reference.
                seen.add(table)
    return sorted(seen)


def _file_argument(node: ast.AST) -> str | None:
    """The table a string constant names as a file path, if it names one."""
    if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
        return None
    file_name = Path(node.value).name
    table = file_name.removesuffix(".parquet")
    return table if file_name == table_file_name(table) else None


def _handle_argument(node: ast.AST) -> str | None:
    """The table name a `datasets.load("...")`-style call names, if any."""
    if not (isinstance(node, ast.Call) and node.args and isinstance(node.func, ast.Attribute)):
        return None
    handle = node.func.value
    if not (isinstance(handle, ast.Name) and handle.id == HANDLE_NAME and node.func.attr in {"load", "describe"}):
        return None
    argument = node.args[0]
    return argument.value if isinstance(argument, ast.Constant) and isinstance(argument.value, str) else None


def _validate(validator, case_name: str, response: str, runtime, turn: Turn):
    """Run a turn's validator, treating its own crash as a case defect.

    A validator that raises is broken benchmark code, not a model failure and
    not an outage: retrying pays for another model call and reproduces it.
    """
    try:
        verdict = validator(response, runtime, turn)
    except Exception as error:
        raise BenchmarkSpecificationError(
            f"{case_name}: validator raised {type(error).__name__}: {error}"
        ) from error
    if not (hasattr(verdict, "success") and hasattr(verdict, "variables_not_set")):
        raise BenchmarkSpecificationError(
            f"{case_name}: validator returned {type(verdict).__name__}, "
            f"not a ValidatorResult"
        )
    return verdict


def classify_failure(verdict, stop_reason: StopReason) -> str | None:
    """Classify a recorded model failure without turning it into a retry."""
    if verdict.success:
        return None
    if verdict.variables_not_set:
        return "variables_not_set"
    if stop_reason is not StopReason.COMPLETED:
        return stop_reason.value
    return "wrong_value"


def raise_if_infrastructure(result, agent) -> None:
    """Raise when a run ended in an error the conversation did not cause.

    A model error the conversation caused (``agent.stop_cause``) is the agent
    failing at the task and is scored; any other model or runtime error is an
    outage, and the attempt is retried.
    """
    if result.stop_reason is StopReason.RUNTIME_ERROR or (
        result.stop_reason is StopReason.MODEL_ERROR and agent.stop_cause is None
    ):
        raise InfrastructureError(f"agent stopped with {result.stop_reason.value}")


def _needs_protocol_repair(result, verdict, steps_used: int, total_step_budget: int) -> bool:
    """Whether a turn completed without running code, leaving its outputs unset.

    Such a turn is a missed turn, not a wrong answer: the model wrote its code in
    a form the runtime does not execute, so there is no result to judge. A
    function-calling baseline has the same slip caught by its provider, which
    rejects a malformed call; a code fence has no such check, so the repair
    stands in for it. A turn that ran code and still left an output unset has
    answered, and is scored as it stands.
    """
    return (
        verdict.variables_not_set
        and not result.code_snippets
        and result.stop_reason is StopReason.COMPLETED
        and steps_used < total_step_budget
    )


def load_specs(registry_path: Path) -> list[dict]:
    registry = json.loads(registry_path.read_text())
    if registry.get("schema_version") != 2 or not isinstance(registry.get("cases"), dict):
        raise ValueError(f"{registry_path}: expected case registry schema_version 2")
    specs = []
    for case_id, relative in registry["cases"].items():
        path = registry_path.parent / relative
        spec = json.loads(path.read_text())
        if spec.get("name") != case_id:
            raise ValueError(
                f"{path}: name={spec.get('name')!r}, registry case id={case_id!r}"
            )
        task_family = spec.get("task_family")
        if path.parent.name != task_family:
            raise ValueError(
                f"{path}: task_family={task_family!r}, directory={path.parent.name!r}"
            )
        if path.stem != case_id:
            raise ValueError(f"{path}: filename must equal case id {case_id!r}")
        spec["_path"] = str(path)
        specs.append(spec)
    taxonomy = json.loads(CASE_TAXONOMY_PATH.read_text())
    assignments = taxonomy.get("cases", {})
    for spec in specs:
        assignment = assignments.get(spec["name"])
        if not isinstance(assignment, dict):
            raise ValueError(
                f"{CASE_TAXONOMY_PATH}: missing assignment for {spec['name']}"
            )
        domains = assignment.get("financial_domains")
        if not isinstance(domains, list) or not domains:
            raise ValueError(
                f"{CASE_TAXONOMY_PATH}: invalid financial domains for {spec['name']}"
            )
        spec["financial_domains"] = list(domains)
        spec["source_mode"] = (
            "single" if len(set(spec["data_sources"])) == 1 else "multi"
        )
    return specs


def output_contract_fingerprint(module, stores) -> str:
    """Digest the storage contract this turn's outputs declare.

    Post-hoc verification compares this against the case as it stands now.
    Only the outputs the turn registers are digested, in the module's own
    variable order, so editing one turn's precision does not invalidate the
    stored answers of the turns around it.

    The description is the whole contract: this suite puts type, unit,
    precision, date format and any closed token vocabulary there and nowhere
    else, so a change to it changes what a correct answer looks like. Three
    commits in the first week of September 2026 did exactly that -- `25910d9`
    across 42 case modules, `9b41a87` and `1b6b87b` on four more -- and nothing
    could tell afterwards which stored runs had answered which contract.
    """
    wanted = set(stores or ())
    described = [
        f"{variable.name}\0{variable.description or ''}"
        for variable in getattr(module, "variables", [])
        if variable.name in wanted
    ]
    return hashlib.sha256("\0\0".join(described).encode()).hexdigest()[:20]


def _resolve_validator(module, case_name: str, turn: Turn):
    """Find the callable a turn names, refusing to silently auto-pass."""
    if not turn.validator:
        raise BenchmarkSpecificationError(f"{case_name}: turn declares no validator")
    validators = getattr(module, "validators", None)
    if not isinstance(validators, dict) or turn.validator not in validators:
        raise BenchmarkSpecificationError(
            f"{case_name}: module registers no validator named {turn.validator!r}"
        )
    return validators[turn.validator]


async def evaluate_turn(
    agent,
    runtime,
    module,
    case_name: str,
    turn: Turn,
    index: int,
    stores: list[str],
    table_names: list[str],
    settings: RunSettings,
    output_dir: Path | None = None,
) -> TurnResult:
    """Run one turn and judge only the outputs that turn asked for.

    Public because the pipeline family runs its two stages as ordinary turns
    (:mod:`core.pipeline_evaluator`): a stage that went through some other code
    would differ from the delivery study in the protocol repair, the loop-event
    bookkeeping and the usage accounting all at once, and no comparison between
    the two studies would survive that.
    """
    validator = _resolve_validator(module, case_name, turn)
    # The validator reads `turn.stores` to know what to check, so it must see
    # the resolved scope: a short-form turn declares none and would otherwise
    # be handed an empty set and pass judgement on nothing.
    turn = replace(turn, stores=list(stores))
    agent.max_steps = settings.total_step_budget
    outputs = [variable for variable in module.variables if variable.name in stores]
    events_before, spent_before = Counter(agent.loop_events), Counter(agent.spent)
    result = await agent.run(turn_prompt(turn.query, outputs))
    loop_events = dict(agent.loop_events - events_before)
    spent = dict(agent.spent - spent_before)
    stop_cause = agent.stop_cause
    raise_if_infrastructure(result, agent)

    values = await collect_outputs(settings.paradigm, runtime, result.content, stores, output_dir)
    verdict = _validate(
        validator, case_name, result.content, _ResolvedTurnRuntime(values), turn
    )
    usage = result.usage
    protocol_nudges = 0
    protocol_repair = None

    if settings.max_protocol_nudges and _needs_protocol_repair(
        result, verdict, result.steps, settings.total_step_budget
    ):
        totals = {
            "steps": result.steps, "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens, "elapsed": result.elapsed,
        }
        all_code_snippets = list(result.code_snippets)
        all_loop_events, all_spent = Counter(loop_events), Counter(spent)
        attempts = []
        repair_result, repair_values, repair_verdict = result, values, verdict

        while protocol_nudges < settings.max_protocol_nudges and _needs_protocol_repair(
            repair_result, repair_verdict, totals["steps"], settings.total_step_budget
        ):
            missing = [name for name in stores if repair_values.get(name) is None]
            if not missing:
                break
            protocol_nudges += 1
            remaining_steps = settings.total_step_budget - totals["steps"]
            agent.max_steps = remaining_steps
            nudge = repair_nudge(settings.paradigm, missing)
            events_before, spent_before = Counter(agent.loop_events), Counter(agent.spent)
            repair_result = await agent.run(nudge)
            raise_if_infrastructure(repair_result, agent)
            repair_loop_events = agent.loop_events - events_before
            repair_spent = agent.spent - spent_before
            all_loop_events += repair_loop_events
            all_spent += repair_spent
            repair_values = await collect_outputs(
                settings.paradigm, runtime, repair_result.content, stores, output_dir
            )
            repair_verdict = _validate(
                validator, case_name, repair_result.content,
                _ResolvedTurnRuntime(repair_values), turn,
            )
            repair_usage = repair_result.usage
            totals["steps"] += repair_result.steps
            totals["prompt_tokens"] += repair_usage.prompt_tokens
            totals["completion_tokens"] += repair_usage.completion_tokens
            totals["total_tokens"] += repair_usage.total_tokens
            totals["elapsed"] += repair_result.elapsed
            all_code_snippets.extend(repair_result.code_snippets)
            attempts.append({
                "nudge_number": protocol_nudges,
                "nudge": nudge,
                "remaining_step_budget_at_start": remaining_steps,
                "response": repair_result.content,
                "outputs": repair_values,
                "validation_message": repair_verdict.message,
                "variables_not_set": repair_verdict.variables_not_set,
                "steps": repair_result.steps,
                "prompt_tokens": repair_usage.prompt_tokens,
                "completion_tokens": repair_usage.completion_tokens,
                "total_tokens": repair_usage.total_tokens,
                "elapsed": repair_result.elapsed,
                "stop_reason": repair_result.stop_reason.value,
                "executed_code": bool(repair_result.code_snippets),
                "code_snippets": repair_result.code_snippets,
                "loop_events": dict(repair_loop_events),
                "spent": dict(repair_spent),
                "stop_cause": agent.stop_cause,
            })

        protocol_repair = {
            "attempted": bool(protocol_nudges),
            "protocol_nudges": protocol_nudges,
            "success": bool(repair_verdict.success),
            "failure_type": classify_failure(repair_verdict, repair_result.stop_reason),
            "response": repair_result.content,
            "outputs": repair_values,
            "validation_message": repair_verdict.message,
            "variables_not_set": repair_verdict.variables_not_set,
            **totals,
            "stop_reason": repair_result.stop_reason.value,
            "executed_code": bool(all_code_snippets),
            "code_snippets": all_code_snippets,
            "tables_referenced": referenced_names(all_code_snippets, table_names),
            "loop_events": dict(all_loop_events),
            "spent": dict(all_spent),
            "attempts": attempts,
            "total_step_budget": settings.total_step_budget,
        }

    # Strict first pass only, matching every other headline field; the repair
    # arm records its own reference set inside protocol_repair.
    referenced = referenced_names(result.code_snippets, table_names)
    return TurnResult(
        turn=index + 1, query=turn.query, stores=list(stores),
        success=bool(verdict.success),
        failure_type=classify_failure(verdict, result.stop_reason),
        response=result.content, outputs=values,
        validation_message=verdict.message,
        variables_not_set=verdict.variables_not_set, steps=result.steps,
        prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens, elapsed=result.elapsed,
        stop_reason=result.stop_reason.value,
        executed_code=bool(result.code_snippets), code_snippets=result.code_snippets,
        protocol_nudges=protocol_nudges, protocol_repair=protocol_repair,
        outputs_unserializable=unserializable_outputs(values),
        loop_events=loop_events, spent=spent, stop_cause=stop_cause,
        tables_referenced=referenced,
        tables_unreferenced=[n for n in table_names if n not in set(referenced)],
        output_contract=output_contract_fingerprint(module, stores),
    )


def _turn_scopes(case_name: str, conversation: Conversation, outputs: list) -> list[list[str]]:
    """Which outputs each turn registers, checked before anything runs.

    A turn naming an output the module does not declare, or an output no turn
    ever claims, is a case defect: the second leaves a variable unregistered and
    its validator reading a name that was never bound.
    """
    declared = {variable.name for variable in outputs}
    scoped = any(turn.stores for turn in conversation.turns)
    if not scoped:
        return [sorted(declared) for _ in conversation.turns]
    scopes = [list(turn.stores or []) for turn in conversation.turns]
    unknown = sorted({name for scope in scopes for name in scope} - declared)
    if unknown:
        raise BenchmarkSpecificationError(
            f"{case_name}/{conversation.id}: stores name outputs the module does "
            f"not register: {unknown}"
        )
    uncovered = sorted(declared - {name for scope in scopes for name in scope})
    if uncovered:
        raise BenchmarkSpecificationError(
            f"{case_name}/{conversation.id}: no turn claims {uncovered}; those "
            f"outputs would never be registered and their validator would fail"
        )
    return scopes


async def evaluate_case(
    model,
    spec: dict,
    *,
    max_protocol_nudges: int = 0,
    total_step_budget: int = 14,
    injection: str = "lazy",
    paradigm: Paradigm = CAVE,
    max_exec_output: int = 10000,
) -> CaseResult:
    """Run one case's conversations and judge every turn.

    ``paradigm`` decides how data and outputs cross between host and runtime
    (see :mod:`core.paradigms`). When it registers the tables, ``injection``
    decides how: ``"eager"`` as loaded DataFrames, ``"lazy"`` as one
    ``datasets`` handle that loads a table on request. Both expose exactly
    the declared tables; only memory, prompt size and the trace of what was
    loaded differ.
    """
    settings = RunSettings(
        max_protocol_nudges=max_protocol_nudges, total_step_budget=total_step_budget,
        injection=injection, paradigm=paradigm, max_exec_output=max_exec_output,
    )
    try:
        module = importlib.import_module(spec["module"])
    except Exception as error:
        raise BenchmarkSpecificationError(
            f"{spec['name']}: cannot load case module {spec['module']!r}: {error}"
        ) from error

    try:
        tables = select_runtime_tables(spec["data_sources"])
    except ValueError as error:
        raise BenchmarkSpecificationError(f"{spec['name']}: {error}") from error
    reads_files = paradigm.data_access is DataAccess.FILES
    if getattr(module, "revisions", None) and not reads_files and injection != "eager":
        raise ValueError(
            f"{spec['name']} revises its tables between turns; a paradigm that registers "
            "its tables then needs --injection eager, which registers each as a variable"
        )
    conversations = []
    for conversation in conversations_of(spec):
        # Where a conversation exchanges files with the host: private table copies
        # when the case revises them, and delivered outputs. Gone once they are read.
        with tempfile.TemporaryDirectory(prefix="cave-bench-") as workdir:
            try:
                conversations.append(await _evaluate_conversation(
                    model, spec, module, conversation, tables, settings, Path(workdir),
                ))
            except InfrastructureError as error:
                # The attempt is abandoned; what its finished conversations spent counts.
                error.spent += _spent_by(conversations)
                raise
    return CaseResult(name=spec["name"], conversations=conversations)



DEFAULT_STREAM_IDLE_TIMEOUT = 120.0


def idle_timeout(model) -> float:
    """How long to wait for a reply's first chunk: as long as the request may take.

    CaveAgent waits 120s by default. On a four-turn case whose prompt has grown
    past a hundred thousand tokens that is shorter than the endpoint's time to
    first token, and a stall is raised as a model error — so the pool reads a
    slow request as an outage and halves itself for it. The delivery study, whose
    prompts are small, stalled not once at eighteen concurrent runs; the imported
    cases stalled at three. Waiting less for the first chunk than the request is
    allowed to take in total contradicts the timeout the model was configured
    with, so the two are the same number.
    """
    return getattr(model, "kwargs", {}).get("timeout") or DEFAULT_STREAM_IDLE_TIMEOUT

async def _evaluate_conversation(
    model, spec: dict, module, conversation: Conversation, tables,
    settings: RunSettings, workdir: Path,
) -> ConversationResult:
    paradigm = settings.paradigm
    reads_files = paradigm.data_access is DataAccess.FILES
    # What the host does to the data before a turn: {turn index: revise}, where
    # revise maps the tables as they stand to the ones it replaces.
    revisions = getattr(module, "revisions", {})
    output_dir = workdir / "outputs" if paradigm.delivery is Delivery.FILES else None
    if output_dir is not None:
        output_dir.mkdir()
    paths = (
        table_paths(tables, workdir / "data" if revisions else None)
        if reads_files else {}
    )
    current = {table.name: table.loader() for table in tables} if revisions else {}
    # A fresh copy per conversation, so a mutable default cannot carry state
    # from one conversation into the next.
    outputs = deepcopy(module.variables)
    by_name = {variable.name: variable for variable in outputs}
    scopes = _turn_scopes(spec["name"], conversation, outputs)
    # A paradigm registers its outputs only when it delivers them as variables,
    # and its tables only when it does not hand them over as files.
    registers_outputs = paradigm.delivery is Delivery.VARIABLES
    first_outputs = scopes[0] if registers_outputs else []
    registered = set(first_outputs)
    if reads_files:
        data_variables = []
    elif settings.injection == "eager":
        data_variables = runtime_variables(spec["data_sources"])
    else:
        data_variables = [datastore_variable(tables)]
    runtime = IPythonRuntime(
        functions=[],
        variables=[by_name[name] for name in first_outputs] + data_variables,
        types=[],
        security_checker=SECURITY_CHECKER,
    )
    # One loop, two action formats: see core.agents.
    agent_type = ToolCallAgent if paradigm.action is Action.TOOL_CALL else FencedCodeAgent
    agent = agent_type(
        model=model,
        runtime=runtime,
        system_instructions=system_instructions(
            settings.injection, paradigm=paradigm, tables=tables, paths=paths,
            output_dir=output_dir,
            # A case may withhold the warning, to measure the risk it guards against.
            warn_of_revisions=(
                bool(revisions) and getattr(module, "warns_of_revisions", True)
            ),
        ),
        max_steps=settings.total_step_budget,
        max_exec_output=settings.max_exec_output,
        stream_idle_timeout=idle_timeout(model),
    )
    table_names = [table.name for table in tables]
    turns = []
    try:
        for index, (turn, stores) in enumerate(zip(conversation.turns, scopes)):
            # Register this turn's outputs as it begins, so the runtime this
            # turn describes names them and earlier turns' did not.
            for name in stores if registers_outputs else ():
                if name not in registered:
                    runtime.inject_variable(by_name[name])
                    registered.add(name)
            if index in revisions:
                revised = revisions[index](current)
                current.update(revised)
                publish_revision(paradigm, runtime, revised, paths)
            turns.append(await evaluate_turn(
                agent, runtime, module, spec["name"], turn, index, stores,
                table_names, settings, output_dir,
            ))
    except InfrastructureError as error:
        error.spent += agent.spent
        raise
    return ConversationResult(
        id=conversation.id, turns=turns, loop_events=dict(agent.loop_events),
        spent=dict(agent.spent), messages=messages_of(agent) or [],
    )


def write_result(
    path: Path,
    result: CaseResult,
    model_config: dict,
    run_metadata: dict | None = None,
) -> None:
    """Persist the trajectory without embedding an authoritative PV verdict."""
    VERDICT_FIELDS = {
        "success", "failure_type", "validation_message", "variables_not_set",
    }

    def without_verdict(record: dict) -> dict:
        clean = {k: v for k, v in record.items() if k not in VERDICT_FIELDS}
        repair = clean.get("protocol_repair")
        if isinstance(repair, dict):
            repair = {k: v for k, v in repair.items() if k not in VERDICT_FIELDS}
            attempts = repair.get("attempts")
            if isinstance(attempts, list):
                repair["attempts"] = [
                    {k: v for k, v in attempt.items() if k not in VERDICT_FIELDS}
                    if isinstance(attempt, dict) else attempt
                    for attempt in attempts
                ]
            clean["protocol_repair"] = repair
        return clean

    payload = {
        "schema": RESULT_SCHEMA,
        "written_at": utc_now(),
        "case": result.name,
        "model": model_config,
        "run": dict(run_metadata or {}),
        # Summed from the turns on every save, so it cannot drift from them.
        "cost": result.cost(),
        # Every model call, repair arms included; `cost` above is the first passes.
        "spent": result.spent(),
        "conversations": [
            {
                "id": conversation.id,
                **({"transcript": conversation.transcript}
                   if conversation.transcript else {}),
                "loop_events": conversation.loop_events,
                "spent": conversation.spent,
                "turns": [
                    without_verdict({
                        item.name: getattr(turn, item.name)
                        for item in fields(turn)
                    })
                    for turn in conversation.turns
                ],
            }
            for conversation in result.conversations
        ],
    }
    atomic_write_json(path, payload)
