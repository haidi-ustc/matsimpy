"""
Supercell generation tools.

Create supercells from unit cells by repeating the unit cell.
"""

from typing import List, Union
import numpy as np
from ...core import Crystal, Lattice


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

    scaling_matrix = np.array(scaling_matrix, dtype=np.int32)

    # Handle simple [a, b, c] format
    if scaling_matrix.ndim == 1:
        if len(scaling_matrix) != 3:
            raise ValueError("Scaling matrix must have 3 elements for [a, b, c] format")
        scaling_matrix = np.diag(scaling_matrix)

    # Validate matrix format
    if scaling_matrix.shape != (3, 3):
        raise ValueError("Scaling matrix must be 3x3 or [a, b, c] format")

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
                                crystal.site_properties[atom_idx].copy()
                            )
    else:
        # General matrix case - use more robust approach
        # Calculate the determinant to get number of unit cells
        det = int(round(np.linalg.det(scaling_matrix)))
        if det <= 0:
            raise ValueError("Scaling matrix must have positive determinant")

        # Generate all translation vectors in the supercell
        # We need to find all integer combinations that satisfy:
        # 0 <= i*a1 + j*b1 + k*c1 < 1, etc.
        # This is complex, so we use a simpler approach: iterate over a reasonable range

        # Estimate range needed based on matrix elements
        max_elem = np.max(np.abs(scaling_matrix))
        range_estimate = max_elem + 2

        for i in range(-range_estimate, range_estimate + 1):
            for j in range(-range_estimate, range_estimate + 1):
                for k in range(-range_estimate, range_estimate + 1):
                    translation = np.array([i, j, k])
                    # Apply inverse scaling matrix to get fractional coordinates in new cell
                    frac_coords = np.linalg.solve(scaling_matrix.T, translation)

                    # Check if these coordinates are within [0, 1) in the supercell
                    if np.all(frac_coords >= 0) and np.all(frac_coords < 1):
                        # This is a valid translation in the supercell
                        for atom_idx, (spec, pos) in enumerate(
                            zip(crystal.species, crystal.frac_positions)
                        ):
                            new_pos = pos + frac_coords
                            new_pos = new_pos % 1.0  # Wrap to [0, 1)

                            new_species.append(spec)
                            new_positions.append(new_pos.tolist())

                            if (
                                new_site_properties is not None
                                and crystal.site_properties
                            ):
                                new_site_properties.append(
                                    crystal.site_properties[atom_idx].copy()
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
    )


__all__ = ["make_supercell"]
