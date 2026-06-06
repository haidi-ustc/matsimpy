# 2026-06-06 Core Modules Review

Scope reviewed: `matsimpy/core/__init__.py`, `_validation.py`, `composition.py`, `crystal.py`, `graph.py`, `lattice.py`, `molecule.py`, `neighbors.py`, `periodic_table.py`, `site.py`, and `structure.py`.

Validation performed:
- `python -m compileall -q matsimpy/core` — passed.
- `pytest -q tests/core --disable-warnings` — 658 passed, 1 skipped.
- Targeted runtime probes for cutoff handling, periodic self-neighbors, hash/equality consistency, dummy-species mass paths, and high-element-count formulas.

## Executive Summary

The core test suite is broad and currently passes, but several correctness and robustness issues remain in edge cases that are important for a scientific data model: invalid cutoff values can produce physically impossible neighbor lists, periodic neighbor queries can report an atom as its own neighbor through an image, hashing is inconsistent with tolerance-based equality, dummy species can trigger divide-by-zero mass operations, and some graph/composition APIs have behavior gaps for valid but uncommon inputs.

## Findings

### 1. Negative neighbor cutoffs return spurious neighbors

- **File/module location:** `matsimpy/core/molecule.py:899-952`, `matsimpy/core/crystal.py:1346-1477`, `matsimpy/core/graph.py:126-139`, `matsimpy/core/graph.py:633-659`, `matsimpy/core/graph.py:715-754`
- **Issue description:** `Molecule.get_neighbor_list()` and `Crystal.get_neighbor_list()` do not validate that `cutoff` is non-negative before passing it to `scipy.spatial.cKDTree.query_ball_point()`. With SciPy, a negative radius can return all points instead of none or an error. Graph constructors also accept negative cutoffs silently, producing inconsistent downstream behavior.
- **Why it is problematic:** A negative cutoff is invalid physical input. Returning neighbors for it silently corrupts coordination numbers, graph connectivity, shortest paths, ML graph features, and any analysis that trusts the neighbor list.
- **Example scenario where it could fail:**
  ```python
  Molecule(['H', 'H'], [[0, 0, 0], [1, 0, 0]]).get_neighbor_list(-1)
  # observed: {0: [(1, 1.0)], 1: [(0, 1.0)]}
  ```
  The same pattern occurs for `Crystal(...).get_neighbor_list(-1)`.
- **Recommended fix:** Add a shared cutoff validator (for example `validate_cutoff(cutoff, *, allow_zero=True)`) and call it in molecule/crystal neighbor methods and graph constructors/factory functions. Raise `ValueError` for negative or non-finite cutoffs; add regression tests for molecule, crystal, and graph APIs.
- **Severity level:** HIGH
- **Test coverage gaps:** Existing core tests cover `Molecule.get_all_neighbor_lists()` negative cutoff validation but not `get_neighbor_list()` or graph constructors with negative cutoffs.

### 2. Periodic neighbor lists can include self-neighbors from images

- **File/module location:** `matsimpy/core/crystal.py:1458-1474`, `matsimpy/core/graph.py:741-746`
- **Issue description:** When `use_pbc=True`, periodic image indices are reduced with `image_idx = idx % n_atoms`, but image entries where `image_idx == i` are not excluded. If the cutoff reaches a periodic translation of the same atom, the atom is reported as its own neighbor. `CrystalGraph.adjacency_matrix` then writes this as a diagonal self-loop.
- **Why it is problematic:** Neighbor lists and simple structure graphs normally exclude self-neighbors. Self-loops inflate coordination numbers and can change graph Laplacians, connectivity-derived metrics, and ML graph data.
- **Example scenario where it could fail:**
  ```python
  c = Crystal(['He'], [[0, 0, 0]], Lattice.cubic(2.0))
  c.get_neighbor_list(2.1, use_pbc=True)
  # observed: {0: [(0, 2.0)]}
  CrystalGraph(c, cutoff=2.1, use_pbc=True).adjacency_matrix
  # observed: [[1]]
  ```
- **Recommended fix:** In the periodic-image branch, skip entries where `image_idx == i` before recording the neighbor. Also explicitly clear the diagonal in `CrystalGraph.adjacency_matrix` after building it from neighbor lists.
- **Severity level:** HIGH
- **Test coverage gaps:** No regression test covers single-atom periodic crystals or cutoffs larger than a cell repeat where same-atom images enter the KD-tree result.

