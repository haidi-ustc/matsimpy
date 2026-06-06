# Analysis Modules — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement BondAnalyzer, StructureAnalyzer, TopologyAnalyzer classes replacing empty stubs in matsimpy/analysis/.

**Architecture:** Class-based API — each Analyzer wraps a Structure, caches results, exposes methods for geometric/topological analysis. BondAnalyzer uses distance-based bond detection. StructureAnalyzer computes global geometric properties. TopologyAnalyzer delegates to existing graph.py classes.

**Tech Stack:** Python 3.10+, numpy, scipy (cdist), existing graph.py/neighbors.py

---

### Task 1: Implement BondAnalyzer

**Files:**
- Modify: `matsimpy/analysis/bonding.py`
- Create: `tests/analysis/test_bonding.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for BondAnalyzer."""
import pytest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.analysis.bonding import BondAnalyzer


@pytest.fixture
def water():
    return Molecule(
        ['O', 'H', 'H'],
        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
    )


@pytest.fixture
def nacl():
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


class TestBondAnalyzer:
    def test_init(self, water):
        analyzer = BondAnalyzer(water, cutoff=2.0)
        assert analyzer.structure is water
        assert analyzer._cutoff == 2.0

    def test_find_bonds_water(self, water):
        analyzer = BondAnalyzer(water, cutoff=1.5)
        bonds = analyzer.find_bonds()
        # O-H bonds should be found (~0.96 Å)
        assert len(bonds) >= 2

    def test_bonds_property_caches(self, water):
        analyzer = BondAnalyzer(water, cutoff=1.5)
        b1 = analyzer.bonds
        b2 = analyzer.bonds
        assert b1 is b2  # cached

    def test_get_bond_angles(self, water):
        analyzer = BondAnalyzer(water, cutoff=1.5)
        angles = analyzer.get_bond_angles()
        # H-O-H angle ~104.5°
        assert len(angles) == 1
        _, j, _, angle = angles[0]
        assert j == 0  # O is central atom
        assert abs(angle - 104.5) < 5.0

    def test_get_coordination_numbers(self, water):
        analyzer = BondAnalyzer(water, cutoff=1.5)
        cn = analyzer.get_coordination_numbers()
        assert cn[0] == 2  # O has 2 bonds

    def test_dihedral_none_for_water(self, water):
        analyzer = BondAnalyzer(water, cutoff=1.5)
        dihedrals = analyzer.get_dihedral_angles()
        assert len(dihedrals) == 0  # water has no dihedral
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/analysis/test_bonding.py -v
```
Expected: FAIL — BondAnalyzer not defined or methods missing.

- [ ] **Step 3: Implement BondAnalyzer in bonding.py**

```python
"""Bond analysis via geometric distance criteria."""

import numpy as np
from scipy.spatial.distance import cdist
from typing import Optional, Union
from ..core import Crystal, Molecule


class BondAnalyzer:
    """Geometric bond analysis for Crystal and Molecule structures."""

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
        """All (i, j, k, angle_degrees) where j is central, i bonded to j, k bonded to j."""
        cutoff = cutoff if cutoff is not None else self._cutoff
        pos = self.structure.positions
        bonds = self.find_bonds(cutoff)
        # Build adjacency
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
                    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
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
        from ..core.periodic_table import ELEMENTS
        ri = ELEMENTS[species[atom_i]].covalent_radius
        rj = ELEMENTS[species[atom_j]].covalent_radius
        if ri is None or rj is None or ri + rj == 0:
            return 1.0
        ratio = (ri + rj) / d
        if ratio > 1.3:
            return 2.0
        elif ratio > 0.9:
            return 1.0
        else:
            return 0.5

    def get_coordination_numbers(self, cutoff: Optional[float] = None) -> dict[int, int]:
        """Coordination number for each atom."""
        bonds = self.find_bonds(cutoff)
        cn: dict[int, int] = {}
        for i, j, _ in bonds:
            cn[i] = cn.get(i, 0) + 1
            cn[j] = cn.get(j, 0) + 1
        for k in range(len(self.structure)):
            cn.setdefault(k, 0)
        return cn


__all__ = ["BondAnalyzer"]
```

