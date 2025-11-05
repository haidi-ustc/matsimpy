"""
Prototype-based bulk crystal generation.

Generate crystals from common structural prototypes (FCC, BCC, diamond, etc.).
"""

from typing import List, Optional, Union, Dict
import numpy as np
from ...core import Crystal, Lattice


# Common crystal structure prototypes
CRYSTAL_PROTOTYPES = {
    'fcc': {
        'species': ['X', 'X', 'X', 'X'],
        'positions': [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
        'lattice_type': 'cubic',
        'description': 'Face-centered cubic'
    },
    'bcc': {
        'species': ['X', 'X'],
        'positions': [[0, 0, 0], [0.5, 0.5, 0.5]],
        'lattice_type': 'cubic',
        'description': 'Body-centered cubic'
    },
    'diamond': {
        'species': ['X', 'X'],
        'positions': [[0, 0, 0], [0.25, 0.25, 0.25]],
        'lattice_type': 'cubic',
        'description': 'Diamond structure'
    },
    'zincblende': {
        'species': ['X', 'Y'],
        'positions': [[0, 0, 0], [0.25, 0.25, 0.25]],
        'lattice_type': 'cubic',
        'description': 'Zincblende (sphalerite) structure'
    },
    'rocksalt': {
        'species': ['X', 'Y'],
        'positions': [[0, 0, 0], [0.5, 0.5, 0.5]],
        'lattice_type': 'cubic',
        'description': 'Rocksalt (NaCl) structure'
    },
    'wurtzite': {
        'species': ['X', 'Y'],
        'positions': [[1/3, 2/3, 0], [1/3, 2/3, 3/8]],
        'lattice_type': 'hexagonal',
        'description': 'Wurtzite structure'
    },
    'perovskite': {
        'species': ['X', 'Y', 'O', 'O', 'O'],
        'positions': [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
        'lattice_type': 'cubic',
        'description': 'Cubic perovskite ABO3'
    },
    'hcp': {
        'species': ['X', 'X'],
        'positions': [[1/3, 2/3, 1/4], [2/3, 1/3, 3/4]],
        'lattice_type': 'hexagonal',
        'description': 'Hexagonal close-packed'
    },
    'sc': {
        'species': ['X'],
        'positions': [[0, 0, 0]],
        'lattice_type': 'cubic',
        'description': 'Simple cubic'
    },
}


def from_prototype(
    prototype: str,
    species: Union[str, List[str]],
    lattice_constant: Union[float, List[float]],
    **kwargs
) -> Crystal:
    """
    Generate crystal from a prototype structure.
    
    Args:
        prototype: Name of prototype ('fcc', 'bcc', 'diamond', 'rocksalt', etc.)
        species: Element symbol(s) to substitute into prototype
        lattice_constant: Lattice constant(s) in Angstroms
        **kwargs: Additional parameters (e.g., c/a ratio for hexagonal)
    
    Returns:
        Crystal: Generated crystal structure
        
    Examples:
        >>> from matsimpy.builders.bulk import from_prototype
        >>> # Generate FCC Cu
        >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
        >>> # Generate rocksalt NaCl
        >>> nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
        >>> # Generate wurtzite GaN with c/a ratio
        >>> gan = from_prototype('wurtzite', ['Ga', 'N'], [3.19, 5.19])
    """
    if prototype not in CRYSTAL_PROTOTYPES:
        raise ValueError(
            f"Unknown prototype '{prototype}'. "
            f"Available: {list(CRYSTAL_PROTOTYPES.keys())}"
        )
    
    template = CRYSTAL_PROTOTYPES[prototype]
    
    # Parse species
    if isinstance(species, str):
        species = [species]
    
    # Substitute species into template
    template_species = template['species']
    # Preserve order when getting unique elements
    unique_template = []
    for s in template_species:
        if s not in unique_template:
            unique_template.append(s)
    
    if len(species) != len(unique_template):
        raise ValueError(
            f"Prototype '{prototype}' requires {len(unique_template)} species, "
            f"but {len(species)} provided"
        )
    
    # Create species mapping
    species_map = {unique_template[i]: species[i] for i in range(len(species))}
    final_species = [species_map[s] for s in template_species]
    
    # Create lattice
    lattice_type = template['lattice_type']
    if lattice_type == 'cubic':
        if isinstance(lattice_constant, (list, tuple)):
            lattice_constant = lattice_constant[0]
        lattice = Lattice.cubic(lattice_constant)
    
    elif lattice_type == 'hexagonal':
        if isinstance(lattice_constant, (list, tuple)):
            a, c = lattice_constant[0], lattice_constant[1]
        else:
            a = lattice_constant
            c = kwargs.get('c', a * 1.633)  # Ideal c/a ratio
        # Create hexagonal lattice manually
        lattice_vectors = [
            [a, 0, 0],
            [-a/2, a*np.sqrt(3)/2, 0],
            [0, 0, c]
        ]
        lattice = Lattice(lattice_vectors)
    
    else:
        raise NotImplementedError(f"Lattice type '{lattice_type}' not yet implemented")
    
    return Crystal(final_species, template['positions'], lattice)


def list_prototypes() -> Dict[str, str]:
    """
    List all available crystal prototypes.
    
    Returns:
        Dictionary mapping prototype names to descriptions
        
    Examples:
        >>> from matsimpy.builders.bulk import list_prototypes
        >>> prototypes = list_prototypes()
        >>> for name, desc in prototypes.items():
        ...     print(f"{name}: {desc}")
    """
    return {name: info['description'] for name, info in CRYSTAL_PROTOTYPES.items()}


__all__ = ['from_prototype', 'list_prototypes', 'CRYSTAL_PROTOTYPES']

