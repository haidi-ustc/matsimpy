"""
CIF (Crystallographic Information File) format support.

This module provides functions to read and write CIF format files following
the CIF 1.1 standard. Our implementation focuses on the essential data items
needed for crystal structure representation.
"""

from pathlib import Path
from typing import Optional, Dict, List
import re
import shlex
import numpy as np

from ..core import Crystal, Lattice


def _parse_cif_value(value: str) -> float:
    """
    Parse a CIF value, handling uncertainties and parentheses.

    Args:
        value: CIF value string (may contain uncertainty like "1.5(2)")

    Returns:
        float: Parsed numeric value
    """
    # Remove uncertainty in parentheses like "1.5(2)" -> "1.5"
    value = re.sub(r"\([^)]*\)", "", value)
    # Remove leading/trailing whitespace and quotes
    value = value.strip().strip("\"'")
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"Could not parse CIF value as float: {value}")


def _parse_cif_line(line: str) -> tuple:
    """
    Parse a CIF data line.

    Args:
        line: CIF line (may be data_item or loop)

    Returns:
        tuple: (data_name, value) or None if not a data line
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # Check for data_ block
    if line.startswith("data_"):
        return ("data_block", line[5:].strip())

    # Check for loop_ statement
    if line.startswith("loop_"):
        return ("loop_start", None)

    # Check for data item (starts with _)
    if line.startswith("_"):
        parts = line.split(None, 1)
        if len(parts) == 2:
            return (parts[0], parts[1].strip().strip("\"'"))
        elif len(parts) == 1:
            return (parts[0], None)

    return None


def read_CIF(filename: str) -> Crystal:
    """
    Read a CIF (Crystallographic Information File) format file.

    This function reads standard CIF files and extracts crystal structure
    information including lattice parameters and atomic positions.

    Args:
        filename: Path to the CIF file

    Returns:
        Crystal: Crystal structure from the file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid or missing required data
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"CIF file not found: {filename}")

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # Parse CIF data
    cif_data = {}
    in_loop = False
    loop_items = []
    loop_data_lines = []
    current_line_index = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        parsed = _parse_cif_line(line)

        if parsed is None:
            i += 1
            continue

        data_name, value = parsed

        if data_name == "loop_start":
            in_loop = True
            loop_items = []
            loop_data_lines = []
            i += 1
            # Collect loop items
            while i < len(lines):
                loop_line = lines[i]
                if not loop_line.strip():
                    i += 1
                    continue
                loop_parsed = _parse_cif_line(loop_line)
                if loop_parsed is None:
                    # This might be a data line (not a data item)
                    # Check if it's actually data by seeing if it doesn't start with special chars
                    stripped = loop_line.strip()
                    if not (
                        stripped.startswith("_")
                        or stripped.startswith("loop_")
                        or stripped.startswith("data_")
                    ):
                        # This is a data line, break to start collecting data
                        break
                    i += 1
                    continue
                loop_name, loop_value = loop_parsed
                if loop_name.startswith("_"):
                    loop_items.append(loop_name)
                    i += 1
                else:
                    # Start of data (not a data item line)
                    break
            # Collect data lines (everything after loop items until we hit another data item or loop)
            while i < len(lines):
                data_line = lines[i]
                data_line_stripped = data_line.strip()
                if not data_line_stripped:
                    i += 1
                    continue
                # Check if this is a data item or loop start (end of loop)
                if (
                    data_line_stripped.startswith("_")
                    or data_line_stripped.startswith("loop_")
                    or data_line_stripped.startswith("data_")
                ):
                    break
                # This is a data line - add it
                loop_data_lines.append(data_line_stripped)
                i += 1
            # Collect all tokens from loop data lines into a flat list, then
            # slice by the number of columns to reconstruct rows correctly.
            # This handles CIF files where a single row spans multiple lines.
            tokens = []
            for data_line in loop_data_lines:
                tokens.extend(shlex.split(data_line))

            n_cols = len(loop_items)
            if n_cols > 0:
                if len(tokens) % n_cols != 0:
                    raise ValueError(
                        f"Loop token count ({len(tokens)}) is not a multiple of column count ({n_cols})"
                    )
                for row_start in range(0, len(tokens), n_cols):
                    row = tokens[row_start : row_start + n_cols]
                    for j, item in enumerate(loop_items):
                        if j < len(row):
                            cif_data.setdefault(item, []).append(row[j])
            in_loop = False
            # Don't increment i here - we already advanced past data lines
        else:
            if data_name.startswith("_"):
                cif_data[data_name] = value
            i += 1

    # Extract lattice parameters — raise a descriptive error when required keys are absent
    for key in ("_cell_length_a", "_cell_length_b", "_cell_length_c"):
        if cif_data.get(key) is None:
            raise ValueError(f"CIF file missing required key '{key}'")

    a = _parse_cif_value(cif_data["_cell_length_a"])
    b = _parse_cif_value(cif_data["_cell_length_b"])
    c = _parse_cif_value(cif_data["_cell_length_c"])
    alpha = _parse_cif_value(cif_data.get("_cell_angle_alpha", "90"))
    beta = _parse_cif_value(cif_data.get("_cell_angle_beta", "90"))
    gamma = _parse_cif_value(cif_data.get("_cell_angle_gamma", "90"))

    if a == 0 or b == 0 or c == 0:
        raise ValueError("Invalid lattice parameters in CIF file")

    # Create lattice from parameters
    lattice = Lattice.from_parameters(a, b, c, alpha, beta, gamma)

    if "_atom_site_occupancy" in cif_data:
        for occ in cif_data["_atom_site_occupancy"]:
            occ_val = _parse_cif_value(occ)
            if occ_val != 1.0:
                raise ValueError(
                    f"Non-1.0 occupancy detected in CIF file, not supported. Value: {occ_val}"
                )

    symm_keys = ["_symmetry_equiv_pos_as_xyz", "_space_group_symop_operation_xyz"]
    for symm_key in symm_keys:
        if symm_key in cif_data:
            symm_count = len(cif_data[symm_key])
            if symm_count > 1:
                raise ValueError(
                    f"CIF symmetry expansion is not supported. File contains {symm_count} symmetry operation(s). Only P1 CIFs with explicitly listed sites are supported."
                )

    atom_species = []
    atom_positions = []

    # Try to get from loop data
    if "_atom_site_type_symbol" in cif_data:
        atom_species = cif_data["_atom_site_type_symbol"]
    elif "_atom_site_label" in cif_data:
        # Extract element from label (e.g., "Si1" -> "Si")
        labels = cif_data["_atom_site_label"]
        atom_species = [
            (
                re.match(r"([A-Z][a-z]?)", label).group(1)
                if re.match(r"[A-Z][a-z]?", label)
                else label
            )
            for label in labels
        ]

    # Get positions
    frac_x = cif_data.get("_atom_site_fract_x")
    frac_y = cif_data.get("_atom_site_fract_y")
    frac_z = cif_data.get("_atom_site_fract_z")

    if not (frac_x and frac_y and frac_z):
        # Try cartesian coordinates
        cart_x = cif_data.get("_atom_site_Cartn_x")
        cart_y = cif_data.get("_atom_site_Cartn_y")
        cart_z = cif_data.get("_atom_site_Cartn_z")

        if cart_x and cart_y and cart_z:
            # Convert cartesian to fractional using cached inverse
            positions = []
            for x, y, z in zip(cart_x, cart_y, cart_z):
                cart_pos = np.array(
                    [_parse_cif_value(x), _parse_cif_value(y), _parse_cif_value(z)]
                )
                frac_pos = np.dot(cart_pos, lattice.inv_matrix)
                positions.append(frac_pos.tolist())

            if not atom_species:
                raise ValueError("Could not find atomic species in CIF file")

            return Crystal(atom_species, positions, lattice, coords_are_cartesian=False)
        else:
            raise ValueError("Could not find atomic positions in CIF file")

    # Parse fractional positions
    positions = []
    for x, y, z in zip(frac_x, frac_y, frac_z):
        positions.append(
            [_parse_cif_value(x), _parse_cif_value(y), _parse_cif_value(z)]
        )

    if not atom_species:
        raise ValueError("Could not find atomic species in CIF file")

    if len(atom_species) != len(positions):
        raise ValueError(
            f"Number of species ({len(atom_species)}) doesn't match positions ({len(positions)})"
        )

    return Crystal(atom_species, positions, lattice, coords_are_cartesian=False)


