"""
Molecule-specific structural operations.

Provides operations specific to molecular structures like fragmentation,
merging, and conformer generation.
"""

from typing import List, Optional, Tuple
import copy
import numpy as np
from ...core import Molecule
from .._helpers import copy_site_properties


def fragment_molecule(
    molecule: Molecule, break_indices: List[Tuple[int, int]]
) -> List[Molecule]:
    """
    Fragment molecule by breaking bonds.

    Args:
        molecule: Molecule to fragment
        break_indices: List of (atom1, atom2) pairs to break

    Returns:
        List of molecular fragments

    Examples:
        >>> from matsimpy.transformation.structural import fragment_molecule
        >>> # Break bond between atoms 1 and 2
        >>> fragments = fragment_molecule(mol, [(1, 2)])
    """
    raise NotImplementedError(
        "Molecule fragmentation is not implemented yet. A bond graph and "
        "site-property remapping policy are required before this can return "
        "chemically meaningful fragments."
    )


def align_molecules(
    molecule1: Molecule, molecule2: Molecule, indices1: List[int], indices2: List[int]
) -> Molecule:
    """
    Align molecule2 to molecule1 using specified atom pairs.

    Args:
        molecule1: Reference molecule
        molecule2: Molecule to align
        indices1: Atom indices in molecule1
        indices2: Atom indices in molecule2

    Returns:
        Aligned molecule2

    Examples:
        >>> from matsimpy.transformation.structural import align_molecules
        >>> # Align using atoms 0,1,2 of each molecule
        >>> aligned = align_molecules(mol1, mol2, [0,1,2], [0,1,2])
    """
    if len(indices1) != len(indices2):
        raise ValueError("Must have same number of indices")

    # Get coordinates
    coords1 = molecule1.positions[indices1]
    coords2 = molecule2.positions[indices2]

    # Center both sets
    center1 = np.mean(coords1, axis=0)
    center2 = np.mean(coords2, axis=0)
    coords1_centered = coords1 - center1
    coords2_centered = coords2 - center2

    # Find rotation matrix using SVD
    H = np.dot(coords2_centered.T, coords1_centered)
    U, S, Vt = np.linalg.svd(H)
    R = np.dot(Vt.T, U.T)

    # Handle reflection
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = np.dot(Vt.T, U.T)

    # Apply transformation to molecule2
    aligned_coords = np.dot(molecule2.positions - center2, R) + center1

    return Molecule(
        list(molecule2.species),
        aligned_coords.tolist(),
        site_properties=copy_site_properties(molecule2),
    )


def generate_conformers(
    molecule: Molecule, n_conformers: int = 10, energy_window: float = 10.0, **kwargs
) -> List[Molecule]:
    """
    Generate molecular conformers.

    Args:
        molecule: Base molecule
        n_conformers: Number of conformers to generate
        energy_window: Energy window in kcal/mol
        **kwargs: Additional parameters

    Returns:
        List of conformer molecules

    Examples:
        >>> from matsimpy.transformation.structural import generate_conformers
        >>> conformers = generate_conformers(mol, n_conformers=10)

    Note:
        Requires RDKit for conformer generation.
    """
    raise NotImplementedError(
        "Conformer generation is not implemented yet. It requires a validated "
        "Molecule-to-RDKit conversion and back-mapping of site metadata."
    )


def merge_molecules(
    molecule1: Molecule,
    molecule2: Molecule,
    bond_atom1: int,
    bond_atom2: int,
    remove_atoms: Optional[List[int]] = None,
) -> Molecule:
    """
    Merge two molecules by forming a bond.

    Args:
        molecule1: First molecule
        molecule2: Second molecule
        bond_atom1: Atom in molecule1 to bond
        bond_atom2: Atom in molecule2 to bond
        remove_atoms: Atoms to remove after merging (e.g., hydrogens)

    Returns:
        Merged molecule

    Examples:
        >>> from matsimpy.transformation.structural import merge_molecules
        >>> # Merge at specific atoms
        >>> merged = merge_molecules(mol1, mol2, 5, 0)
    """
    # Align molecule2 so bond_atom2 is near bond_atom1
    bond_pos1 = molecule1.positions[bond_atom1]
    bond_pos2 = molecule2.positions[bond_atom2]

    # Translate molecule2
    offset = bond_pos1 - bond_pos2
    new_positions2 = molecule2.positions + offset

    # Combine
    all_species = list(molecule1.species) + list(molecule2.species)
    all_positions = np.vstack([molecule1.positions, new_positions2])
    if molecule1.site_properties or molecule2.site_properties:
        props1 = (
            [copy.deepcopy(prop) for prop in molecule1.site_properties]
            if molecule1.site_properties
            else [{} for _ in molecule1.species]
        )
        props2 = (
            [copy.deepcopy(prop) for prop in molecule2.site_properties]
            if molecule2.site_properties
            else [{} for _ in molecule2.species]
        )
        all_site_properties: Optional[list[dict]] = props1 + props2
    else:
        all_site_properties = None

    # Remove specified atoms
    if remove_atoms is not None:
        mask = np.ones(len(all_species), dtype=bool)
        mask[remove_atoms] = False
        all_species = [s for i, s in enumerate(all_species) if mask[i]]
        all_positions = all_positions[mask]
        if all_site_properties is not None:
            all_site_properties = [
                prop for i, prop in enumerate(all_site_properties) if mask[i]
            ]

    return Molecule(
        all_species,
        all_positions.tolist(),
        site_properties=all_site_properties,
    )


__all__ = [
    "fragment_molecule",
    "align_molecules",
    "generate_conformers",
    "merge_molecules",
]
