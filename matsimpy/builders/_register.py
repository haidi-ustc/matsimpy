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
                "prototype": {"type": "string"},
                "element": {"type": "string"},
                "a": {"type": "number"},
            },
            "required": ["prototype", "element", "a"],
        },
    ))

    # random_crystal requires pyxtal
    try:
        from .bulk.random import random_crystal
        registry.register(BuilderSpec(
            name="random_crystal", category="bulk", callable=random_crystal,
            description="Generate random crystal with symmetry constraints",
            output_type=Crystal,
            requires_optional=("pyxtal",),
        ))
    except ImportError:
        pass

    # --- surface ---
    from .surface.slab import generate_slab
    registry.register(BuilderSpec(
        name="generate_slab", category="surface", callable=generate_slab,
        description="Create surface slab with vacuum from bulk crystal",
        output_type=Crystal,
    ))

    # --- molecule ---
    from .molecule.geometry import (
        build_linear, build_bent, build_tetrahedral,
    )
    for fn, name in [
        (build_linear, "build_linear"),
        (build_bent, "build_bent"),
        (build_tetrahedral, "build_tetrahedral"),
    ]:
        registry.register(BuilderSpec(
            name=name, category="molecule", callable=fn,
            description=f"Build {name.replace('build_', '')} molecule geometry",
            output_type=Molecule,
        ))

    # build_from_smiles requires RDKit
    try:
        from .molecule.smiles import build_from_smiles
        registry.register(BuilderSpec(
            name="build_from_smiles", category="molecule", callable=build_from_smiles,
            description="Build molecule from SMILES string (requires RDKit)",
            output_type=Molecule, requires_optional=("rdkit",),
        ))
    except ImportError:
        pass

    # --- nanostructure ---
    from .nanostructure.nanotube import build_nanotube, build_carbon_nanotube
    from .nanostructure.twisted import (
        build_twisted_bilayer, build_magic_angle_twisted, build_twisted_multilayer,
    )
    for fn, name in [
        (build_nanotube, "build_nanotube"),
        (build_carbon_nanotube, "build_carbon_nanotube"),
        (build_twisted_bilayer, "build_twisted_bilayer"),
        (build_magic_angle_twisted, "build_magic_angle_twisted"),
        (build_twisted_multilayer, "build_twisted_multilayer"),
    ]:
        registry.register(BuilderSpec(
            name=name, category="nanostructure", callable=fn,
            description=f"Build {name.replace('build_', '').replace('_', ' ')} structure",
            output_type=Crystal,
        ))
