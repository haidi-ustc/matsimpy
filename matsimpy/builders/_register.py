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

    from .surface.adsorbate import add_adsorbate
    registry.register(BuilderSpec(
        name="add_adsorbate", category="surface", callable=add_adsorbate,
        description="Add adsorbate to a surface structure",
        output_type=Crystal,
    ))

    # --- alloy ---
    from .alloy.random import generate_random_alloy
    from .alloy.ordered import generate_ordered_alloy, generate_intermetallic
    from .alloy.heusler import (
        build_heusler, build_full_heusler, build_half_heusler, build_inverse_heusler,
    )
    for fn, name in [
        (generate_random_alloy, "generate_random_alloy"),
        (generate_ordered_alloy, "generate_ordered_alloy"),
        (generate_intermetallic, "generate_intermetallic"),
        (build_heusler, "build_heusler"),
        (build_full_heusler, "build_full_heusler"),
        (build_half_heusler, "build_half_heusler"),
        (build_inverse_heusler, "build_inverse_heusler"),
    ]:
        registry.register(BuilderSpec(
            name=name, category="alloy", callable=fn,
            description=f"Generate {name.replace('_', ' ')} structure",
            output_type=Crystal,
        ))

    # --- defects ---
    from .defects.point import (
        create_vacancy, create_interstitial, create_substitution,
        create_frenkel, create_schottky, create_antisite,
    )
    for fn, name in [
        (create_vacancy, "create_vacancy"),
        (create_interstitial, "create_interstitial"),
        (create_substitution, "create_substitution"),
        (create_frenkel, "create_frenkel"),
        (create_schottky, "create_schottky"),
        (create_antisite, "create_antisite"),
    ]:
        registry.register(BuilderSpec(
            name=name, category="defects", callable=fn,
            description=f"{name.replace('_', ' ').title()} in crystal structure",
            output_type=Crystal,
        ))

    # --- interface ---
    from .interface import create_simple_interface
    registry.register(BuilderSpec(
        name="create_simple_interface", category="interface",
        callable=create_simple_interface,
        description="Create a simple interface by stacking two crystals",
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
