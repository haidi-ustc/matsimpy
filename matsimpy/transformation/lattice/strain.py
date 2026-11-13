"""
Strain and deformation operations for crystal lattices.
"""

from matsimpy.utils.tooling import tool
from typing import List, Union, Optional
import numpy as np
from ...core import Crystal, Lattice
from .._helpers import validate_positive_scalar
from ...utils.validation import validate_matrix3, validate_vector3


def _deformed(crystal: Crystal, deformation: np.ndarray, move_atoms: bool) -> Crystal:
    """Apply the deformation gradient *deformation* (column-vector form, x' = F x).

    Lattice rows transform as ``A' = A @ F.T``.  When *move_atoms* is true the
    atoms follow the lattice (their fractional coordinates are unchanged);
    otherwise their Cartesian positions are kept.
    """
    det = float(np.linalg.det(deformation))
    if det <= 1e-12:
        raise ValueError(
            f"Deformation gradient must have a positive determinant, got {det:.6g} "
            "(a zero or negative determinant collapses or inverts the cell)"
        )
    new_lattice = Lattice(crystal.lattice.matrix @ deformation.T)
    if move_atoms:
        positions = crystal.frac_positions
    else:
        positions = crystal.cart_positions @ new_lattice.inv_matrix
    return Crystal(
        list(crystal.species), positions,
        lattice=new_lattice,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
        site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
    )


@tool
def apply_strain(
    crystal: Crystal,
    strain_matrix: Union[List[List[float]], List[float], np.ndarray],
) -> Crystal:
    """
    Apply a homogeneous strain to a crystal; atoms move with the lattice.

    The deformation gradient is ``F = I + strain``; every Cartesian vector
    (lattice vectors and atomic positions) is mapped by ``x' = F x``, so the
    lattice rows become ``A @ F.T`` and fractional coordinates are unchanged.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure to strain
        strain_matrix: 3x3 strain tensor in Cartesian axes, or three numbers
            giving the normal strains along x, y and z (the diagonal).

    Returns:
        New strained crystal structure

    Raises:
        ValueError: If the strain is not a finite 3x3 matrix or 3-vector, or
            if ``I + strain`` has a non-positive determinant.

    Examples:
        >>> from matsimpy.transformation.lattice import apply_strain
        >>> from matsimpy.builders.bulk import from_prototype
        >>> crystal = from_prototype('sc', 'Po', 3.0)
        >>> # 1% tensile strain along x
        >>> strained = apply_strain(crystal, [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])
        >>> round(float(strained.lattice.a), 4)
        3.03
        >>> round(float(apply_strain(crystal, [0.01, 0, 0]).lattice.a), 4)
        3.03
    """
    raw = np.asarray(strain_matrix, dtype=object)
    if raw.shape == (3,):
        strain = np.diag(validate_vector3("strain_matrix", strain_matrix))
    else:
        strain = validate_matrix3("strain_matrix", strain_matrix)
    return _deformed(crystal, np.eye(3) + strain, move_atoms=True)


@tool
def apply_deformation(
    crystal: Crystal,
    deformation_matrix: Union[List[List[float]], np.ndarray],
    deform_positions: bool = True,
) -> Crystal:
    """
    Apply a general deformation gradient to a crystal.

    Cartesian vectors map as ``x' = F x`` (``F`` = *deformation_matrix*), so the
    lattice rows become ``A @ F.T``.

    Always returns a new crystal structure.

    Args:
        crystal: Crystal structure to deform
        deformation_matrix: 3x3 deformation gradient tensor F
        deform_positions: If True (default), the atoms move with the lattice
            (fractional coordinates unchanged).  If False, the atoms keep
            their Cartesian positions and only the cell changes.

    Returns:
        New deformed crystal structure

    Raises:
        ValueError: If F is not a finite 3x3 matrix with positive determinant.

    Examples:
        >>> from matsimpy.transformation.lattice import apply_deformation
        >>> from matsimpy.builders.bulk import from_prototype
        >>> crystal = from_prototype('sc', 'Po', 3.0)
        >>> # simple shear: x' = x + 0.1 y
        >>> sheared = apply_deformation(crystal, [[1, 0.1, 0], [0, 1, 0], [0, 0, 1]])
        >>> sheared.lattice.matrix[1].round(3)
        array([0.3, 3. , 0. ])
    """
    if not isinstance(deform_positions, (bool, np.bool_)):
        raise TypeError("deform_positions must be a bool")
    deformation = validate_matrix3("deformation_matrix", deformation_matrix)
    return _deformed(crystal, deformation, move_atoms=bool(deform_positions))


@tool
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
        amplitude: Standard deviation (Angstroms) of the Gaussian noise added to
            each lattice-vector component (not a hard maximum)
        seed: Random seed for reproducibility

    Returns:
        New crystal with perturbed lattice vectors

    Examples:
        >>> from matsimpy.transformation.lattice import perturb_lattice
        >>> from matsimpy.builders.bulk import from_prototype
        >>> crystal = from_prototype('diamond', 'Si', 5.43)
        >>> # Gaussian noise with a 0.1 Angstrom standard deviation
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
    new_lattice_vectors = crystal.lattice.matrix + perturbations
    new_lattice = Lattice(new_lattice_vectors)

    return Crystal(
        list(crystal.species), crystal.frac_positions.tolist(),
        lattice=new_lattice,
        coords_are_cartesian=False,
        pbc=list(crystal.pbc),
        site_properties=(list(crystal.site_properties) if crystal.site_properties else None),
    )


__all__ = ["apply_strain", "apply_deformation", "perturb_lattice"]
