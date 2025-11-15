"""
Nanotube structure builders.

Generate nanotube structures by rolling up any 2D material sheet
into cylindrical structures. Works with graphene, transition metal
dichalcogenides (MoS2, WS2, etc.), hexagonal boron nitride (hBN),
and any other 2D crystal structure.
"""

from typing import List, Tuple, Optional, Union
from math import sqrt, gcd, atan2, sin, cos, pi
import numpy as np
from ...core import Crystal, Lattice


def build_nanotube(
    base_2d: Crystal,
    chirality: Tuple[int, int],
    length: Optional[float] = None,
    periodic: bool = True,
    center: bool = True,
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
        center: If True, center the nanotube at origin (default: True)
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
    
    # Extract 2D lattice vectors from the base structure
    lattice_2d = base_2d.lattice
    a1_3d = lattice_2d.lattice_vectors[0]
    a2_3d = lattice_2d.lattice_vectors[1]
    
    # Work with 2D projections (xy plane)
    a1 = a1_3d[:2]
    a2 = a2_3d[:2]
    
    # Compute the chiral vector: C = n*a1 + m*a2
    # This vector wraps around the tube circumference
    chiral_vec = n * a1 + m * a2
    circumference = np.linalg.norm(chiral_vec)
    radius = circumference / (2 * pi)
    
    # Find the translational vector T perpendicular to C
    # T defines the repeat unit along the tube axis
    # For general 2D lattices, we find T = t1*a1 + t2*a2 such that T·C = 0
    translation_vec, t1, t2 = _find_translation_vector(a1, a2, n, m)
    tube_period = np.linalg.norm(translation_vec)
    
    # Determine how many unit cells to generate
    if length is None:
        axial_length = tube_period
        num_periods = 1
    else:
        num_periods = max(1, int(np.ceil(length / tube_period)))
        axial_length = num_periods * tube_period
    
    # Create a coordinate system for the nanotube
    # x_hat: along chiral direction (circumference)
    # y_hat: along translation direction (axis)
    x_hat = chiral_vec / circumference
    y_hat = translation_vec / tube_period
    
    # Compute the transformation matrix: 2D sheet coords -> (circumferential, axial)
    transform = np.column_stack([x_hat, y_hat])
    
    # Generate the nanotube by tiling and wrapping the 2D structure
    species_list = []
    positions_list = []
    
    # Determine how many 2D unit cells we need to cover the nanotube unit cell
    # The nanotube unit cell in 2D sheet coords is the parallelogram defined by C and T
    sheet_area = abs(np.cross(a1, a2))
    nanotube_area = abs(np.cross(chiral_vec, translation_vec))
    num_unit_cells = int(np.round(nanotube_area / sheet_area))
    
    # Generate atoms by tiling the 2D structure
    # We need to tile enough to cover the nanotube unit cell plus some margin
    max_range = max(abs(n), abs(m), abs(t1), abs(t2)) + 3
    
    seen_positions = set()
    tolerance = 1e-6
    
    for i in range(-max_range, max_range + 1):
        for j in range(-max_range, max_range + 1):
            # Offset for this unit cell replica
            cell_offset_2d = i * a1 + j * a2
            
            # Process each atom in the base unit cell
            for species, frac_pos in zip(base_2d.species, base_2d.positions):
                # Convert fractional to Cartesian in 2D
                atom_pos_2d = cell_offset_2d + frac_pos[0] * a1 + frac_pos[1] * a2
                
                # Transform to (circumferential, axial) coordinates
                circ_axial = transform.T @ atom_pos_2d
                u = circ_axial[0] / circumference  # Fraction around circumference
                v = circ_axial[1] / tube_period     # Fraction along axis
                
                # Wrap to fundamental domain [0, 1) × [0, 1)
                u = u % 1.0
                v = v % 1.0
                
                # Check for duplicates using rounded coordinates
                pos_key = (round(u, 9), round(v, 9))
                if pos_key in seen_positions:
                    continue
                seen_positions.add(pos_key)
                
                # Convert to cylindrical coordinates
                theta = 2 * pi * u
                z_base = v * tube_period
                
                # Create 3D position on cylinder surface
                x = radius * cos(theta)
                y = radius * sin(theta)
                
                # Replicate along the axis for the requested length
                for period_idx in range(num_periods):
                    z = z_base + period_idx * tube_period
                    positions_list.append([x, y, z])
                    species_list.append(species)
    
    # Create the nanotube lattice
    if periodic:
        cell_c = axial_length
    else:
        cell_c = axial_length + 10.0  # Add vacuum for non-periodic
    
    # Box size should contain the nanotube with some margin
    box_size = 2 * radius + 10.0
    
    try:
        nanotube_lattice = Lattice.orthorhombic(a=box_size, b=box_size, c=cell_c)
    except AttributeError:
        lattice_vecs = np.array([
            [box_size, 0, 0],
            [0, box_size, 0],
            [0, 0, cell_c]
        ])
        nanotube_lattice = Lattice(lattice_vecs)
    
    # Create the Crystal object
    nanotube = Crystal(
        species_list, 
        positions_list, 
        nanotube_lattice, 
        coords_are_cartesian=True
    )
    
    # Center the structure if requested
    if center:
        positions_array = np.array(positions_list)
        center_xy = np.mean(positions_array[:, :2], axis=0)
        center_z = np.mean(positions_array[:, 2])
        
        shift = [-center_xy[0], -center_xy[1], -center_z]
        
        from ...transformation.geometric import translate
        nanotube = translate(nanotube, shift, inplace=False)
    
    return nanotube


def _find_translation_vector(
    a1: np.ndarray, 
    a2: np.ndarray, 
    n: int, 
    m: int
) -> Tuple[np.ndarray, int, int]:
    """
    Find the translational vector T perpendicular to the chiral vector C.
    
    The translation vector T = t1*a1 + t2*a2 must satisfy:
    1. T · C = 0 (perpendicular to chiral vector)
    2. T should be the smallest such vector (defines minimal unit cell)
    
    Args:
        a1, a2: 2D lattice vectors
        n, m: Chirality indices
    
    Returns:
        Tuple of (T vector, t1 coefficient, t2 coefficient)
    """
    # Chiral vector
    C = n * a1 + m * a2
    
    # For hexagonal lattices, there's a known formula
    # Check if this is approximately hexagonal
    cos_angle = np.dot(a1, a2) / (np.linalg.norm(a1) * np.linalg.norm(a2))
    is_hexagonal = abs(cos_angle - 0.5) < 0.15  # cos(60°) = 0.5
    
    if is_hexagonal and abs(np.linalg.norm(a1) - np.linalg.norm(a2)) < 0.1:
        # Use specialized formula for hexagonal lattices
        d = gcd(n, m)
        if d == 0:
            d = 1
        
        # Determine symmetry
        if (n - m) % (3 * d) == 0:
            dR = 3 * d
        else:
            dR = d
        
        t1 = (2 * m + n) // dR
        t2 = -(2 * n + m) // dR
    else:
        # General approach: find smallest T perpendicular to C
        # We search for integer coefficients t1, t2 that minimize |T|
        # subject to T · C = 0
        
        # T · C = 0 means: (t1*a1 + t2*a2) · (n*a1 + m*a2) = 0
        # Expanding: t1*n*(a1·a1) + t1*m*(a1·a2) + t2*n*(a2·a1) + t2*m*(a2·a2) = 0
        # Simplifying: t1*n*|a1|² + (t1*m + t2*n)*(a1·a2) + t2*m*|a2|² = 0
        
        # For a first approximation, use the perpendicular in 2D space
        # If C = (Cx, Cy), then perpendicular is (-Cy, Cx)
        perp = np.array([-C[1], C[0]])
        
        # Express perpendicular in terms of a1, a2
        # Solve: t1*a1 + t2*a2 ≈ perp
        A = np.column_stack([a1, a2])
        try:
            coeffs = np.linalg.solve(A, perp)
            t1 = round(coeffs[0])
            t2 = round(coeffs[1])
            
            # Ensure we have a non-zero vector
            if t1 == 0 and t2 == 0:
                t1 = -m if m != 0 else 1
                t2 = n
        except np.linalg.LinAlgError:
            # Fallback for singular matrices
            t1 = -m if m != 0 else 1
            t2 = n
    
    T = t1 * a1 + t2 * a2
    return T, t1, t2


def build_carbon_nanotube(
    n: int,
    m: int,
    bond_length: float = 1.42,
    length: Optional[float] = None,
    periodic: bool = True,
    center: bool = True,
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
        center: If True, center the nanotube at origin (default: True)
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
    graphene = _create_graphene_sheet(bond_length)
    return build_nanotube(graphene, (n, m), length=length, periodic=periodic, 
                         center=center, **kwargs)


def _create_graphene_sheet(bond_length: float = 1.42) -> Crystal:
    """
    Create a graphene sheet structure.
    
    Args:
        bond_length: C-C bond length in Angstroms
    
    Returns:
        Crystal: Graphene sheet structure with proper hexagonal unit cell
    """
    # Graphene lattice parameter
    a = sqrt(3.0) * bond_length
    
    # Hexagonal lattice vectors
    a1 = np.array([a, 0.0, 0.0])
    a2 = np.array([0.5 * a, 0.5 * sqrt(3) * a, 0.0])
    a3 = np.array([0.0, 0.0, 10.0])  # Vacuum in z direction
    
    lattice = Lattice(np.array([a1, a2, a3]))
    
    # Two carbon atoms per unit cell (A and B sublattices)
    species = ['C', 'C']
    
    # Positions in fractional coordinates
    # These are the standard positions for graphene's hexagonal unit cell
    positions = [
        [0.0, 0.0, 0.0],           # A sublattice
        [1.0/3.0, 1.0/3.0, 0.0]    # B sublattice
    ]
    
    return Crystal(species, positions, lattice)


__all__ = ['build_nanotube', 'build_carbon_nanotube']
