# Remediation Plan: `matsimpy/transformation`

**Date:** 2026-05-03
**Based on:** `reviews/codex_20260503_review_transformation.md`
**Scope:** Fix correctness, hidden-bug, design, and extensibility issues in `matsimpy/transformation/**` without broad product/API churn.
**Primary success target:** transformation functions preserve structure invariants: atom order, site metadata, coordinate frames, PBC, lattice geometry, and reproducibility.

## Requirements summary

1. Preserve per-site metadata through transformations whenever there is a well-defined atom mapping.
2. Preserve Crystal PBC flags in every Crystal-returning transformation.
3. Correct non-diagonal/general supercell coordinate generation.
4. Replace silent placeholder behavior with either real implementations or explicit `NotImplementedError`.
5. Centralize reconstruction and validation to prevent future drift across transformation modules.
6. Harden high-throughput helpers (`Pipeline`, `BatchProcessor`, `ParameterSweep`) where current behavior is misleading or non-reproducible.
7. Keep behavior changes test-driven and reviewable; avoid new dependencies unless already optional in project configuration.

## Non-goals

- Do not redesign `Crystal`, `Molecule`, or `Lattice` public APIs unless a transformation bug cannot be fixed otherwise.
- Do not implement full chemistry/graph algorithms for fragmentation/conformer generation in this pass unless already feasible with existing optional dependencies.
- Do not change serialization contracts outside transformation pipeline JSON unless explicitly required.
- Do not add new mandatory dependencies.

## Acceptance criteria

### Invariant preservation

- `swap_atoms()` and `sort_atoms()` move `site_properties` with their atoms.
- `merge_atoms()` and `split_atom()` have explicit, tested metadata policies.
- Every Crystal-returning transformation preserves `pbc` unless an API explicitly documents and tests a change.
- Crystal coordinate frames are documented and tested for `move_atoms`, `merge_atoms`, `center_structure`, `translate`, and `rotate`.

### Supercell correctness

- Diagonal supercell behavior remains compatible with current passing tests.
- A determinant-1 non-diagonal basis change preserves physical Cartesian positions.
- A non-diagonal determinant > 1 matrix creates exactly `det(matrix) * n_atoms` atoms with correct positions in the new cell.
- Invalid matrices fail with clear errors: non-integer, non-3×3, zero/negative determinant, singular, or unsupported shape.

### Placeholder API honesty

- `get_niggli_reduced()`, `fragment_molecule()`, and `generate_conformers()` no longer silently return fake scientific results.
- Each incomplete function either has a real tested implementation or raises `NotImplementedError` with a clear message.

### High-throughput behavior

- Pipeline save rejects unsupported kwargs or serializes them through explicit codecs; it does not silently stringify typed values.
- Random perturbation helpers do not mutate NumPy global RNG state.
- `process_stream()` yields sequential inputs lazily without materializing the full iterable.

### Verification

- Existing focused transformation suite continues to pass: `tests/test_transformation.py`, `tests/test_structural_transformations.py`, `tests/test_composite_pipeline.py`, `tests/test_composite_batch.py`, `tests/test_composite_sweep.py`, `tests/test_atomic_operations.py`, `tests/test_substitution_common.py`, `tests/test_substitution_dict_selection.py`, `tests/test_substitution_multi_partial.py`.
- New regression tests cover every issue above.
- Run broader core tests most likely to be affected: `tests/test_core_design_fixes.py`, `tests/test_crystal_comprehensive.py`, `tests/test_molecule_comprehensive.py`, `tests/test_lattice_operations.py`.

## Implementation sequence

### Phase 0 — Baseline and characterization tests

**Goal:** Lock current bugs into tests before changing implementation.

Add a new regression test file, suggested path:

- `tests/test_transformation_regressions.py`

Test cases:

1. **Site metadata reordering**
   - Create `Crystal(['Na', 'Cl'], ..., site_properties=[{'id': 'Na'}, {'id': 'Cl'}])`.
   - `swap_atoms(crystal, 0, 1)` should produce species `('Cl', 'Na')` and properties `({'id': 'Cl'}, {'id': 'Na'})`.
   - `sort_atoms(crystal, key='species')` should keep metadata attached to the sorted species.

