# Core Refactor Design

## Goal

Refactor `matsimpy/core` to be a minimal, clean data model layer. Eliminate god objects, fix data model invariants, remove duplication, enforce unidirectional dependency flow.

## Principles

1. **Core is data model only.** No I/O, no calculators, no converters, no DFT interfaces, no symmetry, no transformations, no graph analysis implementations.
2. **Dependencies flow inward.** Higher packages import from core; core never imports from higher packages.
3. **Canonical representation.** `positions` is always Cartesian. Fractional coordinates are a derived, separately-named property.
4. **Atomic mutation.** No individual property setters with cross-validation. Single `_replace_atoms` batch update.
5. **No freeze/thaw.** Use `copy()` when immutability is needed.

## File inventory

```
matsimpy/core/
├── __init__.py          # 7 public exports
├── periodic_table.py    # Element (unchanged, ~1670 lines)
├── composition.py       # Composition (unchanged, ~626 lines)
├── lattice.py           # Lattice - remove _format_lattice_params (~930 lines)
├── site.py              # Site, CrystalSite - LSP fixed (~940 lines)
├── structure.py         # Structure ABC - slimmed, freeze removed, _replace_atoms (~800 lines)
├── molecule.py          # Molecule - slimmed (~500 lines)
├── crystal.py           # Crystal - slimmed (~900 lines)
└── graph.py             # StructureGraph ABC only (~150 lines)
```

## What moves where

| Method removed from core | New location | Signature |
|---|---|---|
| `Crystal.to_file` / `Molecule.to_file` | Already delegates to `matsimpy.io.write` | Delete method, use `io.write(s, path)` |
| `Crystal.from_file` / `Molecule.from_file` | Already delegates to `matsimpy.io.read` | Delete method, use `io.read(path)` |
| `Crystal.to_pymatgen` / `Molecule.to_pymatgen` | Already delegates to `io.converters.to_pymatgen` | Delete method, use `to_pymatgen(s)` |
| `Crystal.to_ase` / `Molecule.to_ase` | Already delegates to `io.converters.to_ase` | Delete method, use `to_ase(s)` |
| `Crystal.from_pymatgen` / `Molecule.from_pymatgen` | Already delegates to `io.converters.from_pymatgen` | Delete method, use `from_pymatgen(obj)` |
| `Crystal.from_ase` / `Molecule.from_ase` | Already delegates to `io.converters.from_ase` | Delete method, use `from_ase(obj)` |
| `Crystal.to_code` / `Molecule.to_code` | Already delegates to `code.get_code_interface` | Delete method, use `code.write_input(s, ...)` |
| `Crystal.from_code` / `Molecule.from_code` | Already delegates to `code.get_code_interface` | Delete method |
| `Crystal.calc` property/setter | `matsimpy/calculator/` | `calc.attach(s, calculator)` / `calc.detach(s)` |
| `Crystal.get_potential_energy` | `matsimpy/calculator/` | `calc.get_energy(s, calculator)` |
| `Crystal.get_forces` / `Molecule.get_forces` | `matsimpy/calculator/` | `calc.get_forces(s, calculator)` |
| `Crystal.get_stress` | `matsimpy/calculator/` | `calc.get_stress(s, calculator)` |
| `Crystal.get_symmetry_info` | `matsimpy/symmetry/` | `symmetry.get_info(crystal)` |
| `Crystal.get_conventional_cell` | `matsimpy/symmetry/` | `symmetry.get_conventional_cell(crystal)` |
| `Crystal.make_supercell` | `matsimpy/transformation/` | Already exists as `make_supercell(s, matrix)` |
| `Crystal.perturb` | `matsimpy/transformation/` | Already exists as `perturb_positions`/`perturb_lattice` |
| `Molecule.perturb` | `matsimpy/transformation/` | Already exists as `perturb_positions` |
| `Molecule.translate` | `matsimpy/transformation/` | `transformation.translate(mol, vector)` |
| `Molecule.rotate` | `matsimpy/transformation/` | `transformation.rotate(mol, angle, axis)` |
| `Crystal.random_crystal` | `matsimpy/generation/` | Already exists as `random_crystal(...)` |
| `Crystal.wrap` | `matsimpy/transformation/` | `transformation.wrap(crystal)` |
| `Molecule.to_crystal` | `matsimpy/transformation/` | `transformation.molecule_to_crystal(mol, vacuum)` |
| `MoleculeGraph` class | `matsimpy/analysis/graph.py` | Same class, different module |
| `CrystalGraph` class | `matsimpy/analysis/graph.py` | Same class, different module |
| `create_structure_graph` | `matsimpy/analysis/graph.py` | Same function, different module |
| 15 functional graph wrappers | `matsimpy/analysis/graph.py` | Same functions, different module |
| `freeze` / `unfreeze` / `is_frozen` / `_check_frozen` | Deleted | Use `copy()` for immutability |
| `FrozenStructureError` | Deleted | — |
| `Lattice._format_lattice_params` | Inline in `__str__` or a display utility | — |