### 3. Hash methods violate equality contracts around tolerance boundaries

- **File/module location:** `matsimpy/core/lattice.py:768-838`, `matsimpy/core/structure.py:520-615`, `matsimpy/core/site.py:431-479`, `matsimpy/core/site.py:904-955`
- **Issue description:** Several classes compare floating-point data with tolerances but hash rounded values. Rounding to a fixed number of decimals does not guarantee that all values within the equality tolerance round to the same bucket. `Structure.__hash__` also includes `self.lattice.as_dict()` rounded to 8 decimals while equality accepts lattice differences up to `LATTICE_TOL`.
- **Why it is problematic:** Python requires `a == b` to imply `hash(a) == hash(b)`. Violating this makes sets and dictionaries behave incorrectly: equal objects can coexist as distinct keys or fail lookup by an equal object.
- **Example scenario where it could fail:**
  ```python
  a = Lattice.cubic(5.0000049)
  b = Lattice.cubic(5.0000058)
  a == b          # observed: True
  hash(a) == hash(b)  # observed: False
  ```
- **Recommended fix:** Either make equality exact for hashed value objects or implement quantization that is mathematically consistent with the equality relation. The simplest robust option is to remove tolerance-based `__hash__` (set `__hash__ = None`) for classes whose equality uses tolerances, or define equality using the same canonical quantized representation used for hashing.
- **Severity level:** HIGH
- **Test coverage gaps:** Current hash tests do not include values that straddle decimal rounding boundaries while still comparing equal under `POSITION_TOL`/`LATTICE_TOL`/`np.allclose`.

### 4. Dummy species are accepted but mass-derived APIs divide by zero

- **File/module location:** `matsimpy/core/periodic_table.py:150-159`, `matsimpy/core/composition.py:636-693`, `matsimpy/core/molecule.py:311-330`, `matsimpy/core/molecule.py:856-897`
- **Issue description:** Dummy species such as `X`, `A`, and `Z` are accepted and assigned atomic mass `0.0`, but mass-derived methods assume positive total mass. `Composition('X').mass_fractions()` and `Molecule(['X'], ...).get_center_of_mass()` raise `ZeroDivisionError`; moment-of-inertia paths also depend on mass and center-of-mass.
- **Why it is problematic:** The validation layer intentionally permits dummy species, so downstream core APIs should fail with domain-specific errors or provide documented behavior. A raw divide-by-zero is hard to diagnose and can surface in template structures, alloy placeholders, or partially specified ML inputs.
- **Example scenario where it could fail:**
  ```python
  Composition('X').mass_fractions()
  # observed: ZeroDivisionError: float division by zero
  Molecule(['X'], [[0, 0, 0]]).get_center_of_mass()
  # observed: ZeroDivisionError: Weights sum to zero, can't be normalized
  ```
- **Recommended fix:** Add explicit total-mass checks in mass-derived methods. Either reject all-zero-mass compositions/molecules with `ValueError("Cannot compute ... for only dummy/zero-mass species")`, or support a documented fallback such as geometric center for dummy-only molecules.
- **Severity level:** MEDIUM
- **Test coverage gaps:** Tests cover dummy species normalization in some paths, but not mass fractions, center of mass, or inertia for dummy-only or mixed dummy/real structures.

### 5. `Composition.anonymous_formula` crashes for more than 26 elements

- **File/module location:** `matsimpy/core/composition.py:371-405`
- **Issue description:** Anonymous labels are generated from `string.ascii_uppercase[i]`, which only supports 26 unique species. A valid composition containing 27 or more species raises `IndexError` instead of producing a formula or a controlled error.
- **Why it is problematic:** High-entropy alloys, generated datasets, or placeholder-rich formulas can exceed 26 unique symbols. The method advertises a generic anonymous formula API and should not fail with an implementation-specific list-index error.
- **Example scenario where it could fail:** A generated composition containing the first 27 real elements calls `anonymous_formula` during descriptor generation and crashes once `i == 26`.
- **Recommended fix:** Implement an Excel-style label sequence (`A`..`Z`, `AA`, `AB`, ...) or raise a clear `ValueError` documenting the maximum supported unique species. The Excel-style sequence is more useful and preserves the method contract for arbitrary compositions.
- **Severity level:** MEDIUM
- **Test coverage gaps:** Anonymous formula tests cover common binary/ternary formulas only; no test covers high unique-element counts.

