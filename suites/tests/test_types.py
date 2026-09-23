"""Tests for core data types."""

from core.types import (
    ToolCall,
    VariableAccess,
    ExpectedArgument,
    ExpectedFunctionCall,
    Turn,
    Conversation,
    TurnMetrics,
    TurnResult,
    ConversationResult,
    ScenarioMetrics,
    ScenarioResult,
)


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_creation(self):
        call = ToolCall(
            function="get_weather",
            arguments={"city": "London"},
            call_id="call_123"
        )
        assert call.function == "get_weather"
        assert call.arguments == {"city": "London"}
        assert call.call_id == "call_123"

    def test_repr(self):
        call = ToolCall(
            function="get_weather",
            arguments={"city": "London"},
            call_id="call_123"
        )
        assert "get_weather" in repr(call)
        assert "call_123" in repr(call)

    def test_empty_arguments(self):
        call = ToolCall(function="get_time", arguments={}, call_id="call_456")
        assert call.arguments == {}


class TestVariableAccess:
    """Tests for VariableAccess dataclass."""

    def test_creation(self):
        access = VariableAccess(reads=["x", "y"], writes=["z"])
        assert access.reads == ["x", "y"]
        assert access.writes == ["z"]

    def test_empty_access(self):
        access = VariableAccess(reads=[], writes=[])
        assert access.reads == []
        assert access.writes == []


class TestExpectedArgument:
    """Tests for ExpectedArgument dataclass."""

    def test_basic_creation(self):
        arg = ExpectedArgument(name="city", value="London", type="str")
        assert arg.name == "city"
        assert arg.value == "London"
        assert arg.type == "str"
        assert arg.required is True  # default

    def test_optional_argument(self):
        arg = ExpectedArgument(name="limit", required=False)
        assert arg.required is False
        assert arg.value is None

    def test_to_dict(self):
        arg = ExpectedArgument(name="city", value="London", type="str")
        d = arg.to_dict()
        assert d["name"] == "city"
        assert d["value"] == "London"
        assert d["type"] == "str"
        assert d["required"] is True

    def test_to_dict_minimal(self):
        arg = ExpectedArgument(name="count")
        d = arg.to_dict()
        assert d["name"] == "count"
        assert "value" not in d  # None values excluded
        assert "type" not in d


class TestExpectedFunctionCall:
    """Tests for ExpectedFunctionCall dataclass."""

    def test_basic_creation(self):
        call = ExpectedFunctionCall(name="get_weather", required=True)
        assert call.name == "get_weather"
        assert call.required is True
        assert call.arguments == []
        assert call.strict_args is False

    def test_with_arguments(self):
        args = [
            ExpectedArgument(name="city", value="London", type="str"),
            ExpectedArgument(name="unit", value="celsius", type="str"),
        ]
        call = ExpectedFunctionCall(name="get_weather", arguments=args)
        assert len(call.arguments) == 2
        assert call.arguments[0].name == "city"

    def test_from_dict(self):
        data = {
            "name": "get_stock_prices",
            "required": True,
            "arguments": [
                {"name": "symbols", "value": ["AAPL", "GOOGL"], "type": "list"}
            ]
        }
        call = ExpectedFunctionCall.from_dict(data)
        assert call.name == "get_stock_prices"
        assert call.required is True
        assert len(call.arguments) == 1
        assert call.arguments[0].name == "symbols"
        assert call.arguments[0].value == ["AAPL", "GOOGL"]

    def test_from_dict_defaults(self):
        data = {"name": "get_time"}
        call = ExpectedFunctionCall.from_dict(data)
        assert call.name == "get_time"
        assert call.required is True  # default
        assert call.arguments == []
        assert call.strict_args is False

    def test_to_dict(self):
        args = [ExpectedArgument(name="city", value="London", type="str")]
        call = ExpectedFunctionCall(name="get_weather", arguments=args)
        d = call.to_dict()
        assert d["name"] == "get_weather"
        assert d["required"] is True
        assert len(d["arguments"]) == 1


class TestTurn:
    """Tests for Turn dataclass."""

    def test_basic_creation(self):
        turn = Turn(query="What is the weather?")
        assert turn.query == "What is the weather?"
        assert turn.expected_function_calls == []
        assert turn.reference_response == ""
        assert turn.validator is None

    def test_with_expected_calls(self):
        calls = [ExpectedFunctionCall(name="get_weather")]
        turn = Turn(
            query="What is the weather?",
            expected_function_calls=calls,
            validator="validate_weather"
        )
        assert len(turn.expected_function_calls) == 1
        assert turn.validator == "validate_weather"

    def test_from_dict(self):
        data = {
            "query": "Get prices for AAPL",
            "expected_function_calls": [
                {"name": "get_stock_prices", "arguments": []}
            ],
            "validator": "validate_prices",
            "expected_variable_reads": ["portfolio"],
            "expected_variable_writes": ["last_prices"]
        }
        turn = Turn.from_dict(data)
        assert turn.query == "Get prices for AAPL"
        assert len(turn.expected_function_calls) == 1
        assert turn.validator == "validate_prices"
        assert turn.expected_variable_reads == ["portfolio"]
        assert turn.expected_variable_writes == ["last_prices"]

    def test_from_dict_with_hook(self):
        data = {
            "query": "",
            "pre_turn_hook": "setup_game_state"
        }
        turn = Turn.from_dict(data)
        assert turn.pre_turn_hook == "setup_game_state"


