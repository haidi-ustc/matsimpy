"""
Translation transformations for structures.

Provides both functional (immutable-style) and in-place translation operations.
"""

from typing import List, Union
import numpy as np
from ...core import Crystal, Molecule
from ..base import _validate_structure


def translate(
    structure: Union[Crystal, Molecule], vector: List[float]
) -> Union[Crystal, Molecule]:
    """
    Translate structure by a vector.

    Always returns a new structure. For in-place modification, use the
    structure's translate method directly.

    Args:
        structure: Crystal or Molecule to translate
        vector: Translation vector [x, y, z] in Angstroms

    Returns:
        New translated structure.

    Raises:
        TypeError: If structure is not Crystal or Molecule
        ValueError: If vector is not 3D

    Examples:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.transformation import translate
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> # Always returns new structure
        >>> mol2 = translate(mol, [1, 1, 1])
    """
    _validate_structure(structure)

    vector = np.array(vector, dtype=np.float64)
    if vector.ndim != 1 or len(vector) != 3:
        raise ValueError("Translation vector must be 3D [x, y, z]")

    # Always create a new structure
    new_structure = structure.copy()
    
    # Apply translation
    if isinstance(new_structure, Molecule):
        new_structure.positions += vector
        if hasattr(new_structure, "_cached_com"):
            new_structure._cached_com = None
        new_structure._sites = new_structure._initialize_sites()
    else:
        # For crystals, modify positions directly
        new_structure.cart_positions += vector
        new_structure.frac_positions = new_structure._convert_to_fractional()
        # Keep canonical fractional positions in sync. Many downstream APIs
        # (sites, serialization, equality, further transformations) read
        # ``positions`` rather than ``frac_positions``.
        new_structure.positions = new_structure.frac_positions
        # Invalidate caches
        new_structure._neighbor_tree = None
        new_structure._neighbor_tree_positions = None
        if hasattr(new_structure, "_sites"):
            new_structure._sites = new_structure._initialize_sites()
    
    return new_structure


def translate_to_origin(
    structure: Union[Crystal, Molecule]
) -> Union[Crystal, Molecule]:
    """
    Translate structure so its center of mass is at the origin.

    Always returns a new structure.

    Args:
        structure: Crystal or Molecule to translate

    Returns:
        New translated structure with COM at origin

    Examples:
        >>> from matsimpy.transformation import translate_to_origin
        >>> mol = translate_to_origin(molecule)
    """
    _validate_structure(structure)

    if isinstance(structure, Molecule):
        com = structure.get_center_of_mass()
        translation_vector = [-coord for coord in com]
    else:
        # For crystals, use center of mass of positions
        com = np.mean(structure.cart_positions, axis=0)
        translation_vector = (-com).tolist()

    return translate(structure, translation_vector)


__all__ = ["translate", "translate_to_origin"]
