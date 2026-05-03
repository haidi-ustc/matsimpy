# Deep Review: `matsimpy/transformation`

**Date:** 2026-05-03
**Scope:** `matsimpy/transformation/**` and transformation-focused tests.
**Review mode:** Read-only code review plus behavioral probes; only this review artifact was written.
**Verification snapshot:** `python -m pytest tests/test_transformation.py tests/test_structural_transformations.py tests/test_composite_pipeline.py tests/test_composite_batch.py tests/test_composite_sweep.py tests/test_atomic_operations.py tests/test_substitution_common.py tests/test_substitution_dict_selection.py tests/test_substitution_multi_partial.py` → **116 passed**.

## Executive summary

The transformation package is broad and convenient, but its current implementation is mainly a thin set of reconstructors around `Crystal` and `Molecule`. The strongest risks are not caught by the current test suite because tests mostly assert object creation and simple counts, not metadata preservation, coordinate-frame invariants, partial-PBC behavior, or non-diagonal lattice transforms.

Highest-priority findings:

1. `site_properties` are frequently misaligned with atoms or cause construction failures after reorder/delete/split/standardize operations.
2. Several transformations drop `pbc` and silently convert slabs/wires/clusters into 3D-periodic crystals.
3. General/non-diagonal supercell generation changes physical Cartesian positions for unimodular transformations.
4. Public functions are placeholders/no-ops while advertised as implemented transformations.
5. Composite serialization/batch APIs have reproducibility and scalability gaps.

## Severity ranking

| Severity | Issue | Category | Confidence | Primary refactor suggestion |
|---|---|---|---|---|
| Critical | Atom metadata (`site_properties`) is not reindexed for swap/sort and fails for merge/split/standardize | Correctness / hidden bug | High | Introduce shared atom-table rebuild/reindex helpers; require explicit merge/split metadata policy. |
| High | Crystal PBC flags are lost by `make_supercell()` and `perturb_positions()` | Correctness | High | Preserve `pbc=list(crystal.pbc)` in every Crystal reconstruction path; add partial-PBC regression tests. |
| High | General supercell algorithm is incorrect for non-diagonal/unimodular matrices | Correctness | High | Replace with a lattice-index/Hermite-normal-form based supercell algorithm and coordinate-frame tests. |
| High | Placeholder public APIs silently return copies or fake results | Correctness / design | High | Implement, de-export, or raise `NotImplementedError` for incomplete scientific operations. |
| High | `standardize_cell()` can fail or corrupt metadata when spglib changes atom count/order | Hidden bug | High | Drop/reindex properties explicitly after symmetry standardization and document property policy. |
| Medium | Crystal coordinate-frame conventions differ across transformations and are under-specified | Design flaw | Medium | Define one contract for Cartesian vs fractional inputs per function; encode in names/tests. |
| Medium | Lattice/deformation functions lack shape/domain validation and matrix-convention tests | Correctness / extensibility | Medium | Centralize 3×3 matrix validators and document row-vector convention. |
| Medium | Pipeline save/load is not reproducible for non-JSON kwargs | Hidden bug | Medium | Serialize transformation specs through typed codecs or reject unsupported kwargs. |
| Medium | Random perturbation helpers mutate NumPy global RNG state | Hidden bug / extensibility | High | Use `np.random.default_rng(seed)` locally. |
| Low | Batch streaming and error-handling names overpromise behavior | Design flaw | Medium | Keep `process_stream()` lazy and clarify whether `skip` returns failures or omits them. |

---

## 1. Correctness issues

### Critical: `site_properties` are not kept aligned with transformed atoms

**Evidence**

