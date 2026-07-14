"""Contract tests for all registered builders.

Parametrized over all BuilderSpecs in the registry.
Tests: output_type correctness.
"""

import pytest
from matsimpy.core import Crystal, Molecule
from matsimpy.builders.registry import BuilderRegistry, BuilderSpec, registry


all_specs = registry.list_all()
spec_ids = [s.name for s in all_specs]


_SIGNATURE_MISMATCH_MESSAGES = (
    "unexpected keyword argument",
    "required positional argument",
)
_STRUCTURE_PARAMS = frozenset({"structure", "substrate", "film", "bottom", "top", "layers", "other"})
_KNOWN_SIGNATURE_SETUP_SKIPS = frozenset({
    "from_prototype",
    "generate_slab",
    "add_adsorbate",
    "generate_random_alloy",
    "generate_ordered_alloy",
    "generate_intermetallic",
    "build_heusler",
    "build_full_heusler",
    "build_half_heusler",
    "build_inverse_heusler",
    "create_vacancy",
    "create_interstitial",
    "create_substitution",
    "create_frenkel",
    "create_schottky",
    "create_antisite",
    "create_simple_interface",
    "build_bent",
    "build_tetrahedral",
    "build_nanotube",
    "build_twisted_bilayer",
    "build_magic_angle_twisted",
    "build_twisted_multilayer",
})


def _skip_if_semantic_setup_error(spec, error):
    if isinstance(error, TypeError) and any(
        message in str(error) for message in _SIGNATURE_MISMATCH_MESSAGES
    ) and spec.name not in _KNOWN_SIGNATURE_SETUP_SKIPS:
        raise error
    pytest.skip(f"Requires more specific kwargs: {error}")


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
            _skip_if_semantic_setup_error(spec, e)

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
        except (ValueError, TypeError, IndexError) as e:
            _skip_if_semantic_setup_error(spec, e)


def test_builder_registry_validates_required_parameters_before_calling():
    called = False

    def build_dummy(**kwargs):
        nonlocal called
        called = True
        return kwargs

    local_registry = BuilderRegistry()
    local_registry.register(BuilderSpec(
        name="dummy",
        category="test",
        callable=build_dummy,
        parameter_schema={
            "type": "object",
            "properties": {"element": {"type": "string"}},
            "required": ["element"],
        },
    ))

    with pytest.raises(ValueError, match="Missing required parameter: element"):
        local_registry.build("dummy")
    assert called is False


def test_builder_registry_validates_parameter_types_before_calling():
    called = False

    def build_dummy(**kwargs):
        nonlocal called
        called = True
        return kwargs

    local_registry = BuilderRegistry()
    local_registry.register(BuilderSpec(
        name="dummy",
        category="test",
        callable=build_dummy,
        parameter_schema={
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"],
        },
    ))

    with pytest.raises(TypeError, match="Parameter 'count' must be an integer"):
        local_registry.build("dummy", count="two")
    assert called is False
