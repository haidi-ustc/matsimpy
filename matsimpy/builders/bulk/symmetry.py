"""
Symmetry-based bulk crystal generation.

Generate crystal structures from space groups and crystal systems.
"""

from functools import lru_cache
from numbers import Integral, Real
from typing import Dict, List, Optional, Union

import numpy as np
import spglib

from ...core import Crystal, Lattice
from ...symmetry import SymmetryAnalyzer

_SYSTEM_RANGES = {
    "triclinic": (1, 2),
    "monoclinic": (3, 15),
    "orthorhombic": (16, 74),
    "tetragonal": (75, 142),
    "trigonal": (143, 167),
    "hexagonal": (168, 194),
    "cubic": (195, 230),
}

_DEFAULT_SPACE_GROUPS = {
    "triclinic": 1,  # P1
    "monoclinic": 12,  # C2/m
    "orthorhombic": 47,  # Pmmm
    "tetragonal": 123,  # P4/mmm
    "trigonal": 166,  # R-3m
    "hexagonal": 194,  # P6_3/mmc
    "cubic": 221,  # Pm-3m
}

# The lattice parameters each crystal system takes, in order
_LATTICE_PARAMETERS = {
    "cubic": ("a",),
    "tetragonal": ("a", "c"),
    "orthorhombic": ("a", "b", "c"),
    "hexagonal": ("a", "c"),
    "trigonal": ("a", "c"),
    "monoclinic": ("a", "b", "c", "beta"),
    "triclinic": ("a", "b", "c", "alpha", "beta", "gamma"),
}


def from_space_group(
    space_group: Union[int, str],
    species: List[str],
    positions: List[List[float]],
    lattice: Optional[Lattice] = None,
    lattice_params: Optional[Union[float, List[float]]] = None,
    symprec: float = 1e-5,
    angle_tolerance: float = -1.0,
    validate_sg: bool = True,
) -> Crystal:
    """
    Generate crystal structure from space group.

    Args:
        space_group: Space group number (1-230) or symbol (e.g., 'Fm-3m', 'P6_3/mmc')
        species: List of atomic species
        positions: Fractional positions of the atoms of the asymmetric unit, in the
            conventional cell of the standard setting
        lattice: Lattice; if None, it is built from lattice_params
        lattice_params: Lattice parameters for the space group's crystal system
            (see from_crystal_system)
        symprec: Symmetry precision for merging images and validation
        angle_tolerance: Angle tolerance for validation (-1 for spglib's default)
        validate_sg: Check with spglib that the result has the requested space group

    Returns:
        Crystal: Generated crystal structure with proper symmetry

    Examples:
        >>> from matsimpy.builders.bulk.symmetry import from_space_group
        >>> from matsimpy.core import Lattice
        >>> rocksalt = from_space_group(225, ['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]],
        ...                             lattice=Lattice.cubic(5.64))
        >>> rocksalt.formula
        'Na4Cl4'
        >>> same = from_space_group('Fm-3m', ['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]],
        ...                         lattice_params=5.64)
    """
    space_group_number = _get_space_group_number(space_group)
    if space_group_number is None:
        raise ValueError(f"Invalid space group: {space_group!r}")

    if lattice is None:
        if lattice_params is None:
            raise ValueError("Either 'lattice' or 'lattice_params' must be provided")
        lattice = _create_lattice_from_system(space_group_number, lattice_params)
    elif lattice_params is not None:
        raise ValueError("Give either 'lattice' or 'lattice_params', not both")

    crystal = _generate_from_spglib(
        space_group_number, species, positions, lattice, symprec, angle_tolerance,
    )
    if validate_sg:
        _raise_if_space_group_mismatch(crystal, space_group_number, symprec, angle_tolerance)
    return crystal


