"""
Random bulk crystal generation.

Generate random crystal structures with symmetry constraints using PyXtal.
"""

from matsimpy.utils.tooling import tool
from typing import List
from ...core import Crystal


@tool
def random_crystal(dim: int, group: int, species: List[str], num_ions: List[int], **kwargs) -> Crystal:
    """
    Generate a random crystal using PyXtal.

    Args:
        dim: The dimensionality of the crystal (2 or 3)
        group: The space group number (layer group for dim=2)
        species: List of chemical symbols for the atoms in the crystal
        num_ions: Number of atoms of each species in the conventional cell
        **kwargs: Passed to ``pyxtal.pyxtal.from_random`` (e.g. factor, thickness)

    Returns:
        Crystal: A random crystal object

    Raises:
        ImportError: If pyxtal package is not installed
        ValueError: If PyXtal cannot place the atoms with the requested symmetry

    Examples:
        >>> from matsimpy.builders.bulk import random_crystal
        >>> # Generate random SiO2 in space group 1
        >>> crystal = random_crystal(3, 1, ['Si', 'O'], [1, 2])
    """
    try:
        from pyxtal import pyxtal
    except ImportError:
        raise ImportError(
            "The pyxtal package is required to generate random crystals. "
            "Install with: pip install pyxtal"
        )
    if len(species) != len(num_ions):
        raise ValueError(f"Got {len(species)} species but {len(num_ions)} num_ions")

    generator = pyxtal()
    generator.from_random(dim, group, species, num_ions, **kwargs)
    if not getattr(generator, "valid", False):
        raise ValueError(
            f"PyXtal could not generate a valid structure in group {group} "
            f"with {dict(zip(species, num_ions))}; try other atom counts or a larger factor"
        )
    from ...io import from_pymatgen

    return from_pymatgen(generator.to_pymatgen())


__all__ = ["random_crystal"]