- `matsimpy/transformation/atomic/manipulation.py:107-124` swaps species and positions but passes `structure.site_properties` unchanged.
- `matsimpy/transformation/atomic/organization.py:63-79` sorts species and positions by `sorted_indices` but passes the original `site_properties` order unchanged.
- `matsimpy/transformation/atomic/manipulation.py:169-199` removes two atoms and inserts one merged atom, but still passes the original full-length `site_properties`.
- `matsimpy/transformation/atomic/manipulation.py:239-255` removes one atom and appends multiple split atoms, but still passes the original full-length `site_properties`.
- `matsimpy/transformation/lattice/transform.py:153-170` passes original `site_properties` after `spglib` can reorder and/or expand atoms.

**Behavioral probe**

```text
swap props ({'id': 'Na'}, {'id': 'Cl'})
sort props ('Cl', 'Na') ({'id': 'Na'}, {'id': 'Cl'})
merge error ValueError Number of site_properties (2) must match number of atoms (1)
split error ValueError Number of site_properties (2) must match number of atoms (3)
standardize error ValueError Number of site_properties (2) must match number of atoms (6)
```

**Impact**

- Swap/sort silently attach metadata to the wrong atoms.
- Merge/split/standardize fail when metadata exists.
- Any downstream workflow using charges, labels, constraints, magnetic moments, tags, or provenance can become wrong even when coordinates/species look valid.

**Refactor suggestion**

Create a single atom-table rebuild utility that takes `species`, positions, optional lattice/PBC, and an explicit `property_index_map`. Operations should state their metadata policy:

- reorder/swap: reindex properties with atoms
- delete: delete corresponding properties
- merge: merge properties via user callback or drop with warning
- split: copy parent properties or require per-child properties
- symmetry standardization: drop by default unless spglib mapping is available

---

### High: Crystal PBC flags are silently reset to fully periodic

**Evidence**

- `matsimpy/transformation/structural/supercell.py:151-158` constructs the result without `pbc=...`; `Crystal` therefore defaults to `(True, True, True)`.
- `matsimpy/transformation/atomic/organization.py:194-199` constructs a perturbed `Crystal` without `pbc=...`; this also defaults to full 3D periodicity.
- Many other Crystal reconstruction paths do pass `pbc=list(structure.pbc)`, which shows the omission is inconsistent rather than a deliberate package-level policy.

**Behavioral probe**

```text
slab = Crystal(..., pbc=[True, True, False])
make_supercell(slab, [2,2,1]).pbc  -> (True, True, True)
perturb_positions(slab, 0.0).pbc   -> (True, True, True)
```

**Impact**

A 2D slab, 1D wire, or isolated cluster can become 3D-periodic after a no-op perturbation or supercell expansion. That changes neighbor finding, density dimensionality, serialization meaning, and physical interpretation.

**Refactor suggestion**

Add a shared `clone_crystal(...)` / `rebuild_crystal(...)` helper that requires a PBC argument or copies it from the source. Add regression tests for every Crystal-returning transformation with partial PBC.

---

### High: General supercell generation is not coordinate-correct for non-diagonal matrices

**Evidence**

- `matsimpy/transformation/structural/supercell.py:63-65` sets `new_lattice_vectors = scaling_matrix @ old_lattice_vectors`.
- `matsimpy/transformation/structural/supercell.py:114-128` generates candidate translation coordinates via `solve(scaling_matrix.T, translation)` and then uses `new_pos = pos + frac_coords` without converting the original fractional coordinates into the new basis.
- The diagonal branch has a different formula (`new_pos = (pos + offset) / diag`) at `matsimpy/transformation/structural/supercell.py:72-89`, so the general branch is not simply a generalized version of the diagonal branch.

**Behavioral probe**

For a determinant-1 basis change `[[1,1,0],[0,1,0],[0,0,1]]`, atom count should stay the same and physical Cartesian positions should be representable in the new lattice. Current behavior moves the atom:

```text
orig cart [[0.25, 0.0, 0.0]]
new lattice [[1.0, 1.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
new frac [[0.25, 0.0, 0.0]]
new cart [[0.25, 0.25, 0.0]]
```

**Impact**

Non-diagonal supercells can contain atoms in the wrong physical positions even when atom counts pass. This is a scientific correctness issue because downstream energies, distances, symmetry, and file exports become wrong.

