"""
CIF (Crystallographic Information File) format support.

This module provides functions to read and write CIF format files following
the CIF 1.1 standard. Our implementation focuses on the essential data items
needed for crystal structure representation.
"""

from pathlib import Path
from typing import Optional, Dict, List
import re
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


def _tokenize_cif(text: str) -> List[tuple]:
    """Split CIF text into (kind, value) tokens.

    Follows the CIF 1.1 lexical rules that matter here:

    * ``#`` starts a comment unless it is inside a quoted string;
    * a quoted string ends only at a matching quote followed by whitespace or
      the end of the line, so ``'C1''`` style primes and apostrophes inside
      names (``'Strel'tsov, V.A.'``) are kept;
    * a line starting with ``;`` opens a text field closed by the next line
      starting with ``;``.

    ``kind`` is ``"tag"``, ``"loop"``, ``"data"`` or ``"value"``.
    """
    tokens: List[tuple] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(";"):
            field = [line[1:]]
            i += 1
            while i < len(lines) and not lines[i].startswith(";"):
                field.append(lines[i])
                i += 1
            if i >= len(lines):
                raise ValueError("Unterminated ';' text field in CIF file")
            tokens.append(("value", "\n".join(field).strip()))
            i += 1
            continue
        pos, n = 0, len(line)
        while pos < n:
            ch = line[pos]
            if ch.isspace():
                pos += 1
                continue
            if ch == "#":
                break
            if ch in "'\"":
                end = pos + 1
                while True:
                    end = line.find(ch, end)
                    if end == -1:
                        raise ValueError(f"No closing quotation on CIF line {i + 1}: {line!r}")
                    if end + 1 >= n or line[end + 1].isspace():
                        break
                    end += 1
                tokens.append(("value", line[pos + 1:end]))
                pos = end + 1
                continue
            end = pos
            while end < n and not line[end].isspace():
                end += 1
            word = line[pos:end]
            pos = end
            low = word.lower()
            if word.startswith("_"):
                tokens.append(("tag", word))
            elif low == "loop_":
                tokens.append(("loop", None))
            elif low.startswith("data_"):
                tokens.append(("data", word[5:]))
            elif low.startswith(("global_", "save_", "stop_")):
                raise ValueError(f"Unsupported CIF construct {word!r} on line {i + 1}")
            else:
                tokens.append(("value", word))
        i += 1
    return tokens


def _parse_cif_blocks(text: str) -> List[tuple]:
    """Return ``[(block_name, {tag: value or [values]})]`` for every data block."""
    tokens = _tokenize_cif(text)
    blocks: List[tuple] = []
    data: Optional[Dict] = None
    k = 0
    while k < len(tokens):
        kind, value = tokens[k]
        if kind == "data":
            data = {}
            blocks.append((value, data))
            k += 1
            continue
        if data is None:
            raise ValueError("CIF content found before the first data_ block")
        if kind == "loop":
            k += 1
            tags = []
            while k < len(tokens) and tokens[k][0] == "tag":
                tags.append(tokens[k][1])
                k += 1
            values = []
            while k < len(tokens) and tokens[k][0] == "value":
                values.append(tokens[k][1])
                k += 1
            if not tags:
                raise ValueError("CIF loop_ without data names")
            if len(values) % len(tags) != 0:
                if any(t.lower().startswith(_STRUCTURE_TAG_PREFIXES) for t in tags):
                    raise ValueError(
                        f"Loop token count ({len(values)}) is not a multiple of column "
                        f"count ({len(tags)}) in loop {tags}"
                    )
                continue  # malformed loop of data not used here (e.g. a powder pattern)
            for col, tag in enumerate(tags):
                data[tag] = values[col::len(tags)]
            continue
        if kind == "tag":
            if k + 1 >= len(tokens) or tokens[k + 1][0] != "value":
                raise ValueError(f"CIF data name {value} has no value")
            data[value] = tokens[k + 1][1]
            k += 2
            continue
        raise ValueError(f"Unexpected CIF value {value!r} outside a loop")
    return blocks


_STRUCTURE_TAG_PREFIXES = ("_atom_site_", "_atom_site.", "_cell_", "_cell.", "_symmetry_", "_space_group")

# symmetry-operation and centering loops in CIF1, CIF2 and magnetic CIF spelling
_SYMOP_TAG = re.compile(r"^_(symmetry_equiv_pos_as_xyz|space_group.*symop.*xyz)$", re.IGNORECASE)
_SG_NAME_TAGS = (
    "_symmetry_space_group_name_h-m", "_space_group_name_h-m_alt",
    "_space_group.name_h-m_alt", "_space_group_name_hall", "_symmetry_space_group_name_hall",
    "_space_group.name_hall", "_space_group_magn.name_bns", "_space_group_magn.name_og",
)
_SG_NUMBER_TAGS = (
    "_symmetry_int_tables_number", "_space_group_it_number", "_space_group.it_number",
    "_space_group_magn.number_bns", "_space_group_magn.number_og",
)


def _is_identity_op(op: str) -> bool:
    return re.sub(r"[\s']", "", op).lower() in ("x,y,z", "+x,+y,+z", "x,y,z,+1")