- [ ] **Step 4: Run tests**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/analysis/test_bonding.py -v
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add matsimpy/analysis/bonding.py tests/analysis/test_bonding.py
git commit -m "feat: implement BondAnalyzer with bond detection, angles, dihedrals"
```

---

### Task 2: Implement StructureAnalyzer

**Files:**
- Modify: `matsimpy/analysis/structure.py`
- Create: `tests/analysis/test_structure.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for StructureAnalyzer."""
import pytest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.analysis.structure import StructureAnalyzer


@pytest.fixture
def water():
    return Molecule(
        ['O', 'H', 'H'],
        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
    )


@pytest.fixture
def nacl():
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


class TestStructureAnalyzer:
    def test_init(self, water):
        analyzer = StructureAnalyzer(water)
        assert analyzer.structure is water

    def test_center_of_mass(self, water):
        analyzer = StructureAnalyzer(water)
        com = analyzer.center_of_mass()
        assert com.shape == (3,)

    def test_radius_of_gyration(self, water):
        analyzer = StructureAnalyzer(water)
        rgyr = analyzer.radius_of_gyration()
        assert rgyr > 0

    def test_inertia_tensor(self, water):
        analyzer = StructureAnalyzer(water)
        I = analyzer.inertia_tensor()
        assert I.shape == (3, 3)
        assert np.allclose(I, I.T)  # symmetric

    def test_principal_axes(self, water):
        analyzer = StructureAnalyzer(water)
        axes, moments = analyzer.principal_axes()
        assert axes.shape == (3, 3)
        assert moments.shape == (3,)
        assert np.all(moments >= 0)

    def test_pair_distance(self, water):
        analyzer = StructureAnalyzer(water)
        d = analyzer.pair_distance(0, 1)
        assert abs(d - 0.96) < 0.05

    def test_density_crystal(self, nacl):
        analyzer = StructureAnalyzer(nacl)
        d = analyzer.density()
        assert d is not None
        assert d > 0

    def test_density_molecule_is_none(self, water):
        analyzer = StructureAnalyzer(water)
        assert analyzer.density() is None

    def test_chemical_formula(self, water):
        analyzer = StructureAnalyzer(water)
        f = analyzer.chemical_formula()
        assert 'H' in f and 'O' in f
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/analysis/test_structure.py -v
```

- [ ] **Step 3: Implement StructureAnalyzer in structure.py**

```python
"""Global geometric property analysis."""

import numpy as np
from typing import Optional, Union
from ..core import Crystal, Molecule


class StructureAnalyzer:
    """Global geometric property analysis for Crystal and Molecule."""

    def __init__(self, structure: Union[Crystal, Molecule]):
        self.structure = structure

    def _get_masses(self) -> np.ndarray:
        """Get atomic masses in amu."""
        from ..core.periodic_table import ELEMENTS
        masses = []
        for s in self.structure.species:
            el = ELEMENTS.get(s)
            masses.append(el.atomic_mass if el and el.atomic_mass else 1.0)
        return np.array(masses)

    def center_of_mass(self) -> np.ndarray:
        """Mass-weighted center of mass in Cartesian coords."""
        masses = self._get_masses()
        pos = self.structure.positions
        total_mass = np.sum(masses)
        return np.sum(pos * masses[:, np.newaxis], axis=0) / total_mass

    def radius_of_gyration(self) -> float:
        """Radius of gyration — measure of compactness."""
        com = self.center_of_mass()
        masses = self._get_masses()
        pos = self.structure.positions
        total_mass = np.sum(masses)
        r2 = np.sum(masses * np.sum((pos - com) ** 2, axis=1)) / total_mass
        return float(np.sqrt(r2))

    def inertia_tensor(self) -> np.ndarray:
        """3×3 moment of inertia tensor."""
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
            pbc = self.structure.pbc
            frac = self.structure.lattice.get_fractional_coords(d)
            for k in range(3):
                if pbc[k]:
                    frac[k] -= np.round(frac[k])
            d = frac @ self.structure.lattice.matrix
        return float(np.linalg.norm(d))

    def density(self) -> Optional[float]:
        """Mass density in g/cm³ (Crystal only)."""
        if isinstance(self.structure, Molecule):
            return None
        AMU_TO_GRAM = 1.660539e-24
        total_mass_amu = np.sum(self._get_masses())
        volume = self.structure.volume
        if volume <= 0:
            return None
        return float((total_mass_amu * AMU_TO_GRAM) / (volume * 1e-24))

    def chemical_formula(self) -> str:
        """Chemical formula with reduced ratios."""
        return self.structure.composition.reduced_formula


__all__ = ["StructureAnalyzer"]
```

- [ ] **Step 4: Run tests**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/analysis/test_structure.py -v
```

- [ ] **Step 5: Commit**

```bash
git add matsimpy/analysis/structure.py tests/analysis/test_structure.py
git commit -m "feat: implement StructureAnalyzer with COM, inertia, density"
```

---

### Task 3: Implement TopologyAnalyzer

**Files:**
- Modify: `matsimpy/analysis/topology.py`
- Create: `tests/analysis/test_topology.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for TopologyAnalyzer."""
import pytest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.analysis.topology import TopologyAnalyzer


@pytest.fixture
def water():
    return Molecule(
        ['O', 'H', 'H'],
        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
    )


