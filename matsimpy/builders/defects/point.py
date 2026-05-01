"""
Point defect builders.

Create various types of point defects in crystal structures.
"""

from typing import List, Optional, Union, Tuple
import numpy as np
from ...core import Crystal, Lattice
from ...transformation.chemical.substitution import substitute


def create_vacancy(
    structure: Crystal, indices: Union[int, List[int]], inplace: bool = False
) -> Crystal:
    """
    Create vacancy defects by removing atoms.

    Args:
        structure: Crystal structure
        indices: Index or list of indices of atoms to remove
        inplace: If True, modify structure in-place (deprecated, always returns new)

    Returns:
        Crystal with vacancies created

    Examples:
        >>> from matsimpy.builders.defects import create_vacancy
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> # Create FCC structure
        >>> fcc = from_prototype('fcc', 'Cu', 3.61)
        >>>
        >>> # Create single vacancy
        >>> with_vacancy = create_vacancy(fcc, 0)
        >>>
        >>> # Create multiple vacancies
        >>> with_vacancies = create_vacancy(fcc, [0, 1, 2])
    """
    if isinstance(indices, int):
        indices = [indices]

    # Remove duplicates
    remove_set = set(indices)

    # Validate indices
    for idx in remove_set:
        if idx < 0 or idx >= len(structure.species):
            raise IndexError(f"Invalid atom index: {idx}")

    # Build new species and positions skipping removed indices
    new_species = [s for i, s in enumerate(structure.species) if i not in remove_set]
    new_positions = [p.tolist() for i, p in enumerate(structure.frac_positions) if i not in remove_set]

    return Crystal(
        new_species, new_positions,
        lattice=structure.lattice,
        coords_are_cartesian=False,
        pbc=list(structure.pbc),
        site_properties=(list(structure.site_properties) if structure.site_properties else None),
    )


def create_interstitial(
    structure: Crystal,
    species: Union[str, List[str]],
    positions: Union[List[float], List[List[float]]],
    inplace: bool = False,
) -> Crystal:
    """
    Create interstitial defects by adding atoms.

    Args:
        structure: Crystal structure
        species: Species or list of species for interstitial atoms
        positions: Fractional position or list of positions
        inplace: If True, modify structure in-place (deprecated, always returns new)

    Returns:
        Crystal with interstitials added

    Examples:
        >>> from matsimpy.builders.defects import create_interstitial
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> # Create FCC structure
        >>> fcc = from_prototype('fcc', 'Cu', 3.61)
        >>>
        >>> # Add single interstitial
        >>> with_interstitial = create_interstitial(fcc, 'H', [0.5, 0.5, 0.5])
        >>>
        >>> # Add multiple interstitials
        >>> with_interstitials = create_interstitial(
        ...     fcc, ['H', 'H'], [[0.5, 0.5, 0.5], [0.25, 0.25, 0.25]]
        ... )
    """
    # Normalize inputs
    if isinstance(species, str):
        species = [species]
    if len(positions) > 0 and isinstance(positions[0], (int, float)):
        positions = [positions]

    if len(species) != len(positions):
        raise ValueError(
            f"Number of species ({len(species)}) must match "
            f"number of positions ({len(positions)})"
        )

    # Add interstitials (chaining new objects)
    result = structure
    for spec, pos in zip(species, positions):
        # Ensure position is 3D
        pos = np.array(pos, dtype=np.float64)
        if pos.ndim != 1 or len(pos) != 3:
            raise ValueError("Positions must be 3D coordinates")

        # Wrap to [0, 1) for fractional coordinates
        pos = pos % 1.0
        result = result.add_atom(spec, pos.tolist())

    return result


def create_substitution(
    structure: Crystal,
    indices: Union[int, List[int]],
    new_species: Union[str, List[str]],
    inplace: bool = False,
) -> Crystal:
    """
    Create substitution defects by replacing atoms.

    Args:
        structure: Crystal structure
        indices: Index or list of indices of atoms to substitute
        new_species: New species or list of species
        inplace: If True, modify structure in-place (deprecated, always returns new)

    Returns:
        Crystal with substitutions

    Examples:
        >>> from matsimpy.builders.defects import create_substitution
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> # Create FCC structure
        >>> fcc = from_prototype('fcc', 'Cu', 3.61)
        >>>
        >>> # Single substitution
        >>> doped = create_substitution(fcc, 0, 'Ni')
        >>>
        >>> # Multiple substitutions
        >>> multi_doped = create_substitution(fcc, [0, 1, 2], ['Ni', 'Ni', 'Zn'])
    """
    # Normalize inputs (substitute function handles this, but we validate first)
    if isinstance(indices, int):
        indices = [indices]
    if isinstance(new_species, str):
        new_species = [new_species]

    if len(indices) != len(new_species):
        raise ValueError(
            f"Number of indices ({len(indices)}) must match "
            f"number of species ({len(new_species)})"
        )

    # Use transformation function for substitution (always returns new structure)
    return substitute(structure, indices, new_species)


