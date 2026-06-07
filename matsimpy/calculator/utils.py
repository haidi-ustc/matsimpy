"""Shared utility functions for calculator subpackages.

These replace simple pymatgen utilities so IO classes don't need
a direct pymatgen dependency for basic operations.
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Physical constants
Ha_to_eV = 27.211386245988  # Hartree to eV conversion


def clean_lines(string_list: list[str], remove_empty_lines: bool = True) -> list[str]:
    """Strip whitespace and optionally remove empty lines from a list of strings.

    Adapted from pymatgen.util.io_utils.clean_lines.
    """
    stripped = [line.strip() for line in string_list]
    if remove_empty_lines:
        return [line for line in stripped if line]
    return stripped


def make_symmetric_matrix_from_upper_tri(
    data: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Construct a symmetric 3x3 matrix from upper-triangular elements.

    Input order: [xx, yy, zz, yz, xz, xy]

    Adapted from pymatgen.util.num.make_symmetric_matrix_from_upper_tri.
    """
    xx, yy, zz, yz, xz, xy = data[:6]
    return np.array(
        [
            [xx, xy, xz],
            [xy, yy, yz],
            [xz, yz, zz],
        ]
    )


def get_angle(v1: NDArray[np.floating], v2: NDArray[np.floating]) -> float:
    """Compute the angle in degrees between two vectors.

    Adapted from pymatgen.util.coord.get_angle.
    """
    dot = np.dot(v1, v2)
    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
    if norms < 1e-12:
        return 0.0
    cosang = max(-1.0, min(1.0, dot / norms))
    return float(np.degrees(np.arccos(cosang)))


def str_delimited(
    items: list[str],
    header: str | None = None,
    delimiter: str = "|",
    width: int = 80,
) -> str:
    """Format a list of strings as a delimited block.

    Adapted from pymatgen.util.string.str_delimited.
    """
    lines = []
    if header:
        lines.append(header)
    for item in items:
        lines.append(f"{delimiter} {item}")
    return "\n".join(lines)


__all__ = [
    "Ha_to_eV",
    "clean_lines",
    "make_symmetric_matrix_from_upper_tri",
    "get_angle",
    "str_delimited",
]
