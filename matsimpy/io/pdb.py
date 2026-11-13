"""
PDB (Protein Data Bank) format support.

Basic support for reading and writing PDB format files. This is a simplified
implementation focused on coordinate data, not full PDB specification.
"""

from pathlib import Path
from typing import Optional, Union
import re
import numpy as np

from ..core import Molecule, Crystal, Lattice


def _pdb_element(line: str) -> str:
    """Element of an ATOM/HETATM record.

    Uses the element columns 77-78 when present, otherwise the atom name
    (columns 13-16): by PDB convention a two-letter element starts in column
    13 (``"FE  "``) and a one-letter element in column 14 (``" CA "`` is a
    C-alpha carbon, not calcium).
    """
    from ..core.periodic_table import ELEMENTS

    def normalize(symbol: str) -> Optional[str]:
        symbol = symbol.strip()
        if not symbol:
            return None
        symbol = symbol[0].upper() + symbol[1:].lower()
        return symbol if symbol in ELEMENTS else None

    if len(line) >= 78:
        element = normalize(re.sub(r"[^A-Za-z]", "", line[76:78]))
        if element:
            return element
        if line[76:78].strip():
            raise ValueError(f"Unknown element {line[76:78]!r} in PDB line: {line.strip()}")
    name = line[12:16]
    candidates = []
    if name[:1].isalpha():
        candidates.append(name[0:2])
    candidates.append(name[1:2] if name[:1] in (" ", "") or name[:1].isdigit() else name[0:1])
    for candidate in candidates:
        element = normalize(re.sub(r"[^A-Za-z]", "", candidate))
        if element:
            return element
    raise ValueError(f"Cannot determine the element of PDB atom {name.strip()!r}: {line.strip()}")


def read_PDB(filename: str, as_crystal: bool = False) -> Union[Molecule, Crystal]:
    """
    Read a PDB format file.

    PDB format is primarily for proteins/molecules, but can also represent
    crystal structures. By default, returns a Molecule.

    Args:
        filename: Path to the PDB file
        as_crystal: If True, return Crystal (requires CRYST1 record)

    Returns:
        Molecule or Crystal: Structure from the file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"PDB file not found: {filename}")

    with open(filepath, "r") as f:
        lines = f.readlines()

    n_models = sum(1 for line in lines if line.startswith("MODEL "))
    if n_models > 1:
        raise ValueError(
            f"PDB file contains {n_models} MODEL records; read_PDB reads a single "
            "structure (use ASE or split the models into separate files)"
        )

    # Parse CRYST1 record if present (for crystal structures)
    lattice = None
    for line in lines:
        if line.startswith("CRYST1"):
            # Format: CRYST1   a     b     c    alpha  beta gamma spacegroup
            try:
                a = float(line[6:15])
                b = float(line[15:24])
                c = float(line[24:33])
                alpha = float(line[33:40])
                beta = float(line[40:47])
                gamma = float(line[47:54])
            except (ValueError, IndexError):
                raise ValueError(f"Malformed PDB CRYST1 record: {line.rstrip()!r}") from None
            if (a, b, c) != (1.0, 1.0, 1.0):  # 1 1 1 marks "no unit cell" in the PDB format
                lattice = Lattice.from_parameters(a, b, c, alpha, beta, gamma)
            break

    # Parse ATOM and HETATM records
    species = []
    positions = []

    for line in lines:
        if line.startswith(("ATOM  ", "HETATM")):
            try:
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
            except (ValueError, IndexError):
                raise ValueError(f"Malformed PDB ATOM/HETATM line: {line.strip()}") from None
            species.append(_pdb_element(line))
            positions.append([x, y, z])

    if not species:
        raise ValueError("No valid ATOM or HETATM records found in PDB file")

    if as_crystal:
        if lattice is None:
            raise ValueError("as_crystal=True requires a valid CRYST1 record")
        # Convert to fractional coordinates
        frac_positions = []
        for pos in positions:
            cart_pos = np.array(pos)
            frac_pos = np.dot(cart_pos, lattice.inv_matrix)
            frac_positions.append(frac_pos.tolist())
        return Crystal(species, frac_positions, lattice, coords_are_cartesian=False)
    else:
        return Molecule(species, positions)


def write_PDB(
    structure: Union[Molecule, Crystal], filename: str, title: Optional[str] = None
) -> None:
    """
    Write a structure to a PDB format file.

    Args:
        structure: Molecule or Crystal object to write
        filename: Output filename
        title: Optional title/header (default: structure formula)

    Raises:
        ValueError: If structure is not a valid Molecule or Crystal
    """
    if not isinstance(structure, (Molecule, Crystal)):
        raise ValueError("write_PDB requires a Molecule or Crystal object")

    if title is None:
        title = (
            structure.formula if hasattr(structure, "formula") else "MatSimPy Structure"
        )

    filepath = Path(filename)

    with open(filepath, "w") as f:
        # Write header
        title = " ".join(str(title).split())  # one line: newlines would corrupt the file
        f.write(f"HEADER    {title[:40]:<40s}\n")
        f.write("REMARK   1 Generated by MatSimPy\n")

        # Write CRYST1 record if Crystal
        if isinstance(structure, Crystal):
            f.write(
                "CRYST1{:9.3f}{:9.3f}{:9.3f}{:7.2f}{:7.2f}{:7.2f} P 1           1\n".format(
                    structure.lattice.a,
                    structure.lattice.b,
                    structure.lattice.c,
                    structure.lattice.alpha,
                    structure.lattice.beta,
                    structure.lattice.gamma,
                )
            )
            # CRYST1 implies the standard PDB orientation (a along x, b in the
            # xy plane); write coordinates in that frame so readers that
            # rebuild the cell from CRYST1 get the right fractional coordinates.
            lat = structure.lattice
            standard = Lattice.from_parameters(lat.a, lat.b, lat.c, lat.alpha, lat.beta, lat.gamma)
            positions = structure.frac_positions @ standard.matrix
        else:
            positions = structure.positions

        # Write ATOM records
        for i, (specie, pos) in enumerate(zip(structure.species, positions)):
            atom_num = i + 1
            # PDB alignment: two-letter elements start in column 13
            atom_name = f"{specie:<4s}" if len(specie) == 2 else f" {specie:<3s}"
            res_name = "UNK"
            res_num = 1
            chain = "A"

            # Format: ATOM  serial  name alt res chain resseq x y z occ temp element
            f.write(
                "ATOM  {:5d} {:4s}{:1s}{:3s} {:1s}{:4d}    {:8.3f}{:8.3f}{:8.3f}{:6.2f}{:6.2f}          {:>2s}\n".format(
                    atom_num,
                    atom_name,
                    " ",  # alt location
                    res_name,
                    chain,
                    res_num,
                    pos[0],
                    pos[1],
                    pos[2],
                    1.0,  # occupancy
                    0.0,  # temp factor
                    specie.upper(),
                )
            )

        f.write("END\n")


__all__ = ["read_PDB", "write_PDB"]

# --- Registry registration ---
from .registry import registry, FormatHandler

_PDB_HANDLER = FormatHandler(
    name="pdb",
    extensions=(".pdb",),
    aliases=("pdb", "PDB"),
    description="Protein Data Bank format",
    reader=read_PDB,
    writer=write_PDB,
    supports_crystal=True,
    supports_molecule=True,
    strict_by_default=True,
)
registry.register(_PDB_HANDLER)
