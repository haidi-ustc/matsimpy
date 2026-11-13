"""
ASE (Atomic Simulation Environment) format support.

This module provides functions to read and write ASE's native formats.
ASE typically uses JSON-like or extended XYZ formats for structure storage.
We implement support for ASE's extended XYZ format which includes cell information.
"""

from pathlib import Path
from typing import Optional, List
import numpy as np

from ..core import Crystal, Molecule, Lattice


def read_ASE(filename: str) -> Crystal:
    """
    Read an ASE format file (extended XYZ with cell information).

    ASE extended XYZ format includes:
    - Standard XYZ header (atom count, title)
    - Extended properties including cell information
    - Format: "symbol x y z [properties]"
    - Cell information in comment line or properties

    If no cell/lattice information is present, a Molecule is returned.

    Args:
        filename: Path to the ASE/XYZ file

    Returns:
        Crystal or Molecule depending on whether lattice metadata is present.

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"ASE file not found: {filename}")

    with open(filepath, "r") as f:
        raw = [line.rstrip("\n") for line in f.readlines()]
    # Line 2 is the comment/properties line and may be blank; keep it, and
    # drop only trailing blank lines.
    while raw and not raw[-1].strip():
        raw.pop()
    lines = [line.strip() for line in raw]

    if len(lines) < 2:
        raise ValueError("ASE file must have at least 2 lines")

    # Read number of atoms
    try:
        n_atoms = int(lines[0])
    except ValueError:
        raise ValueError(f"Invalid atom count in ASE file: {lines[0]}")

    if n_atoms <= 0:
        raise ValueError(f"Invalid atom count in ASE file: {n_atoms}")

    # Ensure we have enough coordinate lines (header=2 + n_atoms)
    if len(lines) < 2 + n_atoms:
        raise ValueError(
            f"ASE file declares {n_atoms} atoms but only has "
            f"{len(lines) - 2} coordinate line(s)"
        )

    # Read properties line (line 1) - may contain cell information
    properties_line = lines[1] if len(lines) > 1 else ""

    # Try to extract cell information from properties
    lattice = None

    # Look for Lattice or cell keywords in properties
    if "Lattice=" in properties_line:
        import re
        match = re.search(r'Lattice="([^"]+)"', properties_line)
        if match:
            cell_values = [float(x) for x in match.group(1).split()]
            if len(cell_values) == 9:
                lattice_matrix = np.array(cell_values).reshape(3, 3)
                lattice = Lattice(lattice_matrix)

    # Alternative: Look for cell parameters
    if lattice is None and "cell=" in properties_line.lower():
        import re
        match = re.search(r'cell="([^"]+)"', properties_line, re.IGNORECASE)
        if match:
            cell_values = [float(x) for x in match.group(1).split()]
            if len(cell_values) == 9:
                lattice_matrix = np.array(cell_values).reshape(3, 3)
                lattice = Lattice(lattice_matrix)

    pbc = None
    if lattice is not None:
        import re
        match = re.search(r'pbc="([^"]+)"', properties_line, re.IGNORECASE)
        if match:
            flags = match.group(1).split()
            truth = {"t": True, "true": True, "1": True, "f": False, "false": False, "0": False}
            if len(flags) != 3 or any(f.lower() not in truth for f in flags):
                raise ValueError(f"Invalid pbc in ASE file: {match.group(1)!r}")
            pbc = [truth[f.lower()] for f in flags]

    # Read atomic coordinates - strict: every declared atom line must parse
    species = []
    positions = []

    for i in range(2, 2 + n_atoms):
        parts = lines[i].split()
        if len(parts) < 4:
            raise ValueError(
                f"Malformed coordinate line {i+1}: expected at least 4 values "
                f"(symbol x y z), got {len(parts)}"
            )

        try:
            specie = parts[0]
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            species.append(specie)
            positions.append([x, y, z])
        except ValueError as e:
            raise ValueError(
                f"Invalid coordinate format at line {i+1}: {e}"
            )

    if not species:
        raise ValueError("No valid atomic coordinates found in ASE file")

    if len(species) != n_atoms:
        raise ValueError(
            f"Parsed {len(species)} atoms but declared count is {n_atoms}"
        )

    # If we have lattice, return Crystal; otherwise return Molecule
    if lattice is not None:
        return Crystal(species, positions, lattice, coords_are_cartesian=True, pbc=pbc)
    else:
        return Molecule(species, positions)


def write_ASE(structure, filename: str, title: Optional[str] = None) -> None:
    """
    Write a structure to ASE extended XYZ format.

    For Crystal structures, includes lattice information in the properties line.
    For Molecule structures, writes standard XYZ format.

    Args:
        structure: Crystal or Molecule object to write
        filename: Output filename
        title: Optional title/comment (default: structure formula)

    Raises:
        ValueError: If structure is not a valid Crystal or Molecule
    """
    from ..core import Crystal, Molecule

    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError("write_ASE requires a Crystal or Molecule object")

    if title is None:
        title = (
            structure.formula if hasattr(structure, "formula") else "MatSimPy Structure"
        )

    if "\n" in title or "\r" in title:
        raise ValueError("title must be a single line")

    filepath = Path(filename)

    with open(filepath, "w") as f:
        # Write number of atoms
        f.write(f"{len(structure)}\n")

        # Write properties line with lattice info if Crystal
        if isinstance(structure, Crystal):
            lattice = structure.lattice
            # Format: Lattice="a1 b1 c1 a2 b2 c2 a3 b3 c3"
            lattice_str = " ".join(
                [f"{v:.10f}" for row in lattice.matrix for v in row]
            )
            pbc_str = " ".join("T" if p else "F" for p in structure.pbc)
            f.write(f'Lattice="{lattice_str}" Properties=species:S:1:pos:R:3 pbc="{pbc_str}" {title}\n')
            # Use cartesian positions
            positions = structure.cart_positions
        else:
            f.write(f"{title}\n")
            positions = structure.positions

        # Write atomic coordinates
        for specie, pos in zip(structure.species, positions):
            f.write(f"{specie:4s} {pos[0]:15.10f} {pos[1]:15.10f} {pos[2]:15.10f}\n")


def _site_property_arrays(structure) -> dict:
    """Per-atom site properties as numeric arrays (one row per atom)."""
    props = structure.site_properties
    if not props:
        return {}
    keys = sorted({k for p in props for k in p})
    arrays = {}
    for key in keys:
        if any(key not in p for p in props):
            raise ValueError(f"Site property {key!r} is missing on some atoms; cannot convert to ASE")
        try:
            arr = np.array([p[key] for p in props], dtype=np.float64)
        except (TypeError, ValueError):
            raise ValueError(
                f"Site property {key!r} is not numeric and cannot be stored on ASE Atoms"
            ) from None
        arrays[key] = arr
    return arrays


def to_ase(structure):
    """Convert a MatSimPy Crystal or Molecule to an ASE Atoms object.

    Site properties are carried over: ``magmom`` becomes the initial magnetic
    moments, ``charge`` the initial charges, and any other numeric property an
    entry of ``atoms.arrays``.  Non-numeric properties raise ``ValueError``.
    """
    from ..core import Crystal, Molecule

    if not isinstance(structure, (Crystal, Molecule)):
        raise ValueError(f"Unsupported structure type: {type(structure)}")

    try:
        from ase import Atoms
    except ImportError as exc:
        raise ImportError(
            "ASE is required for conversion. Install with: pip install 'MatSimPy[io]'"
        ) from exc

    symbols = list(structure.species)
    arrays = _site_property_arrays(structure)

    if isinstance(structure, Crystal):
        atoms = Atoms(
            symbols=symbols,
            positions=structure.cart_positions.tolist(),
            cell=structure.lattice.matrix,
            pbc=structure.pbc,
        )
    else:
        atoms = Atoms(symbols=symbols, positions=structure.positions.tolist())

    if "magmom" in arrays:
        atoms.set_initial_magnetic_moments(arrays.pop("magmom"))
    if "charge" in arrays:
        atoms.set_initial_charges(arrays.pop("charge"))
    for key, arr in arrays.items():
        if key in atoms.arrays:
            raise ValueError(f"Site property {key!r} clashes with an ASE per-atom array")
        atoms.set_array(key, arr)
    return atoms


_ASE_RESERVED_ARRAYS = {"numbers", "positions", "initial_magmoms", "initial_charges"}


def from_ase(ase_atoms):
    """Convert an ASE Atoms object to a MatSimPy Crystal or Molecule.

    Non-zero initial magnetic moments become the site property ``magmom``,
    non-zero initial charges ``charge``, and other per-atom arrays (except
    momenta, masses and tags-like internals listed by ASE) site properties of
    the same name.
    """
    from ..core import Crystal, Molecule, Lattice

    try:
        from ase import Atoms
    except ImportError as exc:
        raise ImportError(
            "ASE is required for conversion. Install with: pip install 'MatSimPy[io]'"
        ) from exc

    if not isinstance(ase_atoms, Atoms):
        raise ValueError(f"Expected ASE Atoms object, got {type(ase_atoms)}")

    symbols = list(ase_atoms.get_chemical_symbols())
    positions = ase_atoms.get_positions().tolist()
    cell = ase_atoms.get_cell()
    pbc = ase_atoms.get_pbc()

    columns = {}
    if ase_atoms.has("initial_magmoms") and np.any(ase_atoms.get_initial_magnetic_moments()):
        columns["magmom"] = ase_atoms.get_initial_magnetic_moments()
    if ase_atoms.has("initial_charges") and np.any(ase_atoms.get_initial_charges()):
        columns["charge"] = ase_atoms.get_initial_charges()
    for key, arr in ase_atoms.arrays.items():
        if key not in _ASE_RESERVED_ARRAYS and key not in columns:
            columns[key] = arr
    site_properties = None
    if columns:
        site_properties = [
            {key: (arr[i].tolist() if np.ndim(arr[i]) else arr[i].item()) for key, arr in columns.items()}
            for i in range(len(symbols))
        ]

    if cell is not None and cell.any() and any(pbc):
        return Crystal(
            symbols,
            positions,
            Lattice(cell.array),
            coords_are_cartesian=True,
            pbc=list(pbc),
            site_properties=site_properties,
        )

    return Molecule(symbols, positions, site_properties=site_properties)


__all__ = ["read_ASE", "write_ASE", "to_ase", "from_ase"]

# --- Registry registration ---
from .registry import registry, FormatHandler

_ASE_HANDLER = FormatHandler(
    name="ase",
    extensions=(".ase",),
    aliases=("ase", "ASE"),
    description="Atomic Simulation Environment format (via converter)",
    reader=read_ASE,
    writer=write_ASE,
    supports_crystal=True,
    supports_molecule=True,
    strict_by_default=True,
)
registry.register(_ASE_HANDLER)