def create_frenkel(
    structure: Crystal,
    index: int,
    interstitial_position: Optional[List[float]] = None,
    inplace: bool = False,
) -> Crystal:
    """
    Create Frenkel defect: atom displaced from lattice site to interstitial position.

    Args:
        structure: Crystal structure
        index: Index of atom to displace
        interstitial_position: Position for interstitial (default: displaced from original)
        inplace: If True, modify structure in-place (deprecated, always returns new)

    Returns:
        Crystal with Frenkel defect

    Examples:
        >>> from matsimpy.builders.defects import create_frenkel
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> # Create structure
        >>> nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
        >>>
        >>> # Create Frenkel defect
        >>> with_frenkel = create_frenkel(nacl, 0, [0.5, 0.5, 0.5])
    """
    if index < 0 or index >= len(structure.species):
        raise IndexError(f"Invalid atom index: {index}")

    # Get original atom info (fractional coordinates)
    species = structure.species[index]
    original_pos = structure.frac_positions[index].copy()

    # Determine interstitial position
    if interstitial_position is None:
        # Default: displace by small amount in random direction
        displacement = np.random.normal(0, 0.1, 3)
        interstitial_position = (original_pos + displacement) % 1.0
    else:
        interstitial_position = np.array(interstitial_position, dtype=np.float64)
        if interstitial_position.ndim != 1 or len(interstitial_position) != 3:
            raise ValueError("Interstitial position must be 3D")
        interstitial_position = interstitial_position % 1.0

    # Remove atom from original position (returns new object)
    result = structure.remove_atom(index)

    # Add atom at interstitial position (returns new object)
    result = result.add_atom(species, interstitial_position.tolist())

    return result


def create_schottky(
    structure: Crystal,
    indices: Optional[List[int]] = None,
    num_vacancies: int = 2,
    inplace: bool = False,
) -> Crystal:
    """
    Create Schottky defect: pair (or set) of vacancies maintaining charge neutrality.

    Args:
        structure: Crystal structure
        indices: Optional list of specific indices to remove (if None, random selection)
        num_vacancies: Number of vacancies to create (default: 2)
        inplace: If True, modify structure in-place (deprecated, always returns new)

    Returns:
        Crystal with Schottky defects

    Examples:
        >>> from matsimpy.builders.defects import create_schottky
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> # Create structure
        >>> nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
        >>>
        >>> # Create Schottky defect (pair of vacancies)
        >>> with_schottky = create_schottky(nacl, num_vacancies=2)
    """
    if indices is None:
        # Random selection
        if num_vacancies > len(structure.species):
            raise ValueError(
                f"Cannot create {num_vacancies} vacancies in structure "
                f"with only {len(structure.species)} atoms"
            )
        indices = np.random.choice(
            len(structure.species), size=num_vacancies, replace=False
        ).tolist()

    if len(indices) != num_vacancies:
        raise ValueError(
            f"Number of indices ({len(indices)}) must match "
            f"num_vacancies ({num_vacancies})"
        )

    # Create vacancies
    return create_vacancy(structure, indices)


def create_antisite(
    structure: Crystal, index1: int, index2: int, inplace: bool = False
) -> Crystal:
    """
    Create antisite defect: swap two different atoms.

    Args:
        structure: Crystal structure
        index1: Index of first atom
        index2: Index of second atom
        inplace: If True, modify structure in-place (deprecated, always returns new)

    Returns:
        Crystal with antisite defect

    Examples:
        >>> from matsimpy.builders.defects import create_antisite
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> # Create structure
        >>> gan = from_prototype('zincblende', ['Ga', 'N'], 4.5)
        >>>
        >>> # Create antisite defect (Ga-N swap)
        >>> with_antisite = create_antisite(gan, 0, 1)
    """
    if index1 < 0 or index1 >= len(structure.species):
        raise IndexError(f"Invalid atom index: {index1}")
    if index2 < 0 or index2 >= len(structure.species):
        raise IndexError(f"Invalid atom index: {index2}")

    if index1 == index2:
        raise ValueError("Cannot swap atom with itself")

    # Antisite defects exchange species on fixed lattice sites.
    # Build new species list with swapped species at the given indices.
    species_list = list(structure.species)
    species_list[index1], species_list[index2] = species_list[index2], species_list[index1]

    return Crystal(
        species_list, structure.frac_positions.tolist(),
        lattice=structure.lattice,
        coords_are_cartesian=False,
        pbc=list(structure.pbc),
        site_properties=(list(structure.site_properties) if structure.site_properties else None),
    )


__all__ = [
    "create_vacancy",
    "create_interstitial",
    "create_substitution",
    "create_frenkel",
    "create_schottky",
    "create_antisite",
]
