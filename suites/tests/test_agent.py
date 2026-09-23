"""Tests for agent interfaces."""

from core.agent import TokenUsage, AgentResponse
from core.types import ToolCall


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_defaults(self):
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_with_values(self):
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_addition(self):
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300)
        combined = usage1 + usage2
        assert combined.prompt_tokens == 300
        assert combined.completion_tokens == 150
        assert combined.total_tokens == 450

    def test_addition_with_zero(self):
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        zero = TokenUsage()
        combined = usage + zero
        assert combined.prompt_tokens == 100
        assert combined.completion_tokens == 50
        assert combined.total_tokens == 150

    def test_to_dict(self):
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        d = usage.to_dict()
        assert d == {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_creation(self):
        call = ToolCall(
            function="get_weather",
            arguments={"city": "London", "unit": "celsius"},
            call_id="call_abc123"
        )
        assert call.function == "get_weather"
        assert call.arguments == {"city": "London", "unit": "celsius"}
        assert call.call_id == "call_abc123"

    def test_empty_arguments(self):
        call = ToolCall(
            function="get_time",
            arguments={},
            call_id="call_xyz"
        )
        assert call.arguments == {}

    def test_to_dict(self):
        call = ToolCall(
            function="get_weather",
            arguments={"city": "London"},
            call_id="call_123"
        )
        d = call.to_dict()
        assert d == {
            "function": "get_weather",
            "arguments": {"city": "London"},
            "call_id": "call_123"
        }

    def test_complex_arguments(self):
        call = ToolCall(
            function="analyze_data",
            arguments={
                "data": [1, 2, 3, 4, 5],
                "options": {"normalize": True, "threshold": 0.5}
            },
            call_id="call_complex"
        )
        assert call.arguments["data"] == [1, 2, 3, 4, 5]
        assert call.arguments["options"]["normalize"] is True


class TestAgentResponse:
    """Tests for AgentResponse dataclass."""

    def test_basic_creation(self):
        response = AgentResponse(
            content="The weather is sunny.",
            tool_calls=[],
            steps=1
        )
        assert response.content == "The weather is sunny."
        assert response.tool_calls == []
        assert response.steps == 1
        assert response.code_snippets == []
        assert response.token_usage.total_tokens == 0

    def test_with_tool_calls(self):
        tool_calls = [
            ToolCall(function="get_weather", arguments={"city": "London"}, call_id="1"),
            ToolCall(function="get_forecast", arguments={"city": "London", "days": 5}, call_id="2"),
        ]
        response = AgentResponse(
            content="Weather info retrieved.",
            tool_calls=tool_calls,
            steps=2
        )
        assert len(response.tool_calls) == 2
        assert response.tool_calls[0].function == "get_weather"
        assert response.tool_calls[1].function == "get_forecast"

    def test_with_code_snippets(self):
        response = AgentResponse(
            content="Analysis complete.",
            tool_calls=[],
            steps=1,
            code_snippets=[
                "prices = get_stock_prices(['AAPL'])",
                "print(prices)"
            ]
        )
        assert len(response.code_snippets) == 2
        assert "get_stock_prices" in response.code_snippets[0]

    def test_with_token_usage(self):
        usage = TokenUsage(prompt_tokens=500, completion_tokens=200, total_tokens=700)
        response = AgentResponse(
            content="Done.",
            tool_calls=[],
            steps=3,
            token_usage=usage
        )
        assert response.token_usage.prompt_tokens == 500
        assert response.token_usage.completion_tokens == 200
        assert response.token_usage.total_tokens == 700


    def test_full_response(self):
        """Test a complete response with all fields."""
        calls = [
            ToolCall(
                function="get_stock_prices",
                arguments={"symbols": ["AAPL", "GOOGL"]},
                call_id="call_1"
            ),
            ToolCall(
                function="calculate_portfolio_value",
                arguments={"holdings": {"AAPL": 100}},
                call_id="call_2"
            ),
        ]
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        response = AgentResponse(
            content="Portfolio analysis complete. Total value: $18,550.00",
            tool_calls=calls,
            steps=2,
            code_snippets=[
                "prices = get_stock_prices(['AAPL', 'GOOGL'])",
                "portfolio = calculate_portfolio_value({'AAPL': 100})"
            ],
            token_usage=usage
        )

        assert response.content == "Portfolio analysis complete. Total value: $18,550.00"
        assert len(response.tool_calls) == 2
        assert response.steps == 2
        assert len(response.code_snippets) == 2
        assert response.token_usage.total_tokens == 1500
