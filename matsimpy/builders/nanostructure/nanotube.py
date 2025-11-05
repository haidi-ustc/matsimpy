"""
Nanotube structure builders.

Generate nanotube structures by rolling up 2D sheets (graphene, etc.)
into cylindrical structures.
"""

from typing import List, Tuple, Optional, Union
import numpy as np
from ...core import Crystal, Lattice


def build_nanotube(
    base_2d: Crystal,
    chirality: Tuple[int, int],
    length: Optional[float] = None,
    periodic: bool = True,
    **kwargs
) -> Crystal:
    """
    Build a nanotube by rolling up a 2D structure.
    
    For carbon nanotubes, use graphene as base_2d with chirality (n, m).
    The chirality indices determine the nanotube's diameter and electronic properties.
    
    Args:
        base_2d: 2D crystal structure to roll up (e.g., graphene)
        chirality: Chirality indices (n, m) for the nanotube
        length: Length of nanotube in Angstroms (if None, uses one unit cell)
        periodic: If True, nanotube is periodic along the axis
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Nanotube structure
    
    Examples:
        >>> from matsimpy.builders.nanostructure import build_nanotube
        >>> from matsimpy.builders.bulk import from_prototype
        >>> 
        >>> # Create graphene (simplified 2D structure)
        >>> # In practice, you'd use a proper graphene builder
        >>> graphene = create_graphene_sheet()
        >>> 
        >>> # Build (10, 10) armchair nanotube
        >>> cnt = build_nanotube(graphene, (10, 10))
        >>> 
        >>> # Build (10, 0) zigzag nanotube
        >>> zigzag = build_nanotube(graphene, (10, 0))
        >>> 
        >>> # Build chiral (7, 3) nanotube
        >>> chiral = build_nanotube(graphene, (7, 3))
    """
    n, m = chirality
    
    if n < 0 or m < 0:
        raise ValueError("Chirality indices must be non-negative")
    if n == 0 and m == 0:
        raise ValueError("Chirality indices cannot both be zero")
    
    # Get 2D lattice vectors (assuming they're in the xy plane)
    lattice_2d = base_2d.lattice
    a1, a2 = lattice_2d.lattice_vectors[0], lattice_2d.lattice_vectors[1]
    
    # Calculate chiral vector C = n*a1 + m*a2
    C = n * a1 + m * a2
    
    # Calculate nanotube diameter
    diameter = np.linalg.norm(C) / np.pi
    
    # Calculate translation vector T (perpendicular to C in the 2D plane)
    # T = t1*a1 + t2*a2, where t1 and t2 are integers
    # T should be the smallest vector that makes the nanotube periodic
    # For simplicity, we'll use a method to find T
    gcd = _gcd(2 * n + m, 2 * m + n)
    if gcd != 0:
        t1 = (2 * m + n) // gcd
        t2 = -(2 * n + m) // gcd
    else:
        t1, t2 = 1, 0
    
    T = t1 * a1 + t2 * a2
    T_length = np.linalg.norm(T)
    
    # Determine the nanotube axis length
    if length is None:
        axis_length = T_length
    else:
        axis_length = length
    
    # Roll up the 2D structure
    species_list = []
    positions_list = []
    
    for i, (species, pos_2d) in enumerate(zip(base_2d.species, base_2d.positions)):
        # Project position onto chiral vector
        # Calculate angle around the nanotube
        proj_on_C = np.dot(pos_2d, C) / (np.linalg.norm(C) ** 2)
        angle = 2 * np.pi * proj_on_C / np.linalg.norm(C)
        
        # Calculate radius at this position
        # For a perfect roll-up, radius = diameter / 2
        radius = diameter / 2
        
        # Convert to cylindrical coordinates
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        
        # z coordinate is the projection onto T (translation vector)
        z = np.dot(pos_2d, T) / T_length
        
        # Scale z to desired length
        if length is not None:
            z = z * (length / T_length)
        
        positions_list.append([x, y, z])
        species_list.append(species)
    
    # Create nanotube lattice
    # The lattice vectors are: [circumference direction, T direction, perpendicular]
    # For a nanotube, we use a rectangular-like lattice
    if periodic:
        # Periodic along the axis
        c_length = axis_length
    else:
        # Add some vacuum in z-direction
        c_length = axis_length + 10.0  # 10 Angstrom vacuum
    
    # Create lattice for nanotube
    # Use a rectangular lattice with the nanotube axis as c
    # Note: using orthorhomic (typo in Lattice class) or manual construction
    try:
        nanotube_lattice = Lattice.orthorhomic(
            a=np.pi * diameter,  # Circumference
            b=np.pi * diameter,  # Perpendicular (for periodic boundary)
            c=c_length  # Axis direction
        )
    except AttributeError:
        # Fallback: create lattice manually
        lattice_vectors = np.array([
            [np.pi * diameter, 0, 0],  # Circumference direction
            [0, np.pi * diameter, 0],  # Perpendicular (for periodic boundary)
            [0, 0, c_length]  # Axis direction
        ])
        nanotube_lattice = Lattice(lattice_vectors)
    
    return Crystal(species_list, positions_list, nanotube_lattice)


