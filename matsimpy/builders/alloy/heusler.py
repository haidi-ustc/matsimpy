"""
Heusler alloy structure builders.

All Heusler structures are four interpenetrating fcc sublattices along the cube
diagonal of the conventional cubic cell, at the Wyckoff positions of F-43m:

    4a (0, 0, 0)   4c (1/4, 1/4, 1/4)   4b (1/2, 1/2, 1/2)   4d (3/4, 3/4, 3/4)

- Full Heusler X2YZ (L2_1, Cu2MnAl type, Fm-3m No. 225): X on 4c and 4d, Y on 4a, Z on 4b.
- Half-Heusler XYZ (C1_b, MgAgAs type, F-43m No. 216): X on 4c, Y on 4a, Z on 4b, 4d empty.
- Inverse Heusler X2YZ (XA, Hg2CuTi type, F-43m No. 216): X on 4a and 4c, Y on 4b, Z on 4d.
- Quaternary Heusler XX'YZ (Y type, LiMgPdSn type, F-43m No. 216): X on 4c, X' on 4d,
  Y on 4b, Z on 4a.

The builders return the conventional cubic cell (16 atoms, 12 for half-Heusler).
"""

from typing import Dict, Optional

import numpy as np

from matsimpy.utils.tooling import tool

from ...core import Crystal, Lattice

__all__ = [
    "build_heusler",
    "build_full_heusler",
    "build_half_heusler",
    "build_inverse_heusler",
    "build_inverse_heusler_quaternary",
    "build_quaternary_heusler",
]

_SITES = {"4a": 0.0, "4c": 0.25, "4b": 0.5, "4d": 0.75}
_FCC = np.array([[0, 0, 0], [0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]])


def _heusler(occupation: Dict[str, Optional[str]], lattice_constant: float) -> Crystal:
    if isinstance(lattice_constant, bool) or not np.isfinite(lattice_constant) or lattice_constant <= 0:
        raise ValueError(f"lattice_constant must be positive, got {lattice_constant}")
    species, positions = [], []
    for site, element in occupation.items():
        if element is None:
            continue
        if not isinstance(element, str) or not element:
            raise ValueError(f"element symbols must be non-empty strings, got {element!r}")
        offset = _SITES[site]
        for translation in _FCC:
            species.append(element)
            positions.append(((translation + offset) % 1.0).tolist())
    return Crystal(species, positions, Lattice.cubic(lattice_constant))


@tool
def build_heusler(
    X: str,
    Y: str,
    Z: str,
    lattice_constant: float,
    heusler_type: str = "full",
) -> Crystal:
    """
    Build a Heusler alloy in its conventional cubic cell.

    Args:
        X: The doubled element of X2YZ (the first element of XYZ for half-Heusler)
        Y: Second element
        Z: Third (main-group) element
        lattice_constant: Cubic lattice constant in Angstroms
        heusler_type: 'full' (X2YZ, L2_1, Fm-3m), 'half' (XYZ, C1_b, F-43m) or
            'inverse' (X2YZ, XA / Hg2CuTi type, F-43m)

    Returns:
        Crystal: 16 atoms (12 for half-Heusler)

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_heusler
        >>> build_heusler('Cu', 'Mn', 'Al', 5.95, 'full').formula
        'Cu8Mn4Al4'
        >>> build_heusler('Ni', 'Mn', 'Sb', 5.92, 'half').formula
        'Ni4Mn4Sb4'
        >>> build_heusler('Mn', 'Co', 'Al', 5.80, 'inverse').formula
        'Mn8Co4Al4'
    """
    builders = {"full": build_full_heusler, "half": build_half_heusler, "inverse": build_inverse_heusler}
    kind = heusler_type.lower() if isinstance(heusler_type, str) else heusler_type
    if kind not in builders:
        raise ValueError(f"Unknown Heusler type '{heusler_type}'. Must be 'full', 'half', or 'inverse'")
    return builders[kind](X, Y, Z, lattice_constant)


