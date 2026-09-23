"""Gemini's unusable responses are resampled, not passed on as a dead turn.

MALFORMED_FUNCTION_CALL is a sampling accident: the same prompt usually succeeds
on the next attempt. Nothing above the provider retries -- litellm's num_retries
is None unless a caller sets it -- so six gemini runs each lost the same handful
of turns to one bad sample before this existed.
"""

import asyncio
import types as pytypes

import pytest
from litellm.llms.custom_llm import CustomLLMError

from bfcl_multiturn import gemini


class FakeResponse:
    """Just enough of a Gemini response for to_model_response to read it."""

    def __init__(self, text):
        part = pytypes.SimpleNamespace(text=text, thought=False, function_call=None,
                                       thought_signature=None)
        content = pytypes.SimpleNamespace(parts=[part] if text else [])
        reason = pytypes.SimpleNamespace(name="STOP" if text else "MALFORMED_FUNCTION_CALL")
        self.candidates = [pytypes.SimpleNamespace(content=content, finish_reason=reason)]
        self.usage_metadata = pytypes.SimpleNamespace(
            thoughts_token_count=0, prompt_token_count=1, candidates_token_count=1)


class FakeClient:
    """Returns the given sequence of responses, one per call."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0
        outer = self

        class Models:
            async def generate_content(self, **_):
                outer.calls += 1
                return outer.responses.pop(0)

        self.aio = pytypes.SimpleNamespace(models=Models())


@pytest.fixture
def provider(monkeypatch):
    holder = {}

    def client(api_base, api_key, timeout):
        return holder["client"]

    monkeypatch.setattr(gemini.GenaiProvider, "_client", staticmethod(client))
    monkeypatch.setattr(gemini, "to_request", lambda messages: (None, []))
    monkeypatch.setattr(gemini, "to_config", lambda params: pytypes.SimpleNamespace(
        system_instruction=None))
    return gemini.GenaiProvider(), holder


def call(provider):
    return asyncio.run(provider.acompletion("m", [], None, "k", {}))


class TestResampling:
    def test_a_usable_response_is_returned_at_once(self, provider):
        arm, holder = provider
        holder["client"] = FakeClient(FakeResponse("hello"))

        assert call(arm).choices[0].message.content == "hello"
        assert holder["client"].calls == 1

    def test_one_unusable_sample_is_resampled(self, provider):
        arm, holder = provider
        holder["client"] = FakeClient(FakeResponse(None), FakeResponse("second try"))

        assert call(arm).choices[0].message.content == "second try"
        assert holder["client"].calls == 2

    def test_it_gives_up_after_the_allowance(self, provider, monkeypatch):
        monkeypatch.setattr(gemini, "RETRIES", 2)
        arm, holder = provider
        holder["client"] = FakeClient(*[FakeResponse(None)] * 3)

        with pytest.raises(CustomLLMError, match="MALFORMED_FUNCTION_CALL"):
            call(arm)
        assert holder["client"].calls == 3        # the first, plus two retries