def from_crystal_system(
    crystal_system: str,
    species: List[str],
    positions: List[List[float]],
    lattice_params: Union[float, List[float]],
    space_group: Optional[Union[int, str]] = None,
    symprec: float = 1e-5,
    angle_tolerance: float = -1.0,
    validate_sg: Optional[bool] = None,
) -> Crystal:
    """
    Generate crystal structure from crystal system.

    Args:
        crystal_system: 'Triclinic', 'Monoclinic', 'Orthorhombic', 'Tetragonal',
            'Trigonal', 'Hexagonal' or 'Cubic' (case-insensitive)
        species: List of atomic species
        positions: Fractional positions of atoms
        lattice_params: Exactly the parameters of the system (lengths in Angstroms,
            angles in degrees):
            - Cubic: a (or [a])
            - Tetragonal: [a, c]
            - Orthorhombic: [a, b, c]
            - Hexagonal/Trigonal: [a, c]
            - Monoclinic: [a, b, c, beta]
            - Triclinic: [a, b, c, alpha, beta, gamma]
        space_group: Space group number or symbol; it must belong to the crystal
            system. If not given, a common group of the system is used (Pm-3m, P6_3/mmc,
            R-3m, P4/mmm, Pmmm, C2/m, P1) and the result is not required to keep it.
        symprec: Symmetry precision
        angle_tolerance: Angle tolerance (-1 for spglib's default)
        validate_sg: Check that the result has the space group (default: only when
            space_group is given)

    Returns:
        Crystal: Generated crystal structure

    Examples:
        >>> from matsimpy.builders.bulk.symmetry import from_crystal_system
        >>> cubic = from_crystal_system('Cubic', ['Si'], [[0, 0, 0]], 5.43)
        >>> tetragonal = from_crystal_system(
        ...     'Tetragonal', ['Ti', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], [3.8, 9.6])
    """
    system = _normalize_system(crystal_system)
    explicit_space_group = space_group is not None
    if space_group is None:
        space_group = _DEFAULT_SPACE_GROUPS[system]
    number = _get_space_group_number(space_group)
    if number is None:
        raise ValueError(f"Invalid space group: {space_group!r}")
    if _get_crystal_system_from_sg(number).lower() != system:
        raise ValueError(
            f"Space group {number} is {_get_crystal_system_from_sg(number)}, not {crystal_system}"
        )
    lattice = _create_lattice_from_system_by_name(system, lattice_params)
    return from_space_group(
        number, species, positions, lattice=lattice, symprec=symprec,
        angle_tolerance=angle_tolerance,
        validate_sg=explicit_space_group if validate_sg is None else validate_sg,
    )


def _normalize_system(crystal_system: str) -> str:
    if not isinstance(crystal_system, str) or crystal_system.lower() not in _SYSTEM_RANGES:
        raise ValueError(
            f"Unknown crystal system {crystal_system!r}; expected one of "
            f"{[name.capitalize() for name in _SYSTEM_RANGES]}"
        )
    return crystal_system.lower()


def _get_space_group_number(space_group: Union[int, str]) -> Optional[int]:
    """The space group number of a number or a Hermann-Mauguin symbol, or None."""
    if isinstance(space_group, bool):
        return None
    if isinstance(space_group, Integral):
        return int(space_group) if 1 <= space_group <= 230 else None
    if not isinstance(space_group, str):
        return None
    return _space_group_symbols().get(_normalize_symbol(space_group))


def _normalize_symbol(symbol: str) -> str:
    return symbol.replace(" ", "").replace("_", "")


@lru_cache(maxsize=1)
def _space_group_symbols() -> Dict[str, int]:
    """Short and full Hermann-Mauguin symbols of every setting in spglib's database."""
    symbols: Dict[str, int] = {}
    for hall in range(1, 531):
        group = spglib.get_spacegroup_type(hall)
        for symbol in (group.international_short, group.international_full, group.international):
            symbols.setdefault(_normalize_symbol(symbol), group.number)
    return symbols


def _create_lattice_from_system(
    space_group_number: int, lattice_params: Union[float, List[float]]
) -> Lattice:
    """Create lattice from space group number and parameters."""
    return _create_lattice_from_system_by_name(
        _get_crystal_system_from_sg(space_group_number), lattice_params
    )


def _get_crystal_system_from_sg(space_group_number: int) -> str:
    """Get crystal system from space group number."""
    for system, (low, high) in _SYSTEM_RANGES.items():
        if low <= space_group_number <= high:
            return system.capitalize()
    raise ValueError(f"Space group number must be 1-230, got {space_group_number}")


