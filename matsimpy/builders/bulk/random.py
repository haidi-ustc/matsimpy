"""
Random bulk crystal generation.

Generate random crystal structures with symmetry constraints using PyXtal.
"""

from typing import List, Optional
from ...core import Crystal, Lattice


def random_crystal(
    dim: int,
    group: int,
    species: List[str],
    num_ions: List[int],
    **kwargs
) -> Crystal:
    """
    Generate a random crystal using PyXtal.
    
    Args:
        dim: The dimensionality of the crystal (2 or 3)
        group: The space group number
        species: List of chemical symbols for the atoms in the crystal
        num_ions: List of integers representing the number of ions of each species
        **kwargs: Additional keyword arguments to pass to PyXtal
    
    Returns:
        Crystal: A random crystal object
        
    Raises:
        ImportError: If pyxtal package is not installed
        
    Examples:
        >>> from matsimpy.builders.bulk import random_crystal
        >>> # Generate random SiO2 in space group 1
        >>> crystal = random_crystal(3, 1, ['Si', 'O'], [1, 2])
    """
    try:
        import pyxtal
    except ImportError:
        raise ImportError(
            "The pyxtal package is required to generate random crystals. "
            "Install with: pip install pyxtal"
        )
    
    pyxtal_crystal = pyxtal.crystal.random_crystal(
        dim=dim,
        group=group,
        species=species,
        numIons=num_ions,
        **kwargs
    )
    
    # Extract from pyxtal_crystal
    species_list = pyxtal_crystal.species
    positions = pyxtal_crystal.frac_coords
    lattice = Lattice(pyxtal_crystal.lattice.matrix)
    
    return Crystal(species_list, positions, lattice)


__all__ = ['random_crystal']

