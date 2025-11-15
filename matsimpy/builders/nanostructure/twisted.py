"""
Magic-angle twisted structure builders.

Generate twisted bilayer and multilayer structures (e.g., twisted bilayer graphene
at magic angles, twisted transition metal dichalcogenides).
"""

from typing import List, Tuple, Optional, Union
import numpy as np
from copy import deepcopy
from ...core import Crystal, Lattice
from ...transformation import rotate, translate


def build_twisted_bilayer(
    layer: Crystal,
    twist_angle: float,
    layer_spacing: Optional[float] = None,
    center: bool = True,
    **kwargs
) -> Crystal:
    """
    Build a twisted bilayer structure from two layers.
    
    This function takes a single layer, duplicates it, rotates one copy,
    and stacks them with a specified spacing.
    
    Args:
        layer: Single layer crystal structure
        twist_angle: Twist angle in degrees (e.g., 1.1° for magic-angle graphene)
        layer_spacing: Vertical spacing between layers in Angstroms
                     (if None, estimated from layer structure)
        center: If True, center the structure in the z-direction
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Twisted bilayer structure
    
    Examples:
        >>> from matsimpy.builders.nanostructure import build_twisted_bilayer
        >>> from matsimpy.builders.nanostructure import _create_graphene_sheet
        >>> 
        >>> # Create graphene layer
        >>> graphene = _create_graphene_sheet()
        >>> 
        >>> # Magic-angle twisted bilayer graphene (~1.1°)
        >>> magic = build_twisted_bilayer(graphene, 1.1, layer_spacing=3.35)
        >>> 
        >>> # Large-angle twisted bilayer
        >>> large_angle = build_twisted_bilayer(graphene, 15.0, layer_spacing=3.35)
    """
    # Default layer spacing (for graphene, typical is ~3.35 Angstrom)
    if layer_spacing is None:
        # Estimate from lattice if possible
        if layer.lattice is not None:
            # Use the c-vector length if available, otherwise default
            c_vec = layer.lattice.lattice_vectors[2]
            layer_spacing = np.linalg.norm(c_vec) if np.linalg.norm(c_vec) > 1.0 else 3.35
        else:
            layer_spacing = 3.35
    
    # Create copies of the layer
    layer1 = deepcopy(layer)
    layer2 = deepcopy(layer)
    
    # Rotate the second layer around the z-axis (perpendicular to the layer)
    # The rotation center should be at the center of the layer
    if layer.lattice is not None:
        # Find the center of the layer in xy plane
        positions_xy = layer.positions[:, :2]
        center_xy = np.mean(positions_xy, axis=0)
        center_3d = np.array([center_xy[0], center_xy[1], 0.0])
    else:
        center_3d = np.array([0.0, 0.0, 0.0])
    
    # Rotate layer2 around z-axis
    layer2 = rotate(layer2, twist_angle, [0, 0, 1], center=center_3d, inplace=False)
    
    # Ensure layer1 is at z=0 (or close to it) in fractional coordinates
    # For crystals, positions are fractional, so we need to work with cartesian
    if isinstance(layer1, Crystal):
        # Get cartesian positions
        pos1_cart = layer1.cart_positions.copy()
        pos2_cart = layer2.cart_positions.copy()
        
        # Set layer1 to start at z=0
        min_z1 = np.min(pos1_cart[:, 2])
        pos1_cart[:, 2] -= min_z1
        
        # Translate layer2 in cartesian space
        pos2_cart[:, 2] += layer_spacing
        
        # Convert back to fractional if needed, or use cartesian directly
        # For now, use cartesian positions directly
        combined_species = list(layer1.species) + list(layer2.species)
        combined_positions = np.vstack([pos1_cart, pos2_cart])
        
        # We'll need to convert these to fractional later
        use_cartesian = True
    else:
        # For molecules, positions are already cartesian
        min_z1 = np.min(layer1.positions[:, 2])
        layer1.positions[:, 2] -= min_z1
        
        # Translate layer2
        translation = np.array([0.0, 0.0, layer_spacing])
        layer2 = translate(layer2, translation, inplace=False)
        
        combined_species = list(layer1.species) + list(layer2.species)
        combined_positions = np.vstack([layer1.positions, layer2.positions])
        use_cartesian = False
    
    # Create new lattice that accommodates both layers
    if layer1.lattice is not None:
        old_lattice = layer1.lattice
        lattice_vectors = old_lattice.lattice_vectors.copy()
        
        # Calculate required height
        max_z = np.max(combined_positions[:, 2])
        min_z = np.min(combined_positions[:, 2])
        
        # Extend the c-vector to accommodate both layers
        # Add vacuum above and below if centering
        if center:
            total_height = max_z - min_z + 20.0  # Add 10 Angstrom vacuum on each side
            lattice_vectors[2] = np.array([0, 0, total_height])
        else:
            # Just extend enough for the second layer
            total_height = max_z + 10.0
            lattice_vectors[2] = np.array([0, 0, total_height])
        
        new_lattice = Lattice(lattice_vectors)
        
        # Convert cartesian positions to fractional if needed
        if use_cartesian:
            # Convert cartesian to fractional
            inv_lattice = np.linalg.inv(new_lattice.lattice_vectors)
            combined_positions = np.dot(combined_positions, inv_lattice)
    else:
        # Create a simple lattice
        max_pos = np.max(combined_positions, axis=0)
        min_pos = np.min(combined_positions, axis=0)
        size = max_pos - min_pos + 10.0  # Add 10 Angstrom padding
        try:
            new_lattice = Lattice.orthorhombic(size[0], size[1], size[2])
        except AttributeError:
            # Fallback: create lattice manually
            lattice_vectors = np.array([
                [size[0], 0, 0],
                [0, size[1], 0],
                [0, 0, size[2]]
            ])
            new_lattice = Lattice(lattice_vectors)
        
        # If we used cartesian, convert to fractional
        if use_cartesian:
            inv_lattice = np.linalg.inv(new_lattice.lattice_vectors)
            combined_positions = np.dot(combined_positions, inv_lattice)
    
    # Center the structure if requested
    if center:
        # Find the center of mass in fractional coordinates
        center_of_mass = np.mean(combined_positions, axis=0)
        # Shift so center is at z = 0.5 (middle of cell)
        z_shift = 0.5 - center_of_mass[2]
        combined_positions[:, 2] += z_shift
    
    return Crystal(combined_species, combined_positions.tolist(), new_lattice)


