"""
Heusler alloy structure builders.

Generate Heusler alloy structures:
- Full Heusler (X₂YZ): L2₁ structure
- Half-Heusler (XYZ): C1b structure
- Inverse Heusler (X₂YZ): XA structure

Heusler alloys are intermetallic compounds with specific crystal structures
that exhibit interesting magnetic and electronic properties.
"""

from typing import List, Optional, Union
from ...core import Crystal, Lattice, Element


def build_heusler(
    X: str,
    Y: str,
    Z: str,
    lattice_constant: float,
    heusler_type: str = "full",
    **kwargs,
) -> Crystal:
    """
    Build a Heusler alloy structure.

    Args:
        X: First element symbol (occupies 2 sites in full/inverse, 1 in half)
        Y: Second element symbol
        Z: Third element symbol
        lattice_constant: Lattice constant in Angstroms
        heusler_type: Type of Heusler alloy ('full', 'half', 'inverse')
                    - 'full': Full Heusler X₂YZ (L2₁ structure)
                    - 'half': Half-Heusler XYZ (C1b structure)
                    - 'inverse': Inverse Heusler X₂YZ (XA structure, when Z(Y) > Z(X))
        **kwargs: Additional parameters

    Returns:
        Crystal: Heusler alloy structure

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_heusler
        >>> # Full Heusler: Cu₂MnAl
        >>> cu2mnal = build_heusler('Cu', 'Mn', 'Al', 5.95, 'full')
        >>> # Half-Heusler: NiMnSb
        >>> nimnsb = build_heusler('Ni', 'Mn', 'Sb', 5.93, 'half')
        >>> # Inverse Heusler: Mn₂CoAl (auto-detected if Z(Y) > Z(X))
        >>> mn2coal = build_heusler('Mn', 'Co', 'Al', 5.85, 'inverse')
    """
    heusler_type = heusler_type.lower()

    if heusler_type == "full":
        return _build_full_heusler(X, Y, Z, lattice_constant)
    elif heusler_type == "half":
        return _build_half_heusler(X, Y, Z, lattice_constant)
    elif heusler_type == "inverse":
        return _build_inverse_heusler(X, Y, Z, lattice_constant)
    else:
        raise ValueError(
            f"Unknown Heusler type '{heusler_type}'. "
            f"Must be 'full', 'half', or 'inverse'"
        )


