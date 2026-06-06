"""
pymatgen adapter for MatSimPy structures.

Converts between MatSimPy Crystal/Molecule and pymatgen Structure/Molecule.

Requires: pymatgen (pip install pymatgen)
"""

from __future__ import annotations

from typing import Union

import numpy as np

from ..core import Crystal, Molecule, Lattice


def to_pymatgen(structure: Union[Crystal, Molecule]):
    """Convert MatSimPy structure to pymatgen Structure or Molecule.

    Args:
        structure: MatSimPy Crystal or Molecule object

    Returns:
        pymatgen.core.Structure or pymatgen.core.structure.Molecule

    Raises:
        ImportError: If pymatgen is not installed
        ValueError: If structure type is not supported
    """
    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(f"Unsupported structure type: {type(structure)}")

    try:
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError:
        raise ImportError(
            "pymatgen is required for conversion. Install with: pip install pymatgen"
        )

    if isinstance(structure, Crystal):
        species = list(structure.species)
        positions = structure.cart_positions.tolist()
        lattice_matrix = structure.lattice.matrix
        return PymatgenStructure(
            lattice_matrix, species, positions, coords_are_cartesian=True
        )

    elif isinstance(structure, Molecule):
        species = list(structure.species)
        positions = structure.positions.tolist()
        return PymatgenMolecule(species, positions)


def from_pymatgen(pymatgen_obj):
    """Convert pymatgen Structure or Molecule to MatSimPy structure.

    Args:
        pymatgen_obj: pymatgen.core.Structure or pymatgen.core.structure.Molecule

    Returns:
        Crystal or Molecule: MatSimPy structure object

    Raises:
        ImportError: If pymatgen is not installed
        ValueError: If object type is not supported
    """
    try:
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError:
        raise ImportError(
            "pymatgen is required for conversion. Install with: pip install pymatgen"
        )

    if isinstance(pymatgen_obj, PymatgenStructure):
        species = [str(specie.symbol) for specie in pymatgen_obj.species]
        positions = pymatgen_obj.cart_coords.tolist()
        lattice_matrix = pymatgen_obj.lattice.matrix
        lattice = Lattice(lattice_matrix)
        return Crystal(species, positions, lattice, coords_are_cartesian=True)

    elif isinstance(pymatgen_obj, PymatgenMolecule):
        species = [str(specie.symbol) for specie in pymatgen_obj.species]
        positions = pymatgen_obj.cart_coords.tolist()
        return Molecule(species, positions)

    else:
        raise ValueError(
            f"Unsupported pymatgen object type: {type(pymatgen_obj)}. "
            "Expected Structure or Molecule."
        )


__all__ = ["to_pymatgen", "from_pymatgen"]
