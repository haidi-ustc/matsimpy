"""Bond analysis via geometric distance criteria."""

import numpy as np
from scipy.spatial.distance import cdist
from typing import Optional, Union
from ..core import Crystal, Molecule


class BondAnalyzer:
    """Geometric bond analysis for Crystal and Molecule structures.

    Computes bonded pairs, bond angles, dihedral angles, and bond orders
    using distance-based criteria. Wraps a Structure for cached repeated analysis.

    Usage::

        >>> analyzer = BondAnalyzer(molecule, cutoff=2.0)
        >>> bonds = analyzer.find_bonds()
        >>> angles = analyzer.get_bond_angles()
    """

    def __init__(self, structure: Union[Crystal, Molecule], cutoff: float = 2.0):
        self.structure = structure
        self._cutoff = cutoff
        self._bonds_cache: Optional[list] = None
        self._cache_cutoff: Optional[float] = None

    @property
    def bonds(self) -> list[tuple[int, int, float]]:
        """Cached list of (i, j, distance) for bonded pairs."""
        if self._bonds_cache is None or self._cache_cutoff != self._cutoff:
            self._bonds_cache = self.find_bonds(self._cutoff)
            self._cache_cutoff = self._cutoff
        return self._bonds_cache

    def find_bonds(self, cutoff: Optional[float] = None) -> list[tuple[int, int, float]]:
        """Find all (i, j, distance) within cutoff where i < j."""
        cutoff = cutoff if cutoff is not None else self._cutoff
        pos = self.structure.positions
        dists = cdist(pos, pos)
        bonds = []
        n = len(pos)
        for i in range(n):
            for j in range(i + 1, n):
                d = dists[i][j]
                if d < cutoff:
                    bonds.append((i, j, float(d)))
        return bonds

    def get_bond_angles(self, cutoff: Optional[float] = None) -> list[tuple[int, int, int, float]]:
        """All (i, j, k, angle_degrees) where j is central, i and k bonded to j."""
        cutoff = cutoff if cutoff is not None else self._cutoff
        pos = self.structure.positions
        bonds = self.find_bonds(cutoff)
        adj = {k: set() for k in range(len(pos))}
        for i, j, _ in bonds:
            adj[i].add(j)
            adj[j].add(i)
        angles = []
        for j in range(len(pos)):
            neighbors = sorted(adj[j])
            for a in range(len(neighbors)):
                for b in range(a + 1, len(neighbors)):
                    i = neighbors[a]
                    k = neighbors[b]
                    v1 = pos[i] - pos[j]
                    v2 = pos[k] - pos[j]
                    n1 = np.linalg.norm(v1)
                    n2 = np.linalg.norm(v2)
                    if n1 < 1e-10 or n2 < 1e-10:
                        continue
                    cos = np.dot(v1, v2) / (n1 * n2)
                    cos = np.clip(cos, -1, 1)
                    angle = np.degrees(np.arccos(cos))
                    angles.append((i, j, k, float(angle)))
        return angles

    def get_dihedral_angles(self, cutoff: Optional[float] = None) -> list[tuple[int, int, int, int, float]]:
        """All (i, j, k, l, angle_degrees) dihedral angles."""
        cutoff = cutoff if cutoff is not None else self._cutoff
        pos = self.structure.positions
        bonds = self.find_bonds(cutoff)
        adj = {k: set() for k in range(len(pos))}
        for i, j, _ in bonds:
            adj[i].add(j)
            adj[j].add(i)
        dihedrals = []
        for j, k in bonds:
            for i in adj[j]:
                if i == k:
                    continue
                for ell in adj[k]:
                    if ell == j:
                        continue
                    v1 = pos[i] - pos[j]
                    v2 = pos[j] - pos[k]
                    v3 = pos[k] - pos[ell]
                    n1 = np.cross(v1, v2)
                    n2 = np.cross(v2, v3)
                    n1_norm = np.linalg.norm(n1)
                    n2_norm = np.linalg.norm(n2)
                    if n1_norm < 1e-10 or n2_norm < 1e-10:
                        continue
                    cos = np.dot(n1, n2) / (n1_norm * n2_norm)
                    cos = np.clip(cos, -1, 1)
                    angle = np.degrees(np.arccos(cos))
                    dihedrals.append((i, j, k, ell, float(angle)))
        return dihedrals

    def get_bond_order(self, atom_i: int, atom_j: int) -> float:
        """Estimate bond order from distance vs. covalent radii."""
        pos = self.structure.positions
        d = float(np.linalg.norm(pos[atom_i] - pos[atom_j]))
        species = self.structure.species
        from ..core.periodic_table import Element
        ei = Element.get_element(species[atom_i])
        ej = Element.get_element(species[atom_j])
        ri = ei.covalent_radius if ei and ei.covalent_radius else 0.7
        rj = ej.covalent_radius if ej and ej.covalent_radius else 0.7
        if ri + rj == 0:
            return 1.0
        ratio = (ri + rj) / d
        if ratio > 1.3:
            return 2.0
        elif ratio > 0.9:
            return 1.0
        else:
            return 0.5

    def get_coordination_numbers(self, cutoff: Optional[float] = None) -> dict[int, int]:
        """Coordination number (bond count) for each atom."""
        bonds = self.find_bonds(cutoff)
        cn: dict[int, int] = {}
        for i, j, _ in bonds:
            cn[i] = cn.get(i, 0) + 1
            cn[j] = cn.get(j, 0) + 1
        for k in range(len(self.structure)):
            cn.setdefault(k, 0)
        return cn


__all__ = ["BondAnalyzer"]
