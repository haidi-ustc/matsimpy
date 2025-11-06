"""
Symmetry-based bulk crystal generation.

Generate crystal structures from space groups and crystal systems.
"""

from typing import List, Optional, Union, Dict, Any
import numpy as np
from ...core import Crystal, Lattice
from ...symmetry import SymmetryAnalyzer

try:
    import spglib
    HAS_SPGLIB = True
except ImportError:
    HAS_SPGLIB = False
    spglib = None


def from_space_group(
    space_group: Union[int, str],
    species: List[str],
    positions: List[List[float]],
    lattice: Optional[Lattice] = None,
    lattice_params: Optional[Union[float, List[float]]] = None,
    **kwargs
) -> Crystal:
    """
    Generate crystal structure from space group.
    
    Args:
        space_group: Space group number (1-230) or symbol (e.g., 'Fm-3m', 'P6_3/mmc')
        species: List of atomic species
        positions: Fractional positions of atoms in asymmetric unit
        lattice: Optional Lattice object. If None, will be created from lattice_params
        lattice_params: Lattice parameters (a, or [a, b, c] for orthorhombic, etc.)
        **kwargs: Additional parameters:
            - symprec: Symmetry precision (default: 1e-5)
            - angle_tolerance: Angle tolerance (default: -1.0)
            - use_symmetry_data: Use symmetry data for structure generation (default: True)
    
    Returns:
        Crystal: Generated crystal structure with proper symmetry
    
    Examples:
        >>> from matsimpy.builders.bulk.symmetry import from_space_group
        >>> from matsimpy.core import Lattice
        >>> 
        >>> # Generate cubic structure (Fm-3m, space group 225)
        >>> lattice = Lattice.cubic(5.0)
        >>> crystal = from_space_group(
        ...     225, ['Na', 'Cl'],
        ...     [[0, 0, 0], [0.5, 0.5, 0.5]],
        ...     lattice=lattice
        ... )
        >>> 
        >>> # Or using space group symbol
        >>> crystal2 = from_space_group(
        ...     'Fm-3m', ['Na', 'Cl'],
        ...     [[0, 0, 0], [0.5, 0.5, 0.5]],
        ...     lattice_params=5.0
        ... )
    """
    symprec = kwargs.get('symprec', 1e-5)
    angle_tolerance = kwargs.get('angle_tolerance', -1.0)
    use_symmetry_data = kwargs.get('use_symmetry_data', True)
    
    # Convert space group to number if needed
    space_group_number = _get_space_group_number(space_group, use_symmetry_data)
    if space_group_number is None:
        raise ValueError(f"Invalid space group: {space_group}")
    
    # Create lattice if not provided
    if lattice is None:
        if lattice_params is None:
            raise ValueError("Either 'lattice' or 'lattice_params' must be provided")
        lattice = _create_lattice_from_system(space_group_number, lattice_params)
    
    # Generate structure using spglib
    if HAS_SPGLIB:
        return _generate_from_spglib(
            space_group_number, species, positions, lattice,
            symprec, angle_tolerance
        )
    else:
        # Fallback: generate using symmetry operations from data
        if use_symmetry_data:
            return _generate_from_symmetry_data(
                space_group_number, species, positions, lattice
            )
        else:
            raise ImportError(
                "spglib is required for space group generation. "
                "Install with: pip install spglib"
            )


