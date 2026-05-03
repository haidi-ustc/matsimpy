"""
Strain and deformation operations for crystal lattices.
"""

from typing import List, Union, Optional
import numpy as np
from ...core import Crystal, Lattice
from .._helpers import validate_positive_scalar


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
    strain_matrix = np.array(strain_matrix, dtype=np.float64)

    # Apply strain: new_lattice = (I + strain) * old_lattice
    deformation = np.eye(3) + strain_matrix
    new_lattice_vectors = np.dot(deformation, crystal.lattice.lattice_vectors)
    new_lattice = Lattice(new_lattice_vectors)

    return Crystal(
        list(crystal.species), crystal.frac_positions.tolist(),
        lattice=new_lattice,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
        site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
    )


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
    deformation_matrix = np.array(deformation_matrix, dtype=np.float64)

    # Apply deformation to lattice
    new_lattice_vectors = np.dot(deformation_matrix, crystal.lattice.lattice_vectors)
    new_lattice = Lattice(new_lattice_vectors)

    if deform_positions:
        # Also deform atomic positions (Cartesian)
        new_cart_positions = np.dot(crystal.cart_positions, deformation_matrix.T)
        # Convert back to fractional
        new_positions = np.dot(
            new_cart_positions, np.linalg.inv(new_lattice_vectors)
        )
    else:
        # Keep fractional positions unchanged
        new_positions = crystal.frac_positions

    return Crystal(
        list(crystal.species), new_positions.tolist(),
        lattice=new_lattice,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
        site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
    )


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
    amplitude = validate_positive_scalar("amplitude", amplitude)

    # Generate random perturbations for each lattice vector
    # Shape: (3, 3) - 3 vectors, each with 3 components
    rng = np.random.default_rng(seed)
    perturbations = rng.normal(size=(3, 3)) * amplitude

    # Add perturbations to lattice vectors
    new_lattice_vectors = crystal.lattice.lattice_vectors + perturbations
    new_lattice = Lattice(new_lattice_vectors)

    return Crystal(
        list(crystal.species), crystal.frac_positions.tolist(),
        lattice=new_lattice,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
        site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
    )


__all__ = ["apply_strain", "apply_deformation", "perturb_lattice"]
