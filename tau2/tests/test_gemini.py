"""Tests for the native Gemini provider: what it sends, and what it returns.

Offline: requests are built and responses parsed, nothing reaches a gateway.
"""

import json

import pytest
from google.genai import types
from litellm.llms.custom_llm import CustomLLMError

from tau2_cave.gemini import to_config, to_model_response, to_request

SIGNATURE = b"\x01opaque-signature\xff"
#: The separator the provider puts between a call id and its signature.
SIGNATURE_MARKER = "__thought__"


def gemini_response(*parts, finish=types.FinishReason.STOP, prompt=100, output=20, thoughts=30):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)),
                                    finish_reason=finish)],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt, candidates_token_count=output, thoughts_token_count=thoughts),
    )


def call_part(name="get_customer_by_phone", args=None, signature=SIGNATURE):
    return types.Part(function_call=types.FunctionCall(name=name, args=args or {"phone_number": "555"}),
                      thought_signature=signature)


class TestRequest:
    def test_system_messages_become_the_instruction(self):
        system, contents = to_request([
            {"role": "system", "content": "Follow the policy."},
            {"role": "assistant", "content": "Hi! How can I help you today?"},
            {"role": "user", "content": "My phone has no service."},
        ])

        assert system == "Follow the policy."
        assert [(c.role, c.parts[0].text) for c in contents] == [
            ("model", "Hi! How can I help you today?"), ("user", "My phone has no service.")]

    def test_a_call_travels_back_with_its_signature(self):
        """The signature Gemini issued must reach Gemini again, byte for byte."""
        call = to_model_response(gemini_response(call_part()), "m").choices[0].message.tool_calls[0]

        _, contents = to_request([{"role": "assistant", "content": None, "tool_calls": [call.model_dump()]}])

        part = contents[0].parts[0]
        assert part.function_call.name == "get_customer_by_phone"
        assert part.function_call.args == {"phone_number": "555"}
        assert part.thought_signature == SIGNATURE

    def test_tool_results_are_named_and_grouped(self):
        calls = [{"id": f"call_{i}", "type": "function",
                  "function": {"name": name, "arguments": "{}"}}
                 for i, name in enumerate(("get_details_by_id", "get_bills_for_customer"))]

        _, contents = to_request([
            {"role": "assistant", "content": None, "tool_calls": calls},
            {"role": "tool", "tool_call_id": "call_0", "content": json.dumps({"line_id": "L1"})},
            {"role": "tool", "tool_call_id": "call_1", "content": "[]"},
        ])

        (answer,) = contents[1:]
        assert answer.role == "user"
        assert [(p.function_response.name, p.function_response.response) for p in answer.parts] == [
            ("get_details_by_id", {"line_id": "L1"}), ("get_bills_for_customer", {"result": []})]

    def test_a_plain_text_result_is_wrapped(self):
        _, contents = to_request([
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c", "content": "Transfer successful"},
        ])

        assert contents[1].parts[0].function_response.response == {"result": "Transfer successful"}


class TestConfig:
    def test_settings_are_carried_over(self):
        config = to_config({
            "temperature": 1.0, "reasoning_effort": "low",
            "tools": [{"type": "function", "function": {
                "name": "f", "description": "does f",
                "parameters": {"type": "object", "properties": {"x": {"type": "string"}}}}}],
        })

        assert config.temperature == 1.0
        assert config.thinking_config.thinking_level == types.ThinkingLevel.LOW
        (declaration,) = config.tools[0].function_declarations
        assert (declaration.name, declaration.parameters_json_schema["properties"]) == ("f", {"x": {"type": "string"}})
        assert config.automatic_function_calling.disable

    def test_nothing_is_set_that_was_not_asked_for(self):
        config = to_config({})

        assert config.temperature is None and config.thinking_config is None and config.tools is None