**Refactor suggestion**

Replace the heuristic range scan with a known supercell algorithm:

1. Validate an integer 3×3 matrix with positive determinant.
2. Generate lattice image representatives via Hermite normal form / Smith normal form or a proven bounded enumeration.
3. Convert coordinates with the same row-vector convention used by `Lattice` and `Crystal`.
4. Add tests for unimodular transforms, shear matrices, off-diagonal determinant > 1 matrices, and partial PBC preservation.

---

### High: Public transformation APIs are placeholders/no-ops

**Evidence**

- `matsimpy/transformation/lattice/transform.py:95-115` exposes `get_niggli_reduced()` but returns `crystal.copy()` unconditionally.
- `matsimpy/transformation/structural/molecular.py:13-35` exposes `fragment_molecule()` but returns `[molecule.copy()]` regardless of `break_indices`.
- `matsimpy/transformation/structural/molecular.py:87-117` imports RDKit for `generate_conformers()` but returns `n_conformers` copies of the original molecule instead of generated conformers.
- `matsimpy/transformation/structural/__init__.py:8-23` and `matsimpy/transformation/__init__.py:71-85` export these functions as normal public API.

**Impact**

Users can get successful-looking results that are scientifically empty. This is worse than an explicit failure because pipelines and sweeps may proceed with unchanged structures.

**Refactor suggestion**

Use one of these policies per function:

- implement fully and add invariant tests;
- mark experimental and raise `NotImplementedError` with a precise message;
- de-export from `__all__` until complete.

---

### Medium: Crystal coordinate frames are inconsistent and under-documented

**Evidence**

- `matsimpy/transformation/geometric/translation.py:42-63` treats the vector as Cartesian for both Molecule and Crystal.
- `matsimpy/transformation/atomic/organization.py:117-137` centers molecules using Cartesian center of mass, but centers crystals by mean fractional coordinates and interprets the user-provided `center` in fractional coordinates.
- `matsimpy/transformation/atomic/manipulation.py:175-184` makes `merge_atoms()` use fractional positions for Crystal and Cartesian positions for Molecule, while the `position` argument docstring does not state the coordinate frame.
- `matsimpy/transformation/geometric/rotation.py:58-64` defaults molecule rotation center to COM, but crystal rotation center to Cartesian origin.

**Impact**

The same conceptual operation has different coordinate-frame semantics depending on the structure type and function. User code can be correct for molecules and subtly wrong for crystals.

**Refactor suggestion**

Adopt explicit naming/arguments:

- `center_cartesian=` vs `center_fractional=`
- `position_cartesian=` vs `position_fractional=`
- `coords_are_cartesian` for any function that accepts positions

Then add cross-function tests for molecule/crystal coordinate-frame behavior.

---

### Medium: Lattice/deformation transforms rely on implicit matrix conventions and weak validation

**Evidence**

- `matsimpy/transformation/lattice/scale.py:33-40` accepts any array-like scale factor and constructs a diagonal matrix without checking shape, positivity, finiteness, or determinant.
- `matsimpy/transformation/lattice/scale.py:76-79` accepts `target_volume` without validating that it is positive and finite.
- `matsimpy/transformation/lattice/strain.py:35-40` and `matsimpy/transformation/lattice/strain.py:76-88` convert matrices to arrays but do not validate shape or singularity before constructing lattices or solving inverses.
- `matsimpy/transformation/lattice/transform.py:38-50` does not validate that `rotation_matrix` is 3×3, orthonormal, or proper (`det ≈ 1`).

**Impact**

Invalid shapes and singular/negative/non-finite values fail later with lower-level NumPy/Lattice errors or can produce physically invalid cells. For valid but non-orthogonal matrices, the row/column convention is not documented by tests, making future fixes risky.

**Refactor suggestion**

Centralize validators:

- `validate_vector3(name, value)`
- `validate_matrix3(name, value, *, finite=True, nonsingular=False, orthonormal=False)`
- `validate_positive_scalar(name, value)`

