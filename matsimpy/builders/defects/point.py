"""
Point defect builders.

Create various types of point defects in crystal structures.
"""

from matsimpy.utils.tooling import tool
from typing import List, Optional, Union, Tuple
import numpy as np
from ...core import Crystal
from ...transformation.chemical.substitution import substitute

_MIN_DISTANCE = 0.5  # Angstrom; closer atoms are treated as overlapping


def _is_index(value) -> bool:
    return isinstance(value, (int, np.integer)) and not isinstance(value, bool)


def _check_index(structure: Crystal, index, name: str = "index") -> int:
    if not _is_index(index):
        raise TypeError(f"{name} must be an integer, got {index!r}")
    if index < 0 or index >= len(structure):
        raise IndexError(f"Invalid atom index: {index}")
    return int(index)


def _wrap(structure: Crystal, frac: np.ndarray) -> np.ndarray:
    """Wrap fractional coordinates into [0, 1) along the periodic axes only."""
    frac = np.array(frac, dtype=np.float64)
    periodic = np.array(structure.pbc, dtype=bool)
    frac[periodic] = np.mod(frac[periodic], 1.0)
    return frac


def _nearest_distance(structure: Crystal, frac: np.ndarray) -> float:
    """Shortest distance from the point ``frac`` to an atom of ``structure``, with periodic images.

    Exact below ``_MIN_DISTANCE``; larger distances are reported as some value above it.
    """
    if len(structure) == 0:
        return np.inf
    vectors = structure.lattice.get_min_image_vectors(
        structure.frac_positions - frac, structure.pbc, cutoff=_MIN_DISTANCE
    )
    return float(np.linalg.norm(vectors, axis=-1).min())


def _check_free(structure: Crystal, frac: np.ndarray, what: str) -> None:
    distance = _nearest_distance(structure, frac)
    if distance < _MIN_DISTANCE:
        raise ValueError(
            f"{what} at {np.round(frac, 4).tolist()} is {distance:.3f} A from an existing atom"
        )


@tool
def create_vacancy(
    structure: Crystal, indices: Union[int, List[int]]
) -> Crystal:
    """
    Create vacancy defects by removing atoms.

    Args:
        structure: Crystal structure
        indices: Index or list of indices of atoms to remove

    Returns:
        Crystal with vacancies created

    Examples:
        >>> from matsimpy.builders.defects import create_vacancy
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> from matsimpy.transformation.structural import make_supercell
        >>> fcc = make_supercell(from_prototype('fcc', 'Cu', 3.61), [2, 2, 2])  # 8 atoms
        >>>
        >>> # Create single vacancy
        >>> with_vacancy = create_vacancy(fcc, 0)
        >>>
        >>> # Create multiple vacancies
        >>> with_vacancies = create_vacancy(fcc, [0, 1, 2])
    """
    # Delegate to Crystal/Structure remove_atom implementation so all per-atom
    # data (e.g. site_properties) is filtered consistently.
    return structure.remove_atom(indices)


@tool
def create_interstitial(
    structure: Crystal,
    species: Union[str, List[str]],
    positions: Union[List[float], List[List[float]]],
) -> Crystal:
    """
    Create interstitial defects by adding atoms.

    Args:
        structure: Crystal structure
        species: Species or list of species for interstitial atoms
        positions: Fractional position or list of positions; wrapped into the
            cell along periodic axes only. An atom closer than 0.5 A to another
            raises ValueError.

    Returns:
        Crystal with interstitials added

    Examples:
        >>> from matsimpy.builders.defects import create_interstitial
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> from matsimpy.transformation.structural import make_supercell
        >>> fcc = make_supercell(from_prototype('fcc', 'Cu', 3.61), [2, 2, 2])  # 8 atoms
        >>>
        >>> # H on an octahedral site
        >>> with_interstitial = create_interstitial(fcc, 'H', [0.25, 0.25, 0.25])
        >>>
        >>> # octahedral and tetrahedral sites
        >>> with_interstitials = create_interstitial(
        ...     fcc, ['H', 'H'], [[0.25, 0.25, 0.25], [0.625, 0.625, 0.625]]
        ... )
    """
    # Normalize inputs
    if isinstance(species, str):
        species = [species]
    if len(positions) > 0 and isinstance(positions[0], (int, float)):
        positions = [positions]

    if len(species) != len(positions):
        raise ValueError(
            f"Number of species ({len(species)}) must match "
            f"number of positions ({len(positions)})"
        )

    # Add interstitials (chaining new objects)
    result = structure
    for spec, pos in zip(species, positions):
        pos = np.array(pos, dtype=np.float64)
        if pos.ndim != 1 or len(pos) != 3 or not np.all(np.isfinite(pos)):
            raise ValueError("Positions must be finite 3D fractional coordinates")
        pos = _wrap(result, pos)
        _check_free(result, pos, f"Interstitial {spec}")
        result = result.add_atom(spec, pos.tolist())

    return result


