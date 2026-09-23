"""Benchmark evaluation engine for cave-bench.

This module provides the Evaluator class which can evaluate
any agent implementation that conforms to the Agent interface.
"""

import logging
import ast
import copy
import inspect
from typing import Any, Dict, List, Callable, Set, Optional
from core.errors import BenchmarkSpecificationError
from core.validation import validate_function_calls, ErrorType, ValidationError, ValidatorResult
from core.transcripts import messages_of
from core.types import (
    ToolCall, TurnMetrics, TurnResult,
    ConversationResult, ScenarioMetrics, ScenarioResult, VariableAccess,
    Turn, Conversation, ExpectedFunctionCall, BenchmarkScenario
)
from core.agent import Agent, AgentFactory


logger = logging.getLogger('Agent.Evaluator')


def analyze_variable_access(code: str) -> VariableAccess:
    """
    Analyze the variable access in a Python code string.

    Args:
        code: Python code string

    Returns:
        VariableAccess with reads and writes lists
    """
    try:
        tree = ast.parse(code)
        analyzer = VariableAnalyzer()
        analyzer.visit(tree)

        return VariableAccess(
            reads=list(analyzer.reads),
            writes=list(analyzer.writes)
        )
    except SyntaxError:
        # If AST parsing fails, return empty results
        return VariableAccess(reads=[], writes=[])


class VariableAnalyzer(ast.NodeVisitor):
    """A simple variable access analyzer"""

    def __init__(self):
        self.reads: Set[str] = set()
        self.writes: Set[str] = set()

    def visit_Name(self, node):
        """Visit variable names"""
        if isinstance(node.ctx, ast.Load):
            # Variable read
            self.reads.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            # Variable write
            self.writes.add(node.id)

        self.generic_visit(node)


def _error_turn_result(turn: Turn, error_msg: str) -> TurnResult:
    """TurnResult for a turn that could not be evaluated (infra error).

    `error` is set so downstream consumers (resume skip-logic in runner.py)
    treat this as a retryable infrastructure failure, not a model failure.
    """
    return TurnResult(
        query=turn.query,
        reference_response=turn.reference_response,
        response="",
        expected_calls=[c.to_dict() for c in turn.expected_function_calls],
        actual_calls=[],
        validation_errors=[f"Infrastructure error: {error_msg}"],
        metrics=TurnMetrics(),
        success=False,
        error=error_msg,
        expected_variable_reads=turn.expected_variable_reads,
        expected_variable_writes=turn.expected_variable_writes,
    )


class _ValidatorRuntimeView:
    """Synchronous variable view handed to validators.

    cave-agent 0.7.5 made ``Runtime.retrieve`` a coroutine function, while
    benchmark validators are deliberately ordinary synchronous callables. Values
    are therefore collected (and awaited) by the evaluator before validation and
    exposed here through the historical synchronous ``retrieve`` contract.
    Without this a validator receives a coroutine and fails with an attribute
    error on whatever it tries to read from the "value".
    """

    def __init__(self, runtime, values: Dict[str, Any]):
        self._runtime = runtime
        self._values = values

    def retrieve(self, name: str) -> Any:
        if name not in self._values:
            raise KeyError(
                f"Variable {name!r} was not present in the runtime snapshot. "
                f"Available variables: {list(self._values)}"
            )
        return self._values[name]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._runtime, name)