def build_carbon_nanotube(
    n: int,
    m: int,
    bond_length: float = 1.42,
    length: Optional[float] = None,
    periodic: bool = True,
    **kwargs
) -> Crystal:
    """
    Build a carbon nanotube from chirality indices.
    
    This is a convenience function that creates graphene and rolls it into a nanotube.
    
    Args:
        n: First chirality index
        m: Second chirality index
        bond_length: C-C bond length in Angstroms (default: 1.42)
        length: Length of nanotube in Angstroms (if None, uses one unit cell)
        periodic: If True, nanotube is periodic along the axis
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Carbon nanotube structure
    
    Examples:
        >>> from matsimpy.builders.nanostructure import build_carbon_nanotube
        >>> 
        >>> # Armchair (5, 5) nanotube
        >>> armchair = build_carbon_nanotube(5, 5)
        >>> 
        >>> # Zigzag (10, 0) nanotube
        >>> zigzag = build_carbon_nanotube(10, 0)
        >>> 
        >>> # Chiral (7, 3) nanotube
        >>> chiral = build_carbon_nanotube(7, 3)
    """
    # Create a simple graphene sheet
    # For a proper implementation, we'd use a graphene builder
    # Here we create a minimal graphene unit cell
    graphene = _create_graphene_sheet(bond_length)
    
    # Build nanotube from graphene
    return build_nanotube(graphene, (n, m), length=length, periodic=periodic, **kwargs)


def _create_graphene_sheet(bond_length: float = 1.42) -> Crystal:
    """
    Create a simple graphene sheet structure.
    
    This is a helper function that creates a minimal graphene unit cell.
    For a more accurate graphene structure, use a dedicated graphene builder.
    
    Args:
        bond_length: C-C bond length in Angstroms
    
    Returns:
        Crystal: Graphene sheet structure
    """
    # Graphene unit cell: 2 atoms in a hexagonal arrangement
    # Lattice vectors
    a = bond_length * np.sqrt(3)  # Lattice parameter
    a1 = np.array([a, 0, 0])
    a2 = np.array([a / 2, a * np.sqrt(3) / 2, 0])
    
    # Create 2D lattice
    lattice_2d = Lattice(np.array([
        a1,
        a2,
        [0, 0, 10.0]  # Large c for 2D structure
    ]))
    
    # Two carbon atoms in graphene unit cell
    species = ['C', 'C']
    positions = [
        [0.0, 0.0, 0.0],
        [a / 3, a / np.sqrt(3) / 3, 0.0]
    ]
    
    return Crystal(species, positions, lattice_2d)


def _gcd(a: int, b: int) -> int:
    """Calculate greatest common divisor."""
    while b:
        a, b = b, a % b
    return abs(a)


__all__ = ['build_nanotube', 'build_carbon_nanotube']

