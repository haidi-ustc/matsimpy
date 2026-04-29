"""
Atom manipulation operations (move, swap, merge, split).

Works for both Crystal and Molecule structures.
"""

from typing import List, Optional, Union
import numpy as np
from ...core import Crystal, Molecule


def move_atoms(
    structure: Union[Crystal, Molecule],
    indices: Union[int, List[int]],
    displacement: Union[List[float], np.ndarray],
    cartesian: bool = True,
) -> Union[Crystal, Molecule]:
    """
    Move specific atoms by a displacement vector.

    Always returns a new structure. For in-place modification, use the
    structure's methods directly.

    Args:
        structure: Crystal or Molecule structure
        indices: Atom index or list of indices to move
        displacement: Displacement vector (3D)
        cartesian: If True, displacement is in Cartesian coordinates

    Returns:
        Structure with moved atoms

    Examples:
        >>> from matsimpy import Crystal, Molecule, Lattice
        >>> from matsimpy.transformation.atomic import move_atoms
        >>> # Crystal
        >>> crystal = Crystal(['Si', 'O'], [[0,0,0], [0.5,0.5,0.5]],
        ...                   Lattice.cubic(5))
        >>> moved = move_atoms(crystal, 0, [0.1, 0, 0])
        >>> # Molecule
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> moved = move_atoms(mol, [0, 1], [0.1, 0.1, 0])
    """
    structure = structure.copy()

    # Ensure indices is a list
    if isinstance(indices, int):
        indices = [indices]

    displacement = np.array(displacement, dtype=np.float64)

    if isinstance(structure, Crystal):
        if cartesian:
            # Convert displacement to fractional
            frac_displacement = np.dot(
                displacement, np.linalg.inv(structure.lattice.lattice_vectors)
            )
        else:
            frac_displacement = displacement

        # Move atoms
        new_positions = structure.positions.copy()
        for idx in indices:
            new_positions[idx] += frac_displacement

        structure.positions = new_positions
        structure.frac_positions = new_positions
        structure.cart_positions = structure._convert_to_cartesian()

    elif isinstance(structure, Molecule):
        if not cartesian:
            raise ValueError("Molecule positions are always Cartesian")

        # Move atoms
        new_positions = structure.positions.copy()
        for idx in indices:
            new_positions[idx] += displacement

        structure.positions = new_positions
        structure._sites = structure._initialize_sites()
        if hasattr(structure, "_cached_com"):
            structure._cached_com = None

    # Invalidate caches
    if hasattr(structure, "_neighbor_tree"):
        structure._neighbor_tree = None
    if hasattr(structure, "_neighbor_tree_positions"):
        structure._neighbor_tree_positions = None
    if isinstance(structure, Crystal):
        structure._sites = structure._initialize_sites()

    return structure


def swap_atoms(
    structure: Union[Crystal, Molecule], index1: int, index2: int
) -> Union[Crystal, Molecule]:
    """
    Swap two atoms (exchange positions and species).

    Always returns a new structure. For in-place modification, use the
    structure's methods directly.

    Args:
        structure: Crystal or Molecule structure
        index1: First atom index
        index2: Second atom index

    Returns:
        Structure with swapped atoms

    Examples:
        >>> from matsimpy.transformation.atomic import swap_atoms
        >>> swapped = swap_atoms(structure, 0, 1)
    """
    structure = structure.copy()

    # Swap species
    species_list = list(structure.species)
    species_list[index1], species_list[index2] = (
        species_list[index2],
        species_list[index1],
    )
    structure.species = tuple(species_list)

    # Swap positions
    positions = structure.positions.copy()
    positions[[index1, index2]] = positions[[index2, index1]]
    structure.positions = positions

    if isinstance(structure, Crystal):
        structure.frac_positions = positions
        structure.cart_positions = structure._convert_to_cartesian()
        structure._sites = structure._initialize_sites()
    else:
        structure._sites = structure._initialize_sites()
        if hasattr(structure, "_cached_com"):
            structure._cached_com = None

    # Invalidate caches
    if hasattr(structure, "_neighbor_tree"):
        structure._neighbor_tree = None
    if hasattr(structure, "_neighbor_tree_positions"):
        structure._neighbor_tree_positions = None
    structure._formula_dirty = True
    structure._cached_composition = None

    return structure


def merge_atoms(
    structure: Union[Crystal, Molecule],
    index1: int,
    index2: int,
    species: Optional[str] = None,
    position: Optional[List[float]] = None,
) -> Union[Crystal, Molecule]:
    """
    Merge two atoms into one.

    Always returns a new structure. For in-place modification, use the
    structure's methods directly.

    Args:
        structure: Crystal or Molecule structure
        index1: First atom index
        index2: Second atom index
        species: Species for merged atom (default: species of first atom)
        position: Position for merged atom (default: midpoint)

    Returns:
        Structure with merged atoms

    Examples:
        >>> from matsimpy.transformation.atomic import merge_atoms
        >>> # Merge atoms at their midpoint
        >>> merged = merge_atoms(structure, 0, 1)
        >>> # Merge with specific species and position
        >>> merged = merge_atoms(structure, 0, 1, species='C',
        ...                      position=[0.25, 0.25, 0.25])
    """
    structure = structure.copy()

    # Determine merged species
    if species is None:
        species = structure.species[index1]

    # Determine merged position
    if position is None:
        # Midpoint
        position = (structure.positions[index1] + structure.positions[index2]) / 2.0
    else:
        position = np.array(position, dtype=np.float64)

    # Remove both atoms and add merged one
    # Keep the lower index
    keep_idx = min(index1, index2)
    remove_idx = max(index1, index2)

    # Remove second atom
    structure.remove_atom(remove_idx)
    # Remove first atom
    structure.remove_atom(keep_idx)
    # Add merged atom at kept position
    structure.add_atom(species, position)

    return structure


def split_atom(
    structure: Union[Crystal, Molecule],
    index: int,
    species: List[str],
    positions: List[List[float]],
) -> Union[Crystal, Molecule]:
    """
    Split one atom into multiple atoms.

    Always returns a new structure. For in-place modification, use the
    structure's methods directly.

    Args:
        structure: Crystal or Molecule structure
        index: Atom index to split
        species: List of species for new atoms
        positions: List of positions for new atoms

    Returns:
        Structure with split atom

    Examples:
        >>> from matsimpy.transformation.atomic import split_atom
        >>> # Split one atom into two
        >>> split = split_atom(structure, 0, ['H', 'H'],
        ...                    [[0, 0, 0], [0.1, 0, 0]])
    """
    structure = structure.copy()

    # Remove original atom
    structure.remove_atom(index)

    # Add new atoms
    for spec, pos in zip(species, positions):
        structure.add_atom(spec, pos)

    return structure


__all__ = ["move_atoms", "swap_atoms", "merge_atoms", "split_atom"]
