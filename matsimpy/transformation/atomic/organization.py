"""
Atom organization operations (sort, center, perturb).

Works for both Crystal and Molecule structures.
"""

from typing import List, Optional, Union, Callable
import numpy as np
from ...core import Crystal, Molecule
from .._helpers import (
    copy_site_properties,
    rebuild_structure,
    site_properties_for_indices,
    validate_positive_scalar,
    validate_vector3,
)


def sort_atoms(
    structure: Union[Crystal, Molecule],
    key: Union[str, Callable] = "species",
    reverse: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Sort atoms by various criteria.

    Always returns a new structure. For in-place modification, use the
    structure's methods directly.

    Args:
        structure: Crystal or Molecule structure
        key: Sort key - 'species', 'z' (atomic number), 'mass',
             'distance' (from origin), or custom function
        reverse: If True, reverse sort order

    Returns:
        Structure with sorted atoms

    Examples:
        >>> from matsimpy.transformation.atomic import sort_atoms
        >>> # Sort by species (alphabetically)
        >>> sorted_struct = sort_atoms(structure, key='species')
        >>> # Sort by atomic number
        >>> sorted_struct = sort_atoms(structure, key='z')
        >>> # Sort by distance from origin
        >>> sorted_struct = sort_atoms(structure, key='distance')
    """
    from ...core import Element

    # Create list of (index, key_value) tuples
    n_atoms = len(structure.species)

    if key == "species":
        keys = [(i, structure.species[i]) for i in range(n_atoms)]
    elif key == "z":
        keys = [(i, structure.elements[i].atomic_no) for i in range(n_atoms)]
    elif key == "mass":
        keys = [(i, structure.elements[i].atomic_mass) for i in range(n_atoms)]
    elif key == "distance":
        if isinstance(structure, Crystal):
            distances = np.linalg.norm(structure.cart_positions, axis=1)
        else:
            distances = np.linalg.norm(structure.positions, axis=1)
        keys = [(i, distances[i]) for i in range(n_atoms)]
    elif callable(key):
        keys = [(i, key(structure, i)) for i in range(n_atoms)]
    else:
        raise ValueError(f"Unknown sort key: {key}")

    # Sort
    sorted_indices = [
        idx for idx, _ in sorted(keys, key=lambda x: x[1], reverse=reverse)
    ]

    # Build sorted species and positions
    new_species = [structure.species[i] for i in sorted_indices]

    if isinstance(structure, Crystal):
        new_positions = [structure.frac_positions[i].tolist() for i in sorted_indices]
        return rebuild_structure(
            structure,
            new_species,
            new_positions,
            coords_are_cartesian=False,
            site_properties=site_properties_for_indices(structure, sorted_indices),
        )
    else:
        new_positions = [structure.positions[i].tolist() for i in sorted_indices]
        return rebuild_structure(
            structure,
            new_species,
            new_positions,
            site_properties=site_properties_for_indices(structure, sorted_indices),
        )


def center_structure(
    structure: Union[Crystal, Molecule],
    center: Optional[List[float]] = None,
) -> Union[Crystal, Molecule]:
    """
    Center structure at a specific position.

    Always returns a new structure. For in-place modification, use the
    structure's methods directly.

    Args:
        structure: Crystal or Molecule structure
        center: Target center position (default: origin)

    Returns:
        Centered structure

    Examples:
        >>> from matsimpy.transformation.atomic import center_structure
        >>> # Center at origin
        >>> centered = center_structure(molecule)
        >>> # Center at specific point
        >>> centered = center_structure(molecule, center=[5, 5, 5])
    """
    if center is None:
        center = np.array([0.0, 0.0, 0.0])
    else:
        center = validate_vector3("center", center)

    if isinstance(structure, Molecule):
        # Get current center of mass
        current_center = structure.get_center_of_mass()
        displacement = center - current_center

        # Move all atoms
        new_positions = structure.positions + displacement

        return rebuild_structure(
            structure,
            list(structure.species),
            new_positions.tolist(),
            site_properties=copy_site_properties(structure),
        )

    else:
        # For crystals, center in fractional coordinates
        frac_pos = structure.frac_positions
        current_center = np.mean(frac_pos, axis=0)
        displacement = center - current_center

        new_positions = frac_pos + displacement

        return rebuild_structure(
            structure,
            list(structure.species),
            new_positions.tolist(),
            coords_are_cartesian=False,
            site_properties=copy_site_properties(structure),
        )


def perturb_positions(
    structure: Union[Crystal, Molecule],
    amplitude: float,
    indices: Optional[List[int]] = None,
    seed: Optional[int] = None,
) -> Union[Crystal, Molecule]:
    """
    Add random perturbations to atomic positions.

    Always returns a new structure. For in-place modification, use the
    structure's methods directly.

    Args:
        structure: Crystal or Molecule structure
        amplitude: Maximum perturbation amplitude (Angstroms)
        indices: Atom indices to perturb (default: all atoms)
        seed: Random seed for reproducibility

    Returns:
        Structure with perturbed positions

    Examples:
        >>> from matsimpy.transformation.atomic import perturb_positions
        >>> # Perturb all atoms by up to 0.1 Angstrom
        >>> perturbed = perturb_positions(structure, 0.1)
        >>> # Perturb specific atoms
        >>> perturbed = perturb_positions(structure, 0.1, indices=[0, 1, 2])
    """
    amplitude = validate_positive_scalar("amplitude", amplitude)

    if indices is None:
        indices = list(range(len(structure.species)))

    # Generate random perturbations (Cartesian) without mutating NumPy global RNG state.
    rng = np.random.default_rng(seed)
    perturbations = rng.normal(size=(len(indices), 3)) * amplitude

    if isinstance(structure, Crystal):
        # Convert Cartesian perturbations to fractional
        frac_perturbations = np.dot(
            perturbations, np.linalg.inv(structure.lattice.lattice_vectors)
        )

        new_positions = structure.frac_positions.copy()
        for i, idx in enumerate(indices):
            new_positions[idx] += frac_perturbations[i]

        return rebuild_structure(
            structure,
            list(structure.species),
            new_positions.tolist(),
            coords_are_cartesian=False,
            site_properties=copy_site_properties(structure),
        )

    # Molecule: apply Cartesian perturbations
    new_positions = structure.positions.copy()
    for i, idx in enumerate(indices):
        new_positions[idx] += perturbations[i]

    return rebuild_structure(
        structure,
        list(structure.species),
        new_positions.tolist(),
        site_properties=copy_site_properties(structure),
    )


__all__ = ["sort_atoms", "center_structure", "perturb_positions"]
