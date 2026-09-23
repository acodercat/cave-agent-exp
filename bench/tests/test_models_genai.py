"""A Gemini entry in models.toml: what it must state, and what it must not."""

import pytest

from core.models import GENAI, ModelConfig


def _config(**fields):
    return ModelConfig(name="m", api_model="gemini", api_key="k", **fields)


def test_a_genai_model_states_a_reasoning_level_and_no_thinking_switch():
    cfg = _config(litellm_provider=GENAI, reasoning_effort="low", temperature=1.0)
    assert cfg.public_fingerprint()["reasoning_effort"] == "low"
    with pytest.raises(ValueError):
        _config(litellm_provider=GENAI)                                   # no level
    with pytest.raises(ValueError):
        _config(litellm_provider=GENAI, reasoning_effort="low", thinking="disabled")
    with pytest.raises(ValueError):
        _config(litellm_provider=GENAI, reasoning_effort="none")


def test_a_reasoning_level_is_refused_on_any_other_provider():
    with pytest.raises(ValueError):
        _config(reasoning_effort="low")
