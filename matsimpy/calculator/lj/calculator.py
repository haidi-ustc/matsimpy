"""
Lennard-Jones potential calculator.

Implements the Lennard-Jones (LJ) potential for classical simulations.
The LJ potential is commonly used for noble gases and simple molecular systems.
"""

import numpy as np
from typing import Optional, Tuple
from scipy.spatial import cKDTree
from ..base import Calculator
from ...core import Crystal, Molecule


class LennardJones(Calculator):
    """
    Lennard-Jones potential calculator.

    The Lennard-Jones potential is given by:
        V(r) = 4*epsilon * [(sigma/r)^12 - (sigma/r)^6]

    where:
        - epsilon: Well depth (energy parameter)
        - sigma: Distance at which potential is zero (size parameter)
        - r: Distance between atoms

    Attributes:
        sigma (float): LJ size parameter in Å
        epsilon (float): LJ energy parameter in eV
        cutoff (float): Cutoff distance in Å (default: 3*sigma)
        rc_smooth (float): Smoothing distance for cutoff (default: cutoff)

    Example:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.calculator import LennardJones
        >>>
        >>> # Create Ar crystal
        >>> crystal = Crystal(['Ar'], [[0,0,0]], Lattice.cubic(5.0))
        >>> calc = LennardJones(sigma=3.4, epsilon=0.0104)
        >>> crystal.calc = calc
        >>> calc.calculate(crystal)
        >>> energy = calc.get_potential_energy()
    """

    def __init__(
        self,
        sigma: float = 3.4,
        epsilon: float = 0.0104,
        cutoff: Optional[float] = None,
        rc_smooth: Optional[float] = None,
        **kwargs,
    ):
        """
        Initialize Lennard-Jones calculator.

        Args:
            sigma: LJ size parameter in Å (default: 3.4 for Ar)
            epsilon: LJ energy parameter in eV (default: 0.0104 for Ar)
            cutoff: Cutoff distance in Å. If None, uses 3*sigma
            rc_smooth: Smoothing distance for cutoff. If None, uses cutoff
            **kwargs: Additional parameters (passed to parent)
        """
        super().__init__(sigma=sigma, epsilon=epsilon, **kwargs)

        # Set cutoff
        if cutoff is None:
            cutoff = 3.0 * sigma
        self.parameters["cutoff"] = cutoff

        # Set smoothing distance
        if rc_smooth is None:
            rc_smooth = cutoff
        self.parameters["rc_smooth"] = rc_smooth

    def _compute(self) -> None:
        """
        Compute LJ energy and forces.

        Stores results in self.results:
            - 'energy': Total potential energy in eV
            - 'forces': Forces array of shape (N, 3) in eV/Å
            - 'stress': Stress tensor (for crystals) in eV/Å³
        """
        if self.structure is None:
            raise ValueError("Structure not set. Call calculate(structure) first.")

        sigma = self.parameters["sigma"]
        epsilon = self.parameters["epsilon"]
        cutoff = self.parameters["cutoff"]
        rc_smooth = self.parameters["rc_smooth"]

        # Get positions (always use Cartesian)
        if isinstance(self.structure, Crystal):
            positions = self.structure.cart_positions
            lattice = self.structure.lattice
            pbc = self.structure.pbc
        else:
            # Molecule uses positions directly (Cartesian)
            positions = np.array(self.structure.positions)
            lattice = None
            pbc = [False, False, False]

        n_atoms = len(positions)
        energy = 0.0
        forces = np.zeros((n_atoms, 3))
        stress = np.zeros((3, 3))

        # Build neighbor list using KDTree
        if lattice is not None and any(pbc):
            # For periodic systems, use minimum image convention
            energy, forces, stress = self._compute_periodic(
                positions, lattice, pbc, sigma, epsilon, cutoff, rc_smooth
            )
        else:
            # For non-periodic systems (molecules or non-periodic crystals)
            energy, forces = self._compute_non_periodic(
                positions, sigma, epsilon, cutoff, rc_smooth
            )

        # Store results
        self.results["energy"] = energy
        self.results["forces"] = forces
        if lattice is not None:
            self.results["stress"] = stress

    def _compute_non_periodic(
        self,
        positions: np.ndarray,
        sigma: float,
        epsilon: float,
        cutoff: float,
        rc_smooth: float,
    ) -> Tuple[float, np.ndarray]:
        """
        Compute LJ energy and forces for non-periodic system.

        Args:
            positions: Atomic positions (N, 3)
            sigma: LJ size parameter
            epsilon: LJ energy parameter
            cutoff: Cutoff distance
            rc_smooth: Smoothing distance

        Returns:
            Tuple of (energy, forces)
        """
        n_atoms = len(positions)
        energy = 0.0
        forces = np.zeros((n_atoms, 3))
        e0 = 4.0 * epsilon * ((sigma / cutoff) ** 12 - (sigma / cutoff) ** 6)

        # Build KDTree for efficient neighbor finding
        tree = cKDTree(positions)

        # Find all pairs within cutoff
        pairs = tree.query_pairs(cutoff, output_type="ndarray")

        # Compute LJ interactions
        for i, j in pairs:
            r_vec = positions[j] - positions[i]
            r = np.linalg.norm(r_vec)

            if r < cutoff:
                # Apply smoothing function if rc_smooth < cutoff
                if rc_smooth < cutoff and r > rc_smooth:
                    # Smooth cutoff function (shifted Fermi)
                    f = 1.0 / (1.0 + np.exp((r - rc_smooth) / (cutoff - rc_smooth)))
                    df_dr = -f * (1.0 - f) / (cutoff - rc_smooth)
                else:
                    f = 1.0
                    df_dr = 0.0

                # LJ potential: V(r) = 4*epsilon * [(sigma/r)^12 - (sigma/r)^6]
                sr6 = (sigma / r) ** 6
                sr12 = sr6**2
                v = 4.0 * epsilon * (sr12 - sr6) * f
                if rc_smooth >= cutoff:
                    v -= e0
                energy += v

                # Force: F = -dV/dr * r_hat
                # dV/dr = 4*epsilon * [12*sigma^12/r^13 - 6*sigma^6/r^7] * f
                #        + 4*epsilon * (sr12 - sr6) * df_dr
                dv_dr = (
                    4.0
                    * epsilon
                    * ((12.0 * sr12 - 6.0 * sr6) / r * f + (sr12 - sr6) * df_dr)
                )
                force_vec = dv_dr * r_vec / r

                forces[i] -= force_vec
                forces[j] += force_vec

        return energy, forces

    def _compute_periodic(
        self,
        positions: np.ndarray,
        lattice,
        pbc: list,
        sigma: float,
        epsilon: float,
        cutoff: float,
        rc_smooth: float,
    ) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Compute LJ energy and forces for periodic system.

        Uses minimum image convention for periodic boundary conditions.

        Args:
            positions: Atomic positions in Cartesian coordinates
            lattice: Lattice object
            pbc: Periodic boundary conditions [x, y, z]
            sigma: LJ size parameter
            epsilon: LJ energy parameter
            cutoff: Cutoff distance
            rc_smooth: Smoothing distance

        Returns:
            Tuple of (energy, forces, stress)
        """
        n_atoms = len(positions)
        energy = 0.0
        forces = np.zeros((n_atoms, 3))
        stress = np.zeros((3, 3))

        positions = np.array(positions, dtype=float)
        offsets = self._periodic_offsets(lattice, pbc, cutoff)
        e0 = 4.0 * epsilon * ((sigma / cutoff) ** 12 - (sigma / cutoff) ** 6)

        for offset in offsets:
            shift = np.dot(offset, lattice.matrix)
            same_cell = tuple(int(x) for x in offset) == (0, 0, 0)

            for i in range(n_atoms):
                for j in range(n_atoms):
                    if same_cell and i == j:
                        continue

                    r_vec_cart = positions[j] + shift - positions[i]
                    r = np.linalg.norm(r_vec_cart)
                    if not (1e-10 < r < cutoff):
                        continue

                    pair_energy, force_vec = self._pair_energy_force(
                        r_vec_cart, r, sigma, epsilon, cutoff, rc_smooth
                    )
                    if rc_smooth >= cutoff:
                        pair_energy -= e0
                    energy += 0.5 * pair_energy
                    forces[i] -= force_vec
                    stress += -0.5 * np.outer(force_vec, r_vec_cart)

        # Stress in eV/Å³ (volume is in Å³)
        volume = lattice.volume  # volume is a property
        if volume > 0:
            stress = stress / volume

        return energy, forces, stress

    def _periodic_offsets(self, lattice, pbc: list, cutoff: float) -> np.ndarray:
        """Return periodic image offsets covering neighbors within the cutoff."""
        ranges = []
        inv_matrix = lattice.inv_matrix
        for axis, periodic in enumerate(pbc):
            if not periodic:
                ranges.append(np.array([0], dtype=int))
                continue
            plane_spacing = 1.0 / np.linalg.norm(inv_matrix[:, axis])
            n_images = int(np.ceil(cutoff / plane_spacing)) + 1
            ranges.append(np.arange(-n_images, n_images + 1, dtype=int))

        offsets = []
        for nx in ranges[0]:
            for ny in ranges[1]:
                for nz in ranges[2]:
                    offset = (int(nx), int(ny), int(nz))
                    offsets.append(offset)
        return np.array(offsets, dtype=int)

    @staticmethod
    def _pair_energy_force(
        r_vec: np.ndarray,
        r: float,
        sigma: float,
        epsilon: float,
        cutoff: float,
        rc_smooth: float,
    ) -> Tuple[float, np.ndarray]:
        if rc_smooth < cutoff and r > rc_smooth:
            f = 1.0 / (1.0 + np.exp((r - rc_smooth) / (cutoff - rc_smooth)))
            df_dr = -f * (1.0 - f) / (cutoff - rc_smooth)
        else:
            f = 1.0
            df_dr = 0.0

        sr6 = (sigma / r) ** 6
        sr12 = sr6**2
        energy = 4.0 * epsilon * (sr12 - sr6) * f
        dv_dr = 4.0 * epsilon * (
            (12.0 * sr12 - 6.0 * sr6) / r * f + (sr12 - sr6) * df_dr
        )
        force_vec = dv_dr * r_vec / r
        return energy, force_vec


__all__ = ["LennardJones"]
