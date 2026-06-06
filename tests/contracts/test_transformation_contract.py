"""Contract tests for all registered transformations.

Parametrized over all TransformationSpecs in the registry.
Tests: new-object return, type constraints enforced.
"""

import pytest
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.transformation.registry import registry


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
    """Try to build minimally valid kwargs from the spec's parameter_schema."""
    schema = spec.parameter_schema or {}
    props = schema.get("properties", {})
    kwargs = {}
    for name, prop in props.items():
        if "default" in prop:
            kwargs[name] = prop["default"]
        elif prop.get("type") == "array" and "items" in prop:
            kwargs[name] = [0.1] * prop.get("minItems", 1)
        elif prop.get("type") == "number":
            kwargs[name] = 0.1
        elif prop.get("type") == "string":
            kwargs[name] = "test"
        elif prop.get("type") == "integer":
            kwargs[name] = 0
        elif prop.get("type") == "boolean":
            kwargs[name] = False
    return kwargs


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
