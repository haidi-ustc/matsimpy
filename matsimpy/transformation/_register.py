"""Auto-register all built-in transformation functions with the registry."""

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
_MOLECULE = (Molecule,)

_V3 = {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}
_M3 = {"type": "array", "items": _V3, "minItems": 3, "maxItems": 3}


def register_all():
    """Register all built-in transformations with the global registry."""

    # --- Geometric ---
    registry.register(TransformationSpec(
        name="translate", category=_GEOMETRIC, callable=translate,
        description="Translate structure by a 3D vector",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {"vector": _V3},
            "required": ["vector"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="translate_to_origin", category=_GEOMETRIC,
        callable=translate_to_origin,
        description="Translate center of mass to origin",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={"type": "object", "properties": {}},
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="rotate", category=_GEOMETRIC, callable=rotate,
        description="Rotate structure around an axis by angle (degrees)",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "angle": {"type": "number", "description": "Rotation angle in degrees"},
                "axis": _V3,
            },
            "required": ["angle", "axis"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="rotate_around_axis", category=_GEOMETRIC,
        callable=rotate_around_axis,
        description="Rotate structure around an arbitrary axis",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "angle": {"type": "number"},
                "axis": _V3,
            },
            "required": ["angle", "axis"],
        },
        version="1.0.0",
    ))

    # --- Lattice ---
    registry.register(TransformationSpec(
        name="apply_strain", category=_LATTICE, callable=apply_strain,
        description="Apply strain tensor to crystal lattice",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {"strain": _M3},
            "required": ["strain"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="apply_deformation", category=_LATTICE, callable=apply_deformation,
        description="Apply deformation gradient to crystal",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {"deformation": _M3},
            "required": ["deformation"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="perturb_lattice", category=_LATTICE, callable=perturb_lattice,
        description="Apply random perturbations to lattice vectors",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {"magnitude": {"type": "number", "default": 0.01}},
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="scale_lattice", category=_LATTICE, callable=scale_lattice,
        description="Scale lattice by isotropic or anisotropic factor",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "scale": {
                    "oneOf": [_V3, {"type": "number"}],
                },
            },
            "required": ["scale"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="set_volume", category=_LATTICE, callable=set_volume,
        description="Scale lattice to achieve target volume",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {"volume": {"type": "number"}},
            "required": ["volume"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="optimize_lattice", category=_LATTICE, callable=optimize_lattice,
        description="Optimize lattice angles while preserving volume",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={"type": "object", "properties": {}},
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="rotate_lattice", category=_LATTICE, callable=rotate_lattice,
        description="Rotate lattice by 3D rotation matrix",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {"matrix": _M3},
            "required": ["matrix"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="transform_lattice", category=_LATTICE, callable=transform_lattice,
        description="Apply arbitrary transformation matrix to lattice",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {"matrix": _M3},
            "required": ["matrix"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="standardize_cell", category=_LATTICE, callable=standardize_cell,
        description="Standardize unit cell to convention",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={"type": "object", "properties": {}},
        version="1.0.0",
    ))

    # --- Atomic ---
    registry.register(TransformationSpec(
        name="move_atoms", category=_ATOMIC, callable=move_atoms,
        description="Move selected atoms by a displacement vector",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "indices": {
                    "oneOf": [
                        {"type": "integer"},
                        {"type": "array", "items": {"type": "integer"}},
                    ],
                },
                "displacement": _V3,
            },
            "required": ["indices", "displacement"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="swap_atoms", category=_ATOMIC, callable=swap_atoms,
        description="Swap positions of two atoms",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "i": {"type": "integer"},
                "j": {"type": "integer"},
            },
            "required": ["i", "j"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="merge_atoms", category=_ATOMIC, callable=merge_atoms,
        description="Merge two atoms into one at their midpoint",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "i": {"type": "integer"},
                "j": {"type": "integer"},
            },
            "required": ["i", "j"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="split_atom", category=_ATOMIC, callable=split_atom,
        description="Split one atom into two at displaced positions",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "index": {"type": "integer"},
                "displacement": _V3,
            },
            "required": ["index", "displacement"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="sort_atoms", category=_ATOMIC, callable=sort_atoms,
        description="Sort atoms by specified criterion",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "default": "species"},
            },
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="center_structure", category=_ATOMIC, callable=center_structure,
        description="Center structure at origin",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={"type": "object", "properties": {}},
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="perturb_positions", category=_ATOMIC, callable=perturb_positions,
        description="Apply random perturbations to atomic positions",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=True, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {"magnitude": {"type": "number", "default": 0.01}},
        },
        version="1.0.0",
    ))

    # --- Chemical ---
    registry.register(TransformationSpec(
        name="substitute", category=_CHEMICAL, callable=substitute,
        description="Substitute specific atom(s) with new species",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=False, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "indices": {
                    "oneOf": [
                        {"type": "integer"},
                        {"type": "array", "items": {"type": "integer"}},
                    ],
                },
                "new_species": {"type": "string"},
            },
            "required": ["indices", "new_species"],
        },
        version="1.0.0",
    ))
    registry.register(TransformationSpec(
        name="substitute_all", category=_CHEMICAL, callable=substitute_all,
        description="Substitute all atoms of one species with another",
        applicable_types=_BOTH, output_type=Crystal,
        preserves_composition=False, preserves_lattice=True,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "old_species": {"type": "string"},
                "new_species": {"type": "string"},
            },
            "required": ["old_species", "new_species"],
        },
        version="1.0.0",
    ))

    # --- Structural ---
    registry.register(TransformationSpec(
        name="make_supercell", category=_STRUCTURAL, callable=make_supercell,
        description="Create supercell by repeating unit cell",
        applicable_types=_CRYSTAL, output_type=Crystal,
        preserves_composition=True, preserves_lattice=False,
        preserves_site_properties=True, preserves_pbc=True,
        parameter_schema={
            "type": "object",
            "properties": {
                "scaling_matrix": {
                    "oneOf": [
                        {"type": "integer"},
                        _V3,
                        _M3,
                    ],
                },
            },
            "required": ["scaling_matrix"],
        },
        version="1.0.0",
    ))

    # --- Molecular ---
    if fragment_molecule is not None:
        registry.register(TransformationSpec(
            name="fragment_molecule", category=_STRUCTURAL,
            callable=fragment_molecule,
            description="Fragment a molecule into pieces",
            applicable_types=_MOLECULE, output_type=Molecule,
            parameter_schema={
                "type": "object",
                "properties": {
                    "indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                },
                "required": ["indices"],
            },
            version="1.0.0",
        ))
    if align_molecules is not None:
        registry.register(TransformationSpec(
            name="align_molecules", category=_STRUCTURAL,
            callable=align_molecules,
            description="Align two molecules by atom mapping",
            applicable_types=_MOLECULE, output_type=Molecule,
            parameter_schema={
                "type": "object",
                "properties": {
                    "ref_indices": {"type": "array", "items": {"type": "integer"}},
                    "target_indices": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["ref_indices", "target_indices"],
            },
            version="1.0.0",
        ))
    if merge_molecules is not None:
        registry.register(TransformationSpec(
            name="merge_molecules", category=_STRUCTURAL,
            callable=merge_molecules,
            description="Merge two molecules into one",
            applicable_types=_MOLECULE, output_type=Molecule,
            parameter_schema={
                "type": "object",
                "properties": {"other": {}},
                "required": ["other"],
            },
            version="1.0.0",
        ))