## Species/Positions deadlock fix

Remove individual `species` and `positions` property setters. Replace with a single atomic update:

```python
class Structure(ABC):
    # Read-only properties
    @property
    def species(self) -> Tuple[str, ...]:
        return self._species

    @property
    def positions(self) -> np.ndarray:  # Always Cartesian
        return self._positions

    def _replace_atoms(
        self,
        species: Sequence[str],
        positions: np.ndarray,
    ) -> None:
        """Atomic batch update. Validates once, invalidates caches once."""
        if len(species) != len(positions):
            raise ValueError(
                f"Species count ({len(species)}) must match "
                f"positions count ({len(positions)})"
            )
        self._species = tuple(species)
        self._positions = self._validate_positions(positions)
        self._invalidate_caches()

    def _invalidate_caches(self):
        self._formula_dirty = True
        self._cached_composition = None
        self._cached_formula = None
```

All mutation methods (`add_atom`, `remove_atom`, `substitute`, `substitute_all`, `sort_atoms`) build new species/positions locally, then call `_replace_atoms` once. Subclasses override `_replace_atoms` to also update derived state:

```python
class Crystal(Structure):
    def _replace_atoms(self, species, positions):
        super()._replace_atoms(species, positions)
        self._frac_positions = self._convert_to_fractional()
        self._invalidate_neighbor_tree()
        self._sites = self._initialize_sites()

class Molecule(Structure):
    def _replace_atoms(self, species, positions):
        super()._replace_atoms(species, positions)
        self._sites = self._initialize_sites()
        self._cached_com = None
```

## Position semantics

`Structure.positions` is **always Cartesian**. No subclass overrides. This is the canonical representation.

`Crystal` adds `frac_positions` as a separate derived property. Conversion happens at construction (input can be fractional or Cartesian via `coords_are_cartesian` flag) and during `_replace_atoms`.

## Cleaner mutation pattern

With `_replace_atoms` as the single atomic update, subclass `add_atom` overrides no longer need try/except rollback. They build the candidate state, validate external constraints (distances, PBC), and only call `_replace_atoms` if everything passes. Validation failures raise before any mutation:

```python
class Crystal(Structure):
    def add_atom(self, species, position, ...):
        # 1. Build candidate species and positions
        new_species = list(self.species) + [species]
        new_positions = np.vstack([self.positions, position_frac])
        # 2. Validate distance constraints
        self._check_distances(new_positions)
        # 3. Atomic commit — only reached if validation passes
        self._replace_atoms(new_species, new_positions)
        # 4. site_properties handled after successful commit
```

Rollback is unnecessary because no mutation occurs before validation succeeds.

## Site LSP fix

`Site.position` is always Cartesian. `CrystalSite.position` is always Cartesian (matches parent). `CrystalSite.frac_position` is the separate fractional coordinate property. No semantic override.

## Graph module

`matsimpy/core/graph.py` keeps only the `StructureGraph` ABC:

```python
class StructureGraph(ABC):
    def __init__(self, structure, cutoff=3.0):
        self.structure = structure
        self.cutoff = cutoff

    @property
    def num_nodes(self) -> int: ...

    @property
    @abstractmethod
    def adjacency_matrix(self) -> np.ndarray: ...

    @property
    @abstractmethod
    def distance_matrix(self) -> np.ndarray: ...

    # Derived properties that use adjacency_matrix and distance_matrix:
    @property
    def edge_list(self) -> List[Tuple[int, int, float]]: ...
    @property
    def num_edges(self) -> int: ...
    @property
    def coordination_numbers(self) -> Dict[int, int]: ...
    @property
    def degree_distribution(self) -> Dict[int, int]: ...
    @property
    def is_connected(self) -> bool: ...
    @property
    def connected_components(self) -> List[List[int]]: ...
    def get_shortest_path(self, start, end) -> Optional[List[int]]: ...
    @property
    def diameter(self) -> Optional[int]: ...
    @property
    def node_features(self) -> np.ndarray: ...
    @property
    def laplacian(self) -> np.ndarray: ...
    def get_normalized_laplacian(self) -> np.ndarray: ...
    @property
    def statistics(self) -> Dict[str, Any]: ...
    def to_networkx(self): ...
    def find_rings(self, max_ring_size=10) -> List[List[int]]: ...
```

`MoleculeGraph`, `CrystalGraph`, `create_structure_graph`, and all 15 functional wrappers move to `matsimpy/analysis/graph.py`.

