"""
Atom organization operations (sort, center, perturb).

Works for both Crystal and Molecule structures.
"""

from typing import List, Optional, Union, Callable
import numpy as np
from ...core import Crystal, Molecule


def sort_atoms(
    structure: Union[Crystal, Molecule],
    key: Union[str, Callable] = "species",
    reverse: bool = False,
    inplace: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Sort atoms by various criteria.

    Args:
        structure: Crystal or Molecule structure
        key: Sort key - 'species', 'z' (atomic number), 'mass',
             'distance' (from origin), or custom function
        reverse: If True, reverse sort order
        inplace: If True, modify structure in-place

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

    if not inplace:
        structure = structure.copy()

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

    # Reorder species and positions
    new_species = tuple(structure.species[i] for i in sorted_indices)
    new_positions = structure.positions[sorted_indices]

    structure.species = new_species
    structure.positions = new_positions

    if isinstance(structure, Crystal):
        structure.frac_positions = new_positions
        structure.cart_positions = structure._convert_to_cartesian()
        structure._sites = structure._initialize_sites()
    else:
        structure.positions = new_positions

    # Invalidate caches
    structure._neighbor_tree = None
    structure._neighbor_tree_positions = None
    structure._formula_dirty = True
    structure._cached_composition = None

    return structure


def center_structure(
    structure: Union[Crystal, Molecule],
    center: Optional[List[float]] = None,
    inplace: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Center structure at a specific position.

    Args:
        structure: Crystal or Molecule structure
        center: Target center position (default: origin)
        inplace: If True, modify structure in-place

    Returns:
        Centered structure

    Examples:
        >>> from matsimpy.transformation.atomic import center_structure
        >>> # Center at origin
        >>> centered = center_structure(molecule)
        >>> # Center at specific point
        >>> centered = center_structure(molecule, center=[5, 5, 5])
    """
    if not inplace:
        structure = structure.copy()

    if center is None:
        center = np.array([0.0, 0.0, 0.0])
    else:
        center = np.array(center, dtype=np.float64)

    if isinstance(structure, Molecule):
        # Get current center of mass
        current_center = structure.get_center_of_mass()
        displacement = center - current_center

        # Move all atoms
        structure.positions += displacement

    else:
        # For crystals, center in fractional coordinates
        current_center = np.mean(structure.positions, axis=0)
        displacement = center - current_center

        structure.positions += displacement
        structure.frac_positions = structure.positions
        structure.cart_positions = structure._convert_to_cartesian()
        structure._sites = structure._initialize_sites()

    # Invalidate caches
    structure._neighbor_tree = None
    structure._neighbor_tree_positions = None

    return structure


def perturb_positions(
    structure: Union[Crystal, Molecule],
    amplitude: float,
    indices: Optional[List[int]] = None,
    seed: Optional[int] = None,
    inplace: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Add random perturbations to atomic positions.

    Args:
        structure: Crystal or Molecule structure
        amplitude: Maximum perturbation amplitude (Angstroms)
        indices: Atom indices to perturb (default: all atoms)
        seed: Random seed for reproducibility
        inplace: If True, modify structure in-place

    Returns:
        Structure with perturbed positions

    Examples:
        >>> from matsimpy.transformation.atomic import perturb_positions
        >>> # Perturb all atoms by up to 0.1 Angstrom
        >>> perturbed = perturb_positions(structure, 0.1)
        >>> # Perturb specific atoms
        >>> perturbed = perturb_positions(structure, 0.1, indices=[0, 1, 2])
    """
    if not inplace:
        structure = structure.copy()

    if seed is not None:
        np.random.seed(seed)

    if indices is None:
        indices = list(range(len(structure.species)))

    # Generate random perturbations
    perturbations = np.random.randn(len(indices), 3) * amplitude

    if isinstance(structure, Crystal):
        # Convert Cartesian perturbations to fractional
        frac_perturbations = np.dot(
            perturbations, np.linalg.inv(structure.lattice.lattice_vectors)
        )

        new_positions = structure.positions.copy()
        for i, idx in enumerate(indices):
            new_positions[idx] += frac_perturbations[i]

        structure.positions = new_positions
        structure.frac_positions = new_positions
        structure.cart_positions = structure._convert_to_cartesian()
        structure._sites = structure._initialize_sites()

    else:
        new_positions = structure.positions.copy()
        for i, idx in enumerate(indices):
            new_positions[idx] += perturbations[i]

        structure.positions = new_positions

    # Invalidate caches
    structure._neighbor_tree = None
    structure._neighbor_tree_positions = None

    return structure


__all__ = ["sort_atoms", "center_structure", "perturb_positions"]
