# Learnings

## Phase 2: validate_cutoff
- Added `validate_cutoff()` to `matsimpy/core/neighbors.py` with checks for non-numeric, NaN, inf, negative, and zero (with allow_zero flag)
- Applied to `molecule.py:get_neighbor_list()` and `crystal.py:get_neighbor_list()` at method entry
- Applied to `graph.py:StructureGraph.__init__()` which covers all subclasses (MoleculeGraph, CrystalGraph) since they call super().__init__()

## Phase 3: Self-neighbor filtering
- Crystal `get_neighbor_list()` periodic-image branch: added `if image_idx == i: continue` guard
- CrystalGraph.adjacency_matrix: added `np.fill_diagonal(adj, 0)` after building adjacency in both PBC and non-PBC branches

## Phase 4: Hash removal
- Removed `__hash__` methods from Lattice, Structure, Site, CrystalSite
- Set `__hash__ = None` on all four classes
- Added `_structural_hash()` private method to Structure for internal use (replaces old __hash__ logic)
- Updated `_needs_calculation()` to use `self._structural_hash()` instead of `hash(self)`
- Note: calculator/base.py still uses `hash(structure)` at line 107 - will raise TypeError. This is outside scope (calculator/ not in core/)

## Phase 5: Zero-mass handling
- composition.py mass_fractions(): raises ValueError if total_mass == 0
- molecule.py get_center_of_mass(): checks total_mass == 0 before np.average
- molecule.py get_moment_of_inertia(): checks total_mass == 0 at start

## Phase 6: anonymous_formula limit
- Added check `if len(sorted_elements) > 26: raise ValueError(...)` before string.ascii_uppercase indexing

## Phase 7: Ring detection
- Changed bare `except:` to `except ImportError:` in find_rings()

## Phase 8: deque optimization
- Added `from collections import deque` at top of graph.py
- Replaced 3 `list.pop(0)` occurrences with `deque.popleft()` in BFS/connected_components/shortest_path

## Phase 9: Clarity fixes
- lattice.py from_parameters(): added angle validation (0 < alpha,beta,gamma < 180)
- molecule.py from_ase(): improved error message when converter returns non-Molecule
