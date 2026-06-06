"""
Auto-register all built-in transformation functions with the registry.

Imported once at package initialization to populate the singleton
TransformationRegistry.
"""

from ..core import Crystal, Molecule
from .registry import registry
from .spec import TransformationSpec

from .geometric.translation import translate, translate_to_origin
from .geometric.rotation import rotate, rotate_around_axis
from .lattice.strain import apply_strain, apply_deformation, perturb_lattice
from .lattice.scale import scale_lattice, set_volume, optimize_lattice
from .lattice.transform import rotate_lattice, transform_lattice, standardize_cell
from .atomic.manipulation import move_atoms, swap_atoms, merge_atoms, split_atom
from .atomic.organization import sort_atoms, center_structure, perturb_positions
from .chemical.substitution import substitute, substitute_all
from .structural.supercell import make_supercell

# Lazy imports for molecular operations (may not exist)
try:
    from .structural.molecular import (
        fragment_molecule, align_molecules, merge_molecules
    )
except ImportError:
    fragment_molecule = None
    align_molecules = None
    merge_molecules = None

_GEOMETRIC = "geometric"
_LATTICE = "lattice"
_ATOMIC = "atomic"
_CHEMICAL = "chemical"
_STRUCTURAL = "structural"
_BOTH = (Crystal, Molecule)
_CRYSTAL = (Crystal,)
_BOTH_TYPES = (Crystal, Molecule)


def _v3():
    return {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 3,
        "maxItems": 3,
    }


def register_all():
    """Register all built-in transformations with the global registry."""

    # --- Geometric ---
    for fn, name, desc, types in [
        (translate, "translate", "Translate structure by a 3D vector", _BOTH),
        (translate_to_origin, "translate_to_origin",
         "Translate center of mass to origin", _BOTH),
        (rotate, "rotate", "Rotate structure around an axis by angle (degrees)", _BOTH),
        (rotate_around_axis, "rotate_around_axis",
         "Rotate structure around an arbitrary axis", _BOTH),
    ]:
        spec = TransformationSpec(
            name=name, category=_GEOMETRIC, callable=fn,
            description=desc, applicable_types=types,
            output_type=Crystal if Crystal in types else None,
            preserves_composition=True, preserves_lattice=True,
            preserves_site_properties=True, preserves_pbc=True,
            parameter_schema={"type": "object"},
            version="1.0.0",
        )
        registry.register(spec)

    # --- Lattice ---
    for fn, name, desc in [
        (apply_strain, "apply_strain",
         "Apply strain tensor to crystal lattice"),
        (apply_deformation, "apply_deformation",
         "Apply deformation gradient to crystal"),
        (perturb_lattice, "perturb_lattice",
         "Apply random perturbations to lattice vectors"),
        (scale_lattice, "scale_lattice",
         "Scale lattice by isotropic or anisotropic factor"),
        (set_volume, "set_volume",
         "Scale lattice to achieve target volume"),
        (optimize_lattice, "optimize_lattice",
         "Optimize lattice angles while preserving volume"),
        (rotate_lattice, "rotate_lattice",
         "Rotate lattice by 3D rotation matrix"),
        (transform_lattice, "transform_lattice",
         "Apply arbitrary transformation matrix to lattice"),
        (standardize_cell, "standardize_cell",
         "Standardize unit cell to convention"),
    ]:
        spec = TransformationSpec(
            name=name, category=_LATTICE, callable=fn,
            description=desc, applicable_types=_CRYSTAL,
            output_type=Crystal,
            preserves_composition=True, preserves_lattice=False,
            preserves_site_properties=True, preserves_pbc=True,
            parameter_schema={"type": "object"},
            version="1.0.0",
        )
        registry.register(spec)

    # --- Atomic ---
    for fn, name, desc in [
        (move_atoms, "move_atoms", "Move selected atoms by a displacement vector"),
        (swap_atoms, "swap_atoms", "Swap positions of two atoms"),
        (merge_atoms, "merge_atoms", "Merge two atoms into one at their midpoint"),
        (split_atom, "split_atom", "Split one atom into two at displaced positions"),
        (sort_atoms, "sort_atoms", "Sort atoms by specified criterion"),
        (center_structure, "center_structure", "Center structure at origin"),
        (perturb_positions, "perturb_positions", "Apply random perturbations to atomic positions"),
    ]:
        spec = TransformationSpec(
            name=name, category=_ATOMIC, callable=fn,
            description=desc, applicable_types=_BOTH,
            output_type=Crystal,
            preserves_composition=True,
            preserves_lattice=True,
            preserves_site_properties=True,
            preserves_pbc=True,
            parameter_schema={"type": "object"},
            version="1.0.0",
        )
        registry.register(spec)

    # --- Chemical ---
    for fn, name, desc, types in [
        (substitute, "substitute",
         "Substitute specific atom(s) with new species", _BOTH),
        (substitute_all, "substitute_all",
         "Substitute all atoms of one species with another", _BOTH),
    ]:
        spec = TransformationSpec(
            name=name, category=_CHEMICAL, callable=fn,
            description=desc, applicable_types=types,
            output_type=Crystal if Crystal in types else None,
            preserves_composition=False, preserves_lattice=True,
            preserves_site_properties=True, preserves_pbc=True,
            parameter_schema={"type": "object"},
            version="1.0.0",
        )
        registry.register(spec)

    # --- Structural ---
    for fn, name, desc, types, preserves_lattice in [
        (make_supercell, "make_supercell",
         "Create supercell by repeating unit cell", _CRYSTAL, False),
    ]:
        spec = TransformationSpec(
            name=name, category=_STRUCTURAL, callable=fn,
            description=desc, applicable_types=types,
            output_type=Crystal,
            preserves_composition=True,
            preserves_lattice=preserves_lattice,
            preserves_site_properties=True,
            preserves_pbc=True,
            parameter_schema={"type": "object"},
            version="1.0.0",
        )
        registry.register(spec)

    # Register molecular operations if available
    if fragment_molecule is not None:
        registry.register(TransformationSpec(
            name="fragment_molecule", category=_STRUCTURAL,
            callable=fragment_molecule,
            description="Fragment a molecule into pieces", applicable_types=(Molecule,),
            output_type=Molecule, parameter_schema={"type": "object"}, version="1.0.0",
        ))
    if align_molecules is not None:
        registry.register(TransformationSpec(
            name="align_molecules", category=_STRUCTURAL,
            callable=align_molecules,
            description="Align two molecules by atom mapping", applicable_types=(Molecule,),
            output_type=Molecule, parameter_schema={"type": "object"}, version="1.0.0",
        ))
    if merge_molecules is not None:
        registry.register(TransformationSpec(
            name="merge_molecules", category=_STRUCTURAL,
            callable=merge_molecules,
            description="Merge two molecules into one", applicable_types=(Molecule,),
            output_type=Molecule, parameter_schema={"type": "object"}, version="1.0.0",
        ))