def build_magic_angle_twisted(
    layer: Crystal,
    n: int = 1,
    m: int = 1,
    layer_spacing: Optional[float] = None,
    **kwargs
) -> Crystal:
    """
    Build a magic-angle twisted structure using specific (n, m) indices.
    
    For twisted bilayer graphene, the magic angle is approximately 1.1°,
    which corresponds to specific (n, m) indices that create a moiré pattern.
    
    The twist angle is calculated as: θ = arccos((3n² + 3nm + m²/2) / (3n² + 3nm + m²))
    
    Common magic angle configurations:
    - (1, 1): ~21.8° (not magic angle)
    - Higher indices give smaller angles approaching magic angle
    
    Args:
        layer: Single layer crystal structure
        n: First moiré index
        m: Second moiré index  
        layer_spacing: Vertical spacing between layers in Angstroms
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Magic-angle twisted structure
    
    Examples:
        >>> from matsimpy.builders.nanostructure import build_magic_angle_twisted
        >>> 
        >>> # Create graphene layer
        >>> graphene = _create_graphene_sheet()
        >>> 
        >>> # Build twisted structure with specific indices
        >>> twisted = build_magic_angle_twisted(graphene, n=1, m=1)
    """
    # Calculate twist angle from moiré indices
    # For a more accurate calculation, we'd need to consider the lattice matching
    # For now, use a simplified formula
    if n == m:
        # Special case: gives approximately 21.8° for graphene
        twist_angle = 21.8
    else:
        # Approximate formula for small angles
        # For graphene, the magic angle is when the moiré pattern matches
        # More sophisticated calculation would use lattice matching
        twist_angle = 360.0 / (n * n + n * m + m * m) if (n * n + n * m + m * m) > 0 else 1.1
    
    # For true magic angle (~1.1°), we need specific (n, m) pairs
    # This is a simplified version - a full implementation would calculate
    # the exact angle based on lattice matching
    
    return build_twisted_bilayer(layer, twist_angle, layer_spacing=layer_spacing, **kwargs)


