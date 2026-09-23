"""CaveAgent adapter for cave-bench benchmarking framework.

This adapter wraps CaveAgent to conform to the abstract Agent interface,
allowing it to be evaluated using the same pipeline as JSON function calling agents.
"""

from typing import Any, Callable, List, Optional
from core.agent import Agent, AgentFactory, AgentResponse, TokenUsage
from core.tracker import FunctionCallTracker
from core.prompts import DEFAULT_AGENT_IDENTITY, DEFAULT_INSTRUCTIONS
from core.security import security_checker
from cave_agent import CaveAgent, Model, StopReason
from cave_agent.runtime import IPythonRuntime, Function, Variable, Type


class CaveAgentWrapper(Agent):
    """Agent implementation that wraps CaveAgent.

    CaveAgent executes Python code to call functions, so we use
    sys.monitoring (PEP 669) via FunctionCallTracker to capture actual
    function calls.
    """

    def __init__(
        self,
        model: Model,
        functions: List[Callable],
        variables: Optional[List[Variable]] = None,
        types: Optional[List[Type]] = None,
        description: Optional[str] = None,
    ):
        """Initialize the CaveAgentWrapper.

        Args:
            model: The LLM model configuration
            functions: List of callable functions/tools
            variables: List of variables for stateful execution
            types: List of custom types
            description: Scenario-specific agent description
        """
        self._model = model
        self._functions = functions
        self._function_names = [f.__name__ for f in functions]
        self._variables = variables or []
        self._types = types or []

        # Task instructions = agent identity + this scenario's description.
        # (cave_agent slots: `instructions` = task/identity, `system_instructions`
        # = the generic how-to-operate block.)
        #
        # No requirements block: it listed every variable the whole scenario
        # would ask for, which on a multi-turn scenario is every later turn's
        # outputs. Each Variable carries its own description and the runtime
        # describes the ones registered at the time.
        instructions = DEFAULT_AGENT_IDENTITY
        if description:
            instructions += "\nTASK DESCRIPTION:\n" + description + "\n"

        # Create runtime with wrapped functions
        wrapped_functions = [Function(f) for f in functions]
        runtime = IPythonRuntime(
            functions=wrapped_functions,
            variables=self._variables,
            types=self._types,
            security_checker=security_checker,
        )

        # Create the underlying CaveAgent
        self._agent = CaveAgent(
            model=model,
            runtime=runtime,
            max_steps=100,
            instructions=instructions,
            system_instructions=DEFAULT_INSTRUCTIONS,
            max_exec_output=80000,
        )

    @property
    def runtime(self) -> IPythonRuntime:
        """Get the Python runtime for accessing variables."""
        return self._agent.runtime

    @property
    def messages(self) -> List[Any]:
        """The conversation history, for the transcript written beside results.

        Live list, not a copy: the caller reads it once the conversation is
        over. Anything the model said is here, including content the code
        parser did not recognise — which is the part a result file loses.
        """
        return self._agent.messages

    async def run(self, query: str) -> AgentResponse:
        """Run the agent and capture function calls via profiling.

        Args:
            query: The user input query

        Returns:
            AgentResponse with result, tool calls, steps, code snippets, and token usage
        """
        # Use context manager to safely track function calls
        with FunctionCallTracker(target_functions=self._functions) as tracker:
            result = await self._agent.run(query)

        # cave-agent 0.8.0: provider/runtime failures no longer raise out of
        # run() — the stream ends with a typed stop reason instead. Re-raise
        # here so the evaluator still books them as errors rather than
        # silently scoring an empty answer as wrong.
        if result.stop_reason in (StopReason.MODEL_ERROR, StopReason.RUNTIME_ERROR):
            raise RuntimeError(f"agent run failed: {result.stop_reason.value}")

        # Get tracked tool calls
        tool_calls = tracker.get_tool_calls()

        # Extract token usage from CaveAgent's response (0.8.0: `usage`/`steps`)
        cave_usage = result.usage
        token_usage = TokenUsage(
            prompt_tokens=cave_usage.prompt_tokens,
            completion_tokens=cave_usage.completion_tokens,
            total_tokens=cave_usage.total_tokens
        )

        return AgentResponse(
            content=result.content,
            tool_calls=tool_calls,
            steps=result.steps,
            code_snippets=result.code_snippets,
            token_usage=token_usage,
            elapsed=result.elapsed,
            stop_reason=result.stop_reason.value,
        )


class CaveAgentFactory(AgentFactory):
    """Factory for creating CaveAgent instances."""

    def __init__(self, model: Model):
        """Initialize the factory with a model configuration.

        Args:
            model: The LLM model to use for all created agents
        """
        self.model = model

    def create_agent(
        self,
        functions: List[Callable],
        variables: Optional[List[Variable]] = None,
        types: Optional[List[Type]] = None,
        description: Optional[str] = None,
    ) -> CaveAgentWrapper:
        """Create a CaveAgent with the specified configuration.

        Args:
            functions: List of callable functions/tools
            variables: List of variables for stateful execution
            types: List of custom types
            description: Scenario-specific agent description

        Returns:
            A CaveAgentWrapper instance
        """
        return CaveAgentWrapper(
            model=self.model,
            functions=functions,
            variables=variables,
            types=types,
            description=description,
        )
