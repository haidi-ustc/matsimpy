"""
MOL (MDL Molfile) format support.

This module provides functions to read and write MOL format files, which are
commonly used in cheminformatics and molecular modeling. MOL format includes
connectivity information as well as atomic coordinates.
"""

from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np

from ..core import Molecule


def read_MOL(filename: str) -> Molecule:
    """
    Read a MOL format file.

    MOL format structure:
    - Header: 3 lines (title, program info, comments)
    - Counts line: "nnn nnn ..." (atom count, bond count, etc.)
    - Atom block: atom lines with coordinates
    - Bond block: bond connectivity information
    - Properties block (optional)

    We primarily extract atomic coordinates and species.

    Args:
        filename: Path to the MOL file

    Returns:
        Molecule: Molecule object from the file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"MOL file not found: {filename}")

    with open(filepath, "r") as f:
        lines = [line.rstrip() for line in f.readlines()]

    if len(lines) < 5:
        raise ValueError("MOL file must have at least 5 lines (header + counts)")

    # Read header (lines 0-2)
    title = lines[0].strip()
    program_info = lines[1].strip() if len(lines) > 1 else ""
    comments = lines[2].strip() if len(lines) > 2 else ""

    # Read counts line (line 3)
    if len(lines) < 4:
        raise ValueError("MOL file missing counts line")

    counts_line = lines[3]
    if "V3000" in counts_line:
        raise ValueError("V3000 MOL files are not supported")
    # V2000 counts are fixed-width (aaabbb...): "96150" is 96 atoms, 150 bonds,
    # so the columns must be read before trying whitespace splitting.
    try:
        n_atoms = int(counts_line[0:3])
        n_bonds = int(counts_line[3:6]) if counts_line[3:6].strip() else 0
    except ValueError:
        counts = counts_line.split()
        try:
            n_atoms = int(counts[0])
            n_bonds = int(counts[1]) if len(counts) > 1 else 0
        except (ValueError, IndexError):
            raise ValueError(f"Invalid atom/bond counts in MOL file: {counts_line}") from None

    if n_atoms <= 0:
        raise ValueError(f"Invalid number of atoms: {n_atoms}")

    # Read atom block (lines 4 to 4+n_atoms)
    if len(lines) < 4 + n_atoms:
        raise ValueError(f"Not enough lines for {n_atoms} atoms")

    species = []
    positions = []

    for i in range(4, 4 + n_atoms):
        if i >= len(lines):
            raise ValueError(f"Not enough lines for {n_atoms} atoms at line {i+1}")

        line = lines[i]
        if len(line) < 30:
            raise ValueError(f"MOL atom line {i+1} is too short (minimum 30 characters): {line}")

        try:
            # MDL V2000 atom line (fixed-width):
            # Columns 0-9: x, 10-19: y, 20-29: z, 31-33: element symbol
            x = float(line[0:10].strip())
            y = float(line[10:20].strip())
            z = float(line[20:30].strip())

            # Primary: fixed-width element at columns 31-34
            element = line[31:34].strip() if len(line) > 31 else ""

            # Fallback: space-separated parsing for non-standard MOL variants
            if not element or not element[0].isalpha():
                parts = line.split()
                element = parts[3] if len(parts) >= 4 else ""

            if not element or not element[0].isalpha():
                raise ValueError(f"Could not parse element symbol at atom line {i+1}")

            species.append(element)
            positions.append([x, y, z])
        except ValueError:
            raise
        except (IndexError,) as e:
            raise ValueError(f"Malformed atom line {i+1}: {e}")

    if len(species) != n_atoms:
        raise ValueError(
            f"MOL atom count mismatch: declared {n_atoms}, parsed {len(species)}"
        )

    return Molecule(species, positions)


def write_MOL(molecule: Molecule, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Molecule to MOL format file.

    Args:
        molecule: Molecule object to write
        filename: Output filename
        title: Optional title (default: molecule formula)

    Raises:
        ValueError: If molecule is not a valid Molecule object
    """
    if not isinstance(molecule, Molecule):
        raise ValueError("write_MOL requires a Molecule object")

    if title is None:
        title = molecule.formula
    if "\n" in title or "\r" in title:
        raise ValueError("MOL title must be a single line")
    if len(molecule) > 999:
        raise ValueError(
            f"MOL V2000 files hold at most 999 atoms, got {len(molecule)}; use XYZ or PDB"
        )

    filepath = Path(filename)

    with open(filepath, "w") as f:
        # Write header
        f.write(f"{title}\n")
        f.write("  MatSimPy\n")
        f.write("\n")

        # Write counts line
        # Format: "nnn nnn ..." (atoms, bonds, ...)
        n_atoms = len(molecule)
        n_bonds = 0  # We don't calculate bonds, set to 0
        f.write(f"{n_atoms:3d}{n_bonds:3d}  0  0  0  0  0  0  0  0  1 V2000\n")

        # Write atom block
        for specie, pos in zip(molecule.species, molecule.positions):
            # Format: xxxxx.xxxx yyyyy.yyyy zzzzz.zzzz EEE MM 0 0 0 0 0 0 0 0 0 0 0 0
            f.write(
                f"{pos[0]:10.4f}{pos[1]:10.4f}{pos[2]:10.4f} {specie:>3s}  0  0  0  0  0  0  0  0  0  0  0  0\n"
            )

        # Write bond block (empty since we don't have bond info)
        # Still write M  END
        f.write("M  END\n")


__all__ = ["read_MOL", "write_MOL"]

# --- Registry registration ---
from .registry import registry, FormatHandler

_MOL_HANDLER = FormatHandler(
    name="mol",
    extensions=(".mol",),
    aliases=("mol", "MOL"),
    description="MDL Molfile format",
    reader=read_MOL,
    writer=write_MOL,
    supports_crystal=False,
    supports_molecule=True,
    strict_by_default=True,
)
registry.register(_MOL_HANDLER)
