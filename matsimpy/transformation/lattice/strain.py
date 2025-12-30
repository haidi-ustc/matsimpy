"""
Strain and deformation operations for crystal lattices.
"""

from typing import List, Union, Optional
import numpy as np
from ...core import Crystal, Lattice


def apply_strain(
    crystal: Crystal,
    strain_matrix: Union[List[List[float]], np.ndarray],
) -> Crystal:
    """
    Apply strain to crystal structure.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure to strain
        strain_matrix: 3x3 strain tensor

    Returns:
        New strained crystal structure

    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.transformation.lattice import apply_strain
        >>> from matsimpy.builders.bulk import from_prototype
        >>> crystal = from_prototype('diamond', 'Si', 5.43)  # Proper diamond structure
        >>> # Apply 1% tensile strain in x direction
        >>> strain = [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]]
        >>> strained = apply_strain(crystal, strain)
    """
    # Always create a new crystal
    crystal = crystal.copy()

    strain_matrix = np.array(strain_matrix, dtype=np.float64)

    # Apply strain: new_lattice = (I + strain) * old_lattice
    deformation = np.eye(3) + strain_matrix
    new_lattice_vectors = np.dot(deformation, crystal.lattice.lattice_vectors)

    crystal.lattice = Lattice(new_lattice_vectors)

    # Update Cartesian positions (fractional positions stay the same in strain)
    crystal.cart_positions = crystal._convert_to_cartesian()
    crystal._neighbor_tree = None
    crystal._neighbor_tree_positions = None

    return crystal


def apply_deformation(
    crystal: Crystal,
    deformation_matrix: Union[List[List[float]], np.ndarray],
    deform_positions: bool = True,
) -> Crystal:
    """
    Apply general deformation to crystal structure.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure to deform
        deformation_matrix: 3x3 deformation gradient tensor
        deform_positions: If True, also deform atomic positions

    Returns:
        New deformed crystal structure

    Examples:
        >>> from matsimpy.transformation.lattice import apply_deformation
        >>> import numpy as np
        >>> # Apply shear deformation
        >>> shear = [[1, 0.1, 0], [0, 1, 0], [0, 0, 1]]
        >>> deformed = apply_deformation(crystal, shear)
    """
    # Always create a new crystal
    crystal = crystal.copy()

    deformation_matrix = np.array(deformation_matrix, dtype=np.float64)

    # Apply deformation to lattice
    new_lattice_vectors = np.dot(deformation_matrix, crystal.lattice.lattice_vectors)
    crystal.lattice = Lattice(new_lattice_vectors)

    if deform_positions:
        # Also deform atomic positions (Cartesian)
        new_cart_positions = np.dot(crystal.cart_positions, deformation_matrix.T)
        # Convert back to fractional
        crystal.positions = np.dot(
            new_cart_positions, np.linalg.inv(new_lattice_vectors)
        )
        crystal.frac_positions = crystal.positions
        crystal.cart_positions = new_cart_positions
    else:
        # Keep fractional positions, update Cartesian
        crystal.cart_positions = crystal._convert_to_cartesian()

    crystal._neighbor_tree = None
    crystal._neighbor_tree_positions = None
    crystal._sites = crystal._initialize_sites()

    return crystal


def perturb_lattice(
    crystal: Crystal,
    amplitude: float,
    seed: Optional[int] = None,
) -> Crystal:
    """
    Add random perturbations to lattice vectors.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure to perturb
        amplitude: Maximum perturbation amplitude (Angstroms) for lattice vectors
        seed: Random seed for reproducibility

    Returns:
        New crystal with perturbed lattice vectors

    Examples:
        >>> from matsimpy.transformation.lattice import perturb_lattice
        >>> from matsimpy.builders.bulk import from_prototype
        >>> crystal = from_prototype('diamond', 'Si', 5.43)
        >>> # Perturb lattice vectors by up to 0.1 Angstrom
        >>> perturbed = perturb_lattice(crystal, 0.1)
        >>> # With random seed for reproducibility
        >>> perturbed = perturb_lattice(crystal, 0.05, seed=42)
    """
    # Always create a new crystal
    crystal = crystal.copy()

    if seed is not None:
        np.random.seed(seed)

    # Generate random perturbations for each lattice vector
    # Shape: (3, 3) - 3 vectors, each with 3 components
    perturbations = np.random.randn(3, 3) * amplitude

    # Add perturbations to lattice vectors
    new_lattice_vectors = crystal.lattice.lattice_vectors + perturbations
    crystal.lattice = Lattice(new_lattice_vectors)

    # Update Cartesian positions (fractional positions stay the same)
    crystal.cart_positions = crystal._convert_to_cartesian()
    crystal._sites = crystal._initialize_sites()
    crystal._neighbor_tree = None
    crystal._neighbor_tree_positions = None

    return crystal


__all__ = ["apply_strain", "apply_deformation", "perturb_lattice"]
