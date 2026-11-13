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

# Parameter names known to expect Structure-like objects in kwargs.
_STRUCTURE_PARAMS = frozenset({"molecule2", "other"})

_IDENTITY_MATRIX = [
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
]

_VALID_KWARG_OVERRIDES = {
    "apply_deformation": {"deformation_matrix": _IDENTITY_MATRIX},
    "optimize_lattice": {"target_volume": 180.0},
    "rotate_lattice": {"rotation_matrix": _IDENTITY_MATRIX},
    "transform_lattice": {"transformation_matrix": _IDENTITY_MATRIX},
    "make_supercell": {"scaling_matrix": [1, 1, 1]},
    "fragment_molecule": {"break_indices": [[0, 1]]},
    "merge_molecules": {"bond_length": 1.5},
    "swap_atoms": {"index1": 0, "index2": 1},
    "merge_atoms": {"index1": 0, "index2": 1},
}


def _structure_for_param(name, spec):
    """Return an appropriate Crystal or Molecule fixture for a structure param."""
    if spec.output_type == Molecule or Molecule in spec.applicable_types:
        return Molecule(
            ['O', 'H', 'H'],
            [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
        )
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


def _minimal_kwargs(spec):
    """Build minimally valid kwargs from the spec's parameter_schema."""
    schema = spec.parameter_schema or {}
    props = schema.get("properties", {})
    kwargs = {}
    required = schema.get("required", [])
    for name in required:
        prop = props[name]
        if name in _STRUCTURE_PARAMS:
            kwargs[name] = _structure_for_param(name, spec)
        elif "default" in prop:
            kwargs[name] = prop["default"]
        elif "oneOf" in prop:
            kwargs[name] = _value_from_schema(prop["oneOf"][0])
        else:
            kwargs[name] = _value_from_schema(prop)
    kwargs.update(_VALID_KWARG_OVERRIDES.get(spec.name, {}))
    return kwargs


def _for_structure(spec, kwargs, structure):
    """Adjust kwargs that depend on the structure (species that must be present)."""
    if spec.name == "substitute_all":
        return {**kwargs, "old_species": structure.species[0]}
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
        return 0
    elif t == "boolean":
        return False
    elif t == "array":
        item_schema = schema.get("items", {"type": "number"})
        min_items = schema.get("minItems", 1)
        return [_value_from_schema(item_schema)] * min_items
    elif t == "object":
        return {}
    return None


@pytest.mark.parametrize("spec", all_specs, ids=spec_ids)
class TestTransformationContract:
    """Every transformation obeys its contract."""

    def test_returns_new_object(self, spec, nacl, water):
        """Every transformation returns a new object."""
        kwargs = _minimal_kwargs(spec)
        structures = []
        if Crystal in spec.applicable_types:
            structures.append(nacl)
        if Molecule in spec.applicable_types:
            structures.append(water)

        for structure in structures:
            result = spec.callable(structure, **_for_structure(spec, kwargs, structure))
            assert id(result) != id(structure)
            assert isinstance(result, spec.output_type)
            if len(spec.applicable_types) > 1:
                assert isinstance(result, type(structure))

    def test_type_constraint(self, spec, nacl, water):
        """Registry.apply rejects incompatible types."""
        kwargs = _minimal_kwargs(spec)
        with pytest.raises(TypeError):
            registry.apply(spec.name, object(), **kwargs)

    def test_registry_apply_works(self, spec, nacl, water):
        """Registry.apply works with valid type."""
        kwargs = _minimal_kwargs(spec)
        structures = []
        if Crystal in spec.applicable_types:
            structures.append(nacl)
        if Molecule in spec.applicable_types:
            structures.append(water)

        for structure in structures:
            result = registry.apply(spec.name, structure, **_for_structure(spec, kwargs, structure))
            assert isinstance(result, spec.output_type)
            if len(spec.applicable_types) > 1:
                assert isinstance(result, type(structure))


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


def test_split_atom_registry_accepts_species_list():
    molecule = Molecule(["O"], [[0.0, 0.0, 0.0]])

    result = registry.apply(
        "split_atom",
        molecule,
        index=0,
        species=["H", "H"],
        positions=[[0.0, 0.0, 0.0], [0.1, 0.0, 0.0]],
    )

    assert isinstance(result, Molecule)
    assert result.species == ("H", "H")


def test_split_atom_registry_rejects_more_species_than_positions():
    molecule = Molecule(["O"], [[0.0, 0.0, 0.0]])

    with pytest.raises(ValueError, match="same length"):
        registry.apply(
            "split_atom",
            molecule,
            index=0,
            species=["H", "H", "H"],
            positions=[[0.0, 0.0, 0.0], [0.1, 0.0, 0.0]],
        )
