"""
High-level I/O interface for convenient file operations.

This module provides simple read() and write() functions that delegate
to the FormatRegistry for table-driven format detection and dispatch.

Usage::

    >>> from matsimpy.io import read, write
    >>> crystal = read('structure.vasp')
    >>> write(crystal, 'output.cif')
"""

from pathlib import Path
from typing import Optional, Union

from ..core import Crystal, Molecule, Structure
from .registry import registry


def read(
    filename: str,
    format: Optional[str] = None,
    **kwargs,
) -> Union[Crystal, Molecule]:
    """Read a structure from a file with automatic format detection.

    Args:
        filename: Path to the structure file.
        format: Optional format name/alias (e.g. ``'vasp'``, ``'cif'``).
            If None, format is detected from file extension.
        **kwargs: Passed to the format-specific reader.

    Returns:
        Crystal or Molecule.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If format is not supported or cannot be detected.
    """
    return registry.read(filename, format=format, **kwargs)


def write(
    structure: Union[Crystal, Molecule, Structure],
    filename: str,
    format: Optional[str] = None,
    **kwargs,
) -> None:
    """Write a structure to a file with automatic format detection.

    Args:
        structure: Structure to write (Crystal or Molecule).
        filename: Output path.
        format: Optional format name/alias (e.g. ``'vasp'``, ``'cif'``).
            If None, format is detected from file extension.
        **kwargs: Passed to the format-specific writer.

    Raises:
        ValueError: If format is not supported or cannot be detected.
    """
    registry.write(structure, filename, format=format, **kwargs)


__all__ = ["read", "write"]
