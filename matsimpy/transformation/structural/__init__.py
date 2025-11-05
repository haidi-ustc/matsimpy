"""
Structural operations (supercell, molecular operations).

- supercell: Crystal supercell generation
- molecular: Molecule-specific operations
"""

from .supercell import make_supercell
from .molecular import (
    fragment_molecule,
    align_molecules,
    generate_conformers,
    merge_molecules,
)

__all__ = [
    # Supercell
    'make_supercell',
    
    # Molecular
    'fragment_molecule',
    'align_molecules',
    'generate_conformers',
    'merge_molecules',
]

