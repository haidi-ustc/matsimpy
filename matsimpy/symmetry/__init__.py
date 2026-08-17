"""
Symmetry analysis tools for crystals and molecules.

This module provides symmetry analysis capabilities:
- Crystal symmetry: Space group determination using spglib
- Molecule symmetry: Point group determination
- Symmetry operations and Wyckoff positions
- Access to symmetry data (space groups, point groups, generator matrices)

The module loads symmetry data from symm_data.json or symm_data.yaml files
in the symmetry directory, providing access to:
- Space group encodings (234 space groups)
- Point group encodings (32 point groups)
- Generator matrices for symmetry operations
- Translations and maximal subgroups
"""

from .analyzer import SymmetryAnalyzer, analyze_symmetry, get_conventional_cell
from .kpath import HighSymmetryKpath
from .matcher import StructureMatcher

__all__ = [
    "SymmetryAnalyzer",
    "analyze_symmetry",
    "get_conventional_cell",
    "HighSymmetryKpath",
    "StructureMatcher",
]
