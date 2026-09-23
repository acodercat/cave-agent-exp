from typing import List, Callable, Optional
from core.evaluator import Agent, AgentFactory
from adapters.cave_agent_tracker import CaveAgentTracker
from cave_agent import CaveAgent, LogLevel, Model
from cave_agent.python_runtime import PythonRuntime, Function
from core.agent import AgentResponse
from core.conversation_storage import ConversationStorage
from datetime import datetime
import logging

logger = logging.getLogger('Agent.CaveAgentFactory')


AGENT_IDENTITY = """
You are a tool-augmented agent specializing in Python programming that enables function-calling through LLM code generation. 
You have to leverage your coding capabilities to interact with tools through a Python runtime environment, allowing direct access to execution results and runtime state. 
The user will give you a task and you should solve it by writing Python code in the Python environment provided.
"""

INSTRUCTIONS = """
1. When the task requires interacting with the system:
   - Write Python code in a markdown code block (```python ... ```)
   - Your code will be executed in a Python environment with access to predefined functions and variables
   - The execution result will be returned to you
   - You can use 'print()' to output important information
   - Review the result and write more code as needed until the task is completed
   - Output only the code. Do not include explanatory text before or after the code within the same response.
2. CRITICAL EXECUTION CONTEXT: You are operating in a persistent Jupyter-like environment where:
   - Each code block you write is executed in a new cell within the SAME continuous session
   - ALL variables, functions, and imports persist across cells automatically
   - You can directly reference any variable created in previous cells
3. IMPORTANT: Write code as plain text in markdown code blocks. Do NOT use any function calling syntax or tool invocation syntax.
4. If the task doesn't require code execution, provide a direct answer.
5. Always provide your final answer in plain text after the code execution completes.
6. You must not perform calculations yourself - use Python code for all operations.
7. Don't care about the execution result. It's just for benchmarking.
8. Be concise.
9. IMPORTANT: Your code must be in a Python code block.
10.IMPORTANT:  When you need to execute code, output it in a Python code block like this:
```python
# Your code here
result = some_function()
print(result)
```
- After seeing execution results, provide your response to the user in plain text.
- Do NOT use JSON, function calls, or any other format - only markdown code blocks and plain text.

IMPORTANT:
Write comprehensive code solutions that solve the user's request completely in a single execution whenever possible. Avoid unnecessary step-by-step iterations.
## TASK Context
You are operating in a benchmark environment where:
- All functions are mocked implementations
- Focus on correct function invocation rather than return values
- Ensure all required functions are called with appropriate parameters
- The goal is to demonstrate proper tool usage and task completion flow
"""

class CaveAgentWrapper(Agent):
    """Agent implementation that wraps CaveAgent"""

    def __init__(self, model: Model, functions: List[Callable] = None, task_name: Optional[str] = None, storage_path: Optional[str] = None):
        """
        Initialize the CaveAgentWrapper.

        Args:
            model: The model to use
            functions: List of callable functions
            task_name: The name of the task/scenario for conversation storage
            storage_path: Path to store conversation files
        """
        functions = [Function(f) for f in functions]

        runtime = PythonRuntime(
            functions=functions,
        )


        self._agent = CaveAgent(model=model, runtime=runtime, max_history=200, log_level=LogLevel.INFO, agent_identity=AGENT_IDENTITY, instructions=INSTRUCTIONS, max_steps=4)
        self._functions = [f.name for f in functions]
        self._previous_steps = 0
        self._task_name = task_name
        self._storage = ConversationStorage(storage_path=storage_path) if storage_path else ConversationStorage()

    
    async def run(self, query: str) -> AgentResponse:
        """
        Run the agent with a query and return the response.

        Args:
            query: The user input query

        Returns:
            The agent's response as an AgentResponse object
        """
        tracker = CaveAgentTracker(target_functions=self._functions)
        # Start tracking
        tracker.start()

        # Run the agent
        result = await self._agent.run(query)

        # Stop tracking
        tracker.stop()

        # Save conversation history if task_name is provided
        if self._task_name:
            self._storage.save_messages(self._agent.messages, self._task_name)

        total_steps = result.steps_taken

        current_steps = total_steps - self._previous_steps

        self._previous_steps = current_steps

        return AgentResponse(result.content, tracker.get_tool_calls(), current_steps)


class CaveAgentFactory(AgentFactory):
    """Factory for creating CaveAgent instances."""

    def __init__(self, model: Model, base_storage_path: str = "./conversations"):
        """
        Initialize the CaveAgentFactory.

        Args:
            model: The model to use
            base_storage_path: Base path to store conversation files
        """
        self.model = model
        # Create storage path with model_id and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = model.model_id.replace("/", "_").replace(":", "_")
        self.storage_path = f"{base_storage_path}/{model_id}/{timestamp}"

    def create_agent(self, functions: List[Callable], task_name: Optional[str] = None) -> CaveAgentWrapper:
        """
        Create a CaveAgent with the specified functions.

        Args:
            functions: List of callable functions
            task_name: The name of the task/scenario for conversation storage
        Returns:
            A CaveAgentWrapper instance
        """
        return CaveAgentWrapper(
            model=self.model,
            functions=functions,
            task_name=task_name,
            storage_path=self.storage_path
        )

