"""Every tool schema names a type, because one endpoint refuses a request without it.

An ``Optional[int]`` parameter arrives from the schema generator as a union with
null and no type of its own. Google's function calling rejects the whole request
for it, so a scenario whose tools carry one produced no tool calls at all on that
model — a result that reads as an inability to do the task. These pin the shape
that cannot happen again.
"""

import glob
import importlib
import os
from typing import Optional

import pytest

from adapters.litellm_adapter import function_to_schema, _flatten_nullable_unions


def _tool_modules():
    for path in sorted(glob.glob("evals/token_efficiency/*_tools.py")):
        yield importlib.import_module("evals.token_efficiency." + os.path.basename(path)[:-3])


def _properties(schema):
    for name, spec in (schema.get("properties") or {}).items():
        yield name, spec


@pytest.mark.parametrize("module", list(_tool_modules()), ids=lambda m: m.__name__.rsplit(".", 1)[1])
def test_every_scenario_tool_parameter_names_a_type(module):
    for function in module.tools:
        schema = function_to_schema(function)["parameters"]
        for name, spec in _properties(schema):
            assert "type" in spec, f"{function.__name__}.{name}: {sorted(spec)}"
            assert "anyOf" not in spec, f"{function.__name__}.{name} still a union"


def test_an_optional_parameter_keeps_its_type_and_stays_out_of_required():
    def reorder(sku: str, quantity: Optional[int] = None):
        """Reorder something.

        Parameters:
            sku (str): [Required] What to reorder.
            quantity (int): [Optional] How many.
        """

    schema = function_to_schema(reorder)["parameters"]
    assert schema["properties"]["quantity"]["type"] == "integer"
    assert schema["required"] == ["sku"]


def test_a_union_that_is_not_about_null_is_left_alone():
    """Only the nullable union is collapsed; a real union still needs a decision."""
    union = {"anyOf": [{"type": "integer"}, {"type": "string"}]}
    assert _flatten_nullable_unions(union) == union


def test_the_collapse_reaches_a_nested_schema():
    nested = {
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "items": {"anyOf": [{"type": "number"}, {"type": "null"}]},
            },
        },
    }
    assert _flatten_nullable_unions(nested)["properties"]["rows"]["items"] == {"type": "number"}


def test_the_description_and_default_survive_the_collapse():
    spec = {
        "anyOf": [{"type": "integer"}, {"type": "null"}],
        "default": None,
        "description": "How many.",
    }
    assert _flatten_nullable_unions(spec) == {
        "type": "integer", "default": None, "description": "How many.",
    }
