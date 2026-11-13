"""
VASP file format support.

This module provides functions to read and write VASP POSCAR/CONTCAR format files.
Our implementation focuses on clean, readable code that integrates with MatSimPy's
Crystal class.
"""

from pathlib import Path
from typing import Optional, List
import numpy as np

from ..core import Crystal, Lattice


def _poscar_symbol(token: str) -> str:
    """Element symbol from a POSCAR species token (``Fe_pv`` / ``Si/abc123`` -> element)."""
    return token.split("/")[0].split("_")[0]


def _is_int_line(tokens: List[str]) -> bool:
    return bool(tokens) and all(t.lstrip("+").isdigit() for t in tokens)


def read_POSCAR(filename: str) -> Crystal:
    """
    Read a VASP 5 POSCAR or CONTCAR file.

    Supports Direct and Cartesian coordinates, positive and negative (volume)
    scale factors, species/count lines spread over several lines, and
    POTCAR-style species names such as ``Fe_pv``.

    * ``Selective dynamics`` flags are stored as the site property
      ``selective_dynamics`` (three bools per atom).
    * A velocity block (CONTCAR of an MD run) is stored as the site property
      ``velocities`` (Cartesian, as written by VASP).  The predictor-corrector
      block that may follow is not read.

    Args:
        filename: Path to the POSCAR/CONTCAR file

    Returns:
        Crystal: Crystal structure from the file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid (VASP 4 files included)
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"POSCAR file not found: {filename}")

    with open(filepath, "r") as f:
        raw = [line.strip() for line in f.readlines()]

    # Lines 0-4 (comment, scale, lattice) never contain blank data lines in a
    # valid file except the comment; skip blank lines only inside the header.
    def next_nonblank(i: int) -> int:
        while i < len(raw) and not raw[i]:
            i += 1
        return i

    if len(raw) < 8:
        raise ValueError(f"Invalid POSCAR file: too few lines ({len(raw)})")

    i = next_nonblank(1)
    try:
        scale_tokens = raw[i].split()
        if len(scale_tokens) != 1:
            raise ValueError
        scale_factor = float(scale_tokens[0])
    except (ValueError, IndexError):
        raise ValueError(
            f"Invalid scale factor in POSCAR: {raw[i] if i < len(raw) else ''!r} "
            "(one number expected; three scale factors are not supported)"
        ) from None
    if not np.isfinite(scale_factor) or scale_factor == 0:
        raise ValueError(f"Invalid scale factor in POSCAR: {scale_factor}")
    i += 1

    lattice_vectors = []
    for _ in range(3):
        i = next_nonblank(i)
        try:
            vec = [float(x) for x in raw[i].split()]
        except (ValueError, IndexError):
            raise ValueError(f"Invalid lattice vector format at line {i + 1}") from None
        if len(vec) != 3:
            raise ValueError(f"Invalid lattice vector at line {i + 1}")
        lattice_vectors.append(vec)
        i += 1

    raw_matrix = np.array(lattice_vectors, dtype=np.float64)
    if scale_factor < 0:
        vol = abs(np.linalg.det(raw_matrix))
        if vol == 0:
            raise ValueError("Lattice vectors have zero volume, cannot apply negative scale")
        scale = (abs(scale_factor) / vol) ** (1 / 3)
    else:
        scale = scale_factor
    lattice = Lattice(raw_matrix * scale)

    # Species symbols, possibly over several lines, then counts (also possibly
    # over several lines) until their number matches the number of symbols.
    i = next_nonblank(i)
    if i >= len(raw):
        raise ValueError("Missing species line in POSCAR")
    if _is_int_line(raw[i].split()):
        raise ValueError(
            "VASP 4 format POSCAR (no element-symbol line after the lattice) is not "
            "supported; add a line with the element symbols before the atom counts."
        )
    symbols: List[str] = []
    while i < len(raw) and raw[i] and not _is_int_line(raw[i].split()):
        symbols.extend(raw[i].split())
        i += 1
    counts: List[int] = []
    while i < len(raw) and len(counts) < len(symbols) and _is_int_line(raw[i].split()):
        counts.extend(int(x) for x in raw[i].split())
        i += 1
    if not counts:
        raise ValueError(f"Invalid species counts in POSCAR at line {i + 1}: {raw[i] if i < len(raw) else ''!r}")
    if len(symbols) != len(counts):
        raise ValueError(
            f"Number of species ({len(symbols)}) and counts ({len(counts)}) don't match"
        )

    species_list: List[str] = []
    for token, count in zip(symbols, counts):
        species_list.extend([_poscar_symbol(token)] * count)
    total_atoms = sum(counts)

    i = next_nonblank(i)
    if i >= len(raw):
        raise ValueError("Missing coordinate type indicator")
    selective = raw[i].lower().startswith("s")
    if selective:
        i = next_nonblank(i + 1)
        if i >= len(raw):
            raise ValueError("Missing coordinate type indicator")
    coord_type_line = raw[i].lower()
    coords_are_cartesian = coord_type_line.startswith(("c", "k"))
    i += 1

    if len(raw) < i + total_atoms:
        raise ValueError(
            f"Not enough position lines: expected {total_atoms}, got {len(raw) - i}"
        )
    positions = []
    flags = []
    for line_no in range(i, i + total_atoms):
        tokens = raw[line_no].split()
        try:
            pos = [float(x) for x in tokens[:3]]
        except ValueError as e:
            raise ValueError(f"Invalid position format at line {line_no + 1}: {e}") from None
        if len(pos) != 3:
            raise ValueError(f"Invalid position at line {line_no + 1}")
        positions.append(pos)
        if selective:
            if len(tokens) < 6 or any(t.upper() not in ("T", "F") for t in tokens[3:6]):
                raise ValueError(
                    f"Selective dynamics flags (T/F x3) missing at line {line_no + 1}"
                )
            flags.append([t.upper() == "T" for t in tokens[3:6]])
    i += total_atoms

    positions_arr = np.array(positions, dtype=np.float64)
    if coords_are_cartesian:
        # the scale factor applies to Cartesian positions as well
        positions_arr = positions_arr * scale

    site_properties = [{} for _ in range(total_atoms)]
    if selective:
        for props, f in zip(site_properties, flags):
            props["selective_dynamics"] = f

    # NPT runs write a "Lattice velocities and vectors" block first; skip it.
    if i < len(raw) and raw[i].lower().startswith("lattice velocities"):
        while i < len(raw) and raw[i]:
            i += 1

    # Optional velocity block: a blank line, optionally a coordinate-type line,
    # then one line of three numbers per atom.
    if i < len(raw) and not raw[i]:
        j = i + 1
        if j < len(raw) and raw[j] and raw[j][0].isalpha():
            j += 1  # e.g. "Cartesian"
        block = raw[j:j + total_atoms]
        if len(block) == total_atoms and all(block):
            try:
                velocities = [[float(x) for x in line.split()[:3]] for line in block]
            except ValueError:
                velocities = None
            if velocities is not None and all(len(v) == 3 for v in velocities):
                for props, v in zip(site_properties, velocities):
                    props["velocities"] = v

    return Crystal(
        species_list,
        positions_arr,
        lattice,
        coords_are_cartesian=coords_are_cartesian,
        site_properties=site_properties if any(site_properties) else None,
    )


def write_POSCAR(crystal: Crystal, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Crystal structure to a VASP 5 POSCAR file (Direct coordinates).

    Atoms are written in their original order; consecutive atoms of the same
    species form one group, so a species may appear in several groups
    (``Fe O Fe``), as VASP allows.  Site properties ``selective_dynamics``
    (three bools per atom) and ``velocities`` (Cartesian) are written.

    Args:
        crystal: Crystal structure to write
        filename: Output filename
        title: Optional title for the POSCAR file (a single line)

    Raises:
        ValueError: If crystal is not a Crystal, the title spans several lines,
            or ``selective_dynamics`` / ``velocities`` are malformed.
    """
    if not isinstance(crystal, Crystal):
        raise ValueError("write_POSCAR requires a Crystal object")

    if title is None:
        title = f"{crystal.__class__.__name__} - {crystal.formula}"
    if "\n" in title or "\r" in title:
        raise ValueError("POSCAR title must be a single line")

    species = list(crystal.species)
    groups: List[List] = []
    for sp in species:
        if groups and groups[-1][0] == sp:
            groups[-1][1] += 1
        else:
            groups.append([sp, 1])


    has_sd = bool(crystal.site_properties) and any(
        "selective_dynamics" in p for p in crystal.site_properties
    )
    has_vel = bool(crystal.site_properties) and any("velocities" in p for p in crystal.site_properties)
    sd = vel = None
    if has_sd:
        sd = []
        for k, p in enumerate(crystal.site_properties):
            flags = p.get("selective_dynamics")
            if flags is None or len(flags) != 3:
                raise ValueError(f"selective_dynamics of atom {k} must be three bools")
            sd.append(["T" if bool(x) else "F" for x in flags])
    if has_vel:
        vel = []
        for k, p in enumerate(crystal.site_properties):
            v = p.get("velocities")
            v = np.asarray(v, dtype=np.float64) if v is not None else None
            if v is None or v.shape != (3,) or not np.all(np.isfinite(v)):
                raise ValueError(f"velocities of atom {k} must be three finite numbers")
            vel.append(v)

    filepath = Path(filename)
    with open(filepath, "w") as f:
        f.write(f"{title}\n")
        f.write("1.0\n")
        for vec in crystal.lattice.matrix:
            f.write(f"{vec[0]:.16f} {vec[1]:.16f} {vec[2]:.16f}\n")
        f.write(" ".join(g[0] for g in groups) + "\n")
        f.write(" ".join(str(g[1]) for g in groups) + "\n")
        if has_sd:
            f.write("Selective dynamics\n")
        f.write("Direct\n")
        for idx, pos in enumerate(crystal.frac_positions):
            line = f"{pos[0]:.16f} {pos[1]:.16f} {pos[2]:.16f}"
            if has_sd:
                line += " " + " ".join(sd[idx])
            f.write(line + "\n")
        if has_vel:
            f.write("\n")
            for v in vel:
                f.write(f"{v[0]:.16e} {v[1]:.16e} {v[2]:.16e}\n")