2. **Site metadata cardinality changes**
   - `merge_atoms()` with metadata should not crash.
   - Expected initial policy: merged atom keeps first atom's properties unless explicit `site_properties`/callback support is added.
   - `split_atom()` with metadata should not crash.
   - Expected initial policy: split children inherit the source atom properties unless explicit child properties are provided.

3. **PBC preservation**
   - For `pbc=[True, True, False]`, verify PBC survives:
     - `make_supercell()`
     - `perturb_positions()`
     - `scale_lattice()`
     - `apply_strain()`
     - `apply_deformation()`
     - `rotate_lattice()`
     - `translate()`
     - `rotate()`

4. **General supercell correctness**
   - Determinant-1 shear matrix preserves physical Cartesian positions.
   - Determinant-2 off-diagonal matrix returns two image representatives per original atom with correct positions.

5. **Placeholder APIs**
   - Assert chosen behavior: `NotImplementedError` or real results.

6. **RNG isolation**
   - Capture `np.random.get_state()` or compare generated random sequence before/after calling perturb helpers with a seed.

7. **Pipeline serialization**
   - Saving a pipeline with NumPy-array kwargs should either reload as equivalent arrays or fail at save time with `TypeError`.

**Files touched:** tests only.

**Stop condition:** New tests fail for the known issues and pass for existing unaffected behavior.

---

### Phase 1 — Centralize rebuild and validation helpers

**Goal:** Remove duplicated construction logic before broad fixes.

Add internal helper module:

- `matsimpy/transformation/_helpers.py`

Suggested helpers:

```python
def validate_vector3(name, value) -> np.ndarray: ...
def validate_matrix3(name, value, *, integer=False, nonsingular=False, positive_det=False) -> np.ndarray: ...
def copy_site_properties_for_indices(site_properties, indices): ...
def copy_site_properties_like(source): ...
def rebuild_molecule_like(source, species, positions, *, site_properties=None) -> Molecule: ...
def rebuild_crystal_like(source, species, positions, *, lattice=None, coords_are_cartesian=False, pbc=None, site_properties=None) -> Crystal: ...
```

Design rules:

- `rebuild_crystal_like()` defaults to `source.lattice` and `source.pbc` if not provided.
- All helpers deep-copy/normalize site properties by relying on existing `Crystal`/`Molecule` validators.
- Helpers are internal; do not export from top-level transformation API.

Refactor current reconstruction sites gradually:

- `matsimpy/transformation/geometric/translation.py`
- `matsimpy/transformation/geometric/rotation.py`
- `matsimpy/transformation/atomic/manipulation.py`
- `matsimpy/transformation/atomic/organization.py`
- `matsimpy/transformation/lattice/scale.py`
- `matsimpy/transformation/lattice/strain.py`
- `matsimpy/transformation/lattice/transform.py`
- `matsimpy/transformation/structural/supercell.py`

**Stop condition:** No functional changes except helper use; existing tests still pass.

---

### Phase 2 — Fix site metadata semantics

**Goal:** Make atom-row transformations preserve or intentionally transform metadata.

Implement policies:

1. `move_atoms()`
   - Same atom order/cardinality: copy properties unchanged.

2. `swap_atoms()`
   - Swap species, positions, and properties together.

3. `sort_atoms()`
   - Reorder properties by `sorted_indices`.

4. `merge_atoms()`
   - Delete both source rows and insert one row.
   - Default merged property policy: copy properties from `index1` / chosen kept atom.
   - Optional future extension: `merge_properties: Callable[[dict, dict], dict]`.

5. `split_atom()`
   - Remove source row and append child rows.
   - Default child property policy: copy source properties to every child.
   - Optional future extension: `site_properties` argument for children.

6. `standardize_cell()`
   - If spglib mapping is unavailable, default to dropping site properties with a warning or require `preserve_site_properties=False`.
   - Do not reuse old properties when atom count/order changes.

**Files touched:**

- `matsimpy/transformation/atomic/manipulation.py`
- `matsimpy/transformation/atomic/organization.py`
- `matsimpy/transformation/lattice/transform.py`
- `tests/test_transformation_regressions.py`

**Stop condition:** Metadata tests pass; existing atomic/substitution/composite tests pass.

---

### Phase 3 — Preserve PBC everywhere

