"""
CaveAgent adapter for tau2-bench evaluation framework.

This adapter leverages CaveAgent's built-in function description and
system prompt building for cleaner, more maintainable code.
"""

import asyncio
from token import OP
from typing import List, Optional
from loguru import logger
from pydantic import BaseModel

from cave_agent import CaveAgent, LogLevel, SecurityChecker
from cave_agent.python_runtime import PythonRuntime, Function
from cave_agent import FunctionRule
from cave_agent.models import OpenAIServerModel, LiteLLMModel, GeminiModel, GPT5Model, AnthropicModel

from adapters.cave_agent_tracker import CaveAgentTracker
from tau2.agent.base import LocalAgent, ValidAgentInputMessage
from tau2.data_model.message import (
    AssistantMessage,
    Message,
    ToolCall,
    UserMessage,
)
from tau2.environment.tool import Tool
from tau2.data_model.tasks import Task

from core.conversation_storage import ConversationStorage
def serialize_argument(value):
    """Serialize a value to be JSON-compatible.

    Handles Pydantic models, lists, dicts, and primitive types.

    Args:
        value: Value to serialize

    Returns:
        JSON-serializable version of the value
    """
    # Handle None
    if value is None:
        return None

    # Handle Pydantic models (have model_dump method)
    if hasattr(value, 'model_dump'):
        return value.model_dump()

    # Handle lists
    if isinstance(value, list):
        return [serialize_argument(item) for item in value]

    # Handle tuples
    if isinstance(value, tuple):
        return tuple(serialize_argument(item) for item in value)

    # Handle dicts
    if isinstance(value, dict):
        return {k: serialize_argument(v) for k, v in value.items()}

    # Handle primitives (str, int, float, bool)
    if isinstance(value, (str, int, float, bool)):
        return value

    # For anything else, try str() as fallback
    logger.warning(f"Unknown type {type(value)} for serialization, using str()")
    return str(value)


def serialize_arguments(arguments: dict) -> dict:
    """Serialize all arguments in a dictionary.

    Args:
        arguments: Dictionary of argument name -> value

    Returns:
        Dictionary with all values serialized to JSON-compatible types
    """
    return {k: serialize_argument(v) for k, v in arguments.items()}


# Custom agent identity that includes policy awareness
AGENT_IDENTITY = """
You are an AI customer service agent.
You interact with the customer service system by writing Python code that will be executed in a provided Python environment.
You help the user according to the <policy> provided.
The user will give you a task and you should solve it by writing Python code.
Try to be helpful and always follow the policy.
"""

INSTRUCTIONS = """
1. Understand what the user wants - ask for missing information
2. When the task requires interacting with the system:
   - Write Python code in a markdown code block (```python ... ```)
   - Your code will be executed in a Python environment with access to predefined functions and variables
   - The execution result will be returned to you
   - You can use 'print()' to output important information
   - Review the result and write more code as needed until the task is completed
   - Output only the code. Do not include explanatory text before or after the code within the same response.
3. CRITICAL EXECUTION CONTEXT: You are operating in a persistent Jupyter-like environment where:
   - Each code block you write is executed in a new cell within the SAME continuous session
   - ALL variables, functions, and imports persist across cells automatically
   - You can directly reference any variable created in previous cells
4. IMPORTANT: Write code as plain text in markdown code blocks. Do NOT use any function calling syntax or tool invocation syntax.
5. If the task doesn't require code execution, provide a direct answer.
6. Always provide your final answer in plain text after the code execution completes.
7. You must not perform calculations yourself - use Python code for all operations.
8. Write your code in a single python code block per step.
9. Never predict or simulate code execution results - wait for actual results.
10. After each code execution, verify the results before proceeding.
11. Be concise.
12. If you need more information, ask the user.
13. Follow a observe-then-act pattern: after each code execution, carefully review the results before deciding next steps.
14. Attempt to complete the task fully before considering transfer to human. Only transfer after all reasonable approaches have been tried and failed, or when explicitly requested by the user.
15. Carefully review the execution result before providing your response.
16. Don't include any comments in your code block. Only write code.
17. Follow the policy exactly: {domain_policy}
"""
# RESPONSE FORMAT:
# - When you need to execute code, output it in a markdown code block like this:
# ```python
# # Your code here
# result = some_function()
# print(result)
# ```
# - After seeing execution results, provide your response to the user in plain text.
# - Do NOT use JSON, function calls, or any other format - only markdown code blocks and plain text.
# - Don't generate any tags like <functions>...</functions> in your response.
# - Don't generate any special tool calling tokens like tool_calls_section_begin,tool_call_begin in your response. You call tools by writing Python code.
# - Don't call Python input() function in your code block like this: input("Enter your name: "). It will cause the code to hang.
# 16. Include comments in your code block to explain your reasoning for key steps and non-obvious logic. Focus on "why" over "what."
class CaveAgentState(BaseModel):
    """State for CaveAgent.

    Note: CaveAgent maintains its own internal message history,
    so this state is minimal and mainly for tau2 compatibility.
    """
    turn_count: int = 0
    cached_response: Optional[str] = None  # Cache final response when reporting tool_calls
    waiting_for_tool_results: bool = False  # Flag to track if we're waiting for tau2 to execute tools

    class Config:
        arbitrary_types_allowed = True