def read_CONTCAR(filename: str) -> Crystal:
    """
    Read a VASP CONTCAR file (alias for read_POSCAR).

    CONTCAR format is identical to POSCAR, so this is just a convenience function.

    Args:
        filename: Path to the CONTCAR file

    Returns:
        Crystal: Crystal structure from the file
    """
    return read_POSCAR(filename)


def write_CONTCAR(crystal: Crystal, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Crystal structure to a VASP CONTCAR file (alias for write_POSCAR).

    Args:
        crystal: Crystal structure to write
        filename: Output filename
        title: Optional title for the CONTCAR file
    """
    write_POSCAR(crystal, filename, title)


__all__ = ["read_POSCAR", "write_POSCAR", "read_CONTCAR", "write_CONTCAR"]

# --- Registry registration ---
from .registry import registry, FormatHandler

_POSCAR_HANDLER = FormatHandler(
    name="vasp-poscar",
    extensions=(".vasp", ".poscar"),
    filename_patterns=("POSCAR", "POSCAR.*", "POSCAR_*"),
    aliases=("poscar", "vasp", "POSCAR"),
    description="VASP POSCAR format (periodic crystal structures)",
    reader=read_POSCAR,
    writer=write_POSCAR,
    supports_crystal=True,
    supports_molecule=False,
    strict_by_default=True,
)
_CONTCAR_HANDLER = FormatHandler(
    name="vasp-contcar",
    extensions=(".contcar",),
    filename_patterns=("CONTCAR", "CONTCAR.*", "CONTCAR_*"),
    aliases=("contcar", "CONTCAR"),
    description="VASP CONTCAR format (output structure)",
    reader=read_CONTCAR,
    writer=write_CONTCAR,
    supports_crystal=True,
    supports_molecule=False,
    strict_by_default=True,
)
registry.register(_POSCAR_HANDLER)
registry.register(_CONTCAR_HANDLER)
