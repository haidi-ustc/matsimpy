"""
Alloy generation tools.

Generate alloy structures with different compositions, distributions,
and ordering (random, SQS, ordered, etc.).
"""

from typing import List, Optional, Union, Dict, Tuple
import numpy as np
from ..core import Crystal


def generate_random_alloy(
    base_structure: Crystal,
    substitution_species: List[str],
    site_species: str,
    concentrations: Optional[List[float]] = None,
    seed: Optional[int] = None,
    **kwargs
) -> Crystal:
    """
    Generate random alloy by substituting atoms.
    
    Args:
        base_structure: Base crystal structure
        substitution_species: List of species to substitute
        site_species: Species to replace
        concentrations: Concentrations for each substitution species (must sum to 1)
        seed: Random seed for reproducibility
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Random alloy structure
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.alloy import generate_random_alloy
        >>> base = Crystal(['Al']*4, [[0,0,0], [0.5,0.5,0], [0.5,0,0.5], [0,0.5,0.5]], 
        ...                Lattice.cubic(4.0))
        >>> # Al-Cu alloy with 50% Cu
        >>> alloy = generate_random_alloy(base, ['Cu'], 'Al', [0.5])
        >>> # Al-Cu-Mg alloy with 40% Cu, 10% Mg
        >>> alloy = generate_random_alloy(base, ['Cu', 'Mg'], 'Al', [0.4, 0.1])
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Default equal concentrations if not specified
    if concentrations is None:
        concentrations = [1.0 / len(substitution_species)] * len(substitution_species)
    
    # Validate concentrations
    if len(concentrations) != len(substitution_species):
        raise ValueError("Number of concentrations must match number of substitution species")
    
    if not np.isclose(sum(concentrations), 1.0):
        raise ValueError(f"Concentrations must sum to 1.0, got {sum(concentrations)}")
    
    # Find all sites with the target species
    site_indices = [i for i, spec in enumerate(base_structure.species) if spec == site_species]
    n_sites = len(site_indices)
    
    if n_sites == 0:
        raise ValueError(f"No sites with species '{site_species}' found")
    
    # Calculate number of each substitution
    n_substitutions = [int(np.round(conc * n_sites)) for conc in concentrations]
    
    # Adjust for rounding errors
    total_subs = sum(n_substitutions)
    if total_subs != n_sites:
        # Add/remove from largest concentration
        diff = n_sites - total_subs
        max_idx = np.argmax(concentrations)
        n_substitutions[max_idx] += diff
    
    # Create substitution list
    substitution_list = []
    for spec, n in zip(substitution_species, n_substitutions):
        substitution_list.extend([spec] * n)
    
    # Shuffle
    np.random.shuffle(substitution_list)
    
    # Create new crystal
    alloy = base_structure.copy()
    new_species = list(alloy.species)
    
    for site_idx, new_spec in zip(site_indices, substitution_list):
        new_species[site_idx] = new_spec
    
    alloy.species = tuple(new_species)
    
    return alloy


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
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.alloy import generate_ordered_alloy
        >>> base = Crystal(['A']*8, positions, Lattice.cubic(4.0))
        >>> # Create L1_0 ordered structure
        >>> pattern = {0: 'Au', 1: 'Au', 2: 'Cu', 3: 'Cu', 4: 'Au', 5: 'Au', 6: 'Cu', 7: 'Cu'}
        >>> ordered = generate_ordered_alloy(base, pattern)
    """
    alloy = base_structure.copy()
    new_species = list(alloy.species)
    
    for idx, spec in substitution_pattern.items():
        if idx >= len(new_species):
            raise ValueError(f"Site index {idx} out of range")
        new_species[idx] = spec
    
    alloy.species = tuple(new_species)
    
    return alloy


def generate_sqs_alloy(
    base_structure: Crystal,
    substitution_species: List[str],
    site_species: str,
    concentrations: List[float],
    **kwargs
) -> Crystal:
    """
    Generate Special Quasi-random Structure (SQS) alloy.
    
    SQS structures mimic random alloys while using small supercells.
    This implementation uses a simplified approach.
    
    Args:
        base_structure: Base crystal structure
        substitution_species: List of species to substitute
        site_species: Species to replace
        concentrations: Target concentrations
        **kwargs: Additional parameters (e.g., 'maxiter', 'tolerance')
    
    Returns:
        Crystal: SQS alloy structure
        
    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.generation.alloy import generate_sqs_alloy
        >>> base = Crystal(['Fe']*8, positions, Lattice.cubic(3.0))
        >>> sqs = generate_sqs_alloy(base, ['Ni'], 'Fe', [0.5])
    
    Note:
        For production SQS generation, consider using specialized tools like mcsqs.
        This is a simplified implementation for demonstration.
    """
    # For now, use random alloy as placeholder
    # Full implementation would optimize pair correlations
    return generate_random_alloy(
        base_structure, 
        substitution_species, 
        site_species, 
        concentrations,
        **kwargs
    )


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
        structure_type: Structure type ('L1_0', 'L1_2', 'B2', 'D0_19', etc.)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Intermetallic structure
        
    Examples:
        >>> from matsimpy.generation.alloy import generate_intermetallic
        >>> # Generate L1_0 FePt
        >>> fept = generate_intermetallic(['Fe', 'Pt'], 'AB', 'L1_0', 3.85)
        >>> # Generate L1_2 Ni3Al
        >>> ni3al = generate_intermetallic(['Ni', 'Al'], 'A3B', 'L1_2', 3.56)
    """
    from .template import from_prototype
    
    # Map structure types to prototypes
    structure_map = {
        'L1_0': ('fcc', 'L1_0 tetragonal variant'),
        'L1_2': ('fcc', 'L1_2 cubic'),
        'B2': ('bcc', 'B2 cubic'),
        'B32': ('diamond', 'B32'),
    }
    
    if structure_type not in structure_map:
        raise ValueError(
            f"Unknown structure type '{structure_type}'. "
            f"Available: {list(structure_map.keys())}"
        )
    
    # For now, use simple prototypes
    # Full implementation would have detailed intermetallic structures
    
    if structure_type == 'L1_2':
        # A3B in fcc
        from ..core import Lattice
        species = [elements[0], elements[0], elements[0], elements[1]]
        positions = [[0,0,0], [0.5,0.5,0], [0.5,0,0.5], [0,0.5,0.5]]
        lattice = Lattice.cubic(lattice_constant)
        return Crystal(species, positions, lattice)
    
    else:
        # Use base prototype
        base_proto = structure_map[structure_type][0]
        return from_prototype(base_proto, elements[0], lattice_constant)


def calculate_composition(crystal: Crystal) -> Dict[str, float]:
    """
    Calculate atomic composition of a crystal.
    
    Args:
        crystal: Crystal structure
    
    Returns:
        Dictionary mapping species to atomic fraction
        
    Examples:
        >>> from matsimpy.generation.alloy import calculate_composition
        >>> composition = calculate_composition(alloy)
        >>> print(composition)  # {'Cu': 0.5, 'Al': 0.5}
    """
    from collections import Counter
    
    species_counts = Counter(crystal.species)
    total = sum(species_counts.values())
    
    return {spec: count / total for spec, count in species_counts.items()}


__all__ = [
    'generate_random_alloy',
    'generate_ordered_alloy',
    'generate_sqs_alloy',
    'generate_intermetallic',
    'calculate_composition',
]

