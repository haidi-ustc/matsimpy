"""Auto-register built-in builder functions with the BuilderRegistry."""

from ..core import Crystal, Molecule
from .registry import registry, BuilderSpec


def register_all():
    """Register all built-in builders with the global registry."""

    # --- bulk ---
    from .bulk.prototype import from_prototype
    registry.register(BuilderSpec(
        name="from_prototype", category="bulk", callable=from_prototype,
        description="Build bulk crystal from prototype (fcc, bcc, hcp, etc.)",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "prototype": {"type": "string", "description": "fcc, bcc, hcp, diamond, rocksalt, etc."},
                "element": {"type": "string"},
                "a": {"type": "number", "description": "Lattice constant in Angstrom"},
            },
            "required": ["prototype", "element", "a"],
        },
    ))

    try:
        from .bulk.random import random_crystal

        def _random_crystal_from_registry(
            sg, species, numIons, dim=3, factor=1.0, **kwargs
        ):
            return random_crystal(
                dim=dim,
                group=sg,
                species=species,
                num_ions=numIons,
                factor=factor,
                **kwargs,
            )

        registry.register(BuilderSpec(
            name="random_crystal", category="bulk", callable=_random_crystal_from_registry,
            description="Generate random crystal with symmetry constraints",
            output_type=Crystal,
            requires_optional=("pyxtal",),
            parameter_schema={
                "type": "object",
                "properties": {
                    "dim": {"type": "integer", "default": 3},
                    "sg": {"type": "integer"},
                    "species": {"type": "array", "items": {"type": "string"}},
                    "numIons": {"type": "array", "items": {"type": "integer"}},
                    "factor": {"type": "number", "default": 1.0},
                },
                "required": ["sg", "species", "numIons"],
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
                "structure": {},
                "miller_index": {
                    "type": "array", "items": {"type": "integer"},
                    "minItems": 3, "maxItems": 3,
                },
                "min_slab_size": {"type": "number"},
                "min_vacuum_size": {"type": "number"},
            },
            "required": ["structure", "miller_index", "min_slab_size", "min_vacuum_size"],
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
                "structure": {},
                "species": {"type": "string"},
                "position": {
                    "type": "array", "items": {"type": "number"},
                    "minItems": 2, "maxItems": 2,
                },
                "height": {"type": "number"},
            },
            "required": ["structure", "species", "position", "height"],
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
                "structure": {},
                "new_species": {"type": "array", "items": {"type": "string"}},
                "old_species": {"type": "string"},
                "concentrations": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["structure", "new_species", "old_species", "concentrations"],
        },
    ))
    registry.register(BuilderSpec(
        name="generate_ordered_alloy", category="alloy", callable=generate_ordered_alloy,
        description="Generate ordered substitution alloy",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure": {},
                "substitutions": {"type": "array"},
            },
            "required": ["structure", "substitutions"],
        },
    ))
    registry.register(BuilderSpec(
        name="generate_intermetallic", category="alloy", callable=generate_intermetallic,
        description="Generate intermetallic compound (L1_2, B2, etc.)",
        output_type=Crystal,
        parameter_schema={
            "type": "object",
            "properties": {
                "structure_type": {"type": "string"},
                "elements": {"type": "array", "items": {"type": "string"}},
                "a": {"type": "number"},
            },
            "required": ["structure_type", "elements", "a"],
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
                    "a": {"type": "number"},
                },
                "required": ["X", "Y", "Z", "a"],
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
                "position": {
                    "type": "array", "items": {"type": "number"},
                    "minItems": 3, "maxItems": 3,
                },
            },
            "required": ["structure", "species", "position"],
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
    for fn, name in [
        (create_frenkel, "create_frenkel"),
        (create_schottky, "create_schottky"),
        (create_antisite, "create_antisite"),
    ]:
        registry.register(BuilderSpec(
            name=name, category="defects", callable=fn,
            description=f"{name.replace('_', ' ').title()} in crystal structure",
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
                "species": {"type": "array", "items": {"type": "string"}},
                "bond_lengths": {"type": "array", "items": {"type": "number"}},
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
                "species": {"type": "array", "items": {"type": "string"}},
                "bond_lengths": {"type": "array", "items": {"type": "number"}},
                "angle": {"type": "number"},
            },
            "required": ["species", "bond_lengths", "angle"],
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
                "outer_atoms": {"type": "array", "items": {"type": "string"}},
                "bond_length": {"type": "number"},
            },
            "required": ["central_atom", "outer_atoms", "bond_length"],
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
                "structure": {},
                "n": {"type": "integer"},
                "m": {"type": "integer"},
            },
            "required": ["structure", "n", "m"],
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
    for fn, name in [
        (build_twisted_bilayer, "build_twisted_bilayer"),
        (build_magic_angle_twisted, "build_magic_angle_twisted"),
    ]:
        registry.register(BuilderSpec(
            name=name, category="nanostructure", callable=fn,
            description=f"Build {name.replace('build_', '').replace('_', ' ')} structure",
            output_type=Crystal,
            parameter_schema={
                "type": "object",
                "properties": {
                    "bottom": {},
                    "top": {},
                    "angle": {"type": "number"},
                },
                "required": ["bottom", "top", "angle"],
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
                "layers": {"type": "array"},
                "angles": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["layers", "angles"],
        },
    ))
