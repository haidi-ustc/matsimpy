"""
Symmetry-based bulk crystal generation.

Generate crystal structures from space groups and crystal systems.
"""

from typing import List, Optional, Union, Dict, Any
import numpy as np
import spglib
from ...core import Crystal, Lattice
from ...symmetry import SymmetryAnalyzer


def from_space_group(
    space_group: Union[int, str],
    species: List[str],
    positions: List[List[float]],
    lattice: Optional[Lattice] = None,
    lattice_params: Optional[Union[float, List[float]]] = None,
    **kwargs,
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
    symprec = kwargs.get("symprec", 1e-5)
    angle_tolerance = kwargs.get("angle_tolerance", -1.0)
    validate_sg = kwargs.pop("validate_sg", True)
    use_symmetry_data = kwargs.get("use_symmetry_data", True)

    # Convert space group to number if needed
    space_group_number = _get_space_group_number(space_group, use_symmetry_data)
    if space_group_number is None:
        raise ValueError(f"Invalid space group: {space_group}")

    # Create lattice if not provided
    if lattice is None:
        if lattice_params is None:
            raise ValueError("Either 'lattice' or 'lattice_params' must be provided")
        lattice = _create_lattice_from_system(space_group_number, lattice_params)

    crystal = _generate_from_spglib(
        space_group_number,
        species,
        positions,
        lattice,
        symprec,
        angle_tolerance,
        require_requested_group=validate_sg,
    )

    if validate_sg:
        _raise_if_space_group_mismatch(
            crystal, space_group_number, symprec, angle_tolerance
        )

    return crystal


def from_crystal_system(
    crystal_system: str,
    species: List[str],
    positions: List[List[float]],
    lattice_params: Union[float, List[float]],
    space_group: Optional[Union[int, str]] = None,
    **kwargs,
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
    # Map crystal system to default space group if not provided. This default is
    # only a lattice-system helper, not an exact space-group request by the user.
    explicit_space_group = space_group is not None
    if space_group is None:
        space_group = _get_default_space_group(crystal_system)

    # Create lattice from crystal system
    lattice = _create_lattice_from_system_by_name(crystal_system, lattice_params)

    # Generate using space group
    kwargs.setdefault("validate_sg", explicit_space_group)
    return from_space_group(space_group, species, positions, lattice=lattice, **kwargs)


def _get_space_group_number(
    space_group: Union[int, str], use_data: bool = True
) -> Optional[int]:
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
            return info.get("int_number")

    # Fallback: try common mappings
    common_sgs = {
        "P1": 1,
        "P-1": 2,
        "P2": 3,
        "P2_1": 4,
        "C2": 5,
        "Pm": 6,
        "Pc": 7,
        "Cm": 8,
        "Cc": 9,
        "P2/m": 10,
        "P2_1/m": 11,
        "C2/m": 12,
        "Pmmm": 47,
        "Pm-3m": 221,
        "Fm-3m": 225,
        "Fd-3m": 227,
        "P6_3/mmc": 194,
    }

    return common_sgs.get(space_group)


def _create_lattice_from_system(
    space_group_number: int, lattice_params: Union[float, List[float]]
) -> Lattice:
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
    crystal_system: str, lattice_params: Union[float, List[float]]
) -> Lattice:
    """Create lattice from crystal system name and parameters."""
    crystal_system = crystal_system.lower()

    if crystal_system == "cubic":
        if isinstance(lattice_params, (list, tuple)):
            a = lattice_params[0]
        else:
            a = lattice_params
        return Lattice.cubic(a)

    elif crystal_system == "tetragonal":
        if isinstance(lattice_params, (list, tuple)):
            a, c = lattice_params[0], lattice_params[1]
        else:
            a = lattice_params
            c = a * 1.5  # Default c/a ratio
        return Lattice.tetragonal(a, c)

    elif crystal_system == "orthorhombic":
        if isinstance(lattice_params, (list, tuple)) and len(lattice_params) >= 3:
            a, b, c = lattice_params[0], lattice_params[1], lattice_params[2]
        else:
            a = (
                lattice_params
                if isinstance(lattice_params, (int, float))
                else lattice_params[0]
            )
            b = a
            c = a
        # Use orthorhombic (note: misspelled in Lattice class)
        return Lattice.orthorhombic(a, b, c)

    elif crystal_system in ["hexagonal", "trigonal"]:
        if isinstance(lattice_params, (list, tuple)):
            a, c = lattice_params[0], lattice_params[1]
        else:
            a = lattice_params
            c = a * 1.633  # Ideal c/a for hexagonal
        # Use convenience method for hexagonal lattice
        return Lattice.hexagonal(a, c)

    elif crystal_system == "monoclinic":
        if isinstance(lattice_params, (list, tuple)) and len(lattice_params) >= 3:
            a, b, c = lattice_params[0], lattice_params[1], lattice_params[2]
            beta = lattice_params[3] if len(lattice_params) > 3 else 90.0
        else:
            a = (
                lattice_params
                if isinstance(lattice_params, (int, float))
                else lattice_params[0]
            )
            b = a
            c = a
            beta = 90.0
        # Use convenience method for monoclinic lattice
        return Lattice.monoclinic(a, b, c, beta)

    elif crystal_system == "triclinic":
        if isinstance(lattice_params, (list, tuple)) and len(lattice_params) >= 6:
            a, b, c = lattice_params[0], lattice_params[1], lattice_params[2]
            alpha, beta, gamma = lattice_params[3], lattice_params[4], lattice_params[5]
        else:
            a = (
                lattice_params
                if isinstance(lattice_params, (int, float))
                else lattice_params[0]
            )
            b = a
            c = a
            alpha = beta = gamma = 90.0
        # Use convenience method for triclinic lattice
        return Lattice.triclinic(a, b, c, alpha, beta, gamma)

    else:
        # Default to cubic
        a = (
            lattice_params
            if isinstance(lattice_params, (int, float))
            else lattice_params[0]
        )
        return Lattice.cubic(a)


def _get_default_space_group(crystal_system: str) -> int:
    """Get default space group for crystal system."""
    defaults = {
        "triclinic": 1,  # P1
        "monoclinic": 12,  # C2/m
        "orthorhombic": 47,  # Pmmm
        "tetragonal": 123,  # P4/mmm
        "trigonal": 166,  # R-3m
        "hexagonal": 194,  # P6_3/mmc
        "cubic": 221,  # Pm-3m
    }
    return defaults.get(crystal_system.lower(), 221)


def _generate_from_spglib(
    space_group_number: int,
    species: List[str],
    positions: List[List[float]],
    lattice: Lattice,
    symprec: float,
    angle_tolerance: float,
    require_requested_group: bool = True,
) -> Crystal:
    """
    Generate structure using spglib with requested space group.

    Gets symmetry operations from spglib by analyzing an input structure that
    should already match the requested space group, then applies those
    operations. If require_requested_group is True and spglib detects another
    group, the caller's exact space-group contract cannot be satisfied and this
    raises. Otherwise, the detected operations are used as a loose symmetry
    expansion path.
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
        angle_tolerance=angle_tolerance,
    )

    if dataset is None:
        raise ValueError(
            f"spglib could not detect symmetry for requested space group "
            f"{space_group_number}"
        )

    # Get symmetry operations
    if hasattr(dataset, "rotations"):
        rotations = dataset.rotations
        translations = dataset.translations
        detected_sg = (
            dataset.number if hasattr(dataset, "number") else dataset["number"]
        )
    else:
        rotations = dataset["rotations"]
        translations = dataset["translations"]
        detected_sg = dataset["number"]

    if require_requested_group and int(detected_sg) != space_group_number:
        raise ValueError(
            f"Input positions/lattice have space group {int(detected_sg)}, "
            f"not requested {space_group_number}. Provide an asymmetric unit "
            "compatible with the requested space group."
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

    return Crystal(unique_species, unique_positions, lattice)


def _validate_space_group(
    crystal: Crystal, space_group_number: int, symprec: float, angle_tolerance: float
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
    analyzer = SymmetryAnalyzer(symprec=symprec, angle_tolerance=angle_tolerance)

    try:
        result = analyzer.analyze_crystal(crystal)
        detected_sg = result.get("space_group_number")

        if detected_sg is None:
            return False

        return int(detected_sg) == space_group_number
    except Exception:
        return False


def _raise_if_space_group_mismatch(
    crystal: Crystal, space_group_number: int, symprec: float, angle_tolerance: float
) -> None:
    """Raise if spglib analysis does not match the requested space group."""
    analyzer = SymmetryAnalyzer(symprec=symprec, angle_tolerance=angle_tolerance)
    result = analyzer.analyze_crystal(crystal)
    detected_sg = result.get("space_group_number")
    if detected_sg is None:
        raise ValueError(
            f"Could not validate generated structure against requested space "
            f"group {space_group_number}"
        )
    if int(detected_sg) != space_group_number:
        raise ValueError(
            f"Generated structure has space group {int(detected_sg)}, "
            f"not requested {space_group_number}"
        )


def list_space_groups_by_system(
    crystal_system: Optional[str] = None,
) -> Dict[str, List[int]]:
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
            "triclinic": (1, 2),
            "monoclinic": (3, 15),
            "orthorhombic": (16, 74),
            "tetragonal": (75, 142),
            "trigonal": (143, 167),
            "hexagonal": (168, 194),
            "cubic": (195, 230),
        }

        if crystal_system in system_ranges:
            start, end = system_ranges[crystal_system]
            return list(range(start, end + 1))
        else:
            return []
    else:
        # Return all space groups organized by system
        return {
            "Triclinic": list(range(1, 3)),
            "Monoclinic": list(range(3, 16)),
            "Orthorhombic": list(range(16, 75)),
            "Tetragonal": list(range(75, 143)),
            "Trigonal": list(range(143, 168)),
            "Hexagonal": list(range(168, 195)),
            "Cubic": list(range(195, 231)),
        }


__all__ = [
    "from_space_group",
    "from_crystal_system",
    "list_space_groups_by_system",
]
