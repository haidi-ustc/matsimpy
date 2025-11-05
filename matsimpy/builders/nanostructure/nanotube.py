"""
Nanotube structure builders.

Generate nanotube structures by rolling up any 2D material sheet
into cylindrical structures. Works with graphene, transition metal
dichalcogenides (MoS2, WS2, etc.), hexagonal boron nitride (hBN),
and any other 2D crystal structure.
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
    Build a nanotube by rolling up any 2D crystal structure.
    
    This is a general function that works with any 2D material. The chirality
    indices (n, m) determine the nanotube's diameter and wrapping direction.
    
    Args:
        base_2d: 2D crystal structure to roll up (any 2D material)
                 Must have lattice vectors in the xy-plane
        chirality: Chirality indices (n, m) for the nanotube.
                  The chiral vector C = n*a1 + m*a2 determines the wrapping
        length: Length of nanotube in Angstroms (if None, uses one unit cell)
        periodic: If True, nanotube is periodic along the axis
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Nanotube structure
    
    Examples:
        >>> from matsimpy.builders.nanostructure import build_nanotube
        >>> from matsimpy.core import Crystal, Lattice
        >>> 
        >>> # Example 1: Carbon nanotube from graphene
        >>> graphene = create_graphene_sheet()  # Helper function
        >>> cnt = build_nanotube(graphene, (10, 10))
        >>> 
        >>> # Example 2: MoS2 nanotube
        >>> # Create MoS2 2D structure (simplified)
        >>> mos2_lattice = Lattice(np.array([
        ...     [3.16, 0, 0],
        ...     [1.58, 2.74, 0],
        ...     [0, 0, 10.0]
        ... ]))
        >>> mos2_2d = Crystal(['Mo', 'S', 'S'], 
        ...                   [[0, 0, 0], [1.58, 0.91, 0], [1.58, 1.83, 0]],
        ...                   mos2_lattice)
        >>> mos2_nanotube = build_nanotube(mos2_2d, (10, 10))
        >>> 
        >>> # Example 3: Hexagonal boron nitride nanotube
        >>> hbn_lattice = Lattice(np.array([
        ...     [2.50, 0, 0],
        ...     [1.25, 2.17, 0],
        ...     [0, 0, 10.0]
        ... ]))
        >>> hbn_2d = Crystal(['B', 'N'], [[0, 0, 0], [0.83, 0.48, 0]], hbn_lattice)
        >>> hbn_nanotube = build_nanotube(hbn_2d, (10, 0))  # Zigzag BN nanotube
    """
    n, m = chirality
    
    if n < 0 or m < 0:
        raise ValueError("Chirality indices must be non-negative")
    if n == 0 and m == 0:
        raise ValueError("Chirality indices cannot both be zero")
    
    # Get 2D lattice vectors (assuming they're in the xy plane)
    lattice_2d = base_2d.lattice
    a1_full = lattice_2d.lattice_vectors[0]
    a2_full = lattice_2d.lattice_vectors[1]
    
    # Extract only xy components (first 2 dimensions) for 2D operations
    a1 = a1_full[:2]
    a2 = a2_full[:2]
    
    # Calculate chiral vector C = n*a1 + m*a2 (in 2D)
    C = n * a1 + m * a2
    
    # Calculate nanotube diameter
    diameter = np.linalg.norm(C) / np.pi
    
    # Calculate translation vector T (perpendicular to C in the 2D plane)
    # T = t1*a1 + t2*a2, where t1 and t2 are integers
    # T should be the smallest vector that makes the nanotube periodic
    # For a general 2D material, we find T such that T is perpendicular to C
    # and has the smallest period along the nanotube axis
    # The general formula: T = (m*a1 - n*a2) / gcd(2n+m, 2m+n) for hexagonal lattices
    # For other lattices, we use a more general approach
    # Check if lattice is hexagonal-like (60 degree angle between a1 and a2)
    cos_angle = np.dot(a1, a2) / (np.linalg.norm(a1) * np.linalg.norm(a2))
    is_hexagonal = abs(cos_angle - 0.5) < 0.1  # cos(60°) = 0.5
    
    if is_hexagonal:
        # Use hexagonal formula
        gcd = _gcd(2 * n + m, 2 * m + n)
        if gcd != 0:
            t1 = (2 * m + n) // gcd
            t2 = -(2 * n + m) // gcd
        else:
            t1, t2 = 1, 0
    else:
        # General approach: find T perpendicular to C
        # T should satisfy: T · C = 0, and T should be a linear combination of a1, a2
        # Use perpendicular vector in 2D: if C = (Cx, Cy), then T = (-Cy, Cx)
        # But we need T in terms of a1, a2
        # For now, use a simple approximation: T ≈ (m*a1 - n*a2)
        t1 = m
        t2 = -n
    
    # Translation vector T (in 2D)
    T = t1 * a1 + t2 * a2
    T_length = np.linalg.norm(T)
    
    # Determine the nanotube axis length
    if length is None:
        axis_length = T_length
    else:
        axis_length = length
    
    # Generate atoms directly in the fundamental parallelogram defined by C and T
    # This avoids duplicate issues from supercell wrapping
    # The fundamental parallelogram contains all unique atoms for one nanotube unit cell
    
    # Get unit cell lattice vectors
    a1_full_vec = base_2d.lattice.lattice_vectors[0]
    a2_full_vec = base_2d.lattice.lattice_vectors[1]
    a1_2d = a1_full_vec[:2]  # xy components only
    a2_2d = a2_full_vec[:2]  # xy components only
    
    # Calculate how many unit cells fit in the fundamental parallelogram
    # The fundamental parallelogram area is |det(C, T)|
    # Unit cell area is |det(a1, a2)|
    unit_cell_area = abs(np.linalg.det(np.array([a1_2d, a2_2d])))
    fundamental_area = abs(np.linalg.det(np.array([C, T])))
    num_unit_cells = int(np.round(fundamental_area / unit_cell_area))
    
    # Generate atoms by tiling unit cells within the fundamental parallelogram
    # Find the range of unit cell indices needed
    # We need enough cells to cover the parallelogram
    max_cells_a1 = max(abs(n), abs(m), abs(t1)) + 2
    max_cells_a2 = max(abs(n), abs(m), abs(t2)) + 2
    
    # Collect all atoms from unit cells that fall within or overlap the fundamental region
    all_atoms = []
    for i in range(-max_cells_a1, max_cells_a1 + 1):
        for j in range(-max_cells_a2, max_cells_a2 + 1):
            # Position of this unit cell origin in cartesian
            cell_origin_2d = i * a1_2d + j * a2_2d
            
            # Add atoms from this unit cell
            for species, pos_frac in zip(base_2d.species, base_2d.positions):
                # Atom position in cartesian (2D)
                atom_pos_2d = cell_origin_2d + pos_frac[0] * a1_2d + pos_frac[1] * a2_2d
                all_atoms.append((species, atom_pos_2d))
    
    species_list = []
    positions_list = []
    
    # Build transformation matrix from (C, T) coordinates to (a1, a2) coordinates
    # We want to find coefficients (u, v) such that: pos = u*C + v*T
    # This defines the fundamental region: 0 <= u < 1, 0 <= v < 1
    # Matrix: [C_x, T_x; C_y, T_y] * [u; v] = [pos_x; pos_y]
    transform_matrix = np.array([[C[0], T[0]], [C[1], T[1]]])
    inv_transform = np.linalg.inv(transform_matrix)
    
    # Use a set to track unique (u, v) pairs to avoid duplicates
    seen_uv = set()
    
    for species, pos_2d_cart in all_atoms:
        # Convert to (C, T) coordinates  
        u_v = inv_transform @ pos_2d_cart
        
        # Wrap to fundamental region [0, 1) x [0, 1)
        u = u_v[0] % 1.0
        v = u_v[1] % 1.0
        
        # Check if this (u, v) pair has been seen (with tolerance for floating point)
        uv_rounded = (round(u, 8), round(v, 8))
        if uv_rounded in seen_uv:
            continue  # Skip duplicate
        seen_uv.add(uv_rounded)
        
        # Calculate angle around the nanotube (0 to 2π)
        # u goes from 0 to 1 along the circumference
        angle = 2 * np.pi * u
        
        # Calculate radius (constant for cylindrical nanotube)
        radius = diameter / 2
        
        # Convert to cylindrical coordinates (nanotube surface)
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        
        # z coordinate is along the translation vector
        # v goes from 0 to 1 along the axis
        if length is not None:
            z = v * length
        else:
            z = v * T_length
        
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
    
    # Create crystal with cartesian coordinates (positions are in Angstroms)
    return Crystal(species_list, positions_list, nanotube_lattice, coords_are_cartesian=True)


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
    
    This is a convenience function specifically for carbon nanotubes.
    It creates a graphene sheet and rolls it into a nanotube using the
    general build_nanotube() function.
    
    For other materials, use build_nanotube() directly with your 2D structure.
    
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
    
    # Build nanotube from graphene using the general function
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