@tool
def build_full_heusler(X: str, Y: str, Z: str, lattice_constant: float) -> Crystal:
    """
    Full Heusler X2YZ: L2_1 (Cu2MnAl type), space group Fm-3m (No. 225).

    Args:
        X: Element on 4c and 4d (1/4 and 3/4 along the cube diagonal), the "2" of X2YZ
        Y: Element on 4a (0, 0, 0)
        Z: Element on 4b (1/2, 1/2, 1/2)
        lattice_constant: Cubic lattice constant in Angstroms

    Returns:
        Crystal: Conventional cell with 16 atoms

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_full_heusler
        >>> build_full_heusler('Co', 'Mn', 'Si', 5.65).formula
        'Co8Mn4Si4'
    """
    return _heusler({"4c": X, "4d": X, "4a": Y, "4b": Z}, lattice_constant)


@tool
def build_half_heusler(X: str, Y: str, Z: str, lattice_constant: float) -> Crystal:
    """
    Half-Heusler XYZ: C1_b (MgAgAs type), space group F-43m (No. 216).

    Args:
        X: Element on 4c (1/4, 1/4, 1/4), tetrahedrally coordinated by Y and Z
        Y: Element on 4a (0, 0, 0)
        Z: Element on 4b (1/2, 1/2, 1/2); Y and Z form a rocksalt lattice
        lattice_constant: Cubic lattice constant in Angstroms

    Returns:
        Crystal: Conventional cell with 12 atoms (4d is empty)

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_half_heusler
        >>> build_half_heusler('Ni', 'Mn', 'Sb', 5.92).formula
        'Ni4Mn4Sb4'
    """
    return _heusler({"4c": X, "4a": Y, "4b": Z}, lattice_constant)


@tool
def build_inverse_heusler(X: str, Y: str, Z: str, lattice_constant: float) -> Crystal:
    """
    Inverse Heusler X2YZ: XA (Hg2CuTi type), space group F-43m (No. 216).

    Unlike the full Heusler, the two X sites are nearest neighbours.

    Args:
        X: Element on 4a (0, 0, 0) and 4c (1/4, 1/4, 1/4)
        Y: Element on 4b (1/2, 1/2, 1/2)
        Z: Element on 4d (3/4, 3/4, 3/4)
        lattice_constant: Cubic lattice constant in Angstroms

    Returns:
        Crystal: Conventional cell with 16 atoms

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_inverse_heusler
        >>> build_inverse_heusler('Mn', 'Co', 'Al', 5.80).formula
        'Mn8Co4Al4'
    """
    return _heusler({"4a": X, "4c": X, "4b": Y, "4d": Z}, lattice_constant)


@tool
def build_quaternary_heusler(X: str, X2: str, Y: str, Z: str, lattice_constant: float) -> Crystal:
    """
    Quaternary Heusler XX'YZ: Y type (LiMgPdSn type), space group F-43m (No. 216).

    Args:
        X: Element on 4c (1/4, 1/4, 1/4)
        X2: Element X' on 4d (3/4, 3/4, 3/4)
        Y: Element on 4b (1/2, 1/2, 1/2)
        Z: Element on 4a (0, 0, 0)
        lattice_constant: Cubic lattice constant in Angstroms

    Returns:
        Crystal: Conventional cell with 16 atoms

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_quaternary_heusler
        >>> build_quaternary_heusler('Co', 'Fe', 'Mn', 'Si', 5.66).formula
        'Co4Fe4Mn4Si4'
    """
    return _heusler({"4c": X, "4d": X2, "4b": Y, "4a": Z}, lattice_constant)


def build_inverse_heusler_quaternary(X1: str, X2: str, Y: str, Z: str, lattice_constant: float) -> Crystal:
    """Deprecated name of :func:`build_quaternary_heusler`, with X1 = X."""
    return build_quaternary_heusler(X1, X2, Y, Z, lattice_constant)