class TestResponse:
    def test_text_excludes_thoughts(self):
        response = to_model_response(gemini_response(
            types.Part(text="reasoning", thought=True), types.Part(text="Your line is active.")), "m")

        choice = response.choices[0]
        assert (choice.message.content, choice.message.tool_calls, choice.finish_reason) == (
            "Your line is active.", None, "stop")

    def test_calls_come_back_as_tool_calls(self):
        response = to_model_response(gemini_response(
            call_part(), call_part("get_bills_for_customer", {"customer_id": "C1"}, signature=None)), "m")

        choice = response.choices[0]
        assert choice.finish_reason == "tool_calls"
        assert [(c.function.name, json.loads(c.function.arguments)) for c in choice.message.tool_calls] == [
            ("get_customer_by_phone", {"phone_number": "555"}), ("get_bills_for_customer", {"customer_id": "C1"})]
        assert len({c.id for c in choice.message.tool_calls}) == 2

    def test_thinking_counts_as_completion(self):
        """Thought tokens are generated and billed like any other output."""
        usage = to_model_response(gemini_response(types.Part(text="ok")), "m").usage

        assert (usage.prompt_tokens, usage.completion_tokens, usage.total_tokens) == (100, 50, 150)
        assert usage.completion_tokens_details.reasoning_tokens == 30

    @pytest.mark.parametrize("finish", [types.FinishReason.MALFORMED_FUNCTION_CALL, types.FinishReason.STOP])
    def test_no_usable_output_is_a_retryable_error(self, finish):
        with pytest.raises(CustomLLMError) as raised:
            to_model_response(gemini_response(finish=finish), "m")

        assert raised.value.status_code == 500


class TestStreamingAWholeResponse:
    """Gemini answers whole, so a stream here is that answer cut into chunks.

    The cut has to satisfy a reader of an OpenAI-style stream, and one reader in
    particular: the `execute_python` arm stops at the *second* tool call, so that
    a turn carries one action. It can only see a second call if a second chunk
    carries it — a single chunk holding every call would read as one.
    """

    @staticmethod
    def chunks(*parts, finish=types.FinishReason.STOP):
        from tau2_cave.gemini import to_stream_chunks

        return to_stream_chunks(to_model_response(gemini_response(*parts, finish=finish), "m"))

    def test_text_alone_is_one_finished_chunk(self):
        """What this provider yielded before calls could be streamed at all."""
        chunks = self.chunks(types.Part(text="hello"))
        assert len(chunks) == 1
        assert chunks[0]["text"] == "hello"
        assert chunks[0]["tool_use"] is None
        assert chunks[0]["is_finished"] and chunks[0]["finish_reason"] == "stop"
        assert chunks[0]["usage"]["total_tokens"] == 150

    def test_each_call_arrives_under_its_own_index(self):
        chunks = self.chunks(call_part(name="first"), call_part(name="second"))
        uses = [chunk["tool_use"] for chunk in chunks if chunk["tool_use"]]
        assert [use["function"]["name"] for use in uses] == ["first", "second"]
        assert [use["index"] for use in uses] == [0, 1]

    def test_a_call_carries_its_signature_bearing_id(self):
        """The id is how the thought signature travels back; chunking must keep it."""
        use = self.chunks(call_part())[0]["tool_use"]
        assert SIGNATURE_MARKER in use["id"]
        assert json.loads(use["function"]["arguments"]) == {"phone_number": "555"}

    def test_text_precedes_the_calls_it_came_with(self):
        chunks = self.chunks(types.Part(text="looking that up"), call_part())
        assert chunks[0]["text"] == "looking that up" and chunks[0]["tool_use"] is None
        assert chunks[1]["tool_use"] is not None

    def test_only_the_last_chunk_finishes_and_carries_the_usage(self):
        chunks = self.chunks(types.Part(text="one moment"), call_part(name="a"), call_part(name="b"))
        assert [chunk["is_finished"] for chunk in chunks] == [False, False, True]
        assert [chunk["usage"] is None for chunk in chunks] == [True, True, False]
        assert chunks[-1]["finish_reason"] == "tool_calls"

    def test_the_whole_reply_survives_the_cut(self):
        """Nothing is dropped or duplicated: the chunks rebuild the response."""
        response = to_model_response(
            gemini_response(types.Part(text="hi"), call_part(name="a"), call_part(name="b")), "m")
        from tau2_cave.gemini import to_stream_chunks

        chunks = to_stream_chunks(response)
        assert "".join(chunk["text"] for chunk in chunks) == response.choices[0].message.content
        rebuilt = [chunk["tool_use"] for chunk in chunks if chunk["tool_use"]]
        assert len(rebuilt) == len(response.choices[0].message.tool_calls)