**Goal:** Eliminate silent dimensionality changes.

Fix known omissions:

- `matsimpy/transformation/structural/supercell.py` should pass `pbc=list(crystal.pbc)`.
- `matsimpy/transformation/atomic/organization.py::perturb_positions()` should preserve PBC for Crystal.

Audit all Crystal-returning transformations after helper migration. Any direct `Crystal(...)` call must specify or inherit PBC.

**Stop condition:** Partial-PBC regression tests pass for all Crystal transformations.

---

### Phase 4 — Correct general supercell generation

**Goal:** Make non-diagonal supercells physically correct.

Implementation approach:

1. Validate `scaling_matrix`:
   - Accept `[a, b, c]` positive integers as diagonal.
   - Accept 3×3 integer matrices with positive determinant.
   - Reject non-integer floats, zero/negative determinant, and singular matrices.

2. Keep diagonal path if correct, but route through shared code where practical.

3. Replace general path:
   - Generate exactly `det(M)` integer translation representatives.
   - Use a proven algorithm, e.g. Hermite normal form or bounded enumeration over `M`'s fundamental parallelepiped.
   - Convert old fractional coordinates to new fractional coordinates consistently with row-vector convention:
     - old Cartesian: `old_frac @ old_lattice_vectors`
     - new lattice: `M @ old_lattice_vectors`
     - new fractional must satisfy `new_frac @ new_lattice_vectors == old_cart + image_cart`.

4. Preserve properties through image replication.

5. Preserve PBC.

**Files touched:**

- `matsimpy/transformation/structural/supercell.py`
- `tests/test_transformation_regressions.py`
- Possibly add helper math to `matsimpy/transformation/_helpers.py`

**Stop condition:** Diagonal and non-diagonal supercell tests pass, including physical-position checks.

---

### Phase 5 — Make placeholder APIs honest

**Goal:** Avoid successful-looking no-op scientific output.

Functions:

- `matsimpy/transformation/lattice/transform.py::get_niggli_reduced()`
- `matsimpy/transformation/structural/molecular.py::fragment_molecule()`
- `matsimpy/transformation/structural/molecular.py::generate_conformers()`

Recommended decisions:

1. `get_niggli_reduced()`
   - If spglib has a suitable Niggli primitive/reduction API available in current environment, implement it.
   - Otherwise raise `NotImplementedError("Niggli reduction is not implemented; use spglib/pymatgen adapter once added")`.

2. `fragment_molecule()`
   - Raise `NotImplementedError` until molecule bond graph semantics are implemented.
   - Do not return `[molecule.copy()]` for arbitrary `break_indices`.

3. `generate_conformers()`
   - If RDKit conversion is not implemented, raise `NotImplementedError` after import check.
   - Do not return repeated copies.

**Compatibility note:** This is a behavior change, but it changes fake success into explicit failure. Document in review/CHANGELOG if project has one.

**Stop condition:** Placeholder tests assert explicit failure or real functionality.

---

### Phase 6 — Validate coordinate-frame and lattice matrix contracts

**Goal:** Make transformation semantics predictable.

Tasks:

1. Update docstrings for:
   - `move_atoms(cartesian=...)`
   - `merge_atoms(position=...)`
   - `split_atom(positions=...)`
   - `center_structure(center=...)`
   - `apply_deformation(deform_positions=...)`
   - `transform_lattice(transform_positions=...)`

2. Add validations:
   - 3-vector arguments: translation, displacement, axis, center, positions.
   - 3×3 matrices: strain, deformation, rotation, scaling.
   - positive scalar: amplitude, target volume, target density.

3. Add row-vector convention tests for active rotations and lattice basis changes.

**Stop condition:** Invalid inputs fail early with domain-specific errors; documented coordinate-frame tests pass.

---

### Phase 7 — Harden composite/high-throughput helpers

**Goal:** Make batch/pipeline/sweep behavior reliable under scale.

Tasks:

1. `TransformationPipeline.save()`
   - Remove `default=str`.
   - Add a supported JSON encoder for primitive types, lists, dicts, and NumPy arrays, or raise `TypeError` for unsupported kwargs.

2. `TransformationPipeline.load()`
   - Reconstruct supported typed kwargs, especially arrays.