def write_CIF(crystal: Crystal, filename: str, title: Optional[str] = None) -> None:
    """
    Write a Crystal structure to a CIF format file.

    This function writes the structure following CIF 1.1 standard conventions.

    Args:
        crystal: Crystal structure to write
        filename: Output filename
        title: Optional title/data block name (default: uses formula)

    Raises:
        ValueError: If crystal is not a valid Crystal object
    """
    if not isinstance(crystal, Crystal):
        raise ValueError("write_CIF requires a Crystal object")

    if title is None:
        # Create valid CIF data block name (alphanumeric and underscores only)
        title = re.sub(r"[^a-zA-Z0-9_]", "_", crystal.formula)
        if not title[0].isalpha():
            title = "structure_" + title

    filepath = Path(filename)

    with open(filepath, "w") as f:
        # Write data block header
        f.write(f"data_{title}\n\n")

        # Write cell parameters
        f.write("_cell_length_a    {:.6f}\n".format(crystal.lattice.a))
        f.write("_cell_length_b    {:.6f}\n".format(crystal.lattice.b))
        f.write("_cell_length_c    {:.6f}\n".format(crystal.lattice.c))
        f.write("_cell_angle_alpha {:.6f}\n".format(crystal.lattice.alpha))
        f.write("_cell_angle_beta  {:.6f}\n".format(crystal.lattice.beta))
        f.write("_cell_angle_gamma {:.6f}\n\n".format(crystal.lattice.gamma))

        # Write space group (if available, otherwise use P1)
        f.write("_space_group_name_H-M_alt     'P 1'\n")
        f.write("_space_group_IT_number       1\n\n")

        # Write loop for atomic positions
        f.write("loop_\n")
        f.write("_atom_site_type_symbol\n")
        f.write("_atom_site_label\n")
        f.write("_atom_site_fract_x\n")
        f.write("_atom_site_fract_y\n")
        f.write("_atom_site_fract_z\n")
        f.write("_atom_site_occupancy\n")

        # Write atomic positions with per-element counters (Si1, Si2, O1, ...)
        element_counters: Dict[str, int] = {}
        for specie, pos in zip(crystal.species, crystal.frac_positions):
            element_counters[specie] = element_counters.get(specie, 0) + 1
            label = f"{specie}{element_counters[specie]}"
            f.write(
                f"{specie:4s} {label:8s} {pos[0]:12.8f} {pos[1]:12.8f} {pos[2]:12.8f} 1.0\n"
            )


__all__ = ["read_CIF", "write_CIF"]

# --- Registry registration ---
from .registry import registry, FormatHandler

_CIF_HANDLER = FormatHandler(
    name="cif",
    extensions=(".cif",),
    aliases=("cif", "CIF"),
    description="Crystallographic Information File format",
    reader=read_CIF,
    writer=write_CIF,
    supports_crystal=True,
    supports_molecule=False,
    strict_by_default=True,
)
registry.register(_CIF_HANDLER)
