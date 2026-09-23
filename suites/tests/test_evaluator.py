"""Tests for benchmark evaluation engine."""

import pytest
from core.evaluator import analyze_variable_access, VariableAnalyzer, Evaluator
from core.types import VariableAccess, ExpectedFunctionCall, ToolCall


class TestAnalyzeVariableAccess:
    """Tests for analyze_variable_access function."""

    def test_simple_read(self):
        code = "print(x)"
        result = analyze_variable_access(code)
        assert "x" in result.reads
        assert len(result.writes) == 0

    def test_simple_write(self):
        code = "x = 5"
        result = analyze_variable_access(code)
        assert "x" in result.writes

    def test_read_and_write(self):
        code = "y = x + 1"
        result = analyze_variable_access(code)
        assert "x" in result.reads
        assert "y" in result.writes

    def test_multiple_reads(self):
        code = "result = a + b + c"
        result = analyze_variable_access(code)
        assert "a" in result.reads
        assert "b" in result.reads
        assert "c" in result.reads
        assert "result" in result.writes

    def test_multiple_writes(self):
        code = """x = 1
y = 2
z = 3"""
        result = analyze_variable_access(code)
        assert "x" in result.writes
        assert "y" in result.writes
        assert "z" in result.writes

    def test_function_call(self):
        code = "prices = get_stock_prices(['AAPL'])"
        result = analyze_variable_access(code)
        assert "prices" in result.writes
        # Note: get_stock_prices is a function call, not a variable read

    def test_complex_code(self):
        code = """
total = 0
for item in items:
    total = total + item.price
print(total)
"""
        result = analyze_variable_access(code)
        assert "total" in result.writes
        assert "items" in result.reads
        assert "item" in result.writes  # loop variable

    def test_augmented_assignment(self):
        code = "count += 1"
        result = analyze_variable_access(code)
        # Note: The simple VariableAnalyzer only detects the write for augmented assignments
        # It doesn't detect the implicit read (this is a limitation of the simple analyzer)
        assert "count" in result.writes

    def test_empty_code(self):
        code = ""
        result = analyze_variable_access(code)
        assert result.reads == []
        assert result.writes == []

    def test_invalid_syntax(self):
        code = "this is not valid python {{"
        result = analyze_variable_access(code)
        # Should return empty results on syntax error
        assert result.reads == []
        assert result.writes == []

    def test_list_comprehension(self):
        code = "squares = [x**2 for x in numbers]"
        result = analyze_variable_access(code)
        assert "squares" in result.writes
        assert "numbers" in result.reads

    def test_dict_access(self):
        code = "value = data['key']"
        result = analyze_variable_access(code)
        assert "data" in result.reads
        assert "value" in result.writes

    def test_attribute_access(self):
        code = "name = person.name"
        result = analyze_variable_access(code)
        assert "person" in result.reads
        assert "name" in result.writes

    def test_tuple_unpacking(self):
        code = "a, b = get_pair()"
        result = analyze_variable_access(code)
        assert "a" in result.writes
        assert "b" in result.writes


class TestVariableAnalyzer:
    """Tests for VariableAnalyzer class."""

    def test_initialization(self):
        analyzer = VariableAnalyzer()
        assert analyzer.reads == set()
        assert analyzer.writes == set()

    def test_visit_multiple_times(self):
        import ast
        analyzer = VariableAnalyzer()

        tree1 = ast.parse("x = 1")
        analyzer.visit(tree1)
        assert "x" in analyzer.writes

        tree2 = ast.parse("y = x")
        analyzer.visit(tree2)
        assert "x" in analyzer.reads
        assert "y" in analyzer.writes


class TestCalculateMissingCallsMetric:
    """Tests for Evaluator._calculate_missing_calls_metric method."""

    def test_no_missing_calls(self):
        # Create a mock evaluator to test the method
        class MockFactory:
            def create_agent(self, **kwargs):
                pass

        evaluator = Evaluator(MockFactory())

        expected = [
            ExpectedFunctionCall(name="func1", required=True),
            ExpectedFunctionCall(name="func2", required=True),
        ]
        actual = [
            ToolCall(function="func1", arguments={}, call_id="1"),
            ToolCall(function="func2", arguments={}, call_id="2"),
        ]

        missing = evaluator._calculate_missing_calls_metric(expected, actual)
        assert missing == 0

    def test_one_missing_call(self):
        class MockFactory:
            def create_agent(self, **kwargs):
                pass

        evaluator = Evaluator(MockFactory())

        expected = [
            ExpectedFunctionCall(name="func1", required=True),
            ExpectedFunctionCall(name="func2", required=True),
        ]
        actual = [
            ToolCall(function="func1", arguments={}, call_id="1"),
        ]

        missing = evaluator._calculate_missing_calls_metric(expected, actual)
        assert missing == 1

    def test_all_missing_calls(self):
        class MockFactory:
            def create_agent(self, **kwargs):
                pass

        evaluator = Evaluator(MockFactory())

        expected = [
            ExpectedFunctionCall(name="func1", required=True),
            ExpectedFunctionCall(name="func2", required=True),
        ]
        actual = []

        missing = evaluator._calculate_missing_calls_metric(expected, actual)
        assert missing == 2

    def test_optional_call_not_counted(self):
        class MockFactory:
            def create_agent(self, **kwargs):
                pass

        evaluator = Evaluator(MockFactory())

        expected = [
            ExpectedFunctionCall(name="func1", required=True),
            ExpectedFunctionCall(name="func2", required=False),  # Optional
        ]
        actual = [
            ToolCall(function="func1", arguments={}, call_id="1"),
        ]

        missing = evaluator._calculate_missing_calls_metric(expected, actual)
        assert missing == 0  # func2 is optional, so not counted as missing

    def test_extra_calls_ignored(self):
        class MockFactory:
            def create_agent(self, **kwargs):
                pass

        evaluator = Evaluator(MockFactory())

        expected = [
            ExpectedFunctionCall(name="func1", required=True),
        ]
        actual = [
            ToolCall(function="func1", arguments={}, call_id="1"),
            ToolCall(function="func2", arguments={}, call_id="2"),
            ToolCall(function="func3", arguments={}, call_id="3"),
        ]

        missing = evaluator._calculate_missing_calls_metric(expected, actual)
        assert missing == 0

    def test_empty_expected(self):
        class MockFactory:
            def create_agent(self, **kwargs):
                pass

        evaluator = Evaluator(MockFactory())

        expected = []
        actual = [
            ToolCall(function="func1", arguments={}, call_id="1"),
        ]

        missing = evaluator._calculate_missing_calls_metric(expected, actual)
        assert missing == 0


class TestEvaluatorInit:
    """Tests for Evaluator initialization."""

    def test_initialization(self):
        class MockFactory:
            def create_agent(self, **kwargs):
                pass

        evaluator = Evaluator(MockFactory())
        assert evaluator.agent_factory is not None
        assert evaluator.metrics is not None

    def test_reset_metrics(self):
        class MockFactory:
            def create_agent(self, **kwargs):
                pass

        evaluator = Evaluator(MockFactory())

        # Modify metrics
        evaluator.metrics.total_turns = 10
        evaluator.metrics.successful_turns = 5

        # Reset
        evaluator._reset_metrics()

        assert evaluator.metrics.total_turns == 0
        assert evaluator.metrics.successful_turns == 0
