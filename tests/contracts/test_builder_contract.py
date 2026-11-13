"""Contract tests for all registered builders.

Parametrized over all BuilderSpecs in the registry.
Tests: output_type correctness.
"""

import pytest
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.builders.registry import BuilderRegistry, BuilderSpec, registry


all_specs = registry.list_all()
spec_ids = [s.name for s in all_specs]


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


# Parameter names known to expect Structure-like objects.
# The contract test provides a real Crystal or Molecule fixture for these.
_STRUCTURE_PARAMS = frozenset({
    "structure", "bulk", "slab", "adsorbate",
    "substrate", "film", "bottom", "top", "layers", "layer",
    "base_structure", "base_2d", "other",
})

_VALID_KWARG_OVERRIDES = {
    "generate_random_alloy": {
        "substitution_species": ["K"],
        "site_species": "Na",
    },
    "generate_ordered_alloy": {"substitution_pattern": {0: "K"}},
    "generate_intermetallic": {
        "elements": ["Fe", "Pt"],
        "composition": "AB",
        "structure_type": "L1_0",
    },
    "create_interstitial": {"positions": [0.25, 0.25, 0.25]},
    "create_antisite": {"index1": 0, "index2": 1},
    "create_frenkel": {"interstitial_position": [0.25, 0.25, 0.25]},
    # one formula unit of the 2-atom fixture would be every atom
    "create_schottky": {"structure": Crystal(
        ['Na'] * 4 + ['Cl'] * 4,
        [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5],
         [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64))},
    "generate_slab": {"layers": 2},
    "generate_symmetric_slab": {"layers": 2, "miller_index": [1, 1, 0]},  # CsCl-type (111) is polar
    "build_from_smiles": {"smiles": "O"},
    # the NaCl fixture is a square sheet (Cl 2.8 A above Na): roll it wide enough,
    # and twist it by a commensurate square-lattice angle
    "build_nanotube": {"chirality": [6, 6]},
    "build_twisted_bilayer": {"twist_angle": 36.869898},
    "build_magic_angle_twisted": {"n": 2, "m": 1},
    "build_twisted_multilayer": {"num_layers": 2, "twist_angles": 36.869898},
}


def _structure_for_param(name, spec):
    """Return an appropriate Crystal or Molecule fixture for a structure param."""
    if spec.output_type == Molecule:
        return Molecule(['O', 'H', 'H'],
                        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
    # Default: Crystal
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


def _minimal_kwargs(spec):
    """Build minimally valid kwargs from spec's parameter_schema."""
    schema = spec.parameter_schema or {}
    props = schema.get("properties", {})
    required = schema.get("required", [])
    kwargs = {}
    for name, prop in props.items():
        if name not in required:
            continue
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
    elif t == "object":
        return {}
    return None


@pytest.mark.parametrize("spec", all_specs, ids=spec_ids)
class TestBuilderContract:

    def test_returns_correct_type(self, spec):
        """Builder returns the declared output_type."""
        if spec.requires_optional:
            for dep in spec.requires_optional:
                try:
                    __import__(dep)
                except ImportError:
                    pytest.skip(f"Optional dependency {dep} not installed")

        kwargs = _minimal_kwargs(spec)
        result = spec.callable(**kwargs)
        assert isinstance(result, spec.output_type)

    def test_output_is_not_none(self, spec):
        """Builder output is not None."""
        if spec.requires_optional:
            for dep in spec.requires_optional:
                try:
                    __import__(dep)
                except ImportError:
                    pytest.skip(f"Optional dependency {dep} not installed")

        kwargs = _minimal_kwargs(spec)
        result = spec.callable(**kwargs)
        assert result is not None


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


def test_generate_intermetallic_registry_accepts_documented_composition():
    result = registry.build(
        "generate_intermetallic",
        elements=["Fe", "Pt"],
        composition="AB",
        structure_type="L1_0",
        lattice_constant=3.85,
    )

    assert isinstance(result, Crystal)