class TestConversation:
    """Tests for Conversation dataclass."""

    def test_creation(self):
        turns = [Turn(query="Hello")]
        conv = Conversation(id="test_conv", turns=turns)
        assert conv.id == "test_conv"
        assert len(conv.turns) == 1

    def test_from_dict(self):
        data = {
            "id": "portfolio_analysis",
            "turns": [
                {"query": "Analyze my portfolio"},
                {"query": "What is the risk?"}
            ]
        }
        conv = Conversation.from_dict(data)
        assert conv.id == "portfolio_analysis"
        assert len(conv.turns) == 2
        assert conv.turns[0].query == "Analyze my portfolio"

    def test_from_dict_default_id(self):
        data = {"turns": []}
        conv = Conversation.from_dict(data)
        assert conv.id == "unnamed_conversation"


class TestTurnMetrics:
    """Tests for TurnMetrics dataclass."""

    def test_defaults(self):
        metrics = TurnMetrics()
        assert metrics.missing_calls == 0
        assert metrics.wrong_argument_types == 0
        assert metrics.wrong_argument_values == 0
        assert metrics.missing_arguments == 0
        assert metrics.steps == 0
        assert metrics.prompt_tokens == 0
        assert metrics.completion_tokens == 0
        assert metrics.total_tokens == 0

    def test_with_values(self):
        metrics = TurnMetrics(
            missing_calls=1,
            wrong_argument_values=2,
            steps=3,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        assert metrics.missing_calls == 1
        assert metrics.steps == 3
        assert metrics.total_tokens == 150

    def test_to_dict(self):
        metrics = TurnMetrics(missing_calls=1, steps=2)
        d = metrics.to_dict()
        assert d["missing_calls"] == 1
        assert d["steps"] == 2
        assert "prompt_tokens" in d


class TestTurnResult:
    """Tests for TurnResult dataclass."""

    def test_creation(self):
        metrics = TurnMetrics(steps=2)
        result = TurnResult(
            query="Test query",
            reference_response="Expected",
            response="Got this",
            expected_calls=[],
            actual_calls=[],
            validation_errors=[],
            metrics=metrics,
            success=True
        )
        assert result.query == "Test query"
        assert result.success is True
        assert result.metrics.steps == 2

    def test_to_dict(self):
        metrics = TurnMetrics(steps=2)
        result = TurnResult(
            query="Test",
            reference_response="",
            response="Response",
            expected_calls=[{"name": "func1"}],
            actual_calls=[{"name": "func1", "arguments": {}}],
            validation_errors=["Error 1"],
            metrics=metrics,
            success=False
        )
        d = result.to_dict()
        assert d["query"] == "Test"
        assert d["success"] is False
        assert d["metrics"]["steps"] == 2
        assert len(d["validation_errors"]) == 1


class TestScenarioMetrics:
    """Tests for ScenarioMetrics dataclass."""

    def test_defaults(self):
        metrics = ScenarioMetrics()
        assert metrics.total_turns == 0
        assert metrics.successful_turns == 0
        assert metrics.failed_turns == 0
        assert metrics.success_rate == 0.0

    def test_to_dict(self):
        metrics = ScenarioMetrics(
            total_turns=10,
            successful_turns=8,
            failed_turns=2,
            success_rate=0.8
        )
        d = metrics.to_dict()
        assert d["total_turns"] == 10
        assert d["success_rate"] == 0.8


class TestScenarioResult:
    """Tests for ScenarioResult dataclass."""

    def test_creation(self):
        metrics = ScenarioMetrics(total_turns=1, successful_turns=1)
        turn_metrics = TurnMetrics()
        turn_result = TurnResult(
            query="Test",
            reference_response="",
            response="OK",
            expected_calls=[],
            actual_calls=[],
            validation_errors=[],
            metrics=turn_metrics,
            success=True
        )
        conv_result = ConversationResult(id="conv1", turns=[turn_result])
        result = ScenarioResult(
            scenario="test_scenario",
            conversations=[conv_result],
            metrics=metrics
        )
        assert result.scenario == "test_scenario"
        assert len(result.conversations) == 1

    def test_to_dict(self):
        metrics = ScenarioMetrics(total_turns=1)
        result = ScenarioResult(
            scenario="test",
            conversations=[],
            metrics=metrics
        )
        d = result.to_dict()
        # The scenario name is the result file's enclosing key; embedding it
        # again was a byte-for-byte duplicate and is deliberately absent.
        assert "scenario" not in d
        assert "conversations" in d
        assert "metrics" in d