### 6. `find_rings()` suppresses all NetworkX algorithm errors

- **File/module location:** `matsimpy/core/graph.py:547-581`
- **Issue description:** Ring finding catches every exception after constructing the NetworkX graph and returns an empty list. This hides algorithm misuse, NetworkX API changes, malformed graph state, and unexpected runtime errors.
- **Why it is problematic:** A silent empty ring list is indistinguishable from a genuinely acyclic graph. Analysis pipelines can report “no rings” for structures where ring detection actually failed.
- **Example scenario where it could fail:** If a future NetworkX version changes `simple_cycles()` behavior on directed views or raises for a malformed input graph, `find_rings()` returns `[]`, causing ring-containing molecules to be classified as ring-free.
- **Recommended fix:** Catch only known non-fatal exceptions, or let unexpected exceptions propagate. If graceful degradation is required, emit a warning with the exception detail and include an optional strict mode.
- **Severity level:** MEDIUM
- **Test coverage gaps:** Tests validate normal ring detection but do not assert that algorithm errors are surfaced rather than silently converted to empty results.

### 7. Graph search implementations are quadratic due to list-backed BFS queues

- **File/module location:** `matsimpy/core/graph.py:279-291`, `matsimpy/core/graph.py:320-336`, `matsimpy/core/graph.py:360-377`, `matsimpy/core/graph.py:379-407`
- **Issue description:** BFS queues use `list.pop(0)`, which shifts the list on every pop. `diameter` also performs pairwise shortest-path searches, compounding the cost on larger structures.
- **Why it is problematic:** Core graph utilities can become unexpectedly slow for large crystals, molecular graphs, or generated ML structures, even after adjacency construction is complete.
- **Example scenario where it could fail:** A 10k-atom graph with many edges spends substantial time shifting Python lists during connected-component and shortest-path calculations, potentially dominating analysis time or making notebook workflows appear hung.
- **Recommended fix:** Use `collections.deque` for BFS queues. For diameter, consider NetworkX/Scipy graph algorithms or a more efficient all-pairs/connected-graph strategy, and document complexity for large graphs.
- **Severity level:** LOW
- **Test coverage gaps:** Existing tests verify graph correctness on small structures but do not include performance/regression benchmarks for large connected components or diameter calculations.

## Additional Observations

- `matsimpy/core/neighbors.py` is compact and validates dimensionality/finite values; it is a good candidate to reuse for cutoff validation and periodic neighbor edge-case tests.
- `Lattice.from_parameters()` generally rejects invalid geometry through downstream validation, but explicit angle validation (`0 < alpha,beta,gamma < 180`) would produce clearer error messages.
- `Molecule.from_ase()` raises a confusing message when `from_ase()` returns a non-`Molecule`; this is minor but worth cleaning up if the converter API is touched.

## Recommended Priority Order

1. Fix invalid cutoff validation and periodic self-neighbor filtering together; they directly affect physical correctness of neighbor lists and graph metrics.
2. Resolve hash/equality consistency, preferably by disabling hashing for tolerance-equal mutable-value semantics or by aligning equality to hash quantization.
3. Add explicit dummy/zero-mass handling in composition and molecule mass-derived methods.
4. Harden graph ring error handling and high-cardinality anonymous formulas.
5. Optimize graph BFS queues if large graph workflows are important.

## Suggested Regression Tests

- `Molecule.get_neighbor_list(-1)` and `Crystal.get_neighbor_list(-1)` raise `ValueError`; graph constructors/factory functions reject negative/non-finite cutoffs.
- A one-atom periodic crystal with cutoff larger than the cell vector has no self-neighbor and `CrystalGraph` diagonal remains zero.
- Equal lattices/structures/sites at tolerance-boundary values either have equal hashes or are unhashable.
- `Composition('X').mass_fractions()` and dummy-only molecule COM/inertia raise clear `ValueError` or return documented fallbacks.
- `anonymous_formula` supports or clearly rejects >26 unique species.
- `find_rings()` does not silently suppress unexpected algorithm failures.
