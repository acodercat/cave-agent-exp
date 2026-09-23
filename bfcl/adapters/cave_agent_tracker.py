import sys
import inspect
from core.agent import AgentToolCall
from typing import List, Optional


class CaveAgentTracker():
    """Tracker for CaveAgent function calls using Python's sys.setprofile."""
    
    def __init__(self, target_functions: Optional[List[str]] = None):
        """
        Initialize a function call and return value tracker.
        
        Args:
            target_functions: List of function names to track. If None, track all functions.
        """
        self.tool_calls = []
        self.current_call_id = 0
        self.target_functions = target_functions
        
    def start(self):
        """Start tracking function calls and returns"""
        self.tool_calls = []
        self.current_call_id = 0
        sys.setprofile(self._profile_handler)
        
    def stop(self):
        """Stop tracking function calls and returns"""
        sys.setprofile(None)
        
    def _profile_handler(self, frame, event, arg):
        """Profile handler to capture function calls and returns"""
        if event != 'call':
            return
            
        # Get function name
        func_name = frame.f_code.co_name
        
        # Check if this is a function we want to track
        if self.target_functions and func_name not in self.target_functions:
            return

        # Increment call ID for this function call
        self.current_call_id += 1
        call_id = self.current_call_id
        
        # Get function arguments
        arg_info = inspect.getargvalues(frame)
        arguments = {}
        
        # Process regular arguments
        for arg_name in arg_info.args:
            if arg_name == 'self':  # Skip self in methods
                continue
                
            if arg_name in arg_info.locals:
                value = arg_info.locals[arg_name]
                arguments[arg_name] = value
        
        tool_call = AgentToolCall(
            call_id=call_id,
            function=func_name,
            arguments=arguments
        )
        
        # Add to call history
        self.tool_calls.append(tool_call)
    
    def get_tool_calls(self):
        """Get tracked tool calls"""
        return self.tool_calls