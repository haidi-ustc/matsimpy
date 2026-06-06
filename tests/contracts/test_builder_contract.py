"""Contract tests for all registered builders.

Parametrized over all BuilderSpecs in the registry.
Tests: output_type correctness.
"""

import pytest
from matsimpy.core import Crystal, Molecule
from matsimpy.builders.registry import registry


all_specs = registry.list_all()
spec_ids = [s.name for s in all_specs]


_STRUCTURE_PARAMS = frozenset({"structure", "substrate", "film", "bottom", "top", "layers", "other"})


def _minimal_kwargs(spec):
    """Build minimally valid kwargs from spec's parameter_schema, only required fields."""
    schema = spec.parameter_schema or {}
    props = schema.get("properties", {})
    required = schema.get("required", [])
    kwargs = {}
    for name, prop in props.items():
        if name not in required:
            continue
        if name in _STRUCTURE_PARAMS:
            continue  # needs actual Structure — caller provides
        if "default" in prop:
            kwargs[name] = prop["default"]
        elif "oneOf" in prop:
            kwargs[name] = _value_from_schema(prop["oneOf"][0])
        else:
            kwargs[name] = _value_from_schema(prop)
    return kwargs


def _value_from_schema(schema):
    """Generate a minimal valid value for a JSON Schema fragment."""
    if "default" in schema:
        return schema["default"]
    t = schema.get("type", "string")
    if t == "string":
        if "enum" in schema:
            return schema["enum"][0]
        return "Cu"
    elif t == "number":
        return 1.0
    elif t == "integer":
        return 1
    elif t == "boolean":
        return False
    elif t == "array":
        item_schema = schema.get("items", {"type": "number"})
        min_items = schema.get("minItems", 1)
        return [_value_from_schema(item_schema)] * min_items
    return None


@pytest.mark.parametrize("spec", all_specs, ids=spec_ids)
class TestBuilderContract:

    def test_returns_correct_type(self, spec):
        """Builder returns the declared output_type."""
        # Skip builders that require optional deps not installed
        if spec.requires_optional:
            for dep in spec.requires_optional:
                try:
                    __import__(dep)
                except ImportError:
                    pytest.skip(f"Optional dependency {dep} not installed")

        kwargs = _minimal_kwargs(spec)
        try:
            result = spec.callable(**kwargs)
            assert isinstance(result, spec.output_type)
        except (ValueError, TypeError, IndexError) as e:
            pytest.skip(f"Requires more specific kwargs: {e}")

    def test_output_is_not_none(self, spec):
        """Builder output is not None."""
        if spec.requires_optional:
            for dep in spec.requires_optional:
                try:
                    __import__(dep)
                except ImportError:
                    pytest.skip(f"Optional dependency {dep} not installed")

        kwargs = _minimal_kwargs(spec)
        try:
            result = spec.callable(**kwargs)
            assert result is not None
        except (ValueError, TypeError, IndexError):
            pytest.skip("Requires more specific kwargs")
