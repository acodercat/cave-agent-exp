import pytest

from core.models import ModelConfig, ModelRegistry, load_model


def write_config(tmp_path, body: str):
    path = tmp_path / "models.toml"
    path.write_text(body)
    return path


def test_keys_are_read_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_KEY", "secret")
    path = write_config(tmp_path, '[m]\napi_model = "m-1"\napi_key = "${BENCH_KEY}"\n')
    assert ModelRegistry.load(path).get("m").api_key == "secret"


@pytest.mark.parametrize("value", [None, ""])
def test_an_unset_or_empty_variable_is_an_error(tmp_path, monkeypatch, value):
    monkeypatch.delenv("BENCH_KEY", raising=False)
    if value is not None:
        monkeypatch.setenv("BENCH_KEY", value)
    path = write_config(tmp_path, '[m]\napi_model = "m-1"\napi_key = "${BENCH_KEY}"\n')
    with pytest.raises(ValueError, match="BENCH_KEY"):
        ModelRegistry.load(path)


def test_the_key_never_reaches_a_stored_fingerprint():
    config = ModelConfig(name="m", api_model="m-1", api_key="secret", thinking="disabled")
    assert "secret" not in repr(config)
    assert "secret" not in str(config.public_fingerprint())
    assert config.public_fingerprint()["thinking"] == "disabled"


def test_thinking_is_sent_with_every_request_when_stated(tmp_path):
    path = write_config(
        tmp_path, '[m]\napi_model = "m-1"\napi_key = "k"\nthinking = "disabled"\n'
    )
    model, _ = load_model(path, "m")
    assert model.kwargs["extra_body"] == {"thinking": {"type": "disabled"}}


def test_an_unstated_thinking_leaves_the_provider_default(tmp_path):
    path = write_config(tmp_path, '[m]\napi_model = "m-1"\napi_key = "k"\n')
    model, _ = load_model(path, "m")
    assert "extra_body" not in model.kwargs


def test_an_unknown_thinking_value_is_rejected():
    with pytest.raises(ValueError, match="thinking"):
        ModelConfig(name="m", api_model="m-1", api_key="k", thinking="off")
