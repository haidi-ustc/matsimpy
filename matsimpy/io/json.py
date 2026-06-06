"""
JSON serialization support for MatSimPy structures.

This module provides JSON serialization and deserialization for Crystal and
Molecule objects using their built-in as_dict() and from_dict() methods.
"""

import json
from pathlib import Path
from typing import Union, Optional

from ..core import Crystal, Molecule, Structure


def to_json(
    structure: Union[Structure, Crystal, Molecule],
    filename: Optional[str] = None,
    indent: Optional[int] = 2,
) -> Optional[str]:
    """
    Serialize a structure to JSON format.

    This function uses the structure's as_dict() method to create a JSON
    representation. The JSON can be written to a file or returned as a string.

    Args:
        structure: Structure, Crystal, or Molecule object to serialize
        filename: Optional filename to write JSON to. If None, returns JSON string
        indent: JSON indentation level (default: 2, None for compact)

    Returns:
        str or None: JSON string if filename is None, otherwise None

    Raises:
        ValueError: If structure is not serializable
        TypeError: If structure doesn't have as_dict method
    """
    if not hasattr(structure, "as_dict"):
        raise TypeError(f"Object {type(structure)} does not support JSON serialization")

    data = structure.as_dict()
    json_str = json.dumps(data, indent=indent, default=str)

    if filename is not None:
        filepath = Path(filename)
        with open(filepath, "w") as f:
            f.write(json_str)
        return None
    else:
        return json_str


def from_json(
    json_string: Optional[str] = None, filename: Optional[str] = None
) -> Union[Crystal, Molecule, Structure]:
    """
    Deserialize a structure from JSON format.

    This function reads JSON (either from a string or file) and reconstructs
    the appropriate structure object (Crystal, Molecule, or Structure).

    Args:
        json_string: JSON string to parse (if filename is None)
        filename: Path to JSON file to read (if json_string is None)

    Returns:
        Crystal, Molecule, or Structure: Reconstructed structure object

    Raises:
        ValueError: If both or neither json_string and filename are provided
        FileNotFoundError: If filename doesn't exist
        ValueError: If JSON format is invalid
    """
    if json_string is None and filename is None:
        raise ValueError("Either json_string or filename must be provided")
    if json_string is not None and filename is not None:
        raise ValueError("Provide either json_string or filename, not both")

    if filename is not None:
        filepath = Path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"JSON file not found: {filename}")
        with open(filepath, "r") as f:
            json_string = f.read()

    data = json.loads(json_string)

    # Determine structure type from data
    class_name = data.get("@class", "")
    module_name = data.get("@module", "")

    if "Crystal" in class_name:
        return Crystal.from_dict(data)
    elif "Molecule" in class_name:
        return Molecule.from_dict(data)
    elif "Structure" in class_name:
        return Structure.from_dict(data)
    else:
        raise ValueError(f"Unknown structure type in JSON: {class_name}")


__all__ = ["to_json", "from_json"]

# --- Registry registration ---
from .registry import registry, FormatHandler

def _read_json(filename, **kwargs):
    """Adapter: calls from_json with filename as keyword argument."""
    return from_json(filename=filename, **kwargs)


def _write_json(structure, filename, **kwargs):
    """Adapter: calls to_json with filename as keyword argument."""
    return to_json(structure, filename=filename, **kwargs)


_JSON_HANDLER = FormatHandler(
    name="json",
    extensions=(".json",),
    aliases=("json", "JSON"),
    description="MatSimPy JSON serialization format",
    reader=_read_json,
    writer=_write_json,
    supports_crystal=True,
    supports_molecule=True,
    strict_by_default=True,
)
registry.register(_JSON_HANDLER)
