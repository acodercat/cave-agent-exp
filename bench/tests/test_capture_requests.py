"""The request capture keeps what a paradigm changes and drops what identifies the caller."""

import asyncio
from types import SimpleNamespace

import litellm
import pytest

from scripts.capture_requests import RECORDED_FIELDS, _recorder


@pytest.fixture
def sent(monkeypatch):
    """Whatever the recorder passes on to litellm, with the real call stubbed out."""
    calls = []

    async def acompletion(**request):
        calls.append(request)
        return "response"

    monkeypatch.setattr(litellm, "acompletion", acompletion)
    return calls


def test_a_recorded_request_holds_the_prompt_and_no_credentials(sent):
    model, requests = SimpleNamespace(), []
    _recorder(model, requests)
    reply = asyncio.run(model._litellm.acompletion(
        model="m", messages=[{"role": "user", "content": "q"}], temperature=0.0,
        api_key="secret", base_url="https://example.invalid/v1", api_base="https://example.invalid",
    ))

    assert reply == "response"
    assert requests == [{
        "model": "m", "messages": [{"role": "user", "content": "q"}], "temperature": 0.0,
    }]
    # The call itself still carries what the provider needs.
    assert sent[0]["api_key"] == "secret"


def test_the_recorded_fields_name_nothing_that_could_carry_a_key():
    assert not {field for field in RECORDED_FIELDS if "key" in field or "api" in field}
    assert "messages" in RECORDED_FIELDS and "tools" in RECORDED_FIELDS