Document the row-vector convention once and test shear/deformation cases where transpose mistakes are visible.

---

## 2. Hidden bugs

### High: `standardize_cell()` can change atom count/order but reuses old metadata

**Evidence**

- `matsimpy/transformation/lattice/transform.py:142-146` builds an spglib cell.
- `matsimpy/transformation/lattice/transform.py:148-171` reconstructs a `Crystal` from `find_primitive()` or `standardize_cell()` output, but passes the original `site_properties` unchanged.

**Behavioral probe**

```text
standardize_cell(Crystal(..., site_properties=[...2 props...]))
-> ValueError Number of site_properties (2) must match number of atoms (6)
```

**Impact**

Symmetry standardization fails for annotated structures, and if atom counts happen to match while order changes, metadata can silently attach to the wrong atoms.

**Refactor suggestion**

For standardization, either compute a mapping from old atoms to standardized atoms or drop properties explicitly with an opt-in `preserve_site_properties=False/True` API.

---

### Medium: Pipeline serialization silently stringifies unsupported values

**Evidence**

- `matsimpy/transformation/composite/pipeline.py:202-210` writes kwargs through `json.dump(..., default=str)`.
- `matsimpy/transformation/composite/pipeline.py:241-253` loads those kwargs and passes them directly back into transformation functions.

**Impact**

A pipeline with NumPy arrays, callables, custom objects, or path-like/scientific objects can save successfully but reload with strings instead of original typed values. The failure is deferred to apply time, which weakens reproducibility.

**Refactor suggestion**

Do not use `default=str` for reproducibility-critical objects. Either reject unsupported kwargs at save time or add explicit codecs for NumPy arrays and supported structures.

---

### Medium: Perturbation helpers mutate global random state

**Evidence**

- `matsimpy/transformation/atomic/organization.py:175-182` calls `np.random.seed(seed)` and then `np.random.randn(...)`.
- `matsimpy/transformation/lattice/strain.py:129-134` does the same for lattice perturbations.

**Impact**

Calling a transformation can change randomness elsewhere in the process. This is especially risky in parameter sweeps, Monte Carlo workflows, tests, and notebooks.

**Refactor suggestion**

Use local generators:

```python
rng = np.random.default_rng(seed)
perturbations = rng.normal(size=(...)) * amplitude
```

---

### Low: Batch `process_stream()` materializes the full iterable

**Evidence**

- `matsimpy/transformation/composite/batch.py:290-323` describes lazy processing but immediately executes `items = [(i, s) for i, s in enumerate(structures)]` at line 305.

**Impact**

Large or infinite iterables are not streamed; memory usage scales with the full input size before the first result is yielded.

**Refactor suggestion**

For sequential mode, enumerate and yield directly. For parallel mode, use `imap` over an enumerated iterator or explicitly document that parallel mode is eager.

---

## 3. Design flaws

### Broad duplication of reconstruction logic

**Evidence**

Across `translation.py`, `rotation.py`, `atomic/manipulation.py`, `atomic/organization.py`, `lattice/*.py`, and `structural/supercell.py`, functions manually reconstruct `Crystal(...)` or `Molecule(...)` and independently decide whether to pass lattice, PBC, coordinate mode, and site properties.

**Impact**

The duplication directly correlates with the bugs above: some paths preserve PBC, some do not; some paths should reindex metadata but do not; some use Cartesian coordinates and others fractional.

**Refactor suggestion**

Introduce internal constructors:

- `rebuild_molecule_like(source, species, positions, site_properties=...)`
- `rebuild_crystal_like(source, species, positions, *, coords_are_cartesian, lattice=None, pbc=None, site_properties=...)`
- `reindex_site_properties(source, indices)`

Require all transformations to use them.

---

### Feature surface is larger than implemented scientific behavior

**Evidence**

`matsimpy/transformation/__init__.py:1-29` advertises comprehensive transformation categories, while several exported operations are placeholders or partial implementations.