class TestACallReachesTheArmThatRunsIt:
    """The chunks are only right if the arm's loop can act on them.

    Shape tests cannot show that: between this provider and the loop sit
    litellm's wrapper, which turns ``tool_use`` into ``delta.tool_calls``, and
    the arm's own stream reader. This drives the whole path on a canned Gemini
    response and asks the only question that matters — did the code run.
    """

    CODE = "result = 6 * 7\nprint(result)"

    @staticmethod
    def _canned(parts):
        return gemini_response(*parts)

    def test_gemini_asks_for_execute_python_and_the_code_runs(self, monkeypatch):
        import asyncio
        from types import SimpleNamespace

        from cave_agent import Variable
        from cave_agent.models import LiteLLMModel
        from cave_agent.runtime import IPythonRuntime

        import tau2_cave.gemini as gemini
        from tau2_json_exec.tool_call_agent import ToolCallAgent

        gemini.register()
        replies = [
            self._canned([types.Part(text="running it"),
                          call_part(name="execute_python", args={"code": self.CODE})]),
            self._canned([types.Part(text="The answer is 42.")]),
        ]
        sent = []

        async def generate_content(**kwargs):
            sent.append(kwargs)
            return replies[min(len(sent) - 1, len(replies) - 1)]

        monkeypatch.setattr(
            gemini.GenaiProvider, "_client",
            staticmethod(lambda *a, **k: SimpleNamespace(
                aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))))

        runtime = IPythonRuntime(
            functions=[], variables=[Variable("result", None, "the answer")], types=[])
        agent = ToolCallAgent(
            model=LiteLLMModel(model_id="gemini-3.1-pro-preview", api_key="k",
                               custom_llm_provider="genai"),
            runtime=runtime, system_instructions="Use execute_python.", max_steps=4)

        response = asyncio.run(agent.run("What is six times seven?"))

        declared = [d.name for tool in (sent[0]["config"].tools or [])
                    for d in (tool.function_declarations or [])]
        assert declared == ["execute_python"], "the arm's tool must reach Gemini as a function"
        assert response.code_snippets == [self.CODE], "the call's code must be what runs"
        assert asyncio.run(runtime.retrieve("result")) == 42, "and it must really have run"
        assert response.stop_reason.value == "completed"

    def test_the_first_of_several_calls_is_the_one_that_runs(self, monkeypatch):
        """One action per turn, as the fenced arm runs only its first block.

        Gemini returns several calls in one message about a quarter of the time
        in this domain, so this is the common case, not the corner. The later
        calls are dropped, and — because the reader stops before the last chunk
        — so is the usage, which is what a real stream does too. Both are
        pinned here so a change to either is a decision rather than a surprise.
        """
        import asyncio
        from types import SimpleNamespace

        from cave_agent.models import LiteLLMModel
        from cave_agent.runtime import IPythonRuntime

        import tau2_cave.gemini as gemini
        from tau2_json_exec.tool_call_agent import ToolCallAgent

        gemini.register()
        replies = [
            self._canned([call_part(name="execute_python", args={"code": "first = 1"}),
                          call_part(name="execute_python", args={"code": "second = 2"})]),
            self._canned([types.Part(text="done")]),
        ]
        sent = []

        async def generate_content(**kwargs):
            sent.append(kwargs)
            return replies[min(len(sent) - 1, len(replies) - 1)]

        monkeypatch.setattr(
            gemini.GenaiProvider, "_client",
            staticmethod(lambda *a, **k: SimpleNamespace(
                aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))))

        runtime = IPythonRuntime(functions=[], variables=[], types=[])
        agent = ToolCallAgent(
            model=LiteLLMModel(model_id="gemini-3.1-pro-preview", api_key="k",
                               custom_llm_provider="genai"),
            runtime=runtime, system_instructions="Use execute_python.", max_steps=3)

        response = asyncio.run(agent.run("do two things"))

        assert response.code_snippets == ["first = 1"], "only the first call runs"
        # 1000 + 500 per reply is what the provider reported; an estimate is far
        # below it, which is how this asserts the usage block was not delivered.
        assert response.usage.total_tokens < 1500, "the usage rides on a chunk never read"