def tau2_tool_to_cave_function(tool: Tool) -> Function:
    """Convert a tau2 Tool to a CaveAgent Function.

    Args:
        tool: tau2 Tool object

    Returns:
        CaveAgent Function object
    """
    # Get the actual callable from the tool (using private attribute)
    func = tool._func
    # CaveAgent's Function class automatically extracts docstring and signature
    return Function(func)


class Tau2CaveAgent(LocalAgent[CaveAgentState]):
    """CaveAgent adapter for tau2-bench framework.

    Uses CaveAgent's built-in features:
    - Automatic function description via runtime.describe_functions()
    - Built-in system prompt building via build_system_prompt()
    - Autonomous execution mode (runs complete task loops internally)

    This adapter lets CaveAgent execute tools in its Python runtime
    autonomously, rather than coordinating with tau2's orchestrator.
    """

    def __init__(
        self,
        tools: List[Tool],
        toolkit,
        domain_policy: str,
        llm_model_id: str,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_args: Optional[dict] = None,
        max_steps: int = 30,
        log_level: LogLevel = LogLevel.DEBUG,
        task: Optional[Task] = None,
        run_id: Optional[str] = None,
        run_domain: Optional[str] = None,
    ):
        """Initialize Tau2CaveAgent with isolated environment.

        Args:
            tools: List of tau2 Tool objects (for parent class compatibility)
            toolkit: The toolkit instance from tau2's environment (e.g., AirlineTools)
            domain_policy: Domain policy text that agent must follow
            llm_model_id: LLM model identifier
            llm_api_key: API key for LLM
            llm_base_url: Base URL for LLM API
            llm_args: Additional LLM arguments
            max_steps: Maximum execution steps
            log_level: Logging level (ERROR=0, INFO=1, DEBUG=2)
            task: Optional Task object for task context
            run_id: Optional run ID for conversation storage (e.g., timestamp)
            run_domain: Optional domain name for conversation storage folder
        """
        super().__init__(tools=tools, domain_policy=domain_policy)


        checker = SecurityChecker([
            FunctionRule(set(["input"]), "Don't call input() function in your code block. The user will input at the next turn."),
        ])

        # Initialize LLM model
        self.llm_model = OpenAIServerModel(
            model_id=llm_model_id,
            api_key=llm_api_key,
            base_url=llm_base_url,
            **(llm_args or {})
        )
        self.task = task

        # Setup conversation storage with run-specific folder
        # Format: ./conversations/{run_id}_{domain}/ or ./conversations/default/
        if run_id and run_domain:
            storage_folder = f"./conversations/{run_id}_{run_domain}"
        elif run_id:
            storage_folder = f"./conversations/{run_id}"
        elif run_domain:
            storage_folder = f"./conversations/{run_domain}"
        else:
            storage_folder = "./conversations/default"

        self.storage = ConversationStorage(storage_path=storage_folder)
        logger.info(f"Conversation storage initialized at: {storage_folder}")

        # ========================================
        # CREATE ISOLATED ENVIRONMENT
        # ========================================

        # The toolkit is passed directly from tau2's INITIALIZED environment
        # (with task-specific users, reservations, etc.)
        # We clone its database to create isolated tools

        original_toolkit = toolkit
        logger.info(f"Original toolkit: {type(original_toolkit).__name__}")
        logger.info(f"Original DB type: {type(original_toolkit.db).__name__}")
        logger.info(f"Original DB id: {id(original_toolkit.db)}")

        # Clone the database (deep copy preserves task initialization data)
        isolated_db = original_toolkit.db.model_copy(deep=True)
        logger.info(f"Created isolated database copy (id: {id(isolated_db)})")
        logger.info(f"Database isolation verified: {id(isolated_db) != id(original_toolkit.db)}")

        # Create new toolkit instance with cloned database
        toolkit_class = type(original_toolkit)
        isolated_toolkit = toolkit_class(db=isolated_db)
        logger.info(f"Created isolated toolkit: {type(isolated_toolkit).__name__}")

        # Get tools from isolated toolkit (these operate on isolated_db)
        isolated_tool_dict = isolated_toolkit.get_tools()
        tools_for_agent = list(isolated_tool_dict.values())
        logger.info(f"Created {len(tools_for_agent)} isolated tools")

        # Verify tool names match
        for orig, iso in zip(tools, tools_for_agent):
            if orig.name != iso.name:
                logger.warning(f"Tool name mismatch: {orig.name} != {iso.name}")

        # ========================================
        # CREATE CAVE AGENT WITH ISOLATED TOOLS
        # ========================================

        # Convert isolated tools to CaveAgent functions
        self.cave_functions = [
            tau2_tool_to_cave_function(tool) for tool in tools_for_agent
        ]

        # Create Python runtime with functions
        # CaveAgent will automatically describe these in the system prompt
        self.runtime = PythonRuntime(
            functions=self.cave_functions,
            security_checker=checker,
            variables=[]  # Can add domain-specific variables if needed
        )

        # Create CaveAgent with customized prompts
        # CaveAgent will automatically call runtime.describe_functions()
        # and runtime.describe_variables() when building system prompt
        self.cave_agent = CaveAgent(
            model=self.llm_model,
            runtime=self.runtime,
            agent_identity=AGENT_IDENTITY,
            max_steps=100,
            max_execution_result_length=10000,
            instructions=INSTRUCTIONS.format(domain_policy=domain_policy),
            max_history=100,  # Keep more history for multi-turn conversations
            log_level=log_level
        )

        # Store function names for tracking
        self.function_names = [f.name for f in self.cave_functions]

        logger.info(f"Initialized Tau2CaveAgent with {len(tools)} isolated tools")
        logger.info(f"Functions: {self.function_names}")
        logger.info("Database isolation: CaveAgent operates on isolated copy, tau2 validation uses original")


    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> CaveAgentState:
        """Get the initial state of the agent.

        Args:
            message_history: Optional message history (ignored, CaveAgent manages its own)

        Returns:
            CaveAgentState
        """
        return CaveAgentState(
            turn_count=0,
            cached_response=None,
            waiting_for_tool_results=False
        )

    def generate_next_message(
        self, message: ValidAgentInputMessage, state: CaveAgentState
    ) -> tuple[AssistantMessage, CaveAgentState]:
        """Generate the next message using CaveAgent.

        CaveAgent executes tools internally in its Python runtime,
        so we only process UserMessages and let CaveAgent handle
        the entire execution loop autonomously.

        Args:
            message: Input message (only UserMessage is processed)
            state: Current agent state

        Returns:
            Tuple of (AssistantMessage, updated state)
        """

        # Handle non-user messages (ToolMessage, MultiToolMessage)
        if not isinstance(message, UserMessage):
            logger.debug(f"Ignoring non-user message: {type(message).__name__}")

            # If we're waiting for tool results, return cached response
            if state.waiting_for_tool_results and state.cached_response:
                logger.info("Returning cached response after tool execution")
                state.waiting_for_tool_results = False
                cached_content = state.cached_response
                state.cached_response = None  # Clear cache
                return AssistantMessage(
                    role="assistant",
                    content=cached_content
                ), state

            # Otherwise, just acknowledge (shouldn't happen in normal flow)
            logger.warning("Received non-user message without cached response")
            return AssistantMessage(
                role="assistant",
                content="Acknowledged"
            ), state

        # Extract user query
        user_query = message.content
        logger.info(f"Processing user query: {user_query[:100]}...")

        try:
            # Create tracker for function calls
            tracker = CaveAgentTracker(target_functions=self.function_names)
            tracker.start()

            # Run CaveAgent - it will handle its own execution loop
            # including generating code, executing tools, and producing final answer
            logger.info("Running CaveAgent (autonomous mode)...")

            # Check if we're already in an event loop
            # try:
            #     asyncio.get_running_loop()
            #     # We're in a running loop, use nest_asyncio
            #     import nest_asyncio
            #     nest_asyncio.apply()
            #     response = asyncio.run(self.cave_agent.run(user_query))
            # except RuntimeError:
            #     # No running loop, safe to use asyncio.run()
            #     response = asyncio.run(self.cave_agent.run(user_query))

            import nest_asyncio
            nest_asyncio.apply()
            response = asyncio.run(self.cave_agent.run(user_query))
            # print("cave agent response", response)

            tracker.stop()

            logger.info(f"CaveAgent completed with status: {response.status.value}")
            logger.info(f"Steps taken: {response.steps_taken}/{response.max_steps}")

            # Save conversation for this task
            task_id = self.task.id if self.task else f"unknown_{state.turn_count}"
            try:
                self.storage.save_messages(
                    messages=self.cave_agent.messages,
                    conversation_id=task_id
                )
                logger.info(f"Saved conversation for task {task_id} ({len(self.cave_agent.messages)} messages)")
            except Exception as save_error:
                logger.warning(f"Failed to save conversation for task {task_id}: {save_error}")

            # CaveAgent has completed its execution loop and returned final answer
            # The tracker captured all function calls that happened during execution
            tool_calls_made = tracker.get_tool_calls()
            logger.debug(f"Tool calls made: {tool_calls_made}")
            logger.info(f"CaveAgent executed {len(tool_calls_made)} tool calls during execution")

            # Convert tracked tool calls to tau2's ToolCall format for evaluation
            tau2_tool_calls = []
            if tool_calls_made:
                for agent_call in tool_calls_made:
                    # Serialize arguments to handle Pydantic models and complex types
                    serialized_args = serialize_arguments(agent_call.arguments)

                    tool_call = ToolCall(
                        id=str(agent_call.call_id),  # Convert int to string
                        name=agent_call.function,
                        arguments=serialized_args,  # Use serialized arguments
                        requestor="assistant"
                    )
                    tau2_tool_calls.append(tool_call)
                logger.info(f"Converted {len(tau2_tool_calls)} tool calls for evaluation")

            # CRITICAL FOR EVALUATION: tau2 does NOT allow both content and tool_calls
            # in the same message. So we must split this into two turns:
            # 1. First: Return tool_calls ONLY (for evaluation)
            # 2. Second: After tau2 "executes" them, return cached content
            if tau2_tool_calls:
                # Cache the final response to return after tau2 executes tools
                state.cached_response = response.content
                state.waiting_for_tool_results = True
                logger.info(f"Cached response for after tool execution: {response.content[:100] if response.content else 'None'}...")

                # Return ONLY tool calls (no content) for evaluation
                assistant_message = AssistantMessage(
                    role="assistant",
                    content=None,  # MUST be None for tool_calls
                    tool_calls=tau2_tool_calls
                )
                logger.info(f"Returning {len(tau2_tool_calls)} tool calls")
            else:
                # No tool calls were made (pure text response)
                assistant_message = AssistantMessage(
                    role="assistant",
                    content=response.content
                )
                logger.info(f"Returning text response: {assistant_message.content[:100]}...")

            # Increment turn counter
            state.turn_count += 1

            return assistant_message, state

        except Exception as e:
            logger.error(f"Error in CaveAgent: {e}")
            import traceback
            traceback.print_exc()

            # Return error message
            error_message = AssistantMessage(
                role="assistant",
                content=f"I encountered an error while processing your request. Please try again."
            )
            return error_message, state