**Impact**

The API looks production-ready but contains no-op scientific functions. This makes downstream workflow results hard to audit.

**Refactor suggestion**

Split API into stable and experimental namespaces. Keep incomplete functions out of the stable top-level import path.

---

### Matrix operations lack a single convention contract

**Evidence**

Lattice, deformation, rotation, and supercell code each apply matrices locally (`scaling_matrix @ lattice_vectors`, `deformation_matrix @ lattice_vectors`, `rotation_matrix @ lattice_vectors`, `cart_positions @ matrix.T`) without a shared explanatory contract or comprehensive tests.

**Impact**

Future contributors can fix one path and break another. Non-diagonal matrices are where these convention mistakes become visible.

**Refactor suggestion**

Add a short internal design note and tests for row-vector basis transformations. Use helper functions for basis changes and Cartesian active rotations.

---

## 4. Extensibility risks

### Metadata extensibility is currently fragile

Transformations need to support future per-site data such as constraints, velocities, charges, oxidation states, magnetic moments, tags, and provenance. The current ad hoc copying/reuse of `site_properties` does not scale to operations that reorder, duplicate, merge, split, or symmetry-map atoms.

**Recommendation:** Treat species, coordinates, and site properties as one atom table. Transform table rows together unless an operation explicitly changes cardinality; then require a policy.

### High-throughput workflows can hide failures

`BatchProcessor` returns `BatchResult` objects with errors for `skip`/`log`, while the name `skip` suggests failed entries might be omitted. Parallel fallback also catches broad exceptions at `matsimpy/transformation/composite/batch.py:267-275`, which can make multiprocessing, pickling, and real transformation failures look similar.

**Recommendation:** Separate infrastructure failures from transformation failures, and include structured error type/traceback in `BatchResult`.

### Parameter sweeps precompute all combinations

`ParameterSweep.__init__()` stores all combinations at `matsimpy/transformation/composite/sweep.py:102-103`. Cartesian generation materializes every combination at `matsimpy/transformation/composite/sweep.py:140-173`.

**Recommendation:** Use lazy combination iterators for large high-throughput sweeps, with optional `len` only when finite and cheap.

### Subclass/type preservation is not addressed

Every transformation reconstructs base `Crystal` or `Molecule` directly. If specialized subclasses or richer structure types are introduced, transformations will strip those types and any extra state.

**Recommendation:** Add a structure protocol / factory hook (`structure.rebuild(...)`) so transformations can preserve subclass-specific state.

---

## Suggested refactor plan

1. **Lock invariants with tests first**
   - Metadata follows atom order after swap/sort.
   - Merge/split define metadata behavior.
   - Partial PBC survives all Crystal transformations.
   - Non-diagonal supercell preserves physical positions for determinant-1 transforms.
   - Placeholder functions either raise or produce real changed results.

2. **Centralize reconstruction**
   - Build `transformation/_rebuild.py` with clone/rebuild helpers and validators.
   - Replace hand-written `Crystal(...)` / `Molecule(...)` reconstruction in transformation modules.

3. **Fix atom-table semantics**
   - Reindex site properties for one-to-one atom mappings.
   - Add explicit policies for many-to-one and one-to-many transformations.

4. **Replace general supercell algorithm**
   - Use a proven integer-lattice representative algorithm.
   - Preserve PBC and site properties through replicated image mappings.

5. **Tighten public API honesty**
   - Implement `get_niggli_reduced`, `fragment_molecule`, and `generate_conformers`, or make them fail explicitly.

6. **Harden high-throughput surfaces**
   - Make sweeps lazy.
   - Make pipeline serialization typed or fail-fast.
   - Separate transform failures from multiprocessing/fallback failures.

## Evidence limits

- The focused transformation suite currently passes, so many findings are gaps in untested behavior rather than failing existing tests.
- Behavioral probes were run locally against the current working tree; they were not added as tests in this review task.
- This review did not inspect optional external packages beyond current import behavior for spglib/RDKit paths.
