"""The tested agent's model, configured from ``models.toml``.

Each ``[section]`` is one selectable model, named on ``scripts.run --model``.
``models.toml`` is gitignored; ``models.toml.example`` is the committed template.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import tomllib
from typing import Any

from cave_agent.models import LiteLLMModel

from core.stream_repair import FenceRepairingModel


# The litellm provider name core.gemini registers; kept here so that reading a
# models.toml does not import the Gemini SDK.
GENAI = "genai"

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class ModelConfig:
    name: str
    api_model: str
    api_key: str = field(repr=False)
    base_url: str | None = None
    temperature: float = 0.1
    max_tokens: int = 8192
    timeout: float = 300.0
    litellm_provider: str = "openai"
    # "enabled" or "disabled", sent with every request. Models disagree on their
    # default, so a study states it; None leaves the provider's default in force.
    thinking: str | None = None
    # Gemini 3 cannot turn reasoning off; it takes a level instead. Only the
    # ``genai`` provider (core.gemini) reads it.
    reasoning_effort: str | None = None
    input_cost_per_million_usd: float | None = None
    output_cost_per_million_usd: float | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.api_model or not self.api_key:
            raise ValueError("model name, api_model and api_key must be non-empty")
        if self.max_tokens < 1 or self.timeout <= 0:
            raise ValueError("max_tokens and timeout must be positive")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if any(
            value is not None and value < 0
            for value in (
                self.input_cost_per_million_usd,
                self.output_cost_per_million_usd,
            )
        ):
            raise ValueError("model token prices cannot be negative")
        if self.thinking not in (None, "enabled", "disabled"):
            raise ValueError("thinking must be 'enabled' or 'disabled'")
        if self.reasoning_effort not in (None, "low", "medium", "high"):
            raise ValueError("reasoning_effort must be 'low', 'medium' or 'high'")
        if self.litellm_provider == GENAI:
            if self.reasoning_effort is None or self.thinking is not None:
                raise ValueError("a genai model states reasoning_effort, not thinking")
        elif self.reasoning_effort is not None:
            raise ValueError("reasoning_effort applies to the genai provider only")

    def public_fingerprint(self) -> dict[str, Any]:
        """Return model metadata safe to persist (never includes the API key)."""
        return {
            "name": self.name,
            "model_id": self.api_model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "litellm_provider": self.litellm_provider,
            "thinking": self.thinking,
            "reasoning_effort": self.reasoning_effort,
            "input_cost_per_million_usd": self.input_cost_per_million_usd,
            "output_cost_per_million_usd": self.output_cost_per_million_usd,
        }


def _expand_env(value: Any, where: str) -> Any:
    """Substitute ``${VAR}`` references in string values from the environment.

    Lets ``models.toml`` carry ``api_key = "${DEEPSEEK_API_KEY}"`` instead of the
    key itself. A variable that is unset *or empty* is an error: an empty key or
    base_url is never legitimate, and passing one on produces a 401 hundreds of
    turns into a study. There is no escape syntax for a literal ``${...}``.
    """
    if not isinstance(value, str):
        return value

    def substitute(match: re.Match) -> str:
        variable = match.group(1)
        if not os.environ.get(variable):
            state = "empty" if variable in os.environ else "not set"
            raise ValueError(f"{where}: environment variable {variable} is {state}")
        return os.environ[variable]

    return _ENV_REF.sub(substitute, value)


class ModelRegistry:
    def __init__(self, configs: dict[str, ModelConfig]):
        self._configs = dict(configs)

    @classmethod
    def load(cls, path: Path | str) -> "ModelRegistry":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"{path} does not exist; create it from models.toml.example"
            )
        raw = tomllib.loads(path.read_text())
        configs = {}
        for name, values in raw.items():
            try:
                fields = {key: _expand_env(value, key) for key, value in values.items()}
                configs[name] = ModelConfig(name=name, **fields)
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid model {name!r} in {path}: {error}") from error
        return cls(configs)

    def get(self, name: str) -> ModelConfig:
        try:
            return self._configs[name]
        except KeyError as error:
            raise ValueError(
                f"unknown model {name!r}; available: {sorted(self._configs)}"
            ) from error


def load_model(path: Path, name: str) -> tuple[LiteLLMModel, ModelConfig]:
    """Build the agent's model wrapper from a models.toml entry.

    ``FenceRepairingModel`` is cave_agent's ``LiteLLMModel`` with its stream
    passed through :mod:`core.stream_repair`, which turns a provider's native
    tool envelope into the markdown fences cave-agent parses, and closes a fence
    the provider left open at a clean stop. Without it those turns run no code
    and set no variable while still reporting ``stop_reason == "completed"``,
    which is indistinguishable from a wrong answer. It is a no-op on a
    well-formed stream.
    """
    cfg = ModelRegistry.load(path).get(name)
    if cfg.litellm_provider == GENAI:
        # Gemini goes through its native API (core.gemini). litellm withholds
        # OpenAI parameters from a custom provider unless they are allowed.
        from core import gemini
        gemini.register()
        extra = {
            "reasoning_effort": cfg.reasoning_effort,
            "allowed_openai_params": ["reasoning_effort"],
        }
    else:
        extra = {"extra_body": {"thinking": {"type": cfg.thinking}}} if cfg.thinking else {}
    model = FenceRepairingModel(
        model_id=cfg.api_model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        custom_llm_provider=cfg.litellm_provider,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        timeout=cfg.timeout,
        num_retries=3,
        **extra,
    )
    return model, cfg
