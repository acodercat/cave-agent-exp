"""LiteLLM adapter for JSON function calling evaluation.

This adapter wraps LiteLLM to evaluate traditional JSON-based function calling,
allowing comparison with CaveAgent's Python code execution approach.

The agent implements a proper agentic loop:
1. Send query to model
2. If model returns tool calls, execute them and feed results back
3. Repeat until model returns final response
"""

from typing import List, Callable, Optional, Any, Dict
import json
import time
import logging
from core.agent import Agent, AgentFactory, AgentResponse, TokenUsage
from core.types import ToolCall
from litellm import acompletion

logger = logging.getLogger('Agent.LitellmAdapter')

# Default system prompt for JSON function calling
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools/functions.
When the user asks you to perform a task, analyze what tools you need and call them appropriately.
Always use the tools when they can help accomplish the user's request.
After getting tool results, provide a helpful response to the user."""


def function_to_schema(func: Callable) -> Dict[str, Any]:
    """
    Convert a Python function to an OpenAI-compatible tool schema.

    Args:
        func: Python function with type hints and docstring

    Returns:
        Dictionary with name, description, and parameters schema

    Note:
        This requires the 'agents' package. Used for compatibility
        with non-CaveAgent frameworks.
    """
    try:
        from agents import function_tool
    except ImportError as exc:
        raise ImportError(
            "The 'agents' package is required for function_to_schema. "
            "Install it with: pip install openai-agents"
        ) from exc

    tool = function_tool(func, strict_mode=False)
    return {
        "name": func.__name__,
        "description": func.__doc__ or tool.description,
        "parameters": _flatten_nullable_unions(tool.params_json_schema),
    }


def _flatten_nullable_unions(schema: Any) -> Any:
    """Give an optional parameter the type it optionally holds.

    An ``Optional[int]`` parameter becomes ``anyOf: [{integer}, {null}]`` with no
    type of its own. OpenAI-compatible endpoints accept that; Google's function
    calling refuses the whole request — "functionDeclaration ... didn't specify
    the schema type field" — so one scenario's tool made every request of that
    scenario fail before a single tool was called, on one model only. Read as a
    completion rate, that looks like the model could not do the task.

    Collapsing the union to its non-null member says the same thing in the form
    every endpoint accepts: the parameter holds an integer, and it stays out of
    ``required``, which is what makes it optional. Nothing else is rewritten.
    """
    if isinstance(schema, list):
        return [_flatten_nullable_unions(item) for item in schema]
    if not isinstance(schema, dict):
        return schema

    options = schema.get("anyOf")
    if isinstance(options, list):
        concrete = [option for option in options
                    if not (isinstance(option, dict) and option.get("type") == "null")]
        if len(concrete) == 1 and len(concrete) < len(options):
            merged = {key: value for key, value in schema.items() if key != "anyOf"}
            merged.update(concrete[0])
            return _flatten_nullable_unions(merged)

    return {key: _flatten_nullable_unions(value) for key, value in schema.items()}

class LitellmModel:
    """Model configuration for LiteLLM.

    Supports multiple providers through LiteLLM's unified API:
    - OpenAI (provider='openai')
    - DeepSeek (provider='deepseek')
    - Google Gemini (provider='gemini')
    - Anthropic Claude (provider='anthropic')
    - And many more via LiteLLM
    """

    def __init__(
        self,
        model_id: str,
        api_key: str,
        provider: str,
        temperature: Optional[float] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the LiteLLM model configuration.

        Args:
            model_id: The model identifier (e.g., 'gpt-4', 'deepseek-chat')
            api_key: API key for the provider
            provider: LiteLLM provider name (e.g., 'openai', 'deepseek')
            temperature: Optional temperature setting
            base_url: Optional custom API base URL
            max_tokens: Optional max completion tokens
            reasoning_effort: Optional reasoning effort ('low'|'medium'|'high')
            extra_body: Optional provider-specific passthrough (e.g. thinking flags)
        """
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.extra_body = extra_body or None


