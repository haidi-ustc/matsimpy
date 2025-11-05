"""
Bulk crystal structure builders.

This module provides tools for generating bulk crystal structures using
various approaches:

- random: Random crystal generation with symmetry (PyXtal)
- prototype: Template-based generation (FCC, BCC, diamond, etc.)
- symmetry: Space group and crystal system based generation
- ai: ML-based generation

Examples:
    >>> from matsimpy.builders.bulk import from_prototype, random_crystal
    >>> from matsimpy.builders.bulk import from_space_group, from_crystal_system
    >>> 
    >>> # Generate FCC copper
    >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
    >>> 
    >>> # Generate random crystal
    >>> random_si = random_crystal(3, 227, ['Si'], [8])
    >>> 
    >>> # Generate from space group
    >>> from matsimpy.core import Lattice
    >>> lattice = Lattice.cubic(5.0)
    >>> crystal = from_space_group(225, ['Na', 'Cl'], 
    ...                             [[0,0,0], [0.5,0.5,0.5]], 
    ...                             lattice=lattice)
    >>> 
    >>> # Generate from crystal system
    >>> cubic = from_crystal_system('Cubic', ['Si'], [[0,0,0]], 5.43)
"""

from .random import random_crystal
from .prototype import from_prototype, list_prototypes, CRYSTAL_PROTOTYPES
from .symmetry import (
    from_space_group,
    from_crystal_system,
    list_space_groups_by_system
)

__all__ = [
    'random_crystal',
    'from_prototype',
    'list_prototypes',
    'CRYSTAL_PROTOTYPES',
    'from_space_group',
    'from_crystal_system',
    'list_space_groups_by_system',
]

