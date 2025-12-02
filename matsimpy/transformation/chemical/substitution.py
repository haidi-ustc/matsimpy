"""
Substitution transformations for structures.

Replace atoms in structures with new species.
Can use selection utilities from matsimpy.utils.selection for flexible atom selection.
"""

from typing import List, Union, Dict
import numpy as np
from ...core import Crystal, Molecule
from ..base import _validate_structure


def substitute(
    structure: Union[Crystal, Molecule],
    indices: Union[int, List[int], "AtomSelection"],
    new_species: Union[str, List[str], Dict[str, str]],
    inplace: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Substitute atoms with new species.

    This function provides a functional interface to atom substitution.
    For direct manipulation, you can use structure methods, but this
    allows for chaining and functional programming style.

    Args:
        structure: Crystal or Molecule to modify
        indices: Atom index, list of indices, or AtomSelection object to substitute
        new_species: New species symbol, list of symbols, or dict mapping old->new species.
                   If dict, maps old species to new species (e.g., {'Si': 'Ge', 'O': 'S'})
        inplace: If True, modify structure in-place (default: False)

    Returns:
        Structure with substituted atoms. If inplace=True, returns the same object.
        If inplace=False, returns a new structure.

    Raises:
        TypeError: If structure is not Crystal or Molecule
        IndexError: If index is out of range
        ValueError: If number of indices doesn't match number of species
        KeyError: If dict mapping doesn't contain a species

    Examples:
        >>> from matsimpy.core import Crystal, Lattice
        >>> from matsimpy.transformation import substitute
        >>> from matsimpy.utils.selection import AtomSelection
        >>> crystal = Crystal(['Si', 'Si'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(10))
        >>> # Substitute one atom
        >>> new_crystal = substitute(crystal, 0, 'Ge')
        >>> # Substitute multiple atoms
        >>> new_crystal = substitute(crystal, [0, 1], ['Ge', 'Ge'])
        >>> # Using AtomSelection
        >>> sel = AtomSelection(crystal).by_species('Si')
        >>> new_crystal = substitute(crystal, sel, 'Ge')
        >>> # Using dict mapping
        >>> new_crystal = substitute(crystal, [0, 1, 2], {'Si': 'Ge', 'O': 'S'})
    """
    _validate_structure(structure)

    # Handle AtomSelection object
    from ...utils.selection import AtomSelection

    if isinstance(indices, AtomSelection):
        if indices.structure is not structure:
            raise ValueError(
                "AtomSelection must be created from the structure being modified"
            )
        indices = indices.indices

    # Handle dict-based species mapping
    if isinstance(new_species, dict):
        # Convert dict to list based on current species at selected indices
        if isinstance(indices, int):
            indices = [indices]
        new_species_list = []
        for idx in indices:
            old_spec = structure.species[idx]
            if old_spec not in new_species:
                raise KeyError(
                    f"Species '{old_spec}' at index {idx} not found in substitution mapping"
                )
            new_species_list.append(new_species[old_spec])
        new_species = new_species_list

    # Normalize inputs
    if isinstance(indices, int):
        indices = [indices]
        if isinstance(new_species, str):
            new_species = [new_species]
        elif isinstance(new_species, list):
            new_species = [new_species[0]]  # Take first if list
    elif isinstance(new_species, str):
        # Multiple indices, single species
        new_species = [new_species] * len(indices)
    elif isinstance(new_species, list):
        # Both are lists
        pass
    else:
        raise TypeError(
            f"new_species must be str, List[str], or Dict[str, str], got {type(new_species)}"
        )

    if len(indices) != len(new_species):
        raise ValueError(
            f"Number of indices ({len(indices)}) must match "
            f"number of species ({len(new_species)})"
        )

    # Validate indices
    for idx in indices:
        if not (0 <= idx < len(structure)):
            raise IndexError(
                f"Atom index {idx} is out of range [0, {len(structure)-1}]"
            )

    if not inplace:
        structure = structure.copy()

    # Perform substitutions
    species_list = list(structure.species)
    for idx, species in zip(indices, new_species):
        species_list[idx] = species

    # Update species tuple
    structure.species = tuple(species_list)

    # Invalidate caches
    structure._formula_dirty = True
    structure._cached_composition = None

    # Update sites if they exist
    if hasattr(structure, "_sites"):
        structure._sites = structure._initialize_sites()

    return structure


def substitute_all(
    structure: Union[Crystal, Molecule],
    old_species: str,
    new_species: str,
    inplace: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Substitute all atoms of a given species with a new species.

    Args:
        structure: Crystal or Molecule to modify
        old_species: Species to replace
        new_species: Replacement species
        inplace: If True, modify structure in-place (default: False)

    Returns:
        Structure with all matching atoms substituted

    Examples:
        >>> from matsimpy.transformation import substitute_all
        >>> # Replace all Si with Ge
        >>> new_crystal = substitute_all(crystal, 'Si', 'Ge')
    """
    _validate_structure(structure)

    # Find all indices of old_species
    indices = [i for i, spec in enumerate(structure.species) if spec == old_species]

    if not indices:
        # No substitution needed
        return structure if inplace else structure.copy()

    # Substitute all at once
    return substitute(structure, indices, [new_species] * len(indices), inplace=inplace)


__all__ = ["substitute", "substitute_all"]