## Dependency rules

```
                    ┌─────────────┐
                    │   analysis  │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
    ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐
    │  calculator │ │  symmetry   │ │     code     │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           └───────────────┼───────────────┘
                    ┌──────┴──────┐
                    │      io     │
                    └──────┬──────┘
                    ┌──────┴──────┐
                    │transform.   │
                    └──────┬──────┘
                    ┌──────┴──────┐
                    │ generation  │
                    └──────┬──────┘
                          │
                    ┌──────┴──────┐
                    │    CORE     │  ← imports only numpy, scipy, monty, stdlib
                    └─────────────┘
```

Arrows point from importer to imported. Core is at the bottom, never imports upward.

## What stays in each class

### Structure(ABC)
- `species` (property, read-only)
- `positions` (property, read-only, always Cartesian)
- `lattice` (attribute, Optional[Lattice])
- `formula` (cached property)
- `composition` (cached property)
- `symbol_set` (property)
- `elements` (property)
- `_replace_atoms(species, positions)` — atomic batch update
- `_validate_positions(positions)` — validation
- `_invalidate_caches()` — cache invalidation
- `add_atom(species, position)` — in-place, calls `_replace_atoms`
- `remove_atom(index)` — in-place, calls `_replace_atoms`
- `substitute(indices, new_species)` — in-place, calls `_replace_atoms`
- `substitute_all(old, new)` — in-place, calls `_replace_atoms`
- `sort_atoms(sort_by)` — in-place, calls `_replace_atoms`
- `copy()` — via `from_dict(as_dict())`
- `as_dict()` / `from_dict()` — MSONable
- `__len__`, `__contains__`, `__iter__`, `__hash__`, `__eq__`
- `get_neighbor_list(cutoff, atom_index=None, **kwargs)` — abstract

### Crystal(Structure)
- `frac_positions` (property, read-only) — derived from positions via lattice
- `cart_positions` (property) — alias for `positions`
- `pbc` (attribute, List[bool])
- `sites` (property, List[CrystalSite])
- `site_properties` (attribute)
- `volume`, `area`, `length`, `density` (properties)
- `set_pbc(pbc)`
- `add_atom` — override for coordinate conversion + PBC distance checks + rollback
- `remove_atom` — override for coordinate + site_properties cleanup
- `substitute` — override for neighbor tree invalidation
- `sort_atoms` — override
- `as_dict()` / `from_dict()` — includes pbc, lattice, site_properties
- `_replace_atoms` — override, updates frac/cart positions
- `_initialize_sites` — creates CrystalSite list
- `_convert_to_cartesian` / `_convert_to_fractional`
- `get_neighbor_list` — concrete implementation with KDTree + PBC

### Molecule(Structure)
- `sites` (property, List[Site])
- `site_properties` (attribute)
- `get_center_of_mass()` (cached)
- `get_moment_of_inertia()`
- `add_atom` — override for distance checks + rollback
- `remove_atom` — override for site_properties cleanup
- `substitute` — override
- `as_dict()` / `from_dict()` — includes site_properties
- `get_neighbor_list` — concrete implementation (no PBC)
- `get_all_neighbor_lists` — vectorized neighbor finding

### Site
- `position` (property, always Cartesian)
- `specie` (property)
- `properties` (property)
- `coords_are_cartesian` (always True)
- `as_dict()` / `from_dict()`

### CrystalSite(Site)
- `frac_position` (property) — added, does not override position
- `cart_position` (property) — alias for position
- `lattice` (property)
- `wrap()` — wrap to unit cell
- `as_dict()` / `from_dict()`

## Public API (`__init__.py`)

```python
from .lattice import Lattice
from .composition import Composition
from .structure import Structure
from .molecule import Molecule
from .crystal import Crystal
from .site import Site, CrystalSite
from .periodic_table import Element
```

`StructureGraph` is NOT exported from `__init__.py` — it lives in `matsimpy.core.graph` for `matsimpy/analysis/graph.py` to import. The `structure_to_graph_data` re-export is removed; consumers use `analysis.graph.structure_to_graph_data`.

## Implementation order

1. `structure.py` — `_replace_atoms`, remove freeze/thaw, remove setters
2. `site.py` — CrystalSite.position LSP fix
3. `lattice.py` — remove `_format_lattice_params`
4. `molecule.py` — strip removed methods, override `_replace_atoms`
5. `crystal.py` — strip removed methods, override `_replace_atoms`
6. `graph.py` — strip to ABC only
7. Create `matsimpy/analysis/graph.py` — move concrete graph classes + functional API
8. `__init__.py` — update exports
9. Update all internal consumers (`io/`, `transformation/`, `symmetry/`, `calculator/`, `code/`, `generation/`, `analysis/`)
10. Update tests
