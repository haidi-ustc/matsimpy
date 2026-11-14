"""Bond analysis via geometric distance criteria."""

import numpy as np
from scipy.spatial.distance import cdist
from typing import Optional, Union
from ..core import Crystal, Molecule
from .graph import _periodic_coordination_numbers


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
        """All (i, j, k, l, angle_degrees) dihedral angles about each bond j-k (j < k).

        The angle is signed (IUPAC convention) in (-180, 180]: positive when, viewed
        along j -> k, the bond j-i must turn clockwise to eclipse the bond k-l.
        Anti butane gives 180, gauche +60 or -60.
        """
        cutoff = cutoff if cutoff is not None else self._cutoff
        pos = self.structure.positions
        bonds = self.find_bonds(cutoff)
        adj = {k: set() for k in range(len(pos))}
        for i, j, _ in bonds:
            adj[i].add(j)
            adj[j].add(i)
        dihedrals = []
        for j, k, _ in bonds:
            for i in sorted(adj[j]):
                if i == k:
                    continue
                for ell in sorted(adj[k]):
                    if ell == j or ell == i:
                        continue
                    b1 = pos[j] - pos[i]
                    b2 = pos[k] - pos[j]
                    b3 = pos[ell] - pos[k]
                    n1 = np.cross(b1, b2)
                    n2 = np.cross(b2, b3)
                    if np.linalg.norm(n1) < 1e-10 or np.linalg.norm(n2) < 1e-10:
                        continue  # collinear atoms: dihedral undefined
                    y = np.linalg.norm(b2) * np.dot(b1, n2)
                    x = np.dot(n1, n2)
                    angle = float(np.degrees(np.arctan2(y, x)))
                    if angle <= -180.0:
                        angle = 180.0
                    dihedrals.append((i, j, k, ell, angle))
        return dihedrals

    def get_bond_order(self, atom_i: int, atom_j: int) -> float:
        """Estimate bond order from distance vs. the sum of atomic radii.

        Uses ``Element.atomic_radius`` (Slater's empirical atomic radii, e.g.
        H 0.25, C 0.70, N 0.65, O 0.60 Angstrom) as a stand-in for covalent radii,
        which MatSimPy's element data does not provide. With
        ``ratio = (r_i + r_j) / d`` the result is a step function: 2.0 if
        ratio > 1.3, 1.0 if ratio > 0.9, else 0.5.

        This is a coarse heuristic. It never returns 3, and it does not separate
        most double bonds from single ones: C=O at 1.21 A has ratio 1.07 and gives
        1.0, the same as C-C at 1.53 A (ratio 0.92). Only bonds shorter than about
        77% of the radius sum count as double.

        Raises:
            ValueError: If an element has no atomic radius.
        """
        pos = self.structure.positions
        d = float(np.linalg.norm(pos[atom_i] - pos[atom_j]))
        species = self.structure.species
        from ..core.periodic_table import Element
        radii = []
        for s in (species[atom_i], species[atom_j]):
            r = Element.get_element(s).atomic_radius
            if r is None:
                raise ValueError(f"No atomic radius for element {s}; cannot estimate bond order")
            radii.append(float(r))
        ratio = sum(radii) / d
        if ratio > 1.3:
            return 2.0
        elif ratio > 0.9:
            return 1.0
        else:
            return 0.5

    def get_coordination_numbers(self, cutoff: Optional[float] = None) -> dict[int, int]:
        """Coordination number for each atom (neighbours closer than ``cutoff``).

        For a :class:`Crystal` with at least one periodic axis every periodic image
        counts separately, including images of the atom itself, so a primitive
        rocksalt cell gives 6. This is then not the per-atom count of
        :meth:`find_bonds`, which pairs atom indices by Cartesian distance inside
        the cell only. For molecules and fully non-periodic crystals it is the
        number of :meth:`find_bonds` bonds each atom takes part in.
        """
        if isinstance(self.structure, Crystal) and any(self.structure.pbc):
            cutoff = cutoff if cutoff is not None else self._cutoff
            return _periodic_coordination_numbers(self.structure, cutoff, inclusive=False)
        bonds = self.find_bonds(cutoff)
        cn: dict[int, int] = {}
        for i, j, _ in bonds:
            cn[i] = cn.get(i, 0) + 1
            cn[j] = cn.get(j, 0) + 1
        for k in range(len(self.structure)):
            cn.setdefault(k, 0)
        return cn


__all__ = ["BondAnalyzer"]
