"""
Utility functions for file format detection and IO operations.
"""

from pathlib import Path
from typing import Optional, Tuple, Callable


# Format registry mapping extensions to reader/writer functions
FORMAT_REGISTRY = {
    # Crystal formats
    ".vasp": ("read_POSCAR", "write_POSCAR"),
    ".poscar": ("read_POSCAR", "write_POSCAR"),
    ".contcar": ("read_CONTCAR", "write_CONTCAR"),
    ".cif": ("read_CIF", "write_CIF"),
    ".xsf": ("read_XSF", "write_XSF"),
    ".json": ("from_json", "to_json"),
    ".ase": ("read_ASE", "write_ASE"),
    # Molecule formats
    ".xyz": ("read_XYZ", "write_XYZ"),
    ".pdb": ("read_PDB", "write_PDB"),
    ".mol": ("read_MOL", "write_MOL"),
}


def detect_format(filename: str) -> Optional[str]:
    """
    Detect file format from filename extension.

    Args:
        filename: Path to file

    Returns:
        str or None: Format extension (e.g., '.vasp', '.xyz') or None if unknown
    """
    filepath = Path(filename)
    ext = filepath.suffix.lower()

    if ext in FORMAT_REGISTRY:
        return ext

    # Handle some common aliases
    ext_mapping = {
        ".pos": ".vasp",
        ".conf": ".xyz",
    }

    return ext_mapping.get(ext, None)


def get_reader_writer(format_ext: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get reader and writer function names for a format.

    Args:
        format_ext: Format extension (e.g., '.vasp')

    Returns:
        tuple: (reader_name, writer_name) or (None, None) if unknown
    """
    return FORMAT_REGISTRY.get(format_ext, (None, None))


def is_crystal_format(format_ext: str) -> bool:
    """
    Check if format is for crystal structures.

    Args:
        format_ext: Format extension

    Returns:
        bool: True if format supports crystal structures
    """
    # .json and .ase are dual-format (support both Crystal and Molecule)
    crystal_formats = {".vasp", ".poscar", ".contcar", ".cif", ".xsf", ".ase", ".json"}
    return format_ext in crystal_formats


def is_molecule_format(format_ext: str) -> bool:
    """
    Check if format is for molecular structures.

    Args:
        format_ext: Format extension

    Returns:
        bool: True if format supports molecular structures
    """
    # .json and .ase are dual-format (support both Crystal and Molecule)
    molecule_formats = {".xyz", ".pdb", ".mol", ".ase", ".json"}
    return format_ext in molecule_formats


__all__ = [
    "detect_format",
    "get_reader_writer",
    "is_crystal_format",
    "is_molecule_format",
    "FORMAT_REGISTRY",
]