async def _snapshot_runtime(runtime, variables) -> Optional["_ValidatorRuntimeView"]:
    """Await every runtime variable once, so validators can read them synchronously.

    The scenario's declared `variables` are the contract and drive the snapshot.
    Anything the agent created at runtime is picked up as well: cave-agent exposes
    no public enumeration API (`describe_variables` returns formatted prose), so
    its internal registry is the only source for those, and this is the single
    place that touches it.
    """
    if runtime is None:
        return None

    # retrieve() raises KeyError for a name the runtime does not manage. With
    # per-turn registration the scenario's variable list runs ahead of the
    # registry, so ask only for what is registered now — the rest belong to
    # turns that have not started.
    managed = getattr(runtime, "_variables", None)
    declared = [var.name for var in variables or []]
    if isinstance(managed, dict):
        names = [n for n in declared if n in managed]
        names.extend(n for n in managed if n not in names)
    else:
        names = declared

    values: Dict[str, Any] = {}
    for name in dict.fromkeys(names):
        try:
            value = runtime.retrieve(name)
            if inspect.isawaitable(value):
                value = await value
        except KeyError:
            # A name the registry does not hold has no value to snapshot, and
            # omitting it leaves the validator seeing exactly what it would
            # have seen from the runtime itself. The filter above avoids this
            # for a readable registry; this is the backstop for one that is
            # not, so a rename of that private attribute degrades to a missing
            # variable instead of killing turn 1 of every scoped conversation.
            continue
        values[name] = value
    return _ValidatorRuntimeView(runtime, values)


