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
        new_positions = structure.frac_positions.copy()
        for idx in indices:
            new_positions[idx] += frac_displacement

        return Crystal(
            list(structure.species), new_positions.tolist(),
            lattice=structure.lattice,
            coords_are_cartesian=False,
            pbc=list(structure.pbc),
            site_properties=(list(structure.site_properties) if structure.site_properties else None),
        )
    else:
        if not cartesian:
            raise ValueError("Molecule positions are always Cartesian")

        # Move atoms
        new_positions = structure.positions.copy()
        for idx in indices:
            new_positions[idx] += displacement

        return Molecule(
            list(structure.species), new_positions.tolist(),
            site_properties=(list(structure.site_properties) if structure.site_properties else None),
        )


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
    # Swap species
    species_list = list(structure.species)
    species_list[index1], species_list[index2] = (
        species_list[index2],
        species_list[index1],
    )

    if isinstance(structure, Crystal):
        # Use fractional coordinates for Crystal construction
        frac_positions = structure.frac_positions.copy()
        frac_positions[[index1, index2]] = frac_positions[[index2, index1]]
        return Crystal(
            species_list, frac_positions.tolist(),
            lattice=structure.lattice,
            coords_are_cartesian=False,
            pbc=list(structure.pbc),
            site_properties=(list(structure.site_properties) if structure.site_properties else None),
        )
    else:
        cart_positions = structure.positions.copy()
        cart_positions[[index1, index2]] = cart_positions[[index2, index1]]
        return Molecule(
            species_list, cart_positions.tolist(),
            site_properties=(list(structure.site_properties) if structure.site_properties else None),
        )


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
    # Determine merged species
    if species is None:
        species = structure.species[index1]

    # Build new species and positions lists
    keep_idx = min(index1, index2)
    remove_idx = max(index1, index2)

    new_species = [s for i, s in enumerate(structure.species) if i != keep_idx and i != remove_idx]

    if isinstance(structure, Crystal):
        src_positions = structure.frac_positions
    else:
        src_positions = structure.positions

    # Determine merged position in the same coordinate frame
    if position is None:
        merged_position = (src_positions[index1] + src_positions[index2]) / 2.0
    else:
        merged_position = np.array(position, dtype=np.float64)

    new_positions = [p for i, p in enumerate(src_positions) if i != keep_idx and i != remove_idx]

    # Add merged atom at the keep position
    new_species.insert(keep_idx, species)
    new_positions.insert(keep_idx, merged_position.tolist())

    if isinstance(structure, Crystal):
        return Crystal(
            new_species, new_positions,
            lattice=structure.lattice,
            coords_are_cartesian=False,
            pbc=list(structure.pbc),
            site_properties=(list(structure.site_properties) if structure.site_properties else None),
        )
    else:
        return Molecule(
            new_species, new_positions,
            site_properties=(list(structure.site_properties) if structure.site_properties else None),
        )


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
    if isinstance(structure, Crystal):
        src_pos = structure.frac_positions
    else:
        src_pos = structure.positions

    # Build new species and positions lists
    new_species = [s for i, s in enumerate(structure.species) if i != index]
    new_positions = [p.tolist() for i, p in enumerate(src_pos) if i != index]

    # Add new atoms at the split position
    for spec, pos in zip(species, positions):
        new_species.append(spec)
        new_positions.append(pos)

    if isinstance(structure, Crystal):
        return Crystal(
            new_species, new_positions,
            lattice=structure.lattice,
            coords_are_cartesian=False,
            pbc=list(structure.pbc),
            site_properties=(list(structure.site_properties) if structure.site_properties else None),
        )
    else:
        return Molecule(
            new_species, new_positions,
            site_properties=(list(structure.site_properties) if structure.site_properties else None),
        )


__all__ = ["move_atoms", "swap_atoms", "merge_atoms", "split_atom"]
