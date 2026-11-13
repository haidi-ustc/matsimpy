"""pymatgen object conversion helpers for MatSimPy structures.

Site properties, periodic boundary conditions and oxidation states are carried
over in both directions.  Oxidation states of pymatgen ``Species`` become the
MatSimPy site property ``oxidation_state``; a MatSimPy structure whose every
site has ``oxidation_state`` gets decorated pymatgen species again.
"""

from __future__ import annotations

_OXI_KEY = "oxidation_state"


def _site_properties_as_columns(structure) -> dict:
    props = structure.site_properties
    if not props:
        return {}
    keys = sorted({k for p in props for k in p})
    missing = [k for k in keys if any(k not in p for p in props)]
    if missing:
        raise ValueError(
            f"Site properties {missing} are missing on some atoms; pymatgen needs every "
            "site property on every site"
        )
    return {k: [p[k] for p in props] for k in keys}


def to_pymatgen(structure):
    """Convert a MatSimPy Crystal or Molecule to a pymatgen object."""
    from ..core import Crystal, Molecule

    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(f"Unsupported structure type: {type(structure)}")

    try:
        from pymatgen.core import Lattice as PymatgenLattice
        from pymatgen.core import Structure as PymatgenStructure
        from pymatgen.core import Molecule as PymatgenMolecule
    except ImportError as exc:
        raise ImportError(
            "pymatgen is required for conversion. "
            "Install with: pip install 'MatSimPy[io]'"
        ) from exc

    columns = _site_properties_as_columns(structure)
    oxidation_states = columns.pop(_OXI_KEY, None)

    if isinstance(structure, Crystal):
        result = PymatgenStructure(
            PymatgenLattice(structure.lattice.matrix, pbc=tuple(structure.pbc)),
            list(structure.species),
            structure.cart_positions.tolist(),
            coords_are_cartesian=True,
            site_properties=columns or None,
        )
    else:
        result = PymatgenMolecule(
            list(structure.species),
            structure.positions.tolist(),
            site_properties=columns or None,
        )
    if oxidation_states is not None:
        result.add_oxidation_state_by_site(list(oxidation_states))
    return result


def _species_and_oxidation(pymatgen_obj):
    if not pymatgen_obj.is_ordered:
        raise ValueError(
            "Disordered pymatgen structures (partial occupancies) cannot be converted; "
            "MatSimPy structures have one species per site"
        )
    species = []
    oxi = []
    for specie in pymatgen_obj.species:
        species.append(str(specie.symbol))
        oxi.append(getattr(specie, "oxi_state", None))
    has_oxi = any(o is not None for o in oxi)
    return species, (oxi if has_oxi else None)


def _site_properties_from(pymatgen_obj, oxidation_states):
    n = len(pymatgen_obj)
    rows = [dict() for _ in range(n)]
    for key, values in pymatgen_obj.site_properties.items():
        if key == _OXI_KEY:
            raise ValueError(f"pymatgen site property {_OXI_KEY!r} clashes with oxidation states")
        for row, value in zip(rows, values):
            row[key] = value.tolist() if hasattr(value, "tolist") else value
    if oxidation_states is not None:
        for row, value in zip(rows, oxidation_states):
            row[_OXI_KEY] = 0 if value is None else value
    return rows if any(rows) else None


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
        species, oxi = _species_and_oxidation(pymatgen_obj)
        return Crystal(
            species,
            pymatgen_obj.cart_coords.tolist(),
            Lattice(pymatgen_obj.lattice.matrix),
            coords_are_cartesian=True,
            pbc=[bool(p) for p in pymatgen_obj.lattice.pbc],
            site_properties=_site_properties_from(pymatgen_obj, oxi),
        )

    if isinstance(pymatgen_obj, PymatgenMolecule):
        species, oxi = _species_and_oxidation(pymatgen_obj)
        return Molecule(
            species,
            pymatgen_obj.cart_coords.tolist(),
            site_properties=_site_properties_from(pymatgen_obj, oxi),
        )

    raise ValueError(
        f"Unsupported pymatgen object type: {type(pymatgen_obj)}. "
        "Expected Structure or Molecule."
    )


__all__ = ["to_pymatgen", "from_pymatgen"]