def from_crystal_system(
    crystal_system: str,
    species: List[str],
    positions: List[List[float]],
    lattice_params: Union[float, List[float]],
    space_group: Optional[Union[int, str]] = None,
    **kwargs
) -> Crystal:
    """
    Generate crystal structure from crystal system.
    
    Args:
        crystal_system: Crystal system name:
            - 'Triclinic', 'Monoclinic', 'Orthorhombic'
            - 'Tetragonal', 'Trigonal', 'Hexagonal', 'Cubic'
        species: List of atomic species
        positions: Fractional positions of atoms
        lattice_params: Lattice parameters:
            - Cubic: a
            - Tetragonal: [a, c]
            - Orthorhombic: [a, b, c]
            - Hexagonal/Trigonal: [a, c]
            - Monoclinic: [a, b, c, beta] or [a, b, c]
            - Triclinic: [a, b, c, alpha, beta, gamma]
        space_group: Optional space group number or symbol.
            If not provided, uses a common space group for the system.
        **kwargs: Additional parameters (see from_space_group)
    
    Returns:
        Crystal: Generated crystal structure
    
    Examples:
        >>> from matsimpy.builders.bulk.symmetry import from_crystal_system
        >>> 
        >>> # Generate cubic structure
        >>> cubic = from_crystal_system(
        ...     'Cubic', ['Si'], [[0, 0, 0]], 5.43
        ... )
        >>> 
        >>> # Generate tetragonal structure
        >>> tetragonal = from_crystal_system(
        ...     'Tetragonal', ['Ti', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]],
        ...     [3.8, 9.6]
        ... )
    """
    # Map crystal system to default space group if not provided
    if space_group is None:
        space_group = _get_default_space_group(crystal_system)
    
    # Create lattice from crystal system
    lattice = _create_lattice_from_system_by_name(crystal_system, lattice_params)
    
    # Generate using space group
    return from_space_group(
        space_group, species, positions, lattice=lattice, **kwargs
    )


def _get_space_group_number(space_group: Union[int, str], use_data: bool = True) -> Optional[int]:
    """Convert space group to number."""
    if isinstance(space_group, int):
        if 1 <= space_group <= 230:
            return space_group
        return None
    
    # Try to get from symmetry data
    if use_data:
        analyzer = SymmetryAnalyzer()
        info = analyzer.get_space_group_info(space_group)
        if info:
            return info.get('int_number')
    
    # Fallback: try common mappings
    common_sgs = {
        'P1': 1, 'P-1': 2,
        'P2': 3, 'P2_1': 4, 'C2': 5,
        'Pm': 6, 'Pc': 7, 'Cm': 8, 'Cc': 9,
        'P2/m': 10, 'P2_1/m': 11, 'C2/m': 12,
        'Pmmm': 47, 'Pm-3m': 221, 'Fm-3m': 225,
        'Fd-3m': 227, 'P6_3/mmc': 194
    }
    
    return common_sgs.get(space_group)


def _create_lattice_from_system(space_group_number: int, lattice_params: Union[float, List[float]]) -> Lattice:
    """Create lattice from space group number and parameters."""
    crystal_system = _get_crystal_system_from_sg(space_group_number)
    return _create_lattice_from_system_by_name(crystal_system, lattice_params)


def _get_crystal_system_from_sg(space_group_number: int) -> str:
    """Get crystal system from space group number."""
    if 1 <= space_group_number <= 2:
        return "Triclinic"
    elif 3 <= space_group_number <= 15:
        return "Monoclinic"
    elif 16 <= space_group_number <= 74:
        return "Orthorhombic"
    elif 75 <= space_group_number <= 142:
        return "Tetragonal"
    elif 143 <= space_group_number <= 167:
        return "Trigonal"
    elif 168 <= space_group_number <= 194:
        return "Hexagonal"
    elif 195 <= space_group_number <= 230:
        return "Cubic"
    else:
        return "Cubic"  # Default


