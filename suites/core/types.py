"""Core data types for cave-bench benchmarking framework."""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable
from cave_agent.runtime import Variable
from cave_agent.runtime import Type

@dataclass
class ToolCall:
    """Represents a tool/function call made by an agent."""

    function: str
    arguments: Dict[str, Any]
    call_id: str

    def __repr__(self) -> str:
        return f"ToolCall(function={self.function}, call_id={self.call_id})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function": self.function,
            "arguments": self.arguments,
            "call_id": self.call_id
        }


@dataclass
class VariableAccess:
    """Represents variable reads and writes in code."""

    reads: List[str]
    writes: List[str]


# Input data structures (from benchmark JSON files)

@dataclass
class ExpectedArgument:
    """Expected argument for a function call."""

    name: str
    value: Any = None
    type: Optional[str] = None
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"name": self.name, "required": self.required}
        if self.value is not None:
            result["value"] = self.value
        if self.type is not None:
            result["type"] = self.type
        return result


@dataclass
class ExpectedFunctionCall:
    """Expected function call in a benchmark."""

    name: str
    required: bool = True
    arguments: List[ExpectedArgument] = field(default_factory=list)
    strict_args: bool = False  # If True, flag unexpected arguments as errors

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExpectedFunctionCall':
        """Create from dictionary loaded from JSON."""
        arguments = [
            ExpectedArgument(**arg) if isinstance(arg, dict) else arg
            for arg in data.get('arguments', [])
        ]
        return cls(
            name=data['name'],
            required=data.get('required', True),
            arguments=arguments,
            strict_args=data.get('strict_args', False)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "required": self.required,
            "arguments": [arg.to_dict() for arg in self.arguments],
            "strict_args": self.strict_args
        }


@dataclass
class Turn:
    """A single turn in a benchmark conversation."""

    query: str = ""  # Optional if pre_turn_hook provides the query
    expected_function_calls: List[ExpectedFunctionCall] = field(default_factory=list)
    reference_response: str = ""
    validator: Optional[str] = None
    expected_variable_reads: List[str] = field(default_factory=list)
    expected_variable_writes: List[str] = field(default_factory=list)
    pre_turn_hook: Optional[str] = None  # Hook to call before turn (modifies state, returns query)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Turn':
        """Create from dictionary loaded from JSON."""
        expected_calls = [
            ExpectedFunctionCall.from_dict(call)
            for call in data.get('expected_function_calls', [])
        ]
        return cls(
            query=data.get('query', ''),
            expected_function_calls=expected_calls,
            reference_response=data.get('reference_response', ''),
            validator=data.get('validator'),
            expected_variable_reads=data.get('expected_variable_reads', []),
            expected_variable_writes=data.get('expected_variable_writes', []),
            pre_turn_hook=data.get('pre_turn_hook')
        )


