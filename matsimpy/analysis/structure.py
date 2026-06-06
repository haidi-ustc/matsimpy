"""Global geometric property analysis."""

import numpy as np
from typing import Optional, Union
from ..core import Crystal, Molecule


class StructureAnalyzer:
    """Global geometric property analysis for Crystal and Molecule.

    Computes center of mass, radius of gyration, inertia tensor, density,
    and pair distances. Wraps a Structure for cached repeated analysis.

    Usage::

        >>> analyzer = StructureAnalyzer(crystal)
        >>> com = analyzer.center_of_mass()
        >>> rgyr = analyzer.radius_of_gyration()
        >>> I = analyzer.inertia_tensor()
    """

    def __init__(self, structure: Union[Crystal, Molecule]):
        self.structure = structure

    def _get_masses(self) -> np.ndarray:
        """Get atomic masses in amu."""
        from ..core.periodic_table import Element
        masses = []
        for s in self.structure.species:
            el = Element.get_element(s)
            masses.append(el.atomic_mass if el and el.atomic_mass else 1.0)
        return np.array(masses)

    def center_of_mass(self) -> np.ndarray:
        """Mass-weighted center of mass as (3,) array in Cartesian coordinates."""
        masses = self._get_masses()
        pos = self.structure.positions
        total_mass = np.sum(masses)
        if total_mass == 0:
            return np.zeros(3)
        return np.sum(pos * masses[:, np.newaxis], axis=0) / total_mass

    def radius_of_gyration(self) -> float:
        """Radius of gyration — measure of structural compactness."""
        com = self.center_of_mass()
        masses = self._get_masses()
        pos = self.structure.positions
        total_mass = np.sum(masses)
        if total_mass == 0:
            return 0.0
        r2 = np.sum(masses * np.sum((pos - com) ** 2, axis=1)) / total_mass
        return float(np.sqrt(r2))

    def inertia_tensor(self) -> np.ndarray:
        """3×3 moment of inertia tensor in Cartesian coordinates."""
        com = self.center_of_mass()
        masses = self._get_masses()
        pos = self.structure.positions - com
        I = np.zeros((3, 3))
        for m, r in zip(masses, pos):
            I[0, 0] += m * (r[1]**2 + r[2]**2)
            I[1, 1] += m * (r[0]**2 + r[2]**2)
            I[2, 2] += m * (r[0]**2 + r[1]**2)
            I[0, 1] -= m * r[0] * r[1]
            I[0, 2] -= m * r[0] * r[2]
            I[1, 2] -= m * r[1] * r[2]
        I[1, 0] = I[0, 1]
        I[2, 0] = I[0, 2]
        I[2, 1] = I[1, 2]
        return I

    def principal_axes(self) -> tuple[np.ndarray, np.ndarray]:
        """Principal axes (eigenvectors) and moments (eigenvalues)."""
        I = self.inertia_tensor()
        eigenvalues, eigenvectors = np.linalg.eigh(I)
        return eigenvectors, eigenvalues

    def pair_distance(self, i: int, j: int) -> float:
        """Distance between atoms i and j (PBC-aware for crystals)."""
        pos = self.structure.positions
        d = pos[i] - pos[j]
        if isinstance(self.structure, Crystal):
            frac = self.structure.lattice.get_fractional_coords(d)
            pbc = self.structure.pbc
            for k in range(3):
                if pbc[k]:
                    frac[k] -= np.round(frac[k])
            d = frac @ self.structure.lattice.matrix
        return float(np.linalg.norm(d))

    def density(self) -> Optional[float]:
        """Mass density in g/cm³ (Crystal only, None for Molecule)."""
        if isinstance(self.structure, Molecule):
            return None
        AMU_TO_GRAM = 1.660539e-24
        total_mass_amu = float(np.sum(self._get_masses()))
        volume = self.structure.volume
        if volume <= 0:
            return None
        return float((total_mass_amu * AMU_TO_GRAM) / (volume * 1e-24))

    def chemical_formula(self) -> str:
        """Chemical formula with reduced ratios."""
        return self.structure.composition.reduced_formula


__all__ = ["StructureAnalyzer"]