class Evaluator:
    """Evaluator for benchmarking agent implementations.

    This evaluator works with any agent that implements the Agent interface,
    including CaveAgent (Python code execution) and LiteLLM (JSON function calling).
    """

    def __init__(self, agent_factory: AgentFactory):
        """
        Initialize the benchmark evaluator.

        Args:
            agent_factory: Factory for creating agent instances
        """
        self.agent_factory = agent_factory
        self._reset_metrics()

    def _reset_metrics(self):
        """
        Reset all evaluation metrics to their initial values.
        This should be called before starting a new evaluation.
        """
        logger.debug("Resetting evaluation metrics")
        self.metrics = ScenarioMetrics()

    async def evaluate(
        self,
        scenario: str,
        module,
        conversations: List[Conversation],
        json_config: dict | None = None
    ) -> ScenarioResult:
        """
        Evaluate an agent against a specific scenario.

        Args:
            scenario: The scenario name
            module: The scenario module
            conversations: List of benchmark conversations to evaluate
            json_config: Optional JSON config dict containing 'description'

        Returns:
            ScenarioResult with complete evaluation results
        """
        # Reset metrics at the start of evaluation
        self._reset_metrics()

        # Load scenario contents with optional JSON overrides for prompts
        scenario_contents = BenchmarkScenario.from_module(module, json_config)

        logger.info(f"Evaluating scenario {scenario} with {len(conversations)} conversations")

        # Process each conversation
        conversation_results = []
        for conversation in conversations:
            result = await self._evaluate_conversation(
                conversation, scenario_contents
            )
            conversation_results.append(result)

        # Calculate success rate
        self.metrics.success_rate = (
            self.metrics.successful_turns / self.metrics.total_turns
            if self.metrics.total_turns > 0 else 0
        )

        logger.info(f"Evaluation complete. Success rate: {self.metrics.success_rate:.2f}")

        return ScenarioResult(
            scenario=scenario,
            conversations=conversation_results,
            metrics=self.metrics
        )

    async def _evaluate_conversation(
        self,
        conversation: Conversation,
        scenario: BenchmarkScenario
    ) -> ConversationResult:
        """Evaluate a single conversation within a scenario."""
        logger.debug(f"Evaluating conversation: {conversation.id}")

        # Deep copy variables to ensure fresh state for each conversation
        # This prevents mutable values (lists, dicts) from persisting across conversations
        fresh_variables = copy.deepcopy(scenario.variables)

        # Register a turn's OUTPUT variables when that turn begins, not all at
        # once. cave-agent rebuilds the system prompt from the runtime's live
        # registrations on every run, so a turn then advertises only what it is
        # being asked for plus what earlier turns already stored. Without this,
        # the first turn of a conversation reads the names of every later turn's
        # outputs and tends either to compute them early or to spend the turn's
        # budget doing so.
        #
        # `expected_variable_writes` already declares the per-turn outputs and
        # is already validated, so it is the declaration — no second one.
        # Variables no turn claims are inputs the agent reads (the DataFrames it
        # is handed) and stay registered from the start.
        registered = {v.name for v in fresh_variables}
        claimed = {
            w for turn in conversation.turns
            for w in (turn.expected_variable_writes or [])
        }
        scoped = bool(claimed)
        pending = []
        if scoped:
            unknown = sorted(claimed - registered)
            if unknown:
                logger.warning(
                    "Conversation %s expects writes to unregistered variables: %s",
                    conversation.id, unknown,
                )
            first = set(conversation.turns[0].expected_variable_writes or [])
            initial = [
                v for v in fresh_variables
                if v.name in first or v.name not in claimed
            ]
            up_front = {v.name for v in initial}
            pending = [v for v in fresh_variables if v.name not in up_front]
        else:
            initial = fresh_variables

        # Create agent using the factory
        agent = self.agent_factory.create_agent(
            functions=scenario.tools,
            variables=initial,
            types=scenario.types,
            description=scenario.description,
        )

        # A turn that raises on INFRASTRUCTURE (API outage, runtime death)
        # must not discard the turns that already succeeded, and must not be
        # recorded as a model failure: it gets `error` set, which marks the
        # whole result retryable for the resume logic (core.results). Turns
        # after the error are skipped — the conversation context is broken,
        # so evaluating them would not be a fair measurement.
        #
        # Deterministic benchmark defects (missing/buggy validator or hook,
        # a turn with nothing checking it) deliberately PROPAGATE instead:
        # recording them as retryable would make the resume loop re-run the
        # same defect forever without ever surfacing it as a defect. Mirrors
        # the sibling harness's evaluator semantics.
        turn_results = []
        aborted: Optional[str] = None
        for turn in conversation.turns:
            if aborted is not None:
                turn_results.append(_error_turn_result(
                    turn, f"skipped: earlier turn in conversation errored ({aborted})"
                ))
                continue
            # Register this turn's outputs before it starts, so its prompt names
            # them and earlier turns' prompts did not. Registration rebinds the
            # name to its initial value, which also discards anything a model
            # wrote to it speculatively.
            #
            # A missing runtime is skipped rather than raised: `Agent.runtime`
            # is documented as None for anything but CaveAgent, and on those
            # adapters runtime variables are not a concept at all.
            if scoped and turn.expected_variable_writes and agent.runtime is not None:
                wanted = set(turn.expected_variable_writes)
                for variable in [v for v in pending if v.name in wanted]:
                    agent.runtime.inject_variable(variable)
                pending = [v for v in pending if v.name not in wanted]

            try:
                result = await self._evaluate_turn(
                    turn, agent, scenario.validators, scenario.hooks, fresh_variables
                )
            except BenchmarkSpecificationError:
                raise
            except Exception as e:
                aborted = f"{type(e).__name__}: {e}"
                logger.error(f"Turn errored in conversation {conversation.id}: {aborted}")
                result = _error_turn_result(turn, aborted)
            turn_results.append(result)

        # Metrics are accounted here, once per recorded turn, so exception
        # paths cannot double-count or drop a turn.
        for r in turn_results:
            self.metrics.total_turns += 1
            if r.success:
                self.metrics.successful_turns += 1
            else:
                self.metrics.failed_turns += 1
            self.metrics.total_expected_calls += len(r.expected_calls)
            self.metrics.total_actual_calls += len(r.actual_calls)
            m = r.metrics
            self.metrics.total_steps += m.steps
            self.metrics.total_elapsed += m.elapsed
            self.metrics.total_prompt_tokens += m.prompt_tokens
            self.metrics.total_completion_tokens += m.completion_tokens
            self.metrics.total_tokens += m.total_tokens
            self.metrics.missing_calls += m.missing_calls
            self.metrics.wrong_argument_types += m.wrong_argument_types
            self.metrics.wrong_argument_values += m.wrong_argument_values
            self.metrics.missing_arguments += m.missing_arguments
            self.metrics.missing_variable_reads += m.missing_variable_reads
            self.metrics.missing_variable_writes += m.missing_variable_writes

        # The raw dialogue travels with the result in memory; the runner, which
        # owns the output path, writes it out and records where it went.
        return ConversationResult(
            id=conversation.id,
            turns=turn_results,
            messages=messages_of(agent),
        )

    def _calculate_missing_calls_metric(
        self,
        expected_calls: List[ExpectedFunctionCall],
        actual_calls: List[ToolCall]
    ) -> int:
        """
        Calculate the number of missing required function calls.

        Args:
            expected_calls: List of expected function calls from benchmarks
            actual_calls: List of actual function calls from the agent

        Returns:
            Number of missing required function calls
        """
        missing_required_calls = 0

        # Create a set of function names from actual calls for quick lookup
        actual_function_names = {call.function for call in actual_calls}

        # Count missing required calls
        for expected in expected_calls:
            if expected.required and expected.name not in actual_function_names:
                missing_required_calls += 1

        return missing_required_calls

    async def _evaluate_turn(
        self,
        turn: Turn,
        agent: Agent,
        validators: Optional[Dict[str, Callable]] = None,
        hooks: Optional[Dict[str, Callable]] = None,
        variables: Optional[List[Any]] = None,
    ) -> TurnResult:
        """Evaluate a single turn within a conversation and return detailed metrics."""
        if validators is None:
            validators = {}
        if hooks is None:
            hooks = {}

        query = turn.query
        reference_response = turn.reference_response
        expected_calls = turn.expected_function_calls
        expected_variable_reads = turn.expected_variable_reads
        expected_variable_writes = turn.expected_variable_writes

        # Call pre-turn hook if specified (injects randomness / modifies state)
        # Note: hooks require runtime access, only available for CaveAgent
        if turn.pre_turn_hook:
            if turn.pre_turn_hook not in hooks:
                raise BenchmarkSpecificationError(
                    f"Hook '{turn.pre_turn_hook}' not found. Available hooks: {list(hooks.keys())}"
                )
            if agent.runtime is None:
                raise BenchmarkSpecificationError(
                    f"Hook '{turn.pre_turn_hook}' requires runtime access, but agent has no runtime"
                )
            try:
                hook_result = hooks[turn.pre_turn_hook](agent.runtime, turn)
            except Exception as exc:
                # Hooks are benchmark code: a crash is deterministic, not an outage.
                raise BenchmarkSpecificationError(
                    f"hook '{turn.pre_turn_hook}' crashed: {type(exc).__name__}: {exc}"
                ) from exc
            # Hook can return a new query string, or None to use the original
            if hook_result is not None:
                query = hook_result
                logger.debug(f"Pre-turn hook modified query to: {query[:100]}...")

        # A turn must carry at least one validation mechanism — a custom
        # validator, expected function calls, or expected variable access.
        # A turn with none of them would silently auto-pass, inflating
        # success rates on a spec typo, so fail loudly instead.
        if (not turn.validator and not expected_calls
                and not expected_variable_reads and not expected_variable_writes):
            raise BenchmarkSpecificationError(
                "Turn declares no validation mechanism (validator / "
                f"expected_function_calls / expected_variable_*): {query[:80]!r}"
            )

        # Initialize metrics (aggregated into ScenarioMetrics by the
        # conversation loop, once per recorded turn)
        turn_metrics = TurnMetrics()

        # Run the agent
        result = await agent.run(query)

        turn_metrics.steps = result.steps
        turn_metrics.elapsed = result.elapsed

        # Track token usage
        token_usage = result.token_usage
        turn_metrics.prompt_tokens = token_usage.prompt_tokens
        turn_metrics.completion_tokens = token_usage.completion_tokens
        turn_metrics.total_tokens = token_usage.total_tokens

        # Analyze code snippets for variable access (only for agents that produce code)
        code_snippets = result.code_snippets
        actual_variable_reads = []
        actual_variable_writes = []

        for code_snippet in code_snippets:
            variable_access = analyze_variable_access(code_snippet)
            for read in variable_access.reads:
                if read in expected_variable_reads:
                    actual_variable_reads.append(read)
            for write in variable_access.writes:
                if write in expected_variable_writes:
                    actual_variable_writes.append(write)

        # Get function calls from agent response
        actual_calls = result.tool_calls
        actual_calls_dict = [call.to_dict() for call in actual_calls]

        # Run validator if specified (after we have actual_calls)
        # Note: validators may require runtime access
        validator_name = turn.validator
        if validator_name:
            if validator_name not in validators:
                raise BenchmarkSpecificationError(
                    f"Validator '{validator_name}' not found. "
                    f"Available validators: {list(validators.keys())}"
                )
            validator_runtime = await _snapshot_runtime(agent.runtime, variables)
            try:
                validator_result = validators[validator_name](
                    result.content, validator_runtime, turn, actual_calls
                )
            except BenchmarkSpecificationError:
                raise
            except Exception as exc:
                # cave-bench validators are local, deterministic code (no live
                # DB), so a crash is always a spec defect — never an outage.
                raise BenchmarkSpecificationError(
                    f"validator {validator_name!r} crashed: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
        else:
            validator_result = ValidatorResult(success=True, message="")

        # Validate function calls
        validation_errors = validate_function_calls(actual_calls, expected_calls)

        # Check for missing variable reads/writes
        for expected_variable_read in expected_variable_reads:
            if expected_variable_read not in actual_variable_reads:
                validation_errors.append(ValidationError(
                    error_type=ErrorType.MISSING_VARIABLE_READ,
                    message=f"Variable {expected_variable_read} is not read",
                ))
        for expected_variable_write in expected_variable_writes:
            if expected_variable_write not in actual_variable_writes:
                validation_errors.append(ValidationError(
                    error_type=ErrorType.MISSING_VARIABLE_WRITE,
                    message=f"Variable {expected_variable_write} is not written",
                ))

        # Store error messages for display
        error_messages = [error.message for error in validation_errors]
        if not validator_result.success:
            error_messages.append(f"Custom validator failed: {validator_result.message}")

        # Calculate missing calls metric
        turn_metrics.missing_calls = self._calculate_missing_calls_metric(expected_calls, actual_calls)

        # Count error types
        for error in validation_errors:
            if error.error_type == ErrorType.WRONG_ARGUMENT_TYPE:
                turn_metrics.wrong_argument_types += 1
            elif error.error_type == ErrorType.WRONG_ARGUMENT_VALUE:
                turn_metrics.wrong_argument_values += 1
            elif error.error_type == ErrorType.MISSING_ARGUMENT:
                turn_metrics.missing_arguments += 1
            elif error.error_type == ErrorType.MISSING_VARIABLE_READ:
                turn_metrics.missing_variable_reads += 1
            elif error.error_type == ErrorType.MISSING_VARIABLE_WRITE:
                turn_metrics.missing_variable_writes += 1

        # Determine turn success (ensure native Python bool for JSON serialization)
        success = bool(not validation_errors and validator_result.success)

        return TurnResult(
            query=query,
            reference_response=reference_response,
            response=result.content,
            expected_calls=[call.to_dict() for call in expected_calls],
            actual_calls=actual_calls_dict,
            validation_errors=error_messages,
            metrics=turn_metrics,
            success=success,
            variables_not_set=bool(getattr(validator_result, "variables_not_set", False)),
            stop_reason=result.stop_reason,
            code_snippets=code_snippets,
            expected_variable_reads=expected_variable_reads,
            expected_variable_writes=expected_variable_writes,
            actual_variable_reads=actual_variable_reads,
            actual_variable_writes=actual_variable_writes
        )
