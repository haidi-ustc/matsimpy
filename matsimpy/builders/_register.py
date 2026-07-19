"""Auto-register built-in builder functions with the BuilderRegistry."""

from ..core import Crystal, Molecule
from .registry import registry, BuilderSpec


def register_all():
    """Register all built-in builders with the global registry."""

    # --- bulk ---
    from .bulk.prototype import from_prototype
    registry.register(BuilderSpec(
        name="from_prototype", category="bulk", callable=from_prototype,
        description=(
            "Build a primitive bulk cell from a named prototype (fcc, rocksalt, etc.); "
            "lattice_constant is the conventional prototype parameter"
        ),
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "prototype": {
                    "type": "string",
                    "enum": ["fcc", "bcc", "hcp", "diamond", "zincblende", "rocksalt", "wurtzite", "perovskite", "sc"],
                },
                "species": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    ],
                    "description": "Element symbol/formula or ordered species for prototype sites",
                },
                "lattice_constant": {
                    "oneOf": [
                        {"type": "number"},
                        {"type": "array", "items": {"type": "number"}, "minItems": 1},
                    ],
                    "description": "Lattice constant in Angstrom; anisotropic prototypes accept a list",
                },
            },
            "required": ["prototype", "species", "lattice_constant"],
        },
    ))

    try:
        from .bulk.random import random_crystal
        registry.register(BuilderSpec(
            name="random_crystal", category="bulk", callable=random_crystal,
            description="Generate random crystal with symmetry constraints",
            output_type=Crystal,
            requires_optional=("pyxtal",),
            parameter_schema={
                "type": "object",
                "properties": {
                    "dim": {"type": "integer", "default": 3},
                    "group": {"type": "integer"},
                    "species": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "num_ions": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
                    "factor": {"type": "number", "default": 1.0},
                },
                "required": ["dim", "group", "species", "num_ions"],
            },
        ))
    except ImportError:
        pass

    # --- surface ---
    from .surface.slab import generate_slab
    registry.register(BuilderSpec(
        name="generate_slab", category="surface", callable=generate_slab,
        description="Create surface slab with vacuum from bulk crystal",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "bulk": {},
                "miller_index": {
                    "type": "array", "items": {"type": "integer"},
                    "minItems": 3, "maxItems": 3,
                },
                "min_slab_size": {"type": "number"},
                "min_vacuum_size": {"type": "number"},
            },
            "required": ["bulk", "miller_index", "min_slab_size", "min_vacuum_size"],
        },
    ))

    from .surface.adsorbate import add_adsorbate
    registry.register(BuilderSpec(
        name="add_adsorbate", category="surface", callable=add_adsorbate,
        description="Add adsorbate to a surface structure",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "slab": {},
                "adsorbate": {"type": "string"},
                "position": {
                    "type": "array", "items": {"type": "number"},
                    "minItems": 2, "maxItems": 2,
                },
                "height": {"type": "number"},
            },
            "required": ["slab", "adsorbate", "position", "height"],
        },
    ))

    # --- alloy ---
    from .alloy.random import generate_random_alloy
    from .alloy.ordered import generate_ordered_alloy, generate_intermetallic
    from .alloy.heusler import (
        build_heusler, build_full_heusler, build_half_heusler, build_inverse_heusler,
    )

    registry.register(BuilderSpec(
        name="generate_random_alloy", category="alloy", callable=generate_random_alloy,
        description="Generate random solid solution alloy",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "base_structure": {},
                "substitution_species": {"type": "array", "items": {"type": "string"}},
                "site_species": {"type": "string"},
                "concentrations": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["base_structure", "substitution_species", "site_species"],
        },
    ))
    registry.register(BuilderSpec(
        name="generate_ordered_alloy", category="alloy", callable=generate_ordered_alloy,
        description="Generate ordered substitution alloy",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "base_structure": {},
                "substitution_pattern": {
                    "type": "object",
                    "description": "Dict mapping site indices (int) to species (str)",
                },
            },
            "required": ["base_structure", "substitution_pattern"],
        },
    ))
    registry.register(BuilderSpec(
        name="generate_intermetallic", category="alloy", callable=generate_intermetallic,
        description="Generate intermetallic compound (L1_2, B2, etc.)",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure_type": {
                    "type": "string",
                    "enum": ["L1_2", "B2", "L1_0"],
                },
                "elements": {"type": "array", "items": {"type": "string"}},
                "composition": {"type": "string"},
                "lattice_constant": {"type": "number"},
            },
            "required": ["structure_type", "elements", "composition", "lattice_constant"],
        },
    ))
    for fn, name in [
        (build_heusler, "build_heusler"),
        (build_full_heusler, "build_full_heusler"),
        (build_half_heusler, "build_half_heusler"),
        (build_inverse_heusler, "build_inverse_heusler"),
    ]:
        registry.register(BuilderSpec(
            name=name, category="alloy", callable=fn,
            description=f"Generate {name.replace('_', ' ')} structure",
            output_type=Crystal,
            parameter_schema={
                "type": "object",
                "properties": {
                    "X": {"type": "string"},
                    "Y": {"type": "string"},
                    "Z": {"type": "string"},
                    "lattice_constant": {"type": "number"},
                },
                "required": ["X", "Y", "Z", "lattice_constant"],
            },
        ))

    # --- defects ---
    from .defects.point import (
        create_vacancy, create_interstitial, create_substitution,
        create_frenkel, create_schottky, create_antisite,
    )

    registry.register(BuilderSpec(
        name="create_vacancy", category="defects", callable=create_vacancy,
        description="Remove atom(s) to create vacancies",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure": {},
                "indices": {
                    "oneOf": [
                        {"type": "integer"},
                        {"type": "array", "items": {"type": "integer"}},
                    ],
                },
            },
            "required": ["structure", "indices"],
        },
    ))
    registry.register(BuilderSpec(
        name="create_interstitial", category="defects", callable=create_interstitial,
        description="Add interstitial atom at specified position",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure": {},
                "species": {"type": "string"},
                "positions": {
                    "type": "array", "items": {"type": "number"},
                    "minItems": 3, "maxItems": 3,
                },
            },
            "required": ["structure", "species", "positions"],
        },
    ))
    registry.register(BuilderSpec(
        name="create_substitution", category="defects", callable=create_substitution,
        description="Substitute atom(s) with different species",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure": {},
                "indices": {
                    "oneOf": [
                        {"type": "integer"},
                        {"type": "array", "items": {"type": "integer"}},
                    ],
                },
                "new_species": {"type": "string"},
            },
            "required": ["structure", "indices", "new_species"],
        },
    ))
    registry.register(BuilderSpec(
        name="create_frenkel", category="defects", callable=create_frenkel,
        description="Create Frenkel defect in crystal structure",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure": {},
                "index": {"type": "integer"},
                "interstitial_position": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["structure", "index"],
        },
    ))
    registry.register(BuilderSpec(
        name="create_schottky", category="defects", callable=create_schottky,
        description="Create Schottky defect in crystal structure",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure": {},
                "indices": {
                    "oneOf": [
                        {"type": "integer"},
                        {"type": "array", "items": {"type": "integer"}},
                    ],
                },
                "num_vacancies": {"type": "integer", "default": 2},
            },
            "required": ["structure"],
        },
    ))
    registry.register(BuilderSpec(
        name="create_antisite", category="defects", callable=create_antisite,
        description="Create antisite defect in crystal structure",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure": {},
                "index1": {"type": "integer"},
                "index2": {"type": "integer"},
            },
            "required": ["structure", "index1", "index2"],
        },
    ))

    # --- interface ---
    from .interface import create_simple_interface
    registry.register(BuilderSpec(
        name="create_simple_interface", category="interface",
        callable=create_simple_interface,
        description="Create a simple interface by stacking two crystals",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "substrate": {},
                "film": {},
            },
            "required": ["substrate", "film"],
        },
    ))

    # --- molecule ---
    from .molecule.geometry import (
        build_linear, build_bent, build_tetrahedral,
    )

    registry.register(BuilderSpec(
        name="build_linear", category="molecule", callable=build_linear,
        description="Build linear molecule geometry",
        output_type=Molecule,
        parameter_schema={
            "type": "object",
            "properties": {
                "species": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                "bond_lengths": {"type": "array", "items": {"type": "number"}, "minItems": 1},
            },
            "required": ["species", "bond_lengths"],
        },
    ))
    registry.register(BuilderSpec(
        name="build_bent", category="molecule", callable=build_bent,
        description="Build bent molecule geometry",
        output_type=Molecule,
        parameter_schema={
            "type": "object",
            "properties": {
                "species": {"type": "array", "items": {"type": "string"}, "minItems": 3},
                "bond_lengths": {"type": "array", "items": {"type": "number"}, "minItems": 2},
                "angles": {"type": "array", "items": {"type": "number"}, "minItems": 1},
            },
            "required": ["species", "bond_lengths", "angles"],
        },
    ))
    registry.register(BuilderSpec(
        name="build_tetrahedral", category="molecule", callable=build_tetrahedral,
        description="Build tetrahedral molecule geometry",
        output_type=Molecule,
        parameter_schema={
            "type": "object",
            "properties": {
                "central_atom": {"type": "string"},
                "peripheral_atoms": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
                "bond_length": {"type": "number"},
            },
            "required": ["central_atom", "peripheral_atoms", "bond_length"],
        },
    ))

    try:
        from .molecule.smiles import build_from_smiles
        registry.register(BuilderSpec(
            name="build_from_smiles", category="molecule", callable=build_from_smiles,
            description="Build molecule from SMILES string (requires RDKit)",
            output_type=Molecule, requires_optional=("rdkit",),
            parameter_schema={
                "type": "object",
                "properties": {
                    "smiles": {"type": "string"},
                    "optimize": {"type": "boolean", "default": True},
                },
                "required": ["smiles"],
            },
        ))
    except ImportError:
        pass

    # --- nanostructure ---
    from .nanostructure.nanotube import build_nanotube, build_carbon_nanotube
    from .nanostructure.twisted import (
        build_twisted_bilayer, build_magic_angle_twisted, build_twisted_multilayer,
    )

    registry.register(BuilderSpec(
        name="build_nanotube", category="nanostructure", callable=build_nanotube,
        description="Build nanotube from 2D sheet",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "base_2d": {},
                "chirality": {
                    "type": "array", "items": {"type": "integer"},
                    "minItems": 2, "maxItems": 2,
                },
            },
            "required": ["base_2d", "chirality"],
        },
    ))
    registry.register(BuilderSpec(
        name="build_carbon_nanotube", category="nanostructure",
        callable=build_carbon_nanotube,
        description="Build carbon nanotube from chirality (n, m)",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "n": {"type": "integer"},
                "m": {"type": "integer"},
                "bond_length": {"type": "number", "default": 1.42},
            },
            "required": ["n", "m"],
        },
    ))
    registry.register(BuilderSpec(
        name="build_twisted_bilayer", category="nanostructure",
        callable=build_twisted_bilayer,
        description="Build twisted bilayer structure",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "layer": {},
                "twist_angle": {"type": "number"},
            },
            "required": ["layer", "twist_angle"],
        },
    ))
    registry.register(BuilderSpec(
        name="build_magic_angle_twisted", category="nanostructure",
        callable=build_magic_angle_twisted,
        description="Build magic-angle twisted bilayer structure",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "layer": {},
                "n": {"type": "integer"},
                "m": {"type": "integer"},
            },
            "required": ["layer", "n", "m"],
        },
    ))
    registry.register(BuilderSpec(
        name="build_twisted_multilayer", category="nanostructure",
        callable=build_twisted_multilayer,
        description="Build twisted multilayer structure",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "layer": {},
                "num_layers": {"type": "integer"},
                "twist_angles": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["layer", "num_layers", "twist_angles"],
        },
    ))