@tool
def create_substitution(
    structure: Crystal,
    indices: Union[int, List[int]],
    new_species: Union[str, List[str]],
) -> Crystal:
    """
    Create substitution defects by replacing atoms.

    Args:
        structure: Crystal structure
        indices: Index or list of indices of atoms to substitute
        new_species: New species or list of species

    Returns:
        Crystal with substitutions

    Examples:
        >>> from matsimpy.builders.defects import create_substitution
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> from matsimpy.transformation.structural import make_supercell
        >>> fcc = make_supercell(from_prototype('fcc', 'Cu', 3.61), [2, 2, 2])  # 8 atoms
        >>>
        >>> # Single substitution
        >>> doped = create_substitution(fcc, 0, 'Ni')
        >>>
        >>> # Multiple substitutions
        >>> multi_doped = create_substitution(fcc, [0, 1, 2], ['Ni', 'Ni', 'Zn'])
    """
    # Normalize inputs (substitute function handles this, but we validate first)
    if _is_index(indices):
        indices = [indices]
    indices = [_check_index(structure, i, "indices") for i in indices]
    if isinstance(new_species, str):
        new_species = [new_species]

    if len(indices) != len(new_species):
        raise ValueError(
            f"Number of indices ({len(indices)}) must match "
            f"number of species ({len(new_species)})"
        )

    # Use transformation function for substitution (always returns new structure)
    return substitute(structure, indices, new_species)


@tool
def create_frenkel(
    structure: Crystal,
    index: int,
    interstitial_position: List[float],
) -> Crystal:
    """
    Create a Frenkel pair: move an atom from its site to an interstitial position.

    Args:
        structure: Crystal structure
        index: Index of the atom to move (its site becomes the vacancy)
        interstitial_position: Fractional coordinates of the interstitial site; it
            must be at least 0.5 A from every remaining atom

    Returns:
        Crystal with the Frenkel pair (the moved atom is last)

    Examples:
        >>> from matsimpy.builders.defects import create_frenkel
        >>> from matsimpy.core import Crystal, Lattice
        >>> agbr = Crystal(['Ag'] * 4 + ['Br'] * 4,
        ...                [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5],
        ...                 [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5], [0.5, 0.5, 0.5]],
        ...                Lattice.cubic(5.77))
        >>> # move Ag 0 to the tetrahedral interstitial site
        >>> frenkel = create_frenkel(agbr, 0, [0.25, 0.25, 0.25])
    """
    index = _check_index(structure, index)
    position = np.array(interstitial_position, dtype=np.float64)
    if position.shape != (3,) or not np.all(np.isfinite(position)):
        raise ValueError("Interstitial position must be finite 3D fractional coordinates")

    species = structure.species[index]
    properties = dict(structure.site_properties[index]) if structure.site_properties else None
    result = structure.remove_atom(index)
    position = _wrap(result, position)
    _check_free(result, position, "Interstitial")
    if properties:
        return result.add_atom(species, position.tolist(), site_properties=properties)
    return result.add_atom(species, position.tolist())