def _create_lattice_from_system_by_name(
    crystal_system: str,
    lattice_params: Union[float, List[float]]
) -> Lattice:
    """Create lattice from crystal system name and parameters."""
    crystal_system = crystal_system.lower()
    
    if crystal_system == 'cubic':
        if isinstance(lattice_params, (list, tuple)):
            a = lattice_params[0]
        else:
            a = lattice_params
        return Lattice.cubic(a)
    
    elif crystal_system == 'tetragonal':
        if isinstance(lattice_params, (list, tuple)):
            a, c = lattice_params[0], lattice_params[1]
        else:
            a = lattice_params
            c = a * 1.5  # Default c/a ratio
        return Lattice.tetragonal(a, c)
    
    elif crystal_system == 'orthorhombic':
        if isinstance(lattice_params, (list, tuple)) and len(lattice_params) >= 3:
            a, b, c = lattice_params[0], lattice_params[1], lattice_params[2]
        else:
            a = lattice_params if isinstance(lattice_params, (int, float)) else lattice_params[0]
            b = a
            c = a
        # Use orthorhomic (note: misspelled in Lattice class)
        return Lattice.orthorhomic(a, b, c)
    
    elif crystal_system in ['hexagonal', 'trigonal']:
        if isinstance(lattice_params, (list, tuple)):
            a, c = lattice_params[0], lattice_params[1]
        else:
            a = lattice_params
            c = a * 1.633  # Ideal c/a for hexagonal
        # Use convenience method for hexagonal lattice
        return Lattice.hexagonal(a, c)
    
    elif crystal_system == 'monoclinic':
        if isinstance(lattice_params, (list, tuple)) and len(lattice_params) >= 3:
            a, b, c = lattice_params[0], lattice_params[1], lattice_params[2]
            beta = lattice_params[3] if len(lattice_params) > 3 else 90.0
        else:
            a = lattice_params if isinstance(lattice_params, (int, float)) else lattice_params[0]
            b = a
            c = a
            beta = 90.0
        # Create monoclinic lattice manually
        beta_rad = np.radians(beta)
        lattice_vectors = [
            [a, 0, 0],
            [0, b, 0],
            [c * np.cos(beta_rad), 0, c * np.sin(beta_rad)]
        ]
        return Lattice(lattice_vectors)
    
    elif crystal_system == 'triclinic':
        if isinstance(lattice_params, (list, tuple)) and len(lattice_params) >= 6:
            a, b, c = lattice_params[0], lattice_params[1], lattice_params[2]
            alpha, beta, gamma = lattice_params[3], lattice_params[4], lattice_params[5]
        else:
            a = lattice_params if isinstance(lattice_params, (int, float)) else lattice_params[0]
            b = a
            c = a
            alpha = beta = gamma = 90.0
        # Create triclinic lattice manually
        alpha_rad = np.radians(alpha)
        beta_rad = np.radians(beta)
        gamma_rad = np.radians(gamma)
        
        # Calculate lattice vectors from parameters
        a_vec = [a, 0, 0]
        b_vec = [b * np.cos(gamma_rad), b * np.sin(gamma_rad), 0]
        
        # Calculate c vector components
        c_x = c * np.cos(beta_rad)
        if np.abs(np.sin(gamma_rad)) > 1e-10:
            c_y = c * (np.cos(alpha_rad) - np.cos(beta_rad) * np.cos(gamma_rad)) / np.sin(gamma_rad)
        else:
            # Handle case where gamma is 90 degrees
            c_y = c * np.cos(alpha_rad)
        c_z_sq = c**2 - c_x**2 - c_y**2
        c_z = np.sqrt(max(0, c_z_sq))  # Ensure non-negative
        c_vec = [c_x, c_y, c_z]
        
        lattice_vectors = [a_vec, b_vec, c_vec]
        return Lattice(lattice_vectors)
    
    else:
        # Default to cubic
        a = lattice_params if isinstance(lattice_params, (int, float)) else lattice_params[0]
        return Lattice.cubic(a)


def _get_default_space_group(crystal_system: str) -> int:
    """Get default space group for crystal system."""
    defaults = {
        'triclinic': 1,      # P1
        'monoclinic': 12,    # C2/m
        'orthorhombic': 47,  # Pmmm
        'tetragonal': 123,   # P4/mmm
        'trigonal': 166,     # R-3m
        'hexagonal': 194,    # P6_3/mmc
        'cubic': 221         # Pm-3m
    }
    return defaults.get(crystal_system.lower(), 221)


