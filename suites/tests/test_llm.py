"""Tests for the model registry (core.llm) and the thinking on/off axis."""

import pytest
from pydantic import ValidationError

from core.llm import ModelConfig, ModelRegistry


class TestModelConfigDefaults:
    def test_minimal(self):
        cfg = ModelConfig(name="m", api_model="x", api_key="k")
        assert cfg.provider == "openai"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens is None
        assert cfg.reasoning_effort is None
        assert cfg.extra_body == {}
        assert cfg.thinking == {}

    def test_rejects_unknown_field(self):
        # extra="forbid" — typos in models.toml fail fast
        with pytest.raises(ValidationError):
            ModelConfig(name="m", api_model="x", api_key="k", reasonig="oops")

    def test_temperature_bounds(self):
        with pytest.raises(ValidationError):
            ModelConfig(name="m", api_model="x", api_key="k", temperature=5)


class TestResolveExtraBody:
    def _cfg(self, **kw):
        return ModelConfig(name="m", api_model="x", api_key="k", **kw)

    def test_no_thinking_returns_base_copy(self):
        cfg = self._cfg(extra_body={"a": 1})
        out = cfg.resolve_extra_body(None)
        assert out == {"a": 1}
        out["a"] = 999  # must be a copy, not the stored dict
        assert cfg.extra_body == {"a": 1}

    def test_mode_merges_over_base(self):
        cfg = self._cfg(
            extra_body={"a": 1},
            thinking={"on": {"b": 2}, "off": {"a": 0}},
        )
        assert cfg.resolve_extra_body("on") == {"a": 1, "b": 2}
        assert cfg.resolve_extra_body("off") == {"a": 0}   # off overrides a

    def test_mode_ignored_when_no_thinking_table(self):
        cfg = self._cfg(extra_body={"a": 1})
        assert cfg.resolve_extra_body("on") == {"a": 1}

    def test_unknown_mode_raises(self):
        cfg = self._cfg(thinking={"on": {"b": 2}})
        with pytest.raises(ValueError):
            cfg.resolve_extra_body("off")


class TestModelRegistryLoad:
    def _write(self, tmp_path, text):
        p = tmp_path / "models.toml"
        p.write_text(text)
        return p

    def test_load_and_get(self, tmp_path):
        p = self._write(tmp_path, """
[deepseek]
api_model = "deepseek-chat"
api_key = "k"
base_url = "https://api.deepseek.com/v1"

[r1]
api_model = "deepseek-reasoner"
api_key = "k"
reasoning_effort = "high"
max_tokens = 8192
""")
        reg = ModelRegistry.load(p)
        assert reg.names == ["deepseek", "r1"]
        assert "r1" in reg
        r1 = reg.get("r1")
        assert r1.reasoning_effort == "high"
        assert r1.max_tokens == 8192

    def test_thinking_table_parsed(self, tmp_path):
        p = self._write(tmp_path, """
[qwen]
api_model = "qwen3"
api_key = "k"
[qwen.thinking.on]
chat_template_kwargs = { enable_thinking = true }
[qwen.thinking.off]
chat_template_kwargs = { enable_thinking = false }
""")
        cfg = ModelRegistry.load(p).get("qwen")
        assert cfg.resolve_extra_body("on") == {"chat_template_kwargs": {"enable_thinking": True}}
        assert cfg.resolve_extra_body("off") == {"chat_template_kwargs": {"enable_thinking": False}}

    def test_env_refs_expanded(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CAVE_TEST_KEY", "secret-from-env")
        monkeypatch.setenv("CAVE_TEST_HOST", "gateway.example.com")
        p = self._write(tmp_path, """
[m]
api_model = "x"
api_key = "${CAVE_TEST_KEY}"
base_url = "https://${CAVE_TEST_HOST}/v1"
""")
        cfg = ModelRegistry.load(p).get("m")
        assert cfg.api_key == "secret-from-env"
        assert cfg.base_url == "https://gateway.example.com/v1"

    def test_unset_env_ref_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CAVE_TEST_ABSENT", raising=False)
        p = self._write(tmp_path, '[m]\napi_model="x"\napi_key="${CAVE_TEST_ABSENT}"\n')
        with pytest.raises(ValueError, match="CAVE_TEST_ABSENT is not set"):
            ModelRegistry.load(p)

    def test_empty_env_ref_raises(self, tmp_path, monkeypatch):
        """An empty key would otherwise surface as a 401 mid-sweep."""
        monkeypatch.setenv("CAVE_TEST_EMPTY", "")
        p = self._write(tmp_path, '[m]\napi_model="x"\napi_key="${CAVE_TEST_EMPTY}"\n')
        with pytest.raises(ValueError, match="CAVE_TEST_EMPTY is empty"):
            ModelRegistry.load(p)

    def test_env_error_names_the_field_once(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CAVE_TEST_ABSENT", raising=False)
        p = self._write(tmp_path, '[m]\napi_model="x"\napi_key="${CAVE_TEST_ABSENT}"\n')
        with pytest.raises(ValueError) as excinfo:
            ModelRegistry.load(p)
        message = str(excinfo.value)
        assert message.count("model 'm'") == 1
        assert "api_key:" in message

    def test_plain_values_untouched(self, tmp_path):
        p = self._write(tmp_path, '[m]\napi_model="x"\napi_key="literal$key"\n')
        assert ModelRegistry.load(p).get("m").api_key == "literal$key"

    def test_missing_model_lists_available(self, tmp_path):
        p = self._write(tmp_path, '[a]\napi_model="x"\napi_key="k"\n')
        with pytest.raises(ValueError, match="available"):
            ModelRegistry.load(p).get("nope")

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ModelRegistry.load(tmp_path / "nope.toml")
