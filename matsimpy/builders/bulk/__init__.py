"""
Bulk crystal structure builders.

This module provides tools for generating bulk crystal structures using
various approaches:

- random: Random crystal generation with symmetry (PyXtal)
- prototype: Template-based generation (FCC, BCC, diamond, etc.)
- symmetry: Space group based generation
- ai: ML-based generation

Examples:
    >>> from matsimpy.builders.bulk import from_prototype, random_crystal
    >>> 
    >>> # Generate FCC copper
    >>> fcc_cu = from_prototype('fcc', 'Cu', 3.61)
    >>> 
    >>> # Generate random crystal
    >>> random_si = random_crystal(3, 227, ['Si'], [8])
"""

from .random import random_crystal
from .prototype import from_prototype, list_prototypes, CRYSTAL_PROTOTYPES

__all__ = [
    'random_crystal',
    'from_prototype',
    'list_prototypes',
    'CRYSTAL_PROTOTYPES',
]

