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

    Args:
        filename: Path to the ASE/XYZ file

    Returns:
        Crystal: Crystal structure from the file (if cell info present)
                Otherwise returns as Molecule (handled by caller)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"ASE file not found: {filename}")

    with open(filepath, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if len(lines) < 2:
        raise ValueError("ASE file must have at least 2 lines")

    # Read number of atoms
    try:
        n_atoms = int(lines[0])
    except ValueError:
        raise ValueError(f"Invalid atom count in ASE file: {lines[0]}")

    # Read properties line (line 1) - may contain cell information
    properties_line = lines[1] if len(lines) > 1 else ""

    # Try to extract cell information from properties
    lattice = None
    cell_info = None

    # Look for Lattice or cell keywords in properties
    if "Lattice=" in properties_line:
        # ASE format: Lattice="a1 b1 c1 a2 b2 c2 a3 b3 c3"
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

    # Read atomic coordinates
    species = []
    positions = []

    for i in range(2, min(2 + n_atoms, len(lines))):
        parts = lines[i].split()
        if len(parts) < 4:
            continue

        try:
            specie = parts[0]
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            species.append(specie)
            positions.append([x, y, z])
        except ValueError:
            continue

    if not species:
        raise ValueError("No valid atomic coordinates found in ASE file")

    # If we have lattice, return Crystal; otherwise raise (caller should handle)
    if lattice is not None:
        # Positions are typically in cartesian for ASE
        return Crystal(species, positions, lattice, coords_are_cartesian=True)
    else:
        raise ValueError(
            "ASE file does not contain cell/lattice information. Use read_XYZ for molecules."
        )


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

    filepath = Path(filename)

    with open(filepath, "w") as f:
        # Write number of atoms
        f.write(f"{len(structure)}\n")

        # Write properties line with lattice info if Crystal
        if isinstance(structure, Crystal):
            lattice = structure.lattice
            # Format: Lattice="a1 b1 c1 a2 b2 c2 a3 b3 c3"
            lattice_str = " ".join(
                [f"{v:.10f}" for row in lattice.lattice_vectors for v in row]
            )
            f.write(f'Lattice="{lattice_str}" Properties=species:S:1:pos:R:3 {title}\n')
            # Use cartesian positions
            positions = structure.cart_positions
        else:
            f.write(f"{title}\n")
            positions = structure.positions

        # Write atomic coordinates
        for specie, pos in zip(structure.species, positions):
            f.write(f"{specie:4s} {pos[0]:15.10f} {pos[1]:15.10f} {pos[2]:15.10f}\n")


__all__ = ["read_ASE", "write_ASE"]