3. `BatchProcessor._process_parallel()`
   - Separate multiprocessing infrastructure failures from transformation failures.
   - Consider storing exception class and traceback in `BatchResult`.

4. `BatchProcessor.process_stream()`
   - Make sequential mode truly lazy.
   - Document or improve parallel streaming.

5. `ParameterSweep`
   - Avoid precomputing all combinations for large sweeps.
   - Keep `__len__` available by calculating counts without materializing where possible.

**Stop condition:** New tests prove typed pipeline round-trip/fail-fast behavior, lazy stream behavior, and sweep generation remains compatible.

---

## Suggested execution order by risk

1. Phase 0 tests.
2. Phase 1 helpers.
3. Phase 3 PBC preservation — narrow and high-value.
4. Phase 2 metadata fixes — high impact and broad but straightforward after helpers.
5. Phase 4 general supercell — highest algorithmic complexity; isolate after invariants are locked.
6. Phase 5 placeholder honesty.
7. Phase 6 validation/doc contracts.
8. Phase 7 high-throughput hardening.

## Test matrix

### Focused tests to run after each phase

```bash
python -m pytest tests/test_transformation_regressions.py
python -m pytest tests/test_transformation.py tests/test_atomic_operations.py tests/test_structural_transformations.py
```

### Broader transformation suite

```bash
python -m pytest \
  tests/test_transformation.py \
  tests/test_structural_transformations.py \
  tests/test_composite_pipeline.py \
  tests/test_composite_batch.py \
  tests/test_composite_sweep.py \
  tests/test_atomic_operations.py \
  tests/test_substitution_common.py \
  tests/test_substitution_dict_selection.py \
  tests/test_substitution_multi_partial.py
```

### Core regression suite likely affected

```bash
python -m pytest \
  tests/test_core_design_fixes.py \
  tests/test_crystal_comprehensive.py \
  tests/test_molecule_comprehensive.py \
  tests/test_lattice_operations.py
```

### Final verification target

Run full test suite if environment optional-dependency expectations are clear. If full suite still has known optional-dependency failures, report exact failures and rerun the relevant non-optional subsets above.

## Risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Metadata policy may surprise users | Merge/split/standardize have no universally correct metadata mapping | Pick conservative defaults, document them, and expose future callbacks. |
| Supercell algorithm can regress diagonal behavior | Existing tests and users likely depend on diagonal supercells | Preserve diagonal path initially; add compatibility tests before replacing internals. |
| Placeholder functions changing to errors may break callers | Existing callers may rely on no-op success accidentally | Add clear errors and release-note entry; optionally deprecate before raising if compatibility is prioritized. |
| Helper refactor could touch many files | Broad reconstruction churn can introduce regressions | Phase helper migration separately and run focused suite after each module. |
| Pipeline serialization changes may reject formerly accepted files | `default=str` allowed lossy saves | Version pipeline schema and provide explicit error messages. |

## Concrete work breakdown

### PR 1 — Regression tests and helper foundation

- Add `tests/test_transformation_regressions.py`.
- Add `matsimpy/transformation/_helpers.py`.
- Migrate one low-risk module (`geometric/translation.py`) to helpers as proof of pattern.
- Verification: focused transformation tests.

### PR 2 — PBC and metadata one-to-one fixes

- Migrate `atomic/manipulation.py` and `atomic/organization.py` to helpers.
- Fix `swap_atoms()`, `sort_atoms()`, `move_atoms()`, `perturb_positions()`.
- Preserve PBC in `perturb_positions()`.
- Verification: atomic + regression tests.

### PR 3 — Metadata cardinality and standardization policy

- Fix `merge_atoms()` and `split_atom()` metadata behavior.
- Make `standardize_cell()` drop/reindex metadata explicitly.
- Add tests for annotated structures.
- Verification: regression + lattice transform tests.

### PR 4 — Supercell correctness

- Rewrite non-diagonal supercell generation.
- Preserve PBC and metadata for replicated atoms.
- Add diagonal, shear, unimodular, determinant > 1 tests.
- Verification: supercell-focused and full transformation suite.

### PR 5 — Placeholder API honesty

- Update no-op public functions to real implementation or explicit `NotImplementedError`.
- Update tests and docs/comments.
- Verification: structural/lattice tests.

