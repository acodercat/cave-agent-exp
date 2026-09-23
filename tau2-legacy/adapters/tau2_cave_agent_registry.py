"""
Registry integration for Tau2CaveAgent.

This module provides a registry-compatible wrapper that allows CaveAgent to be used
with tau2's native `tau2 run` command.

Usage:
    1. Register the agent in your tau2-bench installation
    2. Run: tau2 run --agent cave_agent --domain airline --agent-llm <model> ...
"""

from typing import List, Optional
from loguru import logger

from tau2.agent.base import LocalAgent, ValidAgentInputMessage
from tau2.data_model.message import AssistantMessage, Message
from tau2.environment.tool import Tool

from adapters.tau2_cave_agent_adapter import (
    Tau2CaveAgentFactory,
    CaveAgentState,
)
from cave_agent import LogLevel
from tau2.data_model.tasks import Task


class Tau2CaveAgentRegistry(LocalAgent[CaveAgentState]):
    """Registry-compatible wrapper for Tau2CaveAgent.

    This class matches tau2's expected agent constructor signature:
        __init__(tools, domain_policy, llm, llm_args)

    It can be registered with tau2's global registry and used with `tau2 run`.

    The wrapper extracts the toolkit from the tools list and delegates all
    operations to the underlying Tau2CaveAgent.
    """

    def __init__(
        self,
        tools: List[Tool],
        domain_policy: str,
        llm: str,
        llm_args: Optional[dict] = None,
        task: Optional[Task] = None,
    ):
        """Initialize registry-compatible CaveAgent wrapper.

        Args:
            tools: List of tau2 Tool objects from environment.get_tools()
            domain_policy: Domain policy text
            llm: LLM model identifier (e.g., "deepseek-chat")
            llm_args: Additional LLM arguments (temperature, etc.)
        """
        # Initialize LocalAgent parent (only takes tools and domain_policy)
        super().__init__(tools=tools, domain_policy=domain_policy)

        if not tools:
            raise ValueError("Tools list cannot be empty")

        # Extract toolkit from tools
        # All tools are bound methods of the same toolkit instance
        # We can access it via tools[0]._func.__self__
        toolkit = tools[0]._func.__self__

        logger.info(f"Extracted toolkit: {type(toolkit).__name__}")
        logger.info(f"Toolkit DB: {type(toolkit.db).__name__} (id: {id(toolkit.db)})")

        # Parse LLM configuration
        # tau2 passes model ID as string and args as dict
        llm_args = llm_args or {}

        # Extract base_url and api_key if provided in llm_args
        # Use .get() instead of .pop() to avoid modifying the original dict
        # (tau2 may reuse the same dict for multiple tasks)
        llm_base_url = llm_args.get("base_url", None)
        llm_api_key = llm_args.get("api_key", None)

        # Max steps from llm_args (if provided) or use default
        max_steps = llm_args.get("max_steps", 30)

        # Log level from llm_args (if provided) or use default
        log_level_str = llm_args.get("log_level", "INFO")
        log_level_map = {
            "ERROR": LogLevel.ERROR,
            "INFO": LogLevel.INFO,
            "DEBUG": LogLevel.DEBUG,
        }
        log_level = log_level_map.get(log_level_str.upper(), LogLevel.INFO)

        # Extract conversation storage settings
        run_id = llm_args.get("run_id", None)
        run_domain = llm_args.get("run_domain", None)

        # Create a copy of llm_args without our custom parameters
        # (api_key, base_url, max_steps, log_level, run_id, run_domain are handled separately)
        remaining_llm_args = {
            k: v for k, v in llm_args.items()
            if k not in ["api_key", "base_url", "max_steps", "log_level", "run_id", "run_domain"]
        }

        # Create factory with configuration
        factory = Tau2CaveAgentFactory(
            llm_model_id=llm,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            llm_args=remaining_llm_args,  # Remaining args (temperature, etc.)
            max_steps=max_steps,
            log_level=log_level,
            run_id=run_id,
            run_domain=run_domain,
        )

        # Create the actual CaveAgent with isolated environment
        self._agent = factory.create_agent(
            tools=tools,
            toolkit=toolkit,
            domain_policy=domain_policy,
            task=task,  # Pass task through to Tau2CaveAgent
        )

        logger.info(f"Initialized Tau2CaveAgentRegistry with {len(tools)} tools")

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> CaveAgentState:
        """Get initial state - delegate to wrapped agent."""
        return self._agent.get_init_state(message_history)

    def generate_next_message(
        self, message: ValidAgentInputMessage, state: CaveAgentState
    ) -> tuple[AssistantMessage, CaveAgentState]:
        """Generate next message - delegate to wrapped agent."""
        return self._agent.generate_next_message(message, state)


# Default configuration for tau2 registry
DEFAULT_MAX_STEPS = 30
DEFAULT_LOG_LEVEL = LogLevel.INFO


def create_cave_agent_for_registry(
    tools: List[Tool],
    domain_policy: str,
    llm: str,
    llm_args: Optional[dict] = None,
) -> Tau2CaveAgentRegistry:
    """Factory function for creating CaveAgent instances for tau2 registry.

    This function signature matches what tau2 expects for agent constructors.

    Args:
        tools: List of tau2 Tool objects
        domain_policy: Domain policy text
        llm: LLM model identifier
        llm_args: Additional LLM arguments

    Returns:
        Tau2CaveAgentRegistry instance
    """
    return Tau2CaveAgentRegistry(
        tools=tools,
        domain_policy=domain_policy,
        llm=llm,
        llm_args=llm_args,
    )
