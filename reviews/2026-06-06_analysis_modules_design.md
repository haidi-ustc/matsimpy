# Analysis Modules Update — Design Spec

Date: 2026-06-06  
Status: Design approved  
Context: Implement bonding.py, structure.py, topology.py analysis modules using class-based API.

## Summary

Replace the three empty stub modules in `matsimpy/analysis/` with real implementations using Analyzer classes. Each wraps a Structure and provides cached geometric/topological analysis.

## API Design

### BondAnalyzer (`matsimpy/analysis/bonding.py`)

```python
class BondAnalyzer:
    """Geometric bond analysis."""
    
    def __init__(self, structure: Structure, cutoff: float = 2.0)
    
    @property
    def bonds(self) -> list[tuple[int, int, float]]
    
    def find_bonds(self, cutoff: float | None = None) -> list[tuple[int, int, float]]
    def get_bond_angles(self, cutoff: float | None = None) -> list[tuple[int, int, int, float]]
    def get_dihedral_angles(self, cutoff: float | None = None) -> list[tuple[int, int, int, int, float]]
    def get_bond_order(self, atom_i: int, atom_j: int) -> float
    def get_coordination_numbers(self, cutoff: float | None = None) -> dict[int, int]
```

### StructureAnalyzer (`matsimpy/analysis/structure.py`)

```python
class StructureAnalyzer:
    """Global geometric property analysis."""
    
    def __init__(self, structure: Structure)
    
    def center_of_mass(self) -> np.ndarray
    def radius_of_gyration(self) -> float
    def inertia_tensor(self) -> np.ndarray
    def principal_axes(self) -> tuple[np.ndarray, np.ndarray]
    def pair_distance(self, i: int, j: int) -> float
    def density(self) -> float | None
    def chemical_formula(self) -> str
```

### TopologyAnalyzer (`matsimpy/analysis/topology.py`)

```python
class TopologyAnalyzer:
    """Connectivity topology — thin wrapper over graph.py."""
    
    def __init__(self, structure: Structure, cutoff: float = 2.0, use_pbc: bool = False)
    
    def is_connected(self) -> bool
    def connected_components(self) -> list[list[int]]
    def get_rings(self, max_size: int = 6) -> list[list[int]]
    def shortest_path(self, source: int, target: int) -> list[int] | None
    def coordination_numbers(self) -> dict[int, int]
    def adjacency_matrix(self) -> np.ndarray
```

### analysis/__init__.py

Exports all three Analyzer classes alongside existing graph and neighbor functions.

## Implementation Notes

- BondAnalyzer: distance-based bond detection using `cdist`. Bond angles via law of cosines. Dihedral angles via vector cross/dot products. Bond order estimated from covalent radii ratios. Caches bond list internally.
- StructureAnalyzer: COM uses atom masses from periodic table. Inertia tensor per standard physics formula. Density uses lattice volume for crystals. PBC-aware pair distances.
- TopologyAnalyzer: all methods delegate to `MoleculeGraph` or `CrystalGraph` from graph.py. Thin wrapper — no new algorithms.

## Non-Goals

- No changes to graph.py or neighbors.py
- No changes to transformation, builders, IO, storage
- No new dependencies
