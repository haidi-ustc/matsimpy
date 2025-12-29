"""
Base utilities for structure transformations.
"""

from typing import Union
from ..core import Crystal, Molecule


def _validate_structure(structure: Union[Crystal, Molecule, None]) -> None:
    """
    Validate that structure is a Crystal or Molecule.

    Args:
        structure: Structure to validate

    Raises:
        TypeError: If structure is not Crystal or Molecule
    """
    if not isinstance(structure, (Crystal, Molecule)):
        raise TypeError(f"Structure must be Crystal or Molecule, got {type(structure)}")


__all__ = ["_validate_structure"]