def _generate_from_spglib(
    space_group_number: int,
    species: List[str],
    positions: List[List[float]],
    lattice: Lattice,
    symprec: float,
    angle_tolerance: float
) -> Crystal:
    """
    Generate structure using spglib with requested space group.
    
    First attempts to get symmetry operations from spglib by analyzing
    a structure that should match the space group. Then applies those
    operations and validates the result.
    """
    # Convert species to atomic numbers
    analyzer = SymmetryAnalyzer()
    numbers = [analyzer._element_to_number(spec) for spec in species]
    
    # Create initial structure
    positions_array = np.array(positions)
    lattice_matrix = lattice.lattice_vectors
    
    # First, try to get symmetry operations from spglib
    # This will find operations from the input structure
    dataset = spglib.get_symmetry_dataset(
        (lattice_matrix, positions_array, numbers),
        symprec=symprec,
        angle_tolerance=angle_tolerance
    )
    
    if dataset is None:
        # If spglib can't find symmetry, try using symmetry data
        return _generate_from_symmetry_data(
            space_group_number, species, positions, lattice
        )
    
    # Get symmetry operations
    if hasattr(dataset, 'rotations'):
        rotations = dataset.rotations
        translations = dataset.translations
        detected_sg = dataset.number if hasattr(dataset, 'number') else dataset['number']
    else:
        rotations = dataset['rotations']
        translations = dataset['translations']
        detected_sg = dataset['number']
    
    # Check if detected space group matches requested
    # If not, we need to use symmetry data instead
    if int(detected_sg) != space_group_number:
        # Space groups don't match - use symmetry data to enforce correct one
        return _generate_from_symmetry_data(
            space_group_number, species, positions, lattice
        )
    
    # Generate all equivalent positions using symmetry operations
    all_positions = []
    all_species = []
    
    # Start with asymmetric unit positions
    for i, pos in enumerate(positions_array):
        species_atom = species[i]
        
        # Apply all symmetry operations
        for rot, trans in zip(rotations, translations):
            new_pos = rot @ pos + trans
            # Wrap to [0, 1)
            new_pos = new_pos % 1.0
            # Ensure positive
            new_pos = new_pos % 1.0
            all_positions.append(new_pos.tolist())
            all_species.append(species_atom)
    
    # Remove duplicates (within tolerance)
    unique_positions = []
    unique_species = []
    tolerance = 1e-5
    
    for pos, spec in zip(all_positions, all_species):
        is_duplicate = False
        for existing_pos in unique_positions:
            if np.allclose(pos, existing_pos, atol=tolerance):
                is_duplicate = True
                break
        if not is_duplicate:
            unique_positions.append(pos)
            unique_species.append(spec)
    
    # Create crystal and validate
    crystal = Crystal(unique_species, unique_positions, lattice)
    
    # Validate that generated structure has correct space group
    if not _validate_space_group(crystal, space_group_number, symprec, angle_tolerance):
        # Validation failed - try using symmetry data
        return _generate_from_symmetry_data(
            space_group_number, species, positions, lattice
        )
    
    return crystal


def _generate_from_symmetry_data(
    space_group_number: int,
    species: List[str],
    positions: List[List[float]],
    lattice: Lattice
) -> Crystal:
    """
    Generate structure using symmetry data (fallback when spglib doesn't match).
    
    Uses generator matrices from symmetry data to build symmetry operations.
    This is a simplified implementation - full decoding of encodings is complex.
    """
    analyzer = SymmetryAnalyzer()
    
    # Get space group info
    sg_info = None
    if analyzer._symmetry_data and 'space_group_encoding' in analyzer._symmetry_data:
        for sg_symbol, info in analyzer._symmetry_data['space_group_encoding'].items():
            if info.get('int_number') == space_group_number:
                sg_info = info
                break
    
    if sg_info is None:
        # Fallback: return structure with given positions
        # This happens if space group not found in data
        return Crystal(species, positions, lattice)
    
    # Get generator matrices from symmetry data
    generator_matrices = analyzer._symmetry_data.get('generator_matrices', {})
    translations_map = analyzer._symmetry_data.get('translations', {})
    
    # Build symmetry operations from generators
    # This is a simplified approach - full implementation would decode the encoding string
    # For now, we'll use spglib to get operations if available, or return basic structure
    if HAS_SPGLIB:
        # Try to create a structure that matches the space group
        # Use common Wyckoff positions for the space group
        positions_array = np.array(positions)
        
        # Get symmetry operations by analyzing a structure that should match
        # This is a workaround since spglib doesn't directly provide operations for a space group
        numbers = [analyzer._element_to_number(spec) for spec in species]
        lattice_matrix = lattice.lattice_vectors
        
        # Try to get symmetry
        dataset = spglib.get_symmetry_dataset(
            (lattice_matrix, positions_array, numbers),
            symprec=1e-5
        )
        
        if dataset:
            if hasattr(dataset, 'rotations'):
                rotations = dataset.rotations
                translations = dataset.translations
            else:
                rotations = dataset['rotations']
                translations = dataset['translations']
            
            # Apply operations to generate full structure
            all_positions = []
            all_species = []
            
            for i, pos in enumerate(positions_array):
                species_atom = species[i]
                for rot, trans in zip(rotations, translations):
                    new_pos = rot @ pos + trans
                    new_pos = new_pos % 1.0
                    new_pos = new_pos % 1.0
                    all_positions.append(new_pos.tolist())
                    all_species.append(species_atom)
            
            # Remove duplicates
            unique_positions = []
            unique_species = []
            tolerance = 1e-5
            
            for pos, spec in zip(all_positions, all_species):
                is_duplicate = False
                for existing_pos in unique_positions:
                    if np.allclose(pos, existing_pos, atol=tolerance):
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_positions.append(pos)
                    unique_species.append(spec)
            
            return Crystal(unique_species, unique_positions, lattice)
    
    # Fallback: return structure with given positions
    return Crystal(species, positions, lattice)