def _create_lattice_from_system_by_name(
    crystal_system: str, lattice_params: Union[float, List[float]]
) -> Lattice:
    """Create a lattice from a crystal system name and exactly its parameters."""
    system = _normalize_system(crystal_system)
    names = _LATTICE_PARAMETERS[system]
    if isinstance(lattice_params, Real) and not isinstance(lattice_params, bool):
        values = [float(lattice_params)]
    elif isinstance(lattice_params, (list, tuple, np.ndarray)):
        values = [float(value) for value in lattice_params]
    else:
        raise TypeError(f"lattice_params must be a number or a list of numbers, got {lattice_params!r}")
    if len(values) != len(names):
        raise ValueError(
            f"A {system} lattice takes [{', '.join(names)}], got {len(values)} value(s): {lattice_params!r}"
        )
    p = dict(zip(names, values))
    if system == "cubic":
        return Lattice.cubic(p["a"])
    if system == "tetragonal":
        return Lattice.tetragonal(p["a"], p["c"])
    if system == "orthorhombic":
        return Lattice.orthorhombic(p["a"], p["b"], p["c"])
    if system in ("hexagonal", "trigonal"):
        return Lattice.hexagonal(p["a"], p["c"])
    if system == "monoclinic":
        return Lattice.monoclinic(p["a"], p["b"], p["c"], p["beta"])
    return Lattice.triclinic(p["a"], p["b"], p["c"], p["alpha"], p["beta"], p["gamma"])


def _get_default_space_group(crystal_system: str) -> int:
    """Get default space group for crystal system."""
    return _DEFAULT_SPACE_GROUPS[_normalize_system(crystal_system)]


def _default_hall_number(space_group_number: int) -> int:
    """The Hall number of the standard setting of a space group.

    This is spglib's first setting of the group, except that origin choice 2 is used
    where there are two (as in the International Tables and pymatgen).
    """
    settings = [
        hall for hall in range(1, 531)
        if spglib.get_spacegroup_type(hall).number == space_group_number
    ]
    for hall in settings:
        if spglib.get_spacegroup_type(hall).choice == "2":
            return hall
    return settings[0]


def _generate_from_spglib(
    space_group_number: int,
    species: List[str],
    positions: List[List[float]],
    lattice: Lattice,
    symprec: float = 1e-5,
    angle_tolerance: float = -1.0,
) -> Crystal:
    """Apply the space group's operations to the asymmetric unit.

    The operations come from spglib's database for the standard setting, so
    ``positions`` are fractional coordinates of the conventional cell, e.g.
    Na (0, 0, 0) and Cl (1/2, 1/2, 1/2) in Fm-3m give the 8-atom rocksalt cell.
    """
    positions_array = np.asarray(positions, dtype=float).reshape(-1, 3)
    if len(positions_array) != len(species):
        raise ValueError(
            f"Got {len(species)} species but {len(positions_array)} positions"
        )
    operations = spglib.get_symmetry_from_database(
        _default_hall_number(space_group_number)
    )
    tolerance = max(symprec, 1e-8)

    unique_positions: List[np.ndarray] = []
    unique_species: List[str] = []
    for specie, position in zip(species, positions_array):
        orbit_start = len(unique_positions)
        for rotation, translation in zip(
            operations["rotations"], operations["translations"]
        ):
            image = (rotation @ position + translation) % 1.0
            image[np.isclose(image, 1.0, atol=tolerance)] = 0.0
            duplicate = False
            for existing in unique_positions:
                difference = image - existing
                difference -= np.round(difference)
                if np.allclose(difference, 0.0, atol=tolerance):
                    duplicate = True
                    break
            if not duplicate:
                unique_positions.append(image)
                unique_species.append(specie)
        if len(unique_positions) == orbit_start:
            raise ValueError(
                f"Position {position.tolist()} of {specie} overlaps an earlier atom"
            )

    return Crystal(unique_species, [p.tolist() for p in unique_positions], lattice)


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
) -> Union[Dict[str, List[int]], List[int]]:
    """
    List space groups, optionally filtered by crystal system.

    Args:
        crystal_system: Optional crystal system name to filter (case-insensitive)

    Returns:
        A dict mapping each crystal system to its space group numbers, or, if
        crystal_system is given, the list of its space group numbers

    Examples:
        >>> from matsimpy.builders.bulk.symmetry import list_space_groups_by_system
        >>> list_space_groups_by_system()['Hexagonal'][:3]
        [168, 169, 170]
        >>> len(list_space_groups_by_system('Cubic'))
        36
    """
    if crystal_system is not None:
        low, high = _SYSTEM_RANGES[_normalize_system(crystal_system)]
        return list(range(low, high + 1))
    return {name.capitalize(): list(range(low, high + 1)) for name, (low, high) in _SYSTEM_RANGES.items()}


__all__ = [
    "from_space_group",
    "from_crystal_system",
    "list_space_groups_by_system",
]
