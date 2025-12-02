"""
Translation transformations for structures.

Provides both functional (immutable-style) and in-place translation operations.
"""

from typing import List, Union
import numpy as np
from ...core import Crystal, Molecule
from ..base import _validate_structure


def translate(
    structure: Union[Crystal, Molecule], vector: List[float], inplace: bool = False
) -> Union[Crystal, Molecule]:
    """
    Translate structure by a vector.

    This function provides a functional interface to translation. For molecules,
    you can also use the in-place method: molecule.translate(vector).

    Args:
        structure: Crystal or Molecule to translate
        vector: Translation vector [x, y, z] in Angstroms
        inplace: If True, modify structure in-place and return same object.
                If False, return a new structure (default: False)

    Returns:
        Translated structure. If inplace=True, returns the same object.
        If inplace=False, returns a new structure.

    Raises:
        TypeError: If structure is not Crystal or Molecule
        ValueError: If vector is not 3D

    Examples:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.transformation import translate
        >>> mol = Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        >>> # Functional (returns new)
        >>> mol2 = translate(mol, [1, 1, 1])
        >>> # In-place
        >>> translate(mol, [1, 1, 1], inplace=True)
    """
    _validate_structure(structure)

    vector = np.array(vector, dtype=np.float64)
    if vector.ndim != 1 or len(vector) != 3:
        raise ValueError("Translation vector must be 3D [x, y, z]")

    if inplace:
        # Use in-place method if available (for molecules)
        if isinstance(structure, Molecule):
            structure.translate(vector.tolist())
            return structure
        else:
            # For crystals, modify positions directly
            structure.cart_positions += vector
            structure.frac_positions = structure._convert_to_fractional()
            # Invalidate caches
            structure._neighbor_tree = None
            structure._neighbor_tree_positions = None
            if hasattr(structure, "_sites"):
                structure._sites = structure._initialize_sites()
            return structure
    else:
        # Create copy and translate
        new_structure = structure.copy()
        return translate(new_structure, vector, inplace=True)


def translate_to_origin(
    structure: Union[Crystal, Molecule], inplace: bool = False
) -> Union[Crystal, Molecule]:
    """
    Translate structure so its center of mass is at the origin.

    Args:
        structure: Crystal or Molecule to translate
        inplace: If True, modify structure in-place (default: False)

    Returns:
        Translated structure with COM at origin

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

    return translate(structure, translation_vector, inplace=inplace)


__all__ = ["translate", "translate_to_origin"]
