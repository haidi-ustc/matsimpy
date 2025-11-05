"""
Structure transformation tools.

This module provides functional transformations for Crystal and Molecule objects.
Transformations can be applied in-place or return new objects (functional style).

Design Philosophy:
- Class methods (add_atom, remove_atom, translate, rotate) are for direct manipulation
- Transformation module provides functional interface for composability and chaining
- Both approaches are available - choose based on use case

Usage:
    # Functional (returns new object)
    from matsimpy.transformation import translate, rotate
    new_molecule = translate(molecule, [1, 1, 1])
    rotated = rotate(new_molecule, 90, [0, 0, 1])
    
    # In-place (modifies existing)
    translate(molecule, [1, 1, 1], inplace=True)
    
    # Or use class methods directly
    molecule.translate([1, 1, 1])
"""

from .translation import translate, translate_to_origin
from .rotation import rotate, rotate_around_axis
from .substitution import substitute, substitute_all
from .supercell import make_supercell
from .composite import chain, apply_transformations

__all__ = [
    # Translation
    'translate',
    'translate_to_origin',
    # Rotation
    'rotate',
    'rotate_around_axis',
    # Substitution
    'substitute',
    'substitute_all',
    # Supercell
    'make_supercell',
    # Composite
    'chain',
    'apply_transformations',
]
