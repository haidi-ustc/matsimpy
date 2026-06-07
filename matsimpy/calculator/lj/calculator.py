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
        species_sigma: Optional[dict[str, float]] = None,
        species_epsilon: Optional[dict[str, float]] = None,
        **kwargs,
    ):
        """
        Initialize Lennard-Jones calculator.

        Args:
            sigma: LJ size parameter in Å (default: 3.4 for Ar)
            epsilon: LJ energy parameter in eV (default: 0.0104 for Ar)
            cutoff: Cutoff distance in Å. If None, uses 3*sigma
            rc_smooth: Smoothing distance for cutoff. If None, uses cutoff
            species_sigma: Per-species sigma overrides (e.g. {"Kr": 3.6}).
                Pairs use Lorentz-Berthelot mixing: sigma_ij = (s_i + s_j)/2
            species_epsilon: Per-species epsilon overrides (e.g. {"Kr": 0.014}).
                Pairs use Lorentz-Berthelot mixing: eps_ij = sqrt(eps_i * eps_j)
            **kwargs: Additional parameters (passed to parent)
        """
        super().__init__(sigma=sigma, epsilon=epsilon, **kwargs)

        # Per-species parameter overrides (Lorentz-Berthelot mixing)
        self._species_sigma: dict[str, float] = dict(species_sigma or {})
        self._species_epsilon: dict[str, float] = dict(species_epsilon or {})
        self._default_sigma = sigma
        self._default_epsilon = epsilon

        # Set cutoff
        if cutoff is None:
            cutoff = 3.0 * sigma
        self.parameters["cutoff"] = cutoff

        # Set smoothing distance
        if rc_smooth is None:
            rc_smooth = cutoff
        self.parameters["rc_smooth"] = rc_smooth

    def get_pair_params(self, species_i: str, species_j: str) -> Tuple[float, float]:
        """Get sigma and epsilon for a species pair using Lorentz-Berthelot mixing.

        sigma_ij = (sigma_i + sigma_j) / 2
        epsilon_ij = sqrt(epsilon_i * epsilon_j)

        Args:
            species_i: First species symbol
            species_j: Second species symbol

        Returns:
            (sigma, epsilon) tuple for the pair
        """
        si = self._species_sigma.get(species_i, self._default_sigma)
        sj = self._species_sigma.get(species_j, self._default_sigma)
        ei = self._species_epsilon.get(species_i, self._default_epsilon)
        ej = self._species_epsilon.get(species_j, self._default_epsilon)
        return (si + sj) / 2.0, np.sqrt(ei * ej)

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

        cutoff = self.parameters["cutoff"]
        rc_smooth = self.parameters["rc_smooth"]
        species = list(self.structure.species)

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
                positions, lattice, pbc, species, cutoff, rc_smooth
            )
        else:
            # For non-periodic systems (molecules or non-periodic crystals)
            energy, forces = self._compute_non_periodic(
                positions, species, cutoff, rc_smooth
            )

        # Store results
        self.results["energy"] = energy
        self.results["forces"] = forces
        if lattice is not None:
            self.results["stress"] = stress

    def _compute_non_periodic(
        self,
        positions: np.ndarray,
        species: list[str],
        cutoff: float,
        rc_smooth: float,
    ) -> Tuple[float, np.ndarray]:
        """Compute LJ energy and forces for non-periodic system with per-pair params.

        Args:
            positions: Atomic positions (N, 3)
            species: Species symbols for each atom
            cutoff: Cutoff distance
            rc_smooth: Smoothing distance

        Returns:
            Tuple of (energy, forces)
        """
        n_atoms = len(positions)
        energy = 0.0
        forces = np.zeros((n_atoms, 3))

        # Build KDTree for efficient neighbor finding
        tree = cKDTree(positions)

        # Find all pairs within cutoff
        pairs = tree.query_pairs(cutoff, output_type="ndarray")

        # Compute LJ interactions
        for i, j in pairs:
            r_vec = positions[j] - positions[i]
            r = np.linalg.norm(r_vec)

            if r < cutoff:
                # Get per-pair LJ parameters
                sp_i = species[i]
                sp_j = species[j]
                sigma, epsilon = self.get_pair_params(sp_i, sp_j)
                e0 = 4.0 * epsilon * ((sigma / cutoff) ** 12 - (sigma / cutoff) ** 6)

                if rc_smooth < cutoff and r > rc_smooth:
                    f = 1.0 / (1.0 + np.exp((r - rc_smooth) / (cutoff - rc_smooth)))
                    df_dr = -f * (1.0 - f) / (cutoff - rc_smooth)
                else:
                    f = 1.0
                    df_dr = 0.0

                sr6 = (sigma / r) ** 6
                sr12 = sr6**2
                v = 4.0 * epsilon * (sr12 - sr6) * f
                if rc_smooth >= cutoff:
                    v -= e0
                energy += v

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
        species: list[str],
        cutoff: float,
        rc_smooth: float,
    ) -> Tuple[float, np.ndarray, np.ndarray]:
        """Compute LJ energy and forces for periodic system with per-pair params.

        Uses minimum image convention for periodic boundary conditions.

        Args:
            positions: Atomic positions in Cartesian coordinates
            lattice: Lattice object
            pbc: Periodic boundary conditions [x, y, z]
            species: Species symbols for each atom
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

                    # Get per-pair LJ parameters
                    sigma, epsilon = self.get_pair_params(species[i], species[j])
                    e0 = 4.0 * epsilon * ((sigma / cutoff) ** 12 - (sigma / cutoff) ** 6)

                    pair_energy, force_vec = self._pair_energy_force(
                        r_vec_cart, r, sigma, epsilon, cutoff, rc_smooth
                    )
                    if rc_smooth >= cutoff:
                        pair_energy -= e0
                    energy += 0.5 * pair_energy
                    forces[i] -= force_vec
                    stress += -0.5 * np.outer(force_vec, r_vec_cart)

        # Stress in eV/Å³ (volume is in Å³)
        volume = lattice.volume
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