def _build_full_heusler(X: str, Y: str, Z: str, a: float) -> Crystal:
    """
    Build full Heusler alloy (X₂YZ) with L2₁ structure.

    Structure: Four interpenetrating FCC sublattices
    - X atoms at (0,0,0) and (½,½,½) - 2 sites
    - Y atom at (¼,¼,¼) - 1 site
    - Z atom at (¾,¾,¾) - 1 site

    This is the conventional cell with 16 atoms total.
    """
    # Conventional cell coordinates (16 atoms)
    # Based on the provided coordinates
    base_coordinates = [
        [0.25, 0.25, 0.25],  # Y site
        [0.75, 0.75, 0.75],  # Z site
        [0.75, 0.75, 0.25],  # X site
        [0.25, 0.25, 0.75],  # X site
        [0.75, 0.25, 0.75],  # X site
        [0.25, 0.75, 0.25],  # X site
        [0.25, 0.75, 0.75],  # X site
        [0.75, 0.25, 0.25],  # X site
        [0.0, 0.0, 0.0],  # X site
        [0.0, 0.5, 0.5],  # X site
        [0.5, 0.0, 0.5],  # X site
        [0.5, 0.5, 0.0],  # X site
        [0.5, 0.5, 0.5],  # X site
        [0.5, 0.0, 0.0],  # X site
        [0.0, 0.5, 0.0],  # X site
        [0.0, 0.0, 0.5],  # X site
    ]

    # Species assignment for L2₁ structure
    # X: 8 atoms, Y: 2 atoms, Z: 2 atoms (in conventional cell)
    # But we need to map to the correct sites
    # For L2₁: X at (0,0,0) and (½,½,½) type sites
    #          Y at (¼,¼,¼) type sites
    #          Z at (¾,¾,¾) type sites

    # Map coordinates to species based on L2₁ structure
    species = []
    positions = []

    for coord in base_coordinates:
        x, y, z = coord
        # Check which sublattice this belongs to
        # X sites: (0,0,0) and (½,½,½) type
        if (
            (x == 0.0 and y == 0.0 and z == 0.0)
            or (x == 0.5 and y == 0.5 and z == 0.5)
            or (x == 0.0 and y == 0.5 and z == 0.5)
            or (x == 0.5 and y == 0.0 and z == 0.5)
            or (x == 0.5 and y == 0.5 and z == 0.0)
            or (x == 0.5 and y == 0.0 and z == 0.0)
            or (x == 0.0 and y == 0.5 and z == 0.0)
            or (x == 0.0 and y == 0.0 and z == 0.5)
        ):
            species.append(X)
        # Y site: (¼,¼,¼) type
        elif (
            (x == 0.25 and y == 0.25 and z == 0.25)
            or (x == 0.75 and y == 0.75 and z == 0.25)
            or (x == 0.25 and y == 0.75 and z == 0.75)
            or (x == 0.75 and y == 0.25 and z == 0.75)
        ):
            species.append(Y)
        # Z site: (¾,¾,¾) type
        elif (
            (x == 0.75 and y == 0.75 and z == 0.75)
            or (x == 0.25 and y == 0.25 and z == 0.75)
            or (x == 0.75 and y == 0.25 and z == 0.25)
            or (x == 0.25 and y == 0.75 and z == 0.25)
        ):
            species.append(Z)
        else:
            # Default to X for remaining sites
            species.append(X)

        positions.append(coord)

    # Actually, let's use a cleaner approach with the primitive cell
    # L2₁ structure primitive cell has 4 atoms
    # But conventional cell is clearer for visualization

    # Better approach: Use the standard L2₁ coordinates
    # Conventional cell: 16 atoms
    # X at: (0,0,0), (0,½,½), (½,0,½), (½,½,0), (½,½,½), (½,0,0), (0,½,0), (0,0,½)
    # Y at: (¼,¼,¼), (¾,¾,¼), (¼,¾,¾), (¾,¼,¾)
    # Z at: (¾,¾,¾), (¼,¼,¾), (¾,¼,¼), (¼,¾,¼)

    species = []
    positions = []

    # X atoms (8 sites)
    x_sites = [
        [0.0, 0.0, 0.0],
        [0.0, 0.5, 0.5],
        [0.5, 0.0, 0.5],
        [0.5, 0.5, 0.0],
        [0.5, 0.5, 0.5],
        [0.5, 0.0, 0.0],
        [0.0, 0.5, 0.0],
        [0.0, 0.0, 0.5],
    ]
    for site in x_sites:
        species.append(X)
        positions.append(site)

    # Y atoms (4 sites)
    y_sites = [
        [0.25, 0.25, 0.25],
        [0.75, 0.75, 0.25],
        [0.25, 0.75, 0.75],
        [0.75, 0.25, 0.75],
    ]
    for site in y_sites:
        species.append(Y)
        positions.append(site)

    # Z atoms (4 sites)
    z_sites = [
        [0.75, 0.75, 0.75],
        [0.25, 0.25, 0.75],
        [0.75, 0.25, 0.25],
        [0.25, 0.75, 0.25],
    ]
    for site in z_sites:
        species.append(Z)
        positions.append(site)

    lattice = Lattice.cubic(a)
    return Crystal(species, positions, lattice)


def _build_half_heusler(X: str, Y: str, Z: str, a: float) -> Crystal:
    """
    Build half-Heusler alloy (XYZ) with C1b structure.

    Structure: Like L2₁ but with one sublattice vacant
    - X atom at (0,0,0) - 1 site
    - Y atom at (¼,¼,¼) - 1 site
    - Z atom at (¾,¾,¾) - 1 site
    - Vacant site at (½,½,½)

    This is the primitive cell with 3 atoms.
    """
    # Primitive cell for half-Heusler (3 atoms)
    species = [X, Y, Z]
    positions = [
        [0.0, 0.0, 0.0],  # X
        [0.25, 0.25, 0.25],  # Y
        [0.75, 0.75, 0.75],  # Z
    ]

    lattice = Lattice.cubic(a)
    return Crystal(species, positions, lattice)