@tool
def create_schottky(
    structure: Crystal,
    indices: Optional[List[int]] = None,
    seed: Optional[int] = None,
) -> Crystal:
    """
    Create a Schottky defect: remove a stoichiometric set of atoms.

    Removing whole formula units keeps an ionic crystal charge neutral.

    Args:
        structure: Crystal structure
        indices: Atoms to remove; their composition must be a whole multiple of
            the structure's reduced formula. If None, one formula unit is removed,
            choosing the atoms of each element at random.
        seed: Random seed for the choice when indices is None

    Returns:
        Crystal with the Schottky defect

    Examples:
        >>> from matsimpy.builders.defects import create_schottky
        >>> from matsimpy.core import Crystal, Lattice
        >>> nacl = Crystal(['Na'] * 4 + ['Cl'] * 4,
        ...                [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5],
        ...                 [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5], [0.5, 0.5, 0.5]],
        ...                Lattice.cubic(5.64))
        >>> create_schottky(nacl, seed=0).formula
        'Na3Cl3'
        >>> create_schottky(nacl, indices=[0, 4]).formula
        'Na3Cl3'
    """
    elements = list(dict.fromkeys(structure.species))
    counts = np.array([structure.species.count(e) for e in elements])
    unit = counts // np.gcd.reduce(counts)
    if indices is None:
        rng = np.random.default_rng(seed)
        indices = []
        for element, n in zip(elements, unit):
            sites = [i for i, s in enumerate(structure.species) if s == element]
            indices.extend(int(i) for i in rng.choice(sites, size=int(n), replace=False))
    else:
        indices = [_check_index(structure, i, "indices") for i in indices]
        if len(set(indices)) != len(indices):
            raise ValueError("indices must not repeat")
        removed = np.array([sum(structure.species[i] == e for i in indices) for e in elements])
        multiple = removed[0] / unit[0]
        if multiple == 0 or not multiple.is_integer() or not np.array_equal(removed, unit * int(multiple)):
            formula = "".join(f"{e}{n if n > 1 else ''}" for e, n in zip(elements, unit))
            raise ValueError(
                f"The atoms removed ({dict(zip(elements, removed.tolist()))}) are not whole "
                f"formula units of {formula}, so the defect would not be neutral"
            )
    if len(indices) >= len(structure):
        raise ValueError("A Schottky defect cannot remove every atom")
    return create_vacancy(structure, sorted(indices))


@tool
def create_antisite(
    structure: Crystal, index1: int, index2: int
) -> Crystal:
    """
    Create antisite defect: swap two different atoms.

    Args:
        structure: Crystal structure
        index1: Index of first atom
        index2: Index of second atom

    Returns:
        Crystal with antisite defect

    Examples:
        >>> from matsimpy.builders.defects import create_antisite
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> # Create structure
        >>> gan = from_prototype('zincblende', ['Ga', 'N'], 4.5)
        >>>
        >>> # Create antisite defect (Ga-N swap)
        >>> with_antisite = create_antisite(gan, 0, 1)
    """
    index1 = _check_index(structure, index1, "index1")
    index2 = _check_index(structure, index2, "index2")
    if index1 == index2:
        raise ValueError("Cannot swap atom with itself")
    if structure.species[index1] == structure.species[index2]:
        raise ValueError(
            f"Atoms {index1} and {index2} are both {structure.species[index1]}; "
            "an antisite swaps atoms of different species"
        )

    # Antisite defects exchange species on fixed lattice sites.
    # Build new species list with swapped species at the given indices.
    species_list = list(structure.species)
    species_list[index1], species_list[index2] = species_list[index2], species_list[index1]

    return Crystal(
        species_list, structure.frac_positions.tolist(),
        lattice=structure.lattice,
        coords_are_cartesian=False,
        pbc=list(structure.pbc),
        site_properties=(list(structure.site_properties) if structure.site_properties else None),
    )


__all__ = [
    "create_vacancy",
    "create_interstitial",
    "create_substitution",
    "create_frenkel",
    "create_schottky",
    "create_antisite",
]