@dataclass
class Conversation:
    """A conversation in a benchmark scenario."""

    id: str
    turns: List[Turn]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create from dictionary loaded from JSON."""
        turns = [Turn.from_dict(turn) for turn in data.get('turns', [])]
        return cls(
            id=data.get('id', 'unnamed_conversation'),
            turns=turns
        )


@dataclass
class BenchmarkScenario:
    """Scenario module contents with tools, variables, validators, hooks, and optional prompts."""

    tools: List[Callable] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    validators: Dict[str, Callable] = field(default_factory=dict)
    hooks: Dict[str, Callable] = field(default_factory=dict)  # Pre-turn hooks for state modification
    types: List[Type] = field(default_factory=list)
    description: Optional[str] = None  # Scenario-specific agent identity/description

    @classmethod
    def from_module(cls, module, json_config: Optional[Dict[str, Any]] = None) -> 'BenchmarkScenario':
        """
        Extract scenario contents from a module with optional JSON overrides.

        Precedence for description: JSON > Python module > None (use defaults)

        Args:
            module: The Python module containing tools, variables, validators
            json_config: Optional dict from JSON with a 'description' key
        """
        json_config = json_config or {}

        # Get from JSON first, then fall back to module attribute
        description = json_config.get('description') or getattr(module, "description", None)

        return cls(
            tools=getattr(module, "tools", []),
            variables=getattr(module, "variables", []),
            validators=getattr(module, "validators", {}),
            hooks=getattr(module, "hooks", {}),
            types=getattr(module, "types", []),
            description=description,
        )


# Output data structures (evaluation results)

@dataclass
class TurnMetrics:
    """Metrics for a single turn evaluation."""

    missing_calls: int = 0
    wrong_argument_types: int = 0
    wrong_argument_values: int = 0
    missing_arguments: int = 0
    steps: int = 0
    missing_variable_reads: int = 0
    missing_variable_writes: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    # Wall-clock seconds for the agent run behind this turn.
    elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TurnResult:
    """Result from evaluating a single turn."""

    query: str
    reference_response: str
    response: str
    expected_calls: List[Dict[str, Any]]
    actual_calls: List[Dict[str, Any]]
    validation_errors: List[str]
    metrics: TurnMetrics
    success: bool
    # True when the custom validator reports the agent never populated the
    # required runtime variables (refusal / infra), vs computed-but-wrong.
    variables_not_set: bool = False
    # Infrastructure error (API/DB) that aborted this turn; None when the turn
    # ran normally (even if it failed validation).
    error: Optional[str] = None
    # Why the agent run behind this turn ended ("completed", "max_steps", ...).
    # Distinguishes "answered wrong" from "ran out of budget" — the two mean
    # entirely different things when analysing failures.
    stop_reason: Optional[str] = None
    code_snippets: List[str] = field(default_factory=list)
    expected_variable_reads: List[str] = field(default_factory=list)
    expected_variable_writes: List[str] = field(default_factory=list)
    actual_variable_reads: List[str] = field(default_factory=list)
    actual_variable_writes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize, omitting what was never there.

        ``None`` and empty containers are absences, not measurements, so they
        do not earn a line in the file — readers already use ``.get``. Numeric
        zeros and booleans stay: a count of 0 and ``success: false`` are
        results.
        """
        result = asdict(self)
        result['metrics'] = self.metrics.to_dict()
        if not result.get('variables_not_set'):
            # A flag, not a measurement: only the True case says anything.
            result.pop('variables_not_set', None)
        return {
            k: v
            for k, v in result.items()
            if v is not None and (not isinstance(v, (list, dict, str)) or v or k == 'response')
        }


@dataclass
class ConversationResult:
    """Result from evaluating a conversation."""

    id: str
    turns: List[TurnResult]
    # The raw dialogue, and where it was written. `messages` is in-memory only:
    # the evaluator collects it, the runner writes it out and records the path.
    # Keeping the messages out of `to_dict` is deliberate — a result file stays
    # a scoring artefact, and the transcript stays a separate, greppable file.
    messages: Optional[List[Any]] = field(default=None, repr=False)
    transcript: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        document: Dict[str, Any] = {
            "id": self.id,
            "turns": [turn.to_dict() for turn in self.turns]
        }
        if self.transcript:
            document["transcript"] = self.transcript
        return document


@dataclass
class ScenarioMetrics:
    """Overall metrics for a scenario evaluation."""

    total_turns: int = 0
    successful_turns: int = 0
    failed_turns: int = 0
    total_expected_calls: int = 0
    total_actual_calls: int = 0
    missing_calls: int = 0
    wrong_argument_values: int = 0
    wrong_argument_types: int = 0
    missing_arguments: int = 0
    total_steps: int = 0
    success_rate: float = 0.0
    missing_variable_reads: int = 0
    missing_variable_writes: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    # Wall-clock seconds summed over every turn's agent run.
    total_elapsed: float = 0.0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioResult:
    """Complete result from evaluating a scenario."""

    scenario: str
    conversations: List[ConversationResult]
    metrics: ScenarioMetrics

    def to_dict(self) -> Dict[str, Any]:
        # The scenario name is the enclosing key in the result file; embedding
        # it again is a byte-for-byte duplicate.
        return {
            "conversations": [conversation.to_dict() for conversation in self.conversations],
            "metrics": self.metrics.to_dict()
        }
