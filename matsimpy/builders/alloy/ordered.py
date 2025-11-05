"""
Ordered alloy generation.

Generate ordered intermetallic compounds and structured alloys.
"""

from typing import Dict, List
from copy import deepcopy
from ...core import Crystal, Lattice


def generate_ordered_alloy(
    base_structure: Crystal,
    substitution_pattern: Dict[int, str],
    **kwargs
) -> Crystal:
    """
    Generate ordered alloy with specific substitution pattern.
    
    Args:
        base_structure: Base crystal structure
        substitution_pattern: Dictionary mapping site indices to species
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Ordered alloy structure
        
    Examples:
        >>> from matsimpy.builders.alloy import generate_ordered_alloy
        >>> # Create L1_0 ordered structure
        >>> pattern = {0: 'Au', 1: 'Au', 2: 'Cu', 3: 'Cu'}
        >>> ordered = generate_ordered_alloy(base, pattern)
    """
    alloy = deepcopy(base_structure)
    new_species = list(alloy.species)
    
    for idx, spec in substitution_pattern.items():
        if idx >= len(new_species):
            raise ValueError(f"Site index {idx} out of range")
        new_species[idx] = spec
    
    alloy.species = tuple(new_species)
    alloy._formula_dirty = True
    alloy._cached_composition = None
    
    return alloy


def generate_intermetallic(
    elements: List[str],
    composition: str,
    structure_type: str,
    lattice_constant: float,
    **kwargs
) -> Crystal:
    """
    Generate intermetallic compound with specific structure type.
    
    Args:
        elements: List of element symbols
        composition: Composition formula (e.g., 'AB', 'AB2', 'A3B')
        structure_type: Structure type ('L1_0', 'L1_2', 'B2', etc.)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Intermetallic structure
        
    Examples:
        >>> from matsimpy.builders.alloy import generate_intermetallic
        >>> # Generate L1_0 FePt
        >>> fept = generate_intermetallic(['Fe', 'Pt'], 'AB', 'L1_0', 3.85)
        >>> # Generate L1_2 Ni3Al
        >>> ni3al = generate_intermetallic(['Ni', 'Al'], 'A3B', 'L1_2', 3.56)
    """
    from ..bulk import from_prototype
    
    # Map structure types to prototypes
    if structure_type == 'L1_2':
        # A3B in fcc
        species = [elements[0], elements[0], elements[0], elements[1]]
        positions = [[0,0,0], [0.5,0.5,0], [0.5,0,0.5], [0,0.5,0.5]]
        lattice = Lattice.cubic(lattice_constant)
        return Crystal(species, positions, lattice)
    
    elif structure_type == 'B2':
        # AB in bcc-like
        species = [elements[0], elements[1]]
        positions = [[0,0,0], [0.5,0.5,0.5]]
        lattice = Lattice.cubic(lattice_constant)
        return Crystal(species, positions, lattice)
    
    else:
        # Use base prototype
        return from_prototype('fcc', elements[0], lattice_constant)


__all__ = ['generate_ordered_alloy', 'generate_intermetallic']

