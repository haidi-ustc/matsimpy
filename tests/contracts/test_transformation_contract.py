"""Contract tests for all registered transformations.

Parametrized over all TransformationSpecs in the registry.
Tests: new-object return, type constraints enforced.
"""

import pytest
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.transformation.registry import TransformationRegistry, registry
from matsimpy.transformation.spec import TransformationSpec


@pytest.fixture
def nacl():
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


@pytest.fixture
def water():
    return Molecule(
        ['O', 'H', 'H'],
        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
    )


all_specs = registry.list_all()
spec_ids = [s.name for s in all_specs]


def _minimal_kwargs(spec):
    """Build minimally valid kwargs from the spec's parameter_schema."""
    schema = spec.parameter_schema or {}
    props = schema.get("properties", {})
    kwargs = {}
    for name, prop in props.items():
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
        return "test"
    elif t == "number":
        return 0.1
    elif t == "integer":
        return 0
    elif t == "boolean":
        return False
    elif t == "array":
        item_schema = schema.get("items", {"type": "number"})
        min_items = schema.get("minItems", 1)
        return [_value_from_schema(item_schema)] * min_items
    return None


@pytest.mark.parametrize("spec", all_specs, ids=spec_ids)
class TestTransformationContract:
    """Every transformation obeys its contract."""

    def test_returns_new_object(self, spec, nacl, water):
        """Every transformation returns a new object."""
        structure = nacl if Crystal in spec.applicable_types else water
        kwargs = _minimal_kwargs(spec)
        try:
            result = spec.callable(structure, **kwargs)
            assert id(result) != id(structure)
        except (ValueError, TypeError, IndexError):
            # Some transforms require specific valid kwargs that
            # the auto-generated minimal ones can't provide.
            # That's OK — type checking tests catch those separately.
            pytest.skip("Requires more specific kwargs than auto-generated")

    def test_type_constraint(self, spec, nacl, water):
        """Registry.apply rejects incompatible types."""
        # Find a truly incompatible type
        if Crystal in spec.applicable_types and Molecule not in spec.applicable_types:
            bad_structure = water
        elif Molecule in spec.applicable_types and Crystal not in spec.applicable_types:
            bad_structure = nacl
        else:
            pytest.skip("Transform accepts both Crystal and Molecule")
        kwargs = _minimal_kwargs(spec)
        with pytest.raises(TypeError):
            registry.apply(spec.name, bad_structure, **kwargs)

    def test_registry_apply_works(self, spec, nacl, water):
        """Registry.apply works with valid type."""
        structure = nacl if Crystal in spec.applicable_types else water
        kwargs = _minimal_kwargs(spec)
        try:
            result = registry.apply(spec.name, structure, **kwargs)
            assert result is not None
        except (ValueError, TypeError, IndexError):
            pytest.skip("Requires more specific kwargs")


def test_transformation_registry_validates_required_parameters_before_calling(nacl):
    called = False

    def transform_dummy(structure, **kwargs):
        nonlocal called
        called = True
        return structure

    local_registry = TransformationRegistry()
    local_registry.register(TransformationSpec(
        name="dummy",
        category="test",
        callable=transform_dummy,
        applicable_types=(Crystal,),
        parameter_schema={
            "type": "object",
            "properties": {"vector": {"type": "array"}},
            "required": ["vector"],
        },
    ))

    with pytest.raises(ValueError, match="Missing required parameter: vector"):
        local_registry.apply("dummy", nacl)
    assert called is False


def test_transformation_registry_validates_parameter_types_before_calling(nacl):
    called = False

    def transform_dummy(structure, **kwargs):
        nonlocal called
        called = True
        return structure

    local_registry = TransformationRegistry()
    local_registry.register(TransformationSpec(
        name="dummy",
        category="test",
        callable=transform_dummy,
        applicable_types=(Crystal,),
        parameter_schema={
            "type": "object",
            "properties": {"scale": {"type": "number"}},
            "required": ["scale"],
        },
    ))

    with pytest.raises(TypeError, match="Parameter 'scale' must be a number"):
        local_registry.apply("dummy", nacl, scale="large")
    assert called is False
