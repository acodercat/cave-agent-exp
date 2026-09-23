from typing import Dict, Any, List, Callable
from abc import ABC, abstractmethod

class AgentToolCall():
    """Represents a tool call made by an agent."""
    
    def __init__(self, function: str, arguments: Dict[str, Any], call_id: str):
        """
        Initialize an AgentToolCall.
        
        Args:
            function: The name of the function to call
            arguments: The arguments to pass to the function
            call_id: Unique identifier for this tool call
        """
        self.function = function
        self.arguments = arguments
        self.call_id = call_id

class AgentResponse():
    """
    Represents the response from an agent.
    """

    def __init__(self, result: str, tool_calls: List[AgentToolCall], steps: int):
        self._result = result
        self._tool_calls = tool_calls
        self._steps = steps
    

    def get_result(self) -> str:
        """
        Get the result from the agent.
        
        Returns:
            The result from the agent
        """
        return self._result
    

    def get_tool_calls(self) -> List[AgentToolCall]:
        """
        Get the tool calls from the agent.
        
        Returns:
            A list of tool calls made by the agent
        """
        return self._tool_calls
    
    def get_steps(self) -> int:
        """
        Get the total number of steps taken by the agent.
        """
        return self._steps

class Agent(ABC):
    """Abstract base class for agent implementations."""
    
    
    @abstractmethod
    async def run(self, model: any, query: str) -> AgentResponse:
        """
        Run the agent with a query and return the response.
        
        Args:
            query: The user query
            model: The model to use
        Returns:
            The agent's response as a string
        """
        pass

class AgentFactory(ABC):
    """Abstract base class for agent factories."""
    
    @abstractmethod
    def create_agent(self, functions: List[Callable]) -> Agent:
        """
        Create an agent with the given functions/tools.
        
        Args:
            functions: List of callable functions
            
        Returns:
            An agent instance
        """
        pass