import logging
from typing import Dict, List, Any, Callable
from core.validation import validate_function_calls, ErrorType
from core.agent import Agent, AgentFactory, AgentToolCall

logger = logging.getLogger('Agent.Evaluator')



class AgentEvaluator:
    def __init__(self, agent_factory: AgentFactory):
        """
        Initialize the evaluator with an agent factory.
        
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
        self.metrics = {
            "total_turns": 0,
            "successful_turns": 0,
            "failed_turns": 0,
            "total_expected_calls": 0,
            "total_actual_calls": 0,
            "missing_calls": 0,
            "wrong_argument_values": 0,
            "wrong_argument_types": 0,
            "missing_arguments": 0,
            "wrong_argument_names": 0,
            "total_steps": 0,
            "success_rate": 0,
        }

    async def evaluate(self, scenario: str, module, conversations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an agent against a specific scenario.
        
        Args:
            scenario: The scenario name
            module: The scenario module
            conversations: The conversations to evaluate
            
        Returns:
            Evaluation results
        """
        results = {
            "scenario": scenario,
            "conversations": []
        }

        # Reset metrics at the start of evaluation
        self._reset_metrics()

        # Get tools from the module
        tools = getattr(module, "tools", None)
        if not tools:
            raise ValueError(f"No tools found in scenario module {scenario}. Please define a 'tools' list in the scenario module.")
        logger.info(f"Evaluating scenario {scenario} with {len(conversations)} conversations")
        
        # Process each conversation
        for conversation in conversations:
            try:
                conversation_results = await self._evaluate_conversation(
                    conversation, tools, scenario_name=scenario
                )
                results["conversations"].append(conversation_results)
            except Exception as e:
                raise RuntimeError(f"Failed to evaluate conversation {conversation}: {e}")
        
        # Calculate success rate
        self.metrics["success_rate"] = self.metrics["successful_turns"] / self.metrics["total_turns"] if self.metrics["total_turns"] > 0 else 0
        
        logger.info(f"Evaluation complete. Success rate: {self.metrics['success_rate']:.2f}")
        # Add metrics to results
        results["metrics"] = self.metrics

        return results

    
    async def _evaluate_conversation(self, conversation: Dict[str, Any],
                               tools: List[Callable], scenario_name: str = None) -> Dict[str, Any]:
        """Evaluate a single conversation within a scenario."""
        conversation_id = conversation.get("id", "unnamed_conversation")
        logger.debug(f"Evaluating conversation: {conversation_id}")

        # Initialize results structure
        results = {
            "id": conversation_id,
            "turns": []
        }

        # Use scenario_name as task_name for conversation storage
        task_name = scenario_name

        # Initialize agent
        agent = self.agent_factory.create_agent(functions=tools, task_name=task_name)
        # Process each turn
        for turn_index, turn in enumerate(conversation.get("turns", [])):
            turn_results = await self._evaluate_turn(
                turn, agent
            )
            results["turns"].append(turn_results)
            self.metrics["total_steps"] += turn_results["metrics"]["steps"]
     
        return results
    
    def calculate_missing_calls_metric(self, expected_calls: List[Dict[str, Any]], actual_calls: List[AgentToolCall]) -> int:
        """
        Calculate the number of missing required function calls.
        
        Args:
            expected_calls: List of expected function calls from ground_truths.json
            actual_calls: List of actual function calls from the tracker
            
        Returns:
            Number of missing required function calls
        """
        missing_required_calls = 0
        
        # Create a set of function names from actual calls for quick lookup
        actual_function_names = {call.function for call in actual_calls}
        
        # Count missing required calls
        for expected in expected_calls:
            is_required = expected.get("required", True)  # Default to True if not specified
            expected_name = expected.get("name")
            if is_required and expected_name not in actual_function_names:
                missing_required_calls += 1

        return missing_required_calls

    async def _evaluate_turn(self, turn: Dict[str, Any], 
                       agent: Agent) -> Dict[str, Any]:
        """Evaluate a single turn within a conversation and return detailed metrics."""
        query = turn["query"]
        reference_response = turn.get("reference_response", "")
        expected_calls = turn.get("expected_function_calls", [])
        
        
        # Initialize results
        turn_results = {
            "query": query,
            "reference_response": reference_response,
            "actual_response": "",
            "expected_calls": expected_calls,
            "actual_calls": [],
            "validation_errors": [],
            "metrics": {
                "missing_calls": 0,
                "wrong_argument_types": 0,
                "wrong_argument_values": 0,
                "missing_arguments": 0,
                "steps": 0,
            }
        }


        required_count = 0
        for call in expected_calls:
            if call.get('required') is True:
                required_count += 1

        self.metrics["total_expected_calls"] += required_count
        self.metrics["total_turns"] += 1
        
        # Run the agent with tracking
        response = await agent.run(query)
        turn_results["actual_response"] = response.get_result()
        turn_results["metrics"]["steps"] = response.get_steps()
        
        # Get function calls and convert to dictionaries
        actual_calls = response.get_tool_calls()
        turn_results["actual_calls"] = [call.__dict__ for call in actual_calls]
        self.metrics["total_actual_calls"] += len(actual_calls)
        
        # Validate function calls
        validation_errors = validate_function_calls(actual_calls, expected_calls)
        
        # Store error messages for display
        error_messages = [error.message for error in validation_errors]
        turn_results["validation_errors"] = error_messages
        # Count missing required calls

        turn_results["metrics"]["missing_calls"] = self.calculate_missing_calls_metric(expected_calls, actual_calls)
        self.metrics["missing_calls"] += turn_results["metrics"]["missing_calls"]

        # Count error types with separate missing and extra argument counts
        for error in validation_errors:
            # if error.error_type == ErrorType.EXTRA_FUNCTION:
            #     self.metrics["extra_calls"] += 1
            
            # if error.error_type == ErrorType.WRONG_FUNCTION_NAME:
            #     self.metrics["wrong_function_names"] += 1
            #     self.metrics["missing_calls"] += 1  
            
            if error.error_type == ErrorType.WRONG_ARGUMENT_TYPE:
                self.metrics["wrong_argument_types"] += 1
                turn_results["metrics"]["wrong_argument_types"] += 1
            elif error.error_type == ErrorType.WRONG_ARGUMENT_VALUE:
                self.metrics["wrong_argument_values"] += 1
                turn_results["metrics"]["wrong_argument_values"] += 1
            elif error.error_type == ErrorType.MISSING_ARGUMENT:
                self.metrics["missing_arguments"] += 1
                turn_results["metrics"]["missing_arguments"] += 1

        # Determine turn success
        if not validation_errors:
            self.metrics["successful_turns"] += 1
            turn_results["success"] = True
        else:
            self.metrics["failed_turns"] += 1
            turn_results["success"] = False
        
        return turn_results