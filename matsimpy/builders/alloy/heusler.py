"""
Heusler alloy structure builders.

Generate Heusler alloy structures:
- Full Heusler (X₂YZ): L2₁ structure (Fm-3m, No. 225)
- Half-Heusler (XYZ): C1b structure (F-43m, No. 216)
- Inverse Heusler (X₂YZ): XA structure (I-4m2, No. 119)

Heusler alloys are intermetallic compounds with specific crystal structures
that exhibit interesting magnetic and electronic properties.
"""

from ...core import Crystal, Lattice


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
        X: First element symbol (occupies different sites based on type)
        Y: Second element symbol
        Z: Third element symbol
        lattice_constant: Lattice constant in Angstroms
        heusler_type: Type of Heusler alloy ('full', 'half', 'inverse')
                    - 'full': Full Heusler X₂YZ (L2₁ structure, Fm-3m, No. 225)
                    - 'half': Half-Heusler XYZ (C1b structure, F-43m, No. 216)
                    - 'inverse': Inverse Heusler X₂YZ (XA structure, I-4m2, No. 119)
        **kwargs: Additional parameters

    Returns:
        Crystal: Heusler alloy structure

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_heusler
        >>> # Full Heusler: X=Mn, Y=Fe, Z=I
        >>> full = build_heusler('Mn', 'Fe', 'I', 6.0, 'full')
        >>> # Half-Heusler: X=Fe, Y=Mn, Z=I
        >>> half = build_heusler('Fe', 'Mn', 'I', 6.0, 'half')
        >>> # Inverse Heusler: X=Mn, Y=Cr, Z=Fe, I=I (quaternary)
        >>> inverse = build_heusler('Mn', 'Cr', 'Fe', 6.0, 'inverse')
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

    Space group: Fm-3m (No. 225)
    Conventional cell (FCC, 16 atoms total):
    - X atoms at 4a: (0.0, 0.0, 0.0) + FCC = 4 atoms
    - X atoms at 4d: (0.75, 0.75, 0.75) + FCC = 4 atoms (total 8 X)
    - Y atoms at 4c: (0.25, 0.25, 0.25) + FCC = 4 atoms
    - Z atoms at 4b: (0.5, 0.5, 0.5) + FCC = 4 atoms

    Based on template: X=Mn, Y=Fe, Z=I
    Note: In L2₁ structure, X₂ means X occupies both 4a and 4d sites.
    """
    species = []
    positions = []
    
    # X atoms at 4a sites (0, 0, 0) - first set of X atoms
    for x, y, z in [
        (0.0, 0.0, 0.0),  # Base position
        (0.0, 0.5, 0.5),  # + FCC translation
        (0.5, 0.0, 0.5),  # + FCC translation
        (0.5, 0.5, 0.0),  # + FCC translation
    ]:
        species.append(X)
        positions.append([x, y, z])
    
    # X atoms at 4d sites (0.75, 0.75, 0.75) - second set of X atoms
    for x, y, z in [
        (0.75, 0.75, 0.75), (0.75, 0.25, 0.25),
        (0.25, 0.75, 0.25), (0.25, 0.25, 0.75),
    ]:
        species.append(X)
        positions.append([x, y, z])
    
    # Y atoms at 4c sites (1/4, 1/4, 1/4)
    for x, y, z in [
        (0.25, 0.25, 0.25), (0.25, 0.75, 0.75),
        (0.75, 0.25, 0.75), (0.75, 0.75, 0.25),
    ]:
        species.append(Y)
        positions.append([x, y, z])
    
    # Z atoms at 4b sites (1/2, 1/2, 1/2)
    for x, y, z in [
        (0.5, 0.5, 0.5),  # Base position
        (0.5, 0.0, 0.0),  # + FCC translation
        (0.0, 0.5, 0.0),  # + FCC translation
        (0.0, 0.0, 0.5),  # + FCC translation
    ]:
        species.append(Z)
        positions.append([x, y, z])
    
    lattice = Lattice.cubic(a)
    return Crystal(species, positions, lattice)


def _build_half_heusler(X: str, Y: str, Z: str, a: float) -> Crystal:
    """
    Build half-Heusler alloy (XYZ) with C1b structure.
    
    Space group: F-43m (No. 216)
    Primitive cell (3 atoms total):
    - X atoms at 4a: (0.0, 0.0, 0.0) - 1 atom in primitive
    - Z atoms at 4b: (0.5, 0.5, 0.5) - 1 atom in primitive
    - Y atoms at 4c: (0.25, 0.25, 0.25) - 1 atom in primitive
    
    Based on template: X=Fe, Y=Mn, Z=I
    Note: Returns primitive cell with 3 atoms, not conventional cell.
    """
    species = []
    positions = []
    
    # X atoms at 4a sites (0, 0, 0) - 1 atom in primitive cell
    species.append(X)
    positions.append([0.0, 0.0, 0.0])
    
    # Y atoms at 4c sites (1/4, 1/4, 1/4) - 1 atom in primitive cell
    species.append(Y)
    positions.append([0.25, 0.25, 0.25])
    
    # Z atoms at 4b sites (1/2, 1/2, 1/2) - 1 atom in primitive cell
    species.append(Z)
    positions.append([0.5, 0.5, 0.5])
    
    lattice = Lattice.cubic(a)
    return Crystal(species, positions, lattice)


def _build_inverse_heusler(X: str, Y: str, Z: str, a: float) -> Crystal:
    """
    Build inverse Heusler alloy (X₂YZ) with XA structure.
    
    Space group: I-4m2 (No. 119)
    Body-centered tetragonal lattice (I lattice)
    Conventional cell (16 atoms total):
    - X atoms at 2a: (0.0, 0.0, 0.0) + I translations = 2 atoms
    - X atoms at 2b: (0.0, 0.0, 0.5) + I translations = 2 atoms (total 4 X in primitive)
    - Y atoms at 2c: (0.0, 0.5, 0.25) + I translations = 2 atoms
    - Z atoms at 2d: (0.0, 0.5, 0.75) + I translations = 2 atoms
    
    To get conventional cell (16 atoms), create 2×2×2 supercell of primitive (8 atoms).
    Based on template: X=Mn, Y=Cr, Z=Fe
    """
    species = []
    positions = []
    
    # For inverse Heusler X₂YZ:
    # X at 2a and 2b (same element, X₂)
    # Y at 2c
    # Z at 2d
    
    # Create conventional cell directly with 16 atoms
    # X atoms at 2a sites (0, 0, 0) - 4 atoms in conventional cell
    for x, y, z in [
        (0.0, 0.0, 0.0), (0.5, 0.5, 0.5),  # Body centering
        (0.5, 0.0, 0.0), (0.0, 0.5, 0.5),  # Additional translations
    ]:
        species.append(X)
        positions.append([x, y, z])
    
    # X atoms at 2b sites (0, 0, 0.5) - 4 atoms in conventional cell
    for x, y, z in [
        (0.0, 0.0, 0.5), (0.5, 0.5, 0.0),  # Body centering
        (0.5, 0.0, 0.5), (0.0, 0.5, 0.0),  # Additional translations
    ]:
        species.append(X)
        positions.append([x, y, z])
    
    # Y atoms at 2c sites (0, 0.5, 0.25) - 4 atoms in conventional cell
    for x, y, z in [
        (0.0, 0.5, 0.25), (0.5, 0.0, 0.75),  # Body centering
        (0.5, 0.5, 0.25), (0.0, 0.0, 0.75),  # Additional translations
    ]:
        species.append(Y)
        positions.append([x, y, z])
    
    # Z atoms at 2d sites (0, 0.5, 0.75) - 4 atoms in conventional cell
    for x, y, z in [
        (0.0, 0.5, 0.75), (0.5, 0.0, 0.25),  # Body centering
        (0.5, 0.5, 0.75), (0.0, 0.0, 0.25),  # Additional translations
    ]:
        species.append(Z)
        positions.append([x, y, z])
    
    # Create body-centered tetragonal lattice
    # For I-4m2, it's actually body-centered tetragonal
    # But template shows a=b=c, so it's actually cubic in this case
    lattice = Lattice.cubic(a)
    
    return Crystal(species, positions, lattice)


def build_inverse_heusler_quaternary(
    X1: str,
    X2: str, 
    Y: str,
    Z: str,
    lattice_constant: float,
    **kwargs,
) -> Crystal:
    """
    Build quaternary inverse Heusler alloy (X1X2YZ) with XA structure.
    
    Space group: I-4m2 (No. 119)
    For cases like the template: X1=Mn, X2=I, Y=Cr, Z=Fe
    
    Args:
        X1: First element at 2a sites (0, 0, 0)
        X2: Second element at 2b sites (0, 0, 0.5)  
        Y: Third element at 2c sites (0, 0.5, 0.25)
        Z: Fourth element at 2d sites (0, 0.5, 0.75)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Quaternary inverse Heusler structure
    """
    species = []
    positions = []
    
    # X1 atoms at 2a sites (0, 0, 0)
    for x, y, z in [
        (0.0, 0.0, 0.0),
        (0.5, 0.5, 0.5),  # Body centering
    ]:
        species.append(X1)
        positions.append([x, y, z])
    
    # X2 atoms at 2b sites (0, 0, 0.5)
    for x, y, z in [
        (0.0, 0.0, 0.5),
        (0.5, 0.5, 0.0),  # Body centering
    ]:
        species.append(X2)
        positions.append([x, y, z])
    
    # Y atoms at 2c sites (0, 0.5, 0.25)
    for x, y, z in [
        (0.0, 0.5, 0.25),
        (0.5, 0.0, 0.75),  # Body centering
    ]:
        species.append(Y)
        positions.append([x, y, z])
    
    # Z atoms at 2d sites (0, 0.5, 0.75)
    for x, y, z in [
        (0.0, 0.5, 0.75),
        (0.5, 0.0, 0.25),  # Body centering
    ]:
        species.append(Z)
        positions.append([x, y, z])
    
    lattice = Lattice.cubic(lattice_constant)
    return Crystal(species, positions, lattice)


def build_full_heusler(
    X: str,
    Y: str,
    Z: str,
    lattice_constant: float,
    **kwargs,
) -> Crystal:
    """
    Convenience function for building full Heusler alloy.

    Args:
        X: First element (at 4a sites)
        Y: Second element (at 8c sites)
        Z: Third element (at 4b sites)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters

    Returns:
        Crystal: Full Heusler structure (X₂YZ)

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_full_heusler
        >>> # Based on template: Mn₂FeI
        >>> full = build_full_heusler('Mn', 'Fe', 'I', 6.0)
    """
    return _build_full_heusler(X, Y, Z, lattice_constant)


def build_half_heusler(
    X: str,
    Y: str,
    Z: str,
    lattice_constant: float,
    **kwargs,
) -> Crystal:
    """
    Convenience function for building half-Heusler alloy.

    Args:
        X: First element (at 4a sites)
        Y: Second element (at 4c sites)
        Z: Third element (at 4b sites)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters

    Returns:
        Crystal: Half-Heusler structure (XYZ)

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_half_heusler
        >>> # Based on template: FeMnI
        >>> half = build_half_heusler('Fe', 'Mn', 'I', 6.0)
    """
    return _build_half_heusler(X, Y, Z, lattice_constant)


def build_inverse_heusler(
    X: str,
    Y: str,
    Z: str,
    lattice_constant: float,
    **kwargs,
) -> Crystal:
    """
    Convenience function for building ternary inverse Heusler alloy.

    Args:
        X: First element (at both 2a and 2b sites, X₂)
        Y: Second element (at 2c sites)
        Z: Third element (at 2d sites)
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters

    Returns:
        Crystal: Inverse Heusler structure (X₂YZ)

    Examples:
        >>> from matsimpy.builders.alloy.heusler import build_inverse_heusler
        >>> # Based on common inverse Heuslers: Mn₂CoAl
        >>> inverse = build_inverse_heusler('Mn', 'Co', 'Al', 6.0)
    """
    return _build_inverse_heusler(X, Y, Z, lattice_constant)



__all__ = [
    "build_heusler",
    "build_full_heusler",
    "build_half_heusler",
    "build_inverse_heusler",
    "build_inverse_heusler_quaternary",
]