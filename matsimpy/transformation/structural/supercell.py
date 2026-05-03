"""
Supercell generation tools.

Create supercells from unit cells by repeating the unit cell.
"""

import copy
import itertools
from typing import List, Union
import numpy as np
from ...core import Crystal, Lattice
from .._helpers import validate_integer_matrix3


def _translation_representatives(
    scaling_matrix: np.ndarray, det: int
) -> list[np.ndarray]:
    """Find integer lattice translations representing cosets in the supercell."""
    inv_scaling = np.linalg.inv(scaling_matrix.astype(np.float64))
    max_elem = int(np.max(np.abs(scaling_matrix)))
    seen: set[tuple[float, float, float]] = set()
    reps: list[np.ndarray] = []
    tol = 1e-10

    # Expand the search bound until all determinant representatives are found.
    # The loop is bounded but generous for the small transformation matrices this
    # functional helper is intended to support.
    max_bound = max(8, 4 * max_elem + det + 2)
    for bound in range(max(1, max_elem), max_bound + 1):
        for translation in itertools.product(range(-bound, bound + 1), repeat=3):
            translation_vector = np.array(translation, dtype=np.float64)
            frac_in_supercell = translation_vector @ inv_scaling
            if np.all(frac_in_supercell >= -tol) and np.all(
                frac_in_supercell < 1.0 - tol
            ):
                key = tuple(np.round(frac_in_supercell % 1.0, 12))
                if key in seen:
                    continue
                seen.add(key)
                reps.append(translation_vector)
                if len(reps) == det:
                    return reps

    raise RuntimeError(
        "Supercell generation failed: could not find the expected translation "
        f"representatives for determinant {det}."
    )


def make_supercell(
    crystal: Crystal,
    scaling_matrix: Union[List[int], List[List[int]], np.ndarray],
) -> Crystal:
    """
    Create supercell from unit cell.

    This function replicates the unit cell according to the scaling matrix.
    Always returns a new Crystal object. The scaling_matrix can be:
    - Simple: [a, b, c] - repeats a times in a, b times in b, c times in c
    - Matrix: [[a1, a2, a3], [b1, b2, b3], [c1, c2, c3]] - general transformation

    Args:
        crystal: Unit cell to expand
        scaling_matrix: Scaling matrix for supercell generation

    Returns:
        New supercell Crystal structure

    Raises:
        TypeError: If crystal is not a Crystal object
        ValueError: If scaling_matrix is invalid

    Examples:
        >>> from matsimpy.core import Crystal, Lattice
        >>> from matsimpy.transformation import make_supercell
        >>> from matsimpy.builders.bulk import from_prototype
        >>> unit_cell = from_prototype('diamond', 'Si', 5.0)  # Proper diamond structure
        >>> # Simple 2x2x2 supercell
        >>> supercell = make_supercell(unit_cell, [2, 2, 2])
        >>> # General transformation
        >>> supercell = make_supercell(unit_cell, [[2,0,0], [0,2,0], [0,0,2]])
    """
    if not isinstance(crystal, Crystal):
        raise TypeError("make_supercell requires a Crystal object")

    scaling_matrix = np.array(scaling_matrix, dtype=np.float64)

    # Handle simple [a, b, c] format
    if scaling_matrix.ndim == 1:
        if len(scaling_matrix) != 3:
            raise ValueError("Scaling matrix must have 3 elements for [a, b, c] format")
        scaling_matrix = np.diag(scaling_matrix)

    # Validate matrix format
    scaling_matrix = validate_integer_matrix3(
        "scaling_matrix", scaling_matrix, positive_determinant=True
    )

    # Check if matrix is diagonal for simpler processing
    is_diagonal = np.allclose(scaling_matrix, np.diag(np.diag(scaling_matrix)))

    # Calculate new lattice vectors
    new_lattice_vectors = np.dot(scaling_matrix, crystal.lattice.lattice_vectors)
    new_lattice = Lattice(new_lattice_vectors)

    # Generate all atoms in supercell
    new_species = []
    new_positions = []
    new_site_properties = [] if crystal.site_properties else None

    if is_diagonal:
        # Simple diagonal case - use optimized approach
        diag = np.diag(scaling_matrix)
        if np.any(diag <= 0):
            raise ValueError("Diagonal scaling factors must be positive")
        na, nb, nc = diag

        # Generate all translation vectors
        for i in range(na):
            for j in range(nb):
                for k in range(nc):
                    offset = np.array([i, j, k], dtype=np.float64)

                    for atom_idx, (spec, pos) in enumerate(
                        zip(crystal.species, crystal.frac_positions)
                    ):
                        new_pos = pos + offset
                        # Scale by supercell dimensions and wrap to [0, 1)
                        new_pos = new_pos / diag
                        new_pos = new_pos % 1.0

                        new_species.append(spec)
                        new_positions.append(new_pos.tolist())

                        if new_site_properties is not None and crystal.site_properties:
                            new_site_properties.append(
                                copy.deepcopy(crystal.site_properties[atom_idx])
                            )
    else:
        # General matrix case - use more robust approach
        # Calculate the determinant to get number of unit cells
        det = int(round(np.linalg.det(scaling_matrix)))
        inv_scaling = np.linalg.inv(scaling_matrix.astype(np.float64))

        for translation in _translation_representatives(scaling_matrix, det):
            for atom_idx, (spec, pos) in enumerate(
                zip(crystal.species, crystal.frac_positions)
            ):
                # Row-vector convention: r_cart = f_old @ L_old.
                # With L_new = S @ L_old, the new fractional coordinate is
                # (f_old + integer_translation) @ inv(S).
                new_pos = (pos + translation) @ inv_scaling
                new_pos = new_pos % 1.0

                new_species.append(spec)
                new_positions.append(new_pos.tolist())

                if new_site_properties is not None and crystal.site_properties:
                    new_site_properties.append(
                        copy.deepcopy(crystal.site_properties[atom_idx])
                    )

        # Verify we found the correct number of atoms
        expected_atoms = len(crystal.species) * det
        actual_atoms = len(new_species)
        if actual_atoms != expected_atoms:
            raise RuntimeError(
                f"Supercell generation failed: expected {expected_atoms} atoms, "
                f"but found {actual_atoms}. This may indicate an issue with the "
                f"scaling matrix or the algorithm."
            )

    # Always create and return a new crystal
    return Crystal(
        new_species,
        new_positions,
        new_lattice,
        site_properties=new_site_properties,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
    )


__all__ = ["make_supercell"]
