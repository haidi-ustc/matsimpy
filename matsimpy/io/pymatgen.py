"""pymatgen object conversion helpers for MatSimPy structures."""

from __future__ import annotations


def to_pymatgen(structure):
    """Convert a MatSimPy Crystal or Molecule to a pymatgen object."""
    from ..core import Crystal, Molecule

    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(f"Unsupported structure type: {type(structure)}")

    try:
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError as exc:
        raise ImportError(
            "pymatgen is required for conversion. "
            "Install with: pip install 'MatSimPy[io]'"
        ) from exc

    if isinstance(structure, Crystal):
        return PymatgenStructure(
            structure.lattice.matrix,
            list(structure.species),
            structure.cart_positions.tolist(),
            coords_are_cartesian=True,
        )

    return PymatgenMolecule(list(structure.species), structure.positions.tolist())


def from_pymatgen(pymatgen_obj):
    """Convert a pymatgen Structure or Molecule to a MatSimPy structure."""
    from ..core import Crystal, Molecule, Lattice

    try:
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError as exc:
        raise ImportError(
            "pymatgen is required for conversion. "
            "Install with: pip install 'MatSimPy[io]'"
        ) from exc

    if isinstance(pymatgen_obj, PymatgenStructure):
        species = [str(specie.symbol) for specie in pymatgen_obj.species]
        return Crystal(
            species,
            pymatgen_obj.cart_coords.tolist(),
            Lattice(pymatgen_obj.lattice.matrix),
            coords_are_cartesian=True,
        )

    if isinstance(pymatgen_obj, PymatgenMolecule):
        species = [str(specie.symbol) for specie in pymatgen_obj.species]
        return Molecule(species, pymatgen_obj.cart_coords.tolist())

    raise ValueError(
        f"Unsupported pymatgen object type: {type(pymatgen_obj)}. "
        "Expected Structure or Molecule."
    )


__all__ = ["to_pymatgen", "from_pymatgen"]