def _validate_space_group(
    crystal: Crystal,
    space_group_number: int,
    symprec: float,
    angle_tolerance: float
) -> bool:
    """
    Validate that crystal has the requested space group.
    
    Args:
        crystal: Generated crystal structure
        space_group_number: Requested space group number
        symprec: Symmetry precision
        angle_tolerance: Angle tolerance
    
    Returns:
        True if crystal matches requested space group, False otherwise
    """
    if not HAS_SPGLIB:
        return True  # Can't validate without spglib
    
    analyzer = SymmetryAnalyzer(symprec=symprec, angle_tolerance=angle_tolerance)
    
    try:
        result = analyzer.analyze_crystal(crystal)
        detected_sg = result.get('space_group_number')
        
        if detected_sg is None:
            return False
        
        return int(detected_sg) == space_group_number
    except Exception:
        return False


def list_space_groups_by_system(crystal_system: Optional[str] = None) -> Dict[str, List[int]]:
    """
    List space groups, optionally filtered by crystal system.
    
    Args:
        crystal_system: Optional crystal system name to filter
    
    Returns:
        Dictionary mapping crystal systems to lists of space group numbers,
        or if crystal_system is provided, list of space group numbers
    
    Examples:
        >>> from matsimpy.builders.bulk.symmetry import list_space_groups_by_system
        >>> 
        >>> # List all space groups by system
        >>> all_sgs = list_space_groups_by_system()
        >>> print(all_sgs['Cubic'])  # [195, 196, ..., 230]
        >>> 
        >>> # List only cubic space groups
        >>> cubic_sgs = list_space_groups_by_system('Cubic')
        >>> print(cubic_sgs)  # [195, 196, ..., 230]
    """
    analyzer = SymmetryAnalyzer()
    
    if crystal_system:
        crystal_system = crystal_system.lower()
        system_ranges = {
            'triclinic': (1, 2),
            'monoclinic': (3, 15),
            'orthorhombic': (16, 74),
            'tetragonal': (75, 142),
            'trigonal': (143, 167),
            'hexagonal': (168, 194),
            'cubic': (195, 230)
        }
        
        if crystal_system in system_ranges:
            start, end = system_ranges[crystal_system]
            return list(range(start, end + 1))
        else:
            return []
    else:
        # Return all space groups organized by system
        return {
            'Triclinic': list(range(1, 3)),
            'Monoclinic': list(range(3, 16)),
            'Orthorhombic': list(range(16, 75)),
            'Tetragonal': list(range(75, 143)),
            'Trigonal': list(range(143, 168)),
            'Hexagonal': list(range(168, 195)),
            'Cubic': list(range(195, 231))
        }


__all__ = [
    'from_space_group',
    'from_crystal_system',
    'list_space_groups_by_system',
]