def build_twisted_multilayer(
    layer: Crystal,
    num_layers: int,
    twist_angles: Union[float, List[float]],
    layer_spacing: Optional[float] = None,
    **kwargs
) -> Crystal:
    """
    Build a twisted multilayer structure.
    
    Args:
        layer: Single layer crystal structure
        num_layers: Number of layers to stack
        twist_angles: Twist angle(s) in degrees. If float, same angle between all layers.
                     If list, must have length num_layers - 1
        layer_spacing: Vertical spacing between layers in Angstroms
        **kwargs: Additional parameters
    
    Returns:
        Crystal: Twisted multilayer structure
    
    Examples:
        >>> from matsimpy.builders.nanostructure import build_twisted_multilayer
        >>> 
        >>> # Create graphene layer
        >>> graphene = _create_graphene_sheet()
        >>> 
        >>> # Build 3-layer structure with 1.1° twist between each layer
        >>> trilayer = build_twisted_multilayer(graphene, 3, 1.1)
        >>> 
        >>> # Build with different angles between layers
        >>> custom = build_twisted_multilayer(graphene, 3, [1.1, 2.0])
    """
    if num_layers < 2:
        raise ValueError("num_layers must be at least 2")
    
    # Normalize twist angles
    if isinstance(twist_angles, float):
        twist_angles = [twist_angles] * (num_layers - 1)
    elif len(twist_angles) != num_layers - 1:
        raise ValueError(f"Number of twist angles ({len(twist_angles)}) must be "
                        f"num_layers - 1 ({num_layers - 1})")
    
    # Start with first layer
    result = deepcopy(layer)
    
    # Add each subsequent layer with rotation
    cumulative_angle = 0.0
    for i in range(1, num_layers):
        cumulative_angle += twist_angles[i - 1]
        
        # Create and rotate new layer
        new_layer = deepcopy(layer)
        
        # Find rotation center
        if layer.lattice is not None:
            positions_xy = layer.positions[:, :2]
            center_xy = np.mean(positions_xy, axis=0)
            center_3d = np.array([center_xy[0], center_xy[1], 0.0])
        else:
            center_3d = np.array([0.0, 0.0, 0.0])
        
        # Rotate around z-axis
        new_layer = rotate(new_layer, cumulative_angle, [0, 0, 1], 
                          center=center_3d, inplace=False)
        
        # Translate vertically
        if layer_spacing is None:
            if layer.lattice is not None:
                c_vec = layer.lattice.lattice_vectors[2]
                spacing = np.linalg.norm(c_vec) if np.linalg.norm(c_vec) > 1.0 else 3.35
            else:
                spacing = 3.35
        else:
            spacing = layer_spacing
        
        translation = np.array([0.0, 0.0, i * spacing])
        new_layer = translate(new_layer, translation, inplace=False)
        
        # Combine layers
        combined_species = list(result.species) + list(new_layer.species)
        combined_positions = np.vstack([result.positions, new_layer.positions])
        
        # Update lattice
        if result.lattice is not None:
            lattice_vectors = result.lattice.lattice_vectors.copy()
            max_z = np.max(combined_positions[:, 2])
            lattice_vectors[2] = np.array([0, 0, max_z + 10.0])
            new_lattice = Lattice(lattice_vectors)
        else:
            max_pos = np.max(combined_positions, axis=0)
            min_pos = np.min(combined_positions, axis=0)
            size = max_pos - min_pos + 10.0
            try:
                new_lattice = Lattice.orthorhombic(size[0], size[1], size[2])
            except AttributeError:
                # Fallback: create lattice manually
                lattice_vectors = np.array([
                    [size[0], 0, 0],
                    [0, size[1], 0],
                    [0, 0, size[2]]
                ])
                new_lattice = Lattice(lattice_vectors)
        
        result = Crystal(combined_species, combined_positions.tolist(), new_lattice)
    
    return result


__all__ = [
    'build_twisted_bilayer',
    'build_magic_angle_twisted',
    'build_twisted_multilayer',
]