class Tau2CaveAgentFactory:
    """Factory for creating Tau2CaveAgent instances."""

    def __init__(
        self,
        llm_model_id: str,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_args: Optional[dict] = None,
        max_steps: int = 30,
        log_level: LogLevel = LogLevel.DEBUG,
        run_id: Optional[str] = None,
        run_domain: Optional[str] = None,
    ):
        """Initialize factory.

        Args:
            llm_model_id: LLM model identifier
            llm_api_key: API key for LLM
            llm_base_url: Base URL for LLM API
            llm_args: Additional LLM arguments
            max_steps: Maximum execution steps per run
            log_level: Logging level
            run_id: Run ID for conversation storage folder
            run_domain: Domain for conversation storage folder
        """
        self.llm_model_id = llm_model_id
        self.llm_api_key = llm_api_key
        self.llm_base_url = llm_base_url
        self.llm_args = llm_args or {}
        self.max_steps = max_steps
        self.log_level = log_level
        self.run_id = run_id
        self.run_domain = run_domain

    def create_agent(
        self,
        tools: List[Tool],
        toolkit,
        domain_policy: str,
        task: Optional[Task] = None,
    ) -> Tau2CaveAgent:
        """Create a Tau2CaveAgent instance.

        Args:
            tools: List of tau2 Tool objects (for parent class compatibility)
            toolkit: The toolkit instance from tau2's environment
            domain_policy: Domain policy text
            task: Optional Task object for task context

        Returns:
            Tau2CaveAgent instance
        """
        return Tau2CaveAgent(
            tools=tools,
            toolkit=toolkit,
            domain_policy=domain_policy,
            llm_model_id=self.llm_model_id,
            llm_api_key=self.llm_api_key,
            llm_base_url=self.llm_base_url,
            llm_args=self.llm_args,
            max_steps=self.max_steps,
            log_level=self.log_level,
            task=task,
            run_id=self.run_id,
            run_domain=self.run_domain,
        )
