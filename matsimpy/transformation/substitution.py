"""
Substitution transformations for structures.

Replace atoms in structures with new species.
"""

from typing import List, Union
import numpy as np
from ..core import Crystal, Molecule
from .base import _copy_structure, _validate_structure


def substitute(structure: Union[Crystal, Molecule],
                indices: Union[int, List[int]],
                new_species: Union[str, List[str]],
                inplace: bool = False) -> Union[Crystal, Molecule]:
    """
    Substitute atoms with new species.
    
    This function provides a functional interface to atom substitution.
    For direct manipulation, you can use structure methods, but this
    allows for chaining and functional programming style.
    
    Args:
        structure: Crystal or Molecule to modify
        indices: Atom index or list of indices to substitute
        new_species: New species symbol or list of symbols
        inplace: If True, modify structure in-place (default: False)
    
    Returns:
        Structure with substituted atoms. If inplace=True, returns the same object.
        If inplace=False, returns a new structure.
        
    Raises:
        TypeError: If structure is not Crystal or Molecule
        IndexError: If index is out of range
        ValueError: If number of indices doesn't match number of species
        
    Examples:
        >>> from matsimpy.core import Crystal, Lattice
        >>> from matsimpy.transformation import substitute
        >>> crystal = Crystal(['Si', 'Si'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(10))
        >>> # Substitute one atom
        >>> new_crystal = substitute(crystal, 0, 'Ge')
        >>> # Substitute multiple atoms
        >>> new_crystal = substitute(crystal, [0, 1], ['Ge', 'Ge'])
    """
    _validate_structure(structure)
    
    # Normalize inputs
    if isinstance(indices, int):
        indices = [indices]
        new_species = [new_species]
    elif isinstance(new_species, str):
        new_species = [new_species]
    
    if len(indices) != len(new_species):
        raise ValueError(
            f"Number of indices ({len(indices)}) must match "
            f"number of species ({len(new_species)})"
        )
    
    # Validate indices
    for idx in indices:
        if not (0 <= idx < len(structure)):
            raise IndexError(f"Atom index {idx} is out of range [0, {len(structure)-1}]")
    
    if not inplace:
        structure = _copy_structure(structure)
    
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
    if hasattr(structure, '_sites'):
        structure._sites = structure._initialize_sites()
    
    return structure


def substitute_all(structure: Union[Crystal, Molecule],
                   old_species: str,
                   new_species: str,
                   inplace: bool = False) -> Union[Crystal, Molecule]:
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
        return structure if inplace else _copy_structure(structure)
    
    # Substitute all at once
    return substitute(structure, indices, [new_species] * len(indices), inplace=inplace)


__all__ = ['substitute', 'substitute_all']