def _check_p1(data: Dict) -> None:
    """Raise unless the block describes a P1 structure with every site listed."""
    lower = {k.lower(): v for k, v in data.items()}
    for tag, value in data.items():
        if _SYMOP_TAG.match(tag):
            ops = value if isinstance(value, list) else [value]
            if len(ops) > 1 or (ops and not _is_identity_op(ops[0])):
                raise ValueError(
                    f"CIF symmetry expansion is not supported: {tag} lists {len(ops)} "
                    "operation(s). Only P1 CIFs with every site listed are supported."
                )
    for tag in _SG_NAME_TAGS:
        name = lower.get(tag)
        if isinstance(name, str) and name not in ("?", "."):
            compact = re.sub(r"\s", "", name).upper()
            if compact not in ("P1", "P1(NO.1)"):
                raise ValueError(
                    f"CIF space group {name!r} is not P1 and symmetry expansion is not "
                    "supported; convert the file to P1 first (e.g. with pymatgen)."
                )
    for tag in _SG_NUMBER_TAGS:
        number = lower.get(tag)
        if isinstance(number, str) and number not in ("?", ".") and number.strip() not in ("1", "1.1"):
            raise ValueError(
                f"CIF space group number {number} is not 1 (P1); symmetry expansion is not supported."
            )


def _element_from_cif_symbol(symbol: str) -> str:
    """``Fe3+`` / ``O2-`` / ``Fe0+`` / ``Si1`` -> element symbol."""
    match = re.match(r"([A-Z][a-z]?)", symbol.strip())
    if match is None:
        raise ValueError(f"Cannot get an element symbol from CIF atom type {symbol!r}")
    return match.group(1)


def read_CIF(filename: str) -> Crystal:
    """
    Read a P1 CIF (Crystallographic Information File).

    Only files whose sites are all listed (space group P1) are supported; a
    file that declares other symmetry operations or another space group
    raises ``ValueError`` instead of being read without expansion.  Charges
    in atom types (``Fe3+``) are stripped to the element.

    Args:
        filename: Path to the CIF file

    Returns:
        Crystal: Crystal structure from the file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If the file is malformed, has several structure blocks,
            is not P1, has partial occupancies or lacks required data
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"CIF file not found: {filename}")

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    blocks = [b for b in _parse_cif_blocks(text)
              if any(t in b[1] for t in ("_atom_site_fract_x", "_atom_site_Cartn_x"))]
    if not blocks:
        raise ValueError("Could not find atomic positions in CIF file")
    if len(blocks) > 1:
        raise ValueError(
            f"CIF file contains {len(blocks)} structures (data blocks "
            f"{', '.join(repr(b[0]) for b in blocks)}); read_CIF reads one structure per file"
        )
    cif_data = blocks[0][1]

    for key in ("_cell_length_a", "_cell_length_b", "_cell_length_c",
                "_cell_angle_alpha", "_cell_angle_beta", "_cell_angle_gamma"):
        value = cif_data.get(key)
        if isinstance(value, list) and len(value) == 1:
            cif_data[key] = value = value[0]  # a single-row loop, seen in real files
        if value is None or isinstance(value, list) or value in ("?", "."):
            raise ValueError(f"CIF file missing required key '{key}'")

    a = _parse_cif_value(cif_data["_cell_length_a"])
    b = _parse_cif_value(cif_data["_cell_length_b"])
    c = _parse_cif_value(cif_data["_cell_length_c"])
    alpha = _parse_cif_value(cif_data["_cell_angle_alpha"])
    beta = _parse_cif_value(cif_data["_cell_angle_beta"])
    gamma = _parse_cif_value(cif_data["_cell_angle_gamma"])

    if a <= 0 or b <= 0 or c <= 0:
        raise ValueError("Invalid lattice parameters in CIF file")

    lattice = Lattice.from_parameters(a, b, c, alpha, beta, gamma)

    if "_atom_site_occupancy" in cif_data:
        for occ in cif_data["_atom_site_occupancy"]:
            if occ in ("?", "."):
                continue
            occ_val = _parse_cif_value(occ)
            if abs(occ_val - 1.0) > 1e-6:
                raise ValueError(
                    f"Non-1.0 occupancy detected in CIF file, not supported. Value: {occ_val}"
                )

    _check_p1(cif_data)

    if "_atom_site_type_symbol" in cif_data:
        atom_species = [_element_from_cif_symbol(sym) for sym in cif_data["_atom_site_type_symbol"]]
    elif "_atom_site_label" in cif_data:
        atom_species = [_element_from_cif_symbol(label) for label in cif_data["_atom_site_label"]]
    else:
        raise ValueError("Could not find atomic species in CIF file")

    frac_x = cif_data.get("_atom_site_fract_x")
    frac_y = cif_data.get("_atom_site_fract_y")
    frac_z = cif_data.get("_atom_site_fract_z")
    if frac_x and frac_y and frac_z:
        positions = [
            [_parse_cif_value(x), _parse_cif_value(y), _parse_cif_value(z)]
            for x, y, z in zip(frac_x, frac_y, frac_z)
        ]
        cartesian = False
    else:
        cart = [cif_data.get(f"_atom_site_Cartn_{ax}") for ax in "xyz"]
        if not all(cart):
            raise ValueError("Could not find atomic positions in CIF file")
        # _atom_site_Cartn_* use the standard orientation implied by the cell parameters
        positions = [
            [_parse_cif_value(x), _parse_cif_value(y), _parse_cif_value(z)]
            for x, y, z in zip(*cart)
        ]
        cartesian = True

    if len(atom_species) != len(positions):
        raise ValueError(
            f"Number of species ({len(atom_species)}) doesn't match positions ({len(positions)})"
        )

    return Crystal(atom_species, positions, lattice, coords_are_cartesian=cartesian)


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
        title = crystal.formula
    # A data block name is one word: no whitespace (a newline would corrupt the file)
    title = re.sub(r"[^a-zA-Z0-9_]", "_", title)
    if not title or not title[0].isalpha():
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