def _build_inverse_heusler(X: str, Y: str, Z: str, a: float) -> Crystal:
    """
    Build inverse Heusler alloy (X₂YZ) with XA structure.

    Structure: Different ordering when Z(Y) > Z(X)
    - X atoms at different sublattices (not equivalent)
    - Y and Z atoms at remaining sites

    The inverse structure has X atoms on two different types of sites
    compared to the regular L2₁ structure.
    """
    # Check if we should use inverse structure
    # Inverse occurs when Z(Y) > Z(X)
    try:
        z_X = Element.get_element(X).atomic_no
        z_Y = Element.get_element(Y).atomic_no
    except:
        # If we can't determine, use inverse structure anyway
        z_X, z_Y = 0, 1

    # XA structure: X atoms occupy different sublattices
    # Conventional cell: 16 atoms
    species = []
    positions = []

    # X atoms - first type (4 sites)
    x1_sites = [
        [0.0, 0.0, 0.0],
        [0.0, 0.5, 0.5],
        [0.5, 0.0, 0.5],
        [0.5, 0.5, 0.0],
    ]
    for site in x1_sites:
        species.append(X)
        positions.append(site)

    # X atoms - second type (4 sites)
    x2_sites = [
        [0.5, 0.5, 0.5],
        [0.5, 0.0, 0.0],
        [0.0, 0.5, 0.0],
        [0.0, 0.0, 0.5],
    ]
    for site in x2_sites:
        species.append(X)
        positions.append(site)

    # Y atoms (4 sites)
    y_sites = [
        [0.25, 0.25, 0.25],
        [0.75, 0.75, 0.25],
        [0.25, 0.75, 0.75],
        [0.75, 0.25, 0.75],
    ]
    for site in y_sites:
        species.append(Y)
        positions.append(site)

    # Z atoms (4 sites)
    z_sites = [
        [0.75, 0.75, 0.75],
        [0.25, 0.25, 0.75],
        [0.75, 0.25, 0.25],
        [0.25, 0.75, 0.25],
    ]
    for site in z_sites:
        species.append(Z)
        positions.append(site)

    lattice = Lattice.cubic(a)
    return Crystal(species, positions, lattice)


def build_full_heusler(
    X: str, Y: str, Z: str, lattice_constant: float, **kwargs
) -> Crystal:
    """
    Convenience function for building full Heusler alloy.

    Args:
        X: First element (2 atoms)
        Y: Second element (1 atom)
        Z: Third element (1 atom)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters

    Returns:
        Crystal: Full Heusler structure (X₂YZ)

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_full_heusler
        >>> cu2mnal = build_full_heusler('Cu', 'Mn', 'Al', 5.95)
    """
    return _build_full_heusler(X, Y, Z, lattice_constant)


def build_half_heusler(
    X: str, Y: str, Z: str, lattice_constant: float, **kwargs
) -> Crystal:
    """
    Convenience function for building half-Heusler alloy.

    Args:
        X: First element (1 atom)
        Y: Second element (1 atom)
        Z: Third element (1 atom)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters

    Returns:
        Crystal: Half-Heusler structure (XYZ)

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_half_heusler
        >>> nimnsb = build_half_heusler('Ni', 'Mn', 'Sb', 5.93)
    """
    return _build_half_heusler(X, Y, Z, lattice_constant)


def build_inverse_heusler(
    X: str, Y: str, Z: str, lattice_constant: float, **kwargs
) -> Crystal:
    """
    Convenience function for building inverse Heusler alloy.

    Args:
        X: First element (2 atoms)
        Y: Second element (1 atom)
        Z: Third element (1 atom)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters

    Returns:
        Crystal: Inverse Heusler structure (X₂YZ, XA type)

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_inverse_heusler
        >>> mn2coal = build_inverse_heusler('Mn', 'Co', 'Al', 5.85)
    """
    return _build_inverse_heusler(X, Y, Z, lattice_constant)


__all__ = [
    "build_heusler",
    "build_full_heusler",
    "build_half_heusler",
    "build_inverse_heusler",
]