class LitellmAgentWrapper(Agent):
    """Agent that uses LiteLLM for JSON-based function calling.

    Implements a proper agentic loop:
    - Maintains conversation history across turns
    - Executes tool calls and feeds results back to the model
    - Loops until model returns final response (no tool calls)
    - Uses system prompt built from the scenario description
    """

    def __init__(
        self,
        model: LitellmModel,
        tools: List[Callable],
        max_steps: int = 20,
        description: Optional[str] = None,
    ):
        """Initialize the LiteLLM agent wrapper.

        Args:
            model: The LiteLLM model configuration
            tools: List of callable functions to expose to the model
            max_steps: Maximum number of steps (API calls) per run
            description: Task description for system prompt
        """
        self._model = model
        self._max_steps = max_steps
        self._total_steps = 0
        self._total_token_usage = TokenUsage()

        # Build system prompt from the scenario description
        self._system_prompt = self._build_system_prompt(description)

        # Initialize messages with system prompt
        self._messages: List[Dict[str, Any]] = []
        if self._system_prompt:
            self._messages.append({"role": "system", "content": self._system_prompt})

        # Store tools as dict for execution lookup
        self._tools_dict: Dict[str, Callable] = {
            tool.__name__: tool for tool in tools
        }

        # Convert to OpenAI tool format for API calls
        self._tools_schema = [
            {"type": "function", "function": function_to_schema(tool)}
            for tool in tools
        ]

    def _build_system_prompt(self, description: Optional[str]) -> str:
        """Build system prompt from the scenario description.

        Args:
            description: Task description

        Returns:
            Formatted system prompt string
        """
        parts = [DEFAULT_SYSTEM_PROMPT]

        if description:
            parts.append(f"\n\nTASK DESCRIPTION:\n{description}")

        return "".join(parts)

    def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return the result as a string.

        Args:
            function_name: Name of the function to call
            arguments: Arguments to pass to the function

        Returns:
            String representation of the result
        """
        if function_name not in self._tools_dict:
            return f"Error: Unknown function '{function_name}'"

        try:
            func = self._tools_dict[function_name]
            result = func(**arguments)
            return json.dumps(result) if not isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Tool execution failed: {function_name}({arguments}): {e}")
            return f"Error: {e}"

    async def _call_model(self) -> Any:
        """Make an API call to the model.

        Returns:
            The LiteLLM response object
        """
        # Per-model knobs from the registry (reasoning/thinking config), only
        # the ones that are set. Replaces the old hardcoded gemini special-case.
        extra_params = {}
        if self._model.max_tokens is not None:
            extra_params["max_tokens"] = self._model.max_tokens
        if self._model.reasoning_effort:
            extra_params["reasoning_effort"] = self._model.reasoning_effort
        if self._model.extra_body:
            extra_params["extra_body"] = self._model.extra_body

        return await acompletion(
            model=self._model.model_id,
            api_key=self._model.api_key,
            base_url=self._model.base_url,
            custom_llm_provider=self._model.provider,
            tools=self._tools_schema if self._tools_schema else None,
            parallel_tool_calls=True,
            tool_choice="auto" if self._tools_schema else None,
            messages=self._messages,
            temperature=self._model.temperature,
            **extra_params
        )

    def _extract_token_usage(self, response: Any) -> TokenUsage:
        """Extract token usage from LiteLLM response.

        Args:
            response: The LiteLLM response object

        Returns:
            TokenUsage with extracted values
        """
        if hasattr(response, 'usage') and response.usage:
            return TokenUsage(
                prompt_tokens=getattr(response.usage, 'prompt_tokens', 0) or 0,
                completion_tokens=getattr(response.usage, 'completion_tokens', 0) or 0,
                total_tokens=getattr(response.usage, 'total_tokens', 0) or 0
            )
        return TokenUsage()

    async def run(self, query: str) -> AgentResponse:
        """Run the agent with a query using the agentic loop.

        The agent will:
        1. Add user query to message history
        2. Call model
        3. If model returns tool calls, execute them and add results to history
        4. Repeat until model returns final response or max_steps reached

        Args:
            query: The user input query

        Returns:
            AgentResponse with result, all tool calls made, step count, and token usage
        """
        # Add user message to history
        self._messages.append({"role": "user", "content": query})

        all_tool_calls: List[ToolCall] = []
        steps = 0
        total_token_usage = TokenUsage()
        started = time.monotonic()

        while steps < self._max_steps:
            steps += 1

            try:
                response = await self._call_model()
            except Exception as e:
                logger.error(f"LiteLLM API call failed: {e}")
                return AgentResponse(
                    content=f"Error: {e}",
                    tool_calls=all_tool_calls,
                    steps=steps,
                    token_usage=total_token_usage,
                    elapsed=time.monotonic() - started,
                    stop_reason="model_error",
                )

            # Accumulate token usage from this API call
            total_token_usage = total_token_usage + self._extract_token_usage(response)

            choice = response.choices[0]
            assistant_message = choice.message

            # Check if model wants to call tools
            if choice.finish_reason == "tool_calls" and assistant_message.tool_calls:

                logger.debug(f"Tool calls: {assistant_message.tool_calls}")
                logger.debug(f"Assistant message: {assistant_message}")
                
                # Add assistant message with tool calls to history
                self._messages.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                # Execute each tool call and add results
                for tool_call in assistant_message.tool_calls:
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse arguments: {tool_call.function.arguments}")
                        arguments = {}

                    # Record the tool call
                    agent_tool_call = ToolCall(
                        call_id=tool_call.id,
                        function=tool_call.function.name,
                        arguments=arguments
                    )
                    all_tool_calls.append(agent_tool_call)

                    # Execute the tool
                    result = self._execute_tool(tool_call.function.name, arguments)

                    # Add tool result to message history
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

                # Continue the loop to get model's next response
                continue

            else:
                # Model returned final response (no tool calls)
                content = assistant_message.content or ""

                # Add final assistant message to history
                self._messages.append({
                    "role": "assistant",
                    "content": content
                })

                self._total_steps += steps
                self._total_token_usage = self._total_token_usage + total_token_usage

                return AgentResponse(
                    content=content,
                    tool_calls=all_tool_calls,
                    steps=steps,
                    token_usage=total_token_usage,
                    elapsed=time.monotonic() - started,
                    stop_reason="completed",
                )

        # Max steps reached
        logger.warning(f"Max steps ({self._max_steps}) reached")
        self._total_steps += steps
        self._total_token_usage = self._total_token_usage + total_token_usage

        return AgentResponse(
            content="Max steps reached without final response",
            tool_calls=all_tool_calls,
            steps=steps,
            token_usage=total_token_usage,
            elapsed=time.monotonic() - started,
            stop_reason="max_steps",
        )

    @property
    def messages(self) -> List[Dict[str, Any]]:
        """The conversation history, for the transcript written beside results.

        OpenAI-style dicts, written through as they are: a tool call and its
        result are the record of what this agent actually did, and a result
        file keeps only the outcome.
        """
        return self._messages

    def get_total_steps(self) -> int:
        """Get total steps taken across all runs."""
        return self._total_steps

    def get_total_token_usage(self) -> TokenUsage:
        """Get total token usage across all runs."""
        return self._total_token_usage

    def clear_history(self) -> None:
        """Clear conversation history for a fresh start (keeps system prompt)."""
        self._messages = []
        if self._system_prompt:
            self._messages.append({"role": "system", "content": self._system_prompt})
        self._total_steps = 0
        self._total_token_usage = TokenUsage()


class LitellmAgentFactory(AgentFactory):
    """Factory for creating LiteLLM-based agents.

    This factory creates agents that use JSON function calling
    with a proper agentic loop (execute tools, feed back results).
    """

    def __init__(self, model: LitellmModel, max_steps: int = 20):
        """Initialize the factory with a model configuration.

        Args:
            model: The LiteLLM model configuration
            max_steps: Maximum steps per agent run (default: 20)
        """
        self.model = model
        self.max_steps = max_steps

    def create_agent(
        self,
        functions: List[Callable],
        variables: Optional[List[Any]] = None,
        types: Optional[List[Any]] = None,
        description: Optional[str] = None,
    ) -> LitellmAgentWrapper:
        """Create a LiteLLM agent with the specified functions.

        Args:
            functions: List of callable functions
            variables: Ignored (for interface compatibility)
            types: Ignored (for interface compatibility)
            description: Task description for system prompt

        Returns:
            A LitellmAgentWrapper instance
        """
        return LitellmAgentWrapper(
            model=self.model,
            tools=functions,
            max_steps=self.max_steps,
            description=description,
        )