@pytest.fixture
def disconnected():
    return Molecule(
        ['C', 'O', 'C', 'O'],
        [[0, 0, 0], [1.2, 0, 0], [10, 0, 0], [11.2, 0, 0]],
    )


class TestTopologyAnalyzer:
    def test_init(self, water):
        analyzer = TopologyAnalyzer(water, cutoff=1.5)
        assert analyzer.structure is water

    def test_is_connected_true(self, water):
        analyzer = TopologyAnalyzer(water, cutoff=1.5)
        assert analyzer.is_connected()

    def test_is_connected_false(self, disconnected):
        analyzer = TopologyAnalyzer(disconnected, cutoff=1.5)
        assert not analyzer.is_connected()

    def test_connected_components(self, disconnected):
        analyzer = TopologyAnalyzer(disconnected, cutoff=1.5)
        comps = analyzer.connected_components()
        assert len(comps) == 2

    def test_coordination_numbers(self, water):
        analyzer = TopologyAnalyzer(water, cutoff=1.5)
        cn = analyzer.coordination_numbers()
        assert cn[0] == 2

    def test_adjacency_matrix(self, water):
        analyzer = TopologyAnalyzer(water, cutoff=1.5)
        adj = analyzer.adjacency_matrix()
        assert adj.shape == (3, 3)
        assert adj[0][1] == 1
        assert adj[0][0] == 0

    def test_shortest_path(self, water):
        analyzer = TopologyAnalyzer(water, cutoff=1.5)
        path = analyzer.shortest_path(1, 2)
        assert path == [1, 0, 2]

    def test_get_rings_water(self, water):
        analyzer = TopologyAnalyzer(water, cutoff=1.5)
        rings = analyzer.get_rings(max_size=6)
        assert len(rings) == 0  # water has no rings
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/analysis/test_topology.py -v
```

- [ ] **Step 3: Implement TopologyAnalyzer in topology.py**

```python
"""Connectivity topology analysis — thin wrapper over graph.py."""

import numpy as np
from typing import Optional, Union, List
from ..core import Crystal, Molecule
from .graph import MoleculeGraph, CrystalGraph


class TopologyAnalyzer:
    """Structural topology analysis — connectivity, rings, paths."""

    def __init__(self, structure: Union[Crystal, Molecule], cutoff: float = 2.0,
                 use_pbc: bool = False):
        self.structure = structure
        self._cutoff = cutoff
        self._use_pbc = use_pbc
        self._graph = None

    def _get_graph(self):
        """Lazy-build the appropriate graph object."""
        if self._graph is None:
            if isinstance(self.structure, Crystal):
                self._graph = CrystalGraph(
                    self.structure, cutoff=self._cutoff, use_pbc=self._use_pbc
                )
            else:
                self._graph = MoleculeGraph(self.structure, cutoff=self._cutoff)
        return self._graph

    def is_connected(self) -> bool:
        return self._get_graph().is_connected

    def connected_components(self) -> List[List[int]]:
        return self._get_graph().connected_components

    def get_rings(self, max_size: int = 6) -> List[List[int]]:
        return self._get_graph().find_rings(max_size=max_size)

    def shortest_path(self, source: int, target: int) -> Optional[List[int]]:
        return self._get_graph().shortest_path(source, target)

    def coordination_numbers(self) -> dict:
        return self._get_graph().coordination_numbers

    def adjacency_matrix(self) -> np.ndarray:
        return self._get_graph().adjacency_matrix


__all__ = ["TopologyAnalyzer"]
```

- [ ] **Step 4: Run tests**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/analysis/test_topology.py -v
```

- [ ] **Step 5: Commit**

```bash
git add matsimpy/analysis/topology.py tests/analysis/test_topology.py
git commit -m "feat: implement TopologyAnalyzer wrapping graph.py"
```

---

### Task 4: Update analysis/__init__.py

**Files:**
- Modify: `matsimpy/analysis/__init__.py`

- [ ] **Step 1: Add analyzer exports**

```python
from .bonding import BondAnalyzer
from .topology import TopologyAnalyzer
from .structure import StructureAnalyzer
```

And add to `__all__`:
```python
"BondAnalyzer",
"StructureAnalyzer",
"TopologyAnalyzer",
```

- [ ] **Step 2: Run all analysis tests**

```bash
/opt/miniconda3/envs/pmg/bin/pytest tests/analysis/ -v
```

- [ ] **Step 3: Run full test suite**

```bash
/opt/miniconda3/envs/pmg/bin/pytest --tb=no -q
```

- [ ] **Step 4: Commit**

```bash
git add matsimpy/analysis/__init__.py
git commit -m "feat: export BondAnalyzer, StructureAnalyzer, TopologyAnalyzer"
```