### PR 6 — Validation, RNG, composite hardening

- Add vector/matrix/scalar validators across remaining modules.
- Switch perturb helpers to local RNG.
- Remove pipeline `default=str`; add typed serialization or fail-fast.
- Make `process_stream()` sequential mode lazy.
- Make sweep combinations lazy or count-only.
- Verification: composite suite + relevant core tests.

## Execution handoff guidance

### Solo `$ralph` path

Use when prioritizing correctness with low merge-conflict risk.

Recommended sequence:

1. `$ralph` on PR 1 + PR 2.
2. Pause for test evidence and review.
3. `$ralph` on PR 3.
4. `$ralph` on PR 4 separately because supercell math is algorithmically risky.
5. `$ralph` on PR 5 + PR 6.

### Parallel `$team` path

Use if speed matters and coordination overhead is acceptable.

Suggested lanes:

- Lane A (`test-engineer`): Phase 0 regression tests only.
- Lane B (`executor`): helper foundation and PBC preservation.
- Lane C (`executor`): metadata semantics after Lane A tests are drafted.
- Lane D (`architect`/`executor`): general supercell algorithm design + implementation.
- Lane E (`executor`): placeholder API honesty and composite hardening.
- Lane F (`verifier`): independent validation, test adequacy, and final evidence.

Dependency rule: Lane C and D should not finalize until Lane A regression tests exist. Lane D should be isolated to avoid conflicting with helper migration.

## Completion checklist

Checked on 2026-05-03 after the Ralph remediation pass.

- [ ] New regression tests cover all review findings.
  - Status: regression coverage was added for the critical/high remediation scope and selected medium-risk findings: metadata remapping, PBC preservation, non-diagonal supercell behavior, placeholder API honesty, RNG isolation, pipeline serialization, and stream laziness.
  - Deferred: a full input-validation audit across every transformation and a full crystallographic supercell algorithm proof suite remain follow-up work.
- [x] All Crystal-returning transformations preserve PBC unless documented otherwise.
  - Evidence: code audit of Crystal constructors under `matsimpy/transformation` and regression coverage for supercell/perturb paths.
- [ ] Site metadata is preserved/reindexed/dropped by explicit policy in every transformation.
  - Status: implemented for the reviewed high-risk mutating paths (`swap_atoms`, `sort_atoms`, `merge_atoms`, `split_atom`, `make_supercell`, molecule alignment/merge) and fail-safe dropped for `standardize_cell()` when spglib may change atom count/order.
  - Deferred: consolidate this as a documented cross-module policy and migrate remaining pass-through transformations to the shared helper for consistency.
- [x] General supercell tests verify physical Cartesian positions.
  - Evidence: `test_make_supercell_general_unimodular_preserves_cartesian_positions` verifies periodic Cartesian equivalence for a non-diagonal unimodular matrix.
- [x] Placeholder functions no longer silently fake results.
  - Evidence: `fragment_molecule()`, `generate_conformers()`, and `get_niggli_reduced()` now raise `NotImplementedError`; regression test covers all three.
- [x] Random perturbation does not mutate global RNG state.
  - Evidence: regression tests cover `perturb_positions()` and `perturb_lattice()`.
- [x] Pipeline serialization is typed or fail-fast.
  - Evidence: regression tests cover NumPy-array round-trip and opaque-object `TypeError`.
- [x] `process_stream()` is genuinely lazy in sequential mode.
  - Evidence: regression test confirms the second input item is not consumed before first yield.
- [x] Focused transformation suite passes.
  - Evidence: `python -m pytest tests/test_transformation_regressions.py tests/test_transformation.py tests/test_structural_transformations.py tests/test_composite_pipeline.py tests/test_composite_batch.py -q` -> 63 passed.
- [x] Core affected suite passes.
  - Evidence: `python -m pytest tests/test_core_design_fixes.py tests/test_crystal_comprehensive.py tests/test_molecule_comprehensive.py tests/test_lattice_operations.py -q` -> 101 passed.
- [x] Remaining risks and any intentionally deferred work are documented.
  - Remaining risks: full transformation-wide validation audit, helper migration for remaining pass-through transformations, and deeper crystallographic supercell validation beyond the current determinant/periodic-equivalence tests.
