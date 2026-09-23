"""Model registry: load and validate `models.toml` into typed configs.

Replaces the scattered `os.getenv("DEEPSEEK_*")` model construction in the
runner scripts with a single validated source of truth. Each ``[section]`` in
`models.toml` is one selectable model, referenced by its section name
(e.g. ``--model deepseek``). `models.toml` holds secrets and is gitignored;
`models.toml.example` is the committed template.
"""

import os
import re
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ModelConfig(BaseModel):
    """One model's configuration; immutable, validated at registry-load time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str                                  # registry key (section header)
    api_model: str                             # identifier sent to the API (model_id)
    api_key: str
    base_url: Optional[str] = None
    provider: str = "openai"                   # litellm custom_llm_provider / provider
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    # Whether this is a reasoning model. Shared vocabulary with the sibling harness's
    # models.toml; reasoning models reject `temperature`.
    reasoning: bool = False
    # Escape hatch for non-reasoning models that also reject `temperature` —
    # claude-sonnet-5 on one gateway answers 400 "`temperature` is
    # deprecated for this model" but is not a reasoning model, so marking it as
    # one to suppress the parameter would misdescribe it. litellm's `drop_params`
    # does not help: it only drops parameters it knows a model lacks, which it
    # cannot know behind a custom gateway (verified).
    supports_temperature: bool = True
    # Per-model knobs for heterogeneous (esp. reasoning) models. All optional and
    # forwarded to litellm as-is, so adding a new model stays a TOML-only edit.
    max_tokens: Optional[int] = Field(None, gt=0)
    timeout: Optional[float] = Field(None, gt=0)
    reasoning_effort: Optional[str] = None     # "low" | "medium" | "high" (reasoning models)
    # Accepted for parity with a shared models.toml. Not consumed by
    # this repo's litellm paths; declared so a copied config loads instead of
    # tripping `extra="forbid"`, which stays on to catch genuine typos.
    lab: Optional[str] = None
    reasoning_summary: Optional[str] = None
    thinking_level: Optional[str] = None
    thinking_echo_field: Optional[str] = None
    extra_body: Dict[str, Any] = Field(default_factory=dict)   # arbitrary provider passthrough
    # Thinking on/off experiment axis: maps a mode name -> an extra_body fragment
    # merged over `extra_body` at build time (e.g. SGLang chat_template_kwargs).
    thinking: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _alias_model_id(cls, data: Any) -> Any:
        """Accept `model_id` as an alias for `api_model`.

        The shared `models.toml` is written with `model_id`; without this alias
        every section in a copied config fails validation.
        """
        if isinstance(data, dict) and "api_model" not in data and "model_id" in data:
            data = dict(data)
            data["api_model"] = data.pop("model_id")
        return data

    def resolve_extra_body(self, thinking_mode: Optional[str] = None) -> Dict[str, Any]:
        """Return `extra_body` with the selected thinking variant merged on top.

        Returns a copy of the base `extra_body` when no mode is requested or no
        `thinking` table is defined. Raises if a mode is requested but the model
        declares a `thinking` table without that key (fail fast on a typo).
        """
        if not thinking_mode or not self.thinking:
            return dict(self.extra_body)
        if thinking_mode not in self.thinking:
            raise ValueError(
                f"model {self.name!r}: thinking mode {thinking_mode!r} not defined; "
                f"available: {sorted(self.thinking)}"
            )
        return {**self.extra_body, **self.thinking[thinking_mode]}


def _expand_env(value: Any, where: str) -> Any:
    """Substitute ``${VAR}`` references in string values from the environment.

    Lets `models.toml` carry `api_key = "${DEEPSEEK_API_KEY}"` instead of the key
    itself, so a config can be shared or committed without leaking secrets. A
    variable that is unset *or empty* is an error: an empty key or base_url is
    never legitimate, and passing one on produces a 401 thousands of turns into
    a sweep. There is no escape syntax, so a literal `${...}` cannot be written.

    `where` names the field being expanded; the caller adds the model and file.
    """
    if isinstance(value, str):
        def sub(match: re.Match) -> str:
            var = match.group(1)
            if not os.environ.get(var):
                state = "empty" if var in os.environ else "not set"
                raise ValueError(f"{where}: environment variable {var} is {state}")
            return os.environ[var]
        return _ENV_REF.sub(sub, value)
    if isinstance(value, dict):
        return {k: _expand_env(v, f"{where}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v, f"{where}[{i}]") for i, v in enumerate(value)]
    return value


class ModelRegistry:
    """Loaded view of `models.toml`. Construct via `ModelRegistry.load(path)`."""

    def __init__(self, configs: Dict[str, ModelConfig]):
        self._configs = configs

    @classmethod
    def load(cls, path: Path | str) -> "ModelRegistry":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Copy models.toml.example to models.toml and fill it in."
            )
        raw = tomllib.loads(path.read_text())
        configs: Dict[str, ModelConfig] = {}
        for name, fields in raw.items():
            try:
                fields = {k: _expand_env(v, k) for k, v in dict(fields).items()}
                configs[name] = ModelConfig(name=name, **fields)
            except Exception as e:
                raise ValueError(f"model {name!r} in {path}: {e}") from e
        return cls(configs)

    def get(self, name: str) -> ModelConfig:
        if name not in self._configs:
            raise ValueError(
                f"model {name!r} not registered; available: {sorted(self._configs)}"
            )
        return self._configs[name]

    def __contains__(self, name: str) -> bool:
        return name in self._configs

    @property
    def names(self) -> List[str]:
        return sorted(self._configs)
