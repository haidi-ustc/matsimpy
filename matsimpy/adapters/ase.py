"""
ASE adapter for MatSimPy structures.

Converts between MatSimPy Crystal/Molecule and ASE Atoms.

Requires: ase (pip install ase)
"""

from __future__ import annotations

from typing import Union

import numpy as np

from ..core import Crystal, Molecule, Lattice


def to_ase(structure: Union[Crystal, Molecule]):
    """Convert MatSimPy structure to ASE Atoms object.

    Args:
        structure: MatSimPy Crystal or Molecule object

    Returns:
        ase.Atoms: ASE Atoms object

    Raises:
        ImportError: If ASE is not installed
        ValueError: If structure type is not supported
    """
    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(f"Unsupported structure type: {type(structure)}")

    try:
        from ase import Atoms
    except ImportError:
        raise ImportError(
            "ASE is required for conversion. Install with: pip install ase"
        )

    symbols = list(structure.species)

    if isinstance(structure, Crystal):
        positions = structure.cart_positions.tolist()
        cell = structure.lattice.matrix
        pbc = structure.pbc
        return Atoms(symbols=symbols, positions=positions, cell=cell, pbc=pbc)
    else:
        positions = structure.positions.tolist()
        return Atoms(symbols=symbols, positions=positions)


def from_ase(ase_atoms):
    """Convert ASE Atoms object to MatSimPy structure.

    Args:
        ase_atoms: ase.Atoms object

    Returns:
        Crystal or Molecule: MatSimPy structure object

    Raises:
        ImportError: If ASE is not installed
        ValueError: If object type is not supported
    """
    try:
        from ase import Atoms
    except ImportError:
        raise ImportError(
            "ASE is required for conversion. Install with: pip install ase"
        )

    if not isinstance(ase_atoms, Atoms):
        raise ValueError(f"Expected ASE Atoms object, got {type(ase_atoms)}")

    symbols = [symbol for symbol in ase_atoms.get_chemical_symbols()]
    positions = ase_atoms.get_positions().tolist()

    cell = ase_atoms.get_cell()
    pbc = ase_atoms.get_pbc()

    if cell is not None and cell.any() and any(pbc):
        lattice_matrix = cell.array
        lattice = Lattice(lattice_matrix)
        return Crystal(
            symbols, positions, lattice, coords_are_cartesian=True, pbc=list(pbc)
        )
    else:
        return Molecule(symbols, positions)


__all__ = ["to_ase", "from_ase"]
