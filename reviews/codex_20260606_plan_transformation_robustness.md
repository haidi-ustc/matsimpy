# Transformation Robustness Development Plan

Date: 2026-06-06

Status: Complete

Source review: `reviews/codex_20260606_review_transformation_robustness.md`

## Objective

Make the transformation layer safer for production use by fixing metadata loss, large-sweep memory behavior, streaming semantics, parallel error handling, validation clarity, and molecule alignment input checks.

## Scope

In scope:

- `matsimpy/transformation/lattice/transform.py`
- `matsimpy/transformation/composite/sweep.py`
- `matsimpy/transformation/composite/batch.py`
- `matsimpy/transformation/lattice/scale.py`
- `matsimpy/transformation/structural/molecular.py`
- Focused tests under `tests/transformation/` and `tests/code/`

Out of scope:

- DFT calculators
- Calculator/MatterSim work
- Docs/examples unrelated to this review
- Broad transformation refactors unrelated to the six review findings

## Success Criteria

- [x] Existing transformation behavior remains compatible for normal small inputs.
- [x] Site metadata is preserved by `standardize_cell()` when a reliable atom mapping exists.
- [x] Cartesian parameter sweeps can be constructed without materializing the full product.
- [x] `process_stream()` in parallel mode does not convert the full input iterable to a list.
- [x] Parallel batch failures in `error_handling="raise"` do not rerun transformations sequentially.
- [x] Lattice scaling rejects invalid factors, target volume, and target density with clear `ValueError`s.
- [x] Molecule alignment rejects empty or invalid selections before NumPy emits NaN warnings.
- [x] Targeted and full tests pass.

## Review Findings Resolution

### Metadata preservation in `standardize_cell`

- [x] Added a test for preserving `site_properties` when the standardized cell is a pure reorder.
- [x] Kept the existing changed-cell regression so stale metadata is not attached to incompatible outputs.
- [x] Added stable spglib species-number mapping instead of relying on `species.index()`.
- [x] Added one-to-one site-property mapping by species and periodic Cartesian distance tolerance.
- [x] Preserves property order after reordering.
- [x] Drops metadata only when atom count or site mapping is not reliably one-to-one.

Completion note:

`standardize_cell()` now preserves metadata for same-size/reordered cells. When spglib changes the cell in a way that cannot be mapped safely, properties are not attached to the new structure.

### Lazy parameter sweep construction

- [x] Added a huge Cartesian sweep regression test.
- [x] Replaced stored `self._combinations` with lazy combination iterators.
- [x] Kept deterministic ordering for small sweeps.
- [x] Kept `len()` support for finite cartesian, zip, and sized custom combinations.
- [x] Added unknown-length behavior for custom generator sweeps without materializing them.

Completion note:

`ParameterSweep` now computes length from parameter sizes when possible and generates combinations during iteration.

### Parallel stream laziness

- [x] Preserved sequential streaming laziness.
- [x] Replaced parallel-mode list materialization with direct `pool.imap(...)` over `enumerate(structures)`.
- [x] Preserved ordered streaming behavior.
- [x] Added fallback only for non-raise modes.

Completion note:

Parallel `process_stream()` no longer consumes the full input iterable before yielding results.

### Parallel raise-mode failure behavior

- [x] Added a side-effect regression test for `n_workers > 1` and `error_handling="raise"`.
- [x] Added a single helper for consistent failed-result errors.
- [x] Propagates raise-mode failures immediately.
- [x] Does not fall back to sequential processing in raise mode.
- [x] Keeps skip/log compatibility for recoverable parallel infrastructure failures.

Completion note:

Raise-mode parallel failures no longer duplicate transformation side effects through fallback retry.

### Lattice scale validation

- [x] Added `_validate_scale_factor(scale_factor)`.
- [x] Accepts one finite positive scalar.
- [x] Accepts exactly three finite positive factors.
- [x] Rejects invalid vector lengths.
- [x] Rejects zero, negative, NaN, and infinite scale factors.
- [x] Validates `target_volume` before deriving scale.
- [x] Validates `target_density` before deriving scale.
- [x] Preserves existing valid scalar and anisotropic scaling behavior.

Completion note:

Invalid scale, volume, and density inputs now fail at the public API boundary with direct `ValueError`s.

### Molecule alignment validation

- [x] Normalizes selections to integer index arrays.
- [x] Rejects empty selections before slicing.
- [x] Rejects mismatched lengths.
- [x] Rejects out-of-range and negative indices.
- [x] Rejects duplicate indices.
- [x] Keeps existing successful alignment behavior for valid selections.
- [x] Keeps one-atom-pair translation alignment valid.

Completion note:

Empty or invalid selections now raise clear validation errors before NumPy can produce NaN centers.

## Implementation Checklist

- [x] Add regression tests for all six review findings.
- [x] Implement `standardize_cell()` metadata preservation/mapping.
- [x] Implement lazy parameter sweep storage and iteration.
- [x] Implement non-materializing parallel `process_stream()`.
- [x] Fix parallel raise-mode fallback semantics.
- [x] Add explicit lattice scale, target volume, and target density validation.
- [x] Add molecule alignment selection validation.
- [x] Run targeted transformation/composite/lattice tests.
- [x] Run compileall.
- [x] Run full pytest.
- [x] Update this plan with completion notes.

## Verification Evidence

- [x] `conda run -n pmg python -m pytest tests/transformation/test_transformation_regressions.py tests/code/test_composite_sweep.py tests/code/test_composite_batch.py tests/core/test_lattice_operations.py tests/transformation/test_structural_transformations.py -q`
  - Result: 81 passed.
- [x] `conda run -n pmg python -m compileall matsimpy`
  - Result: passed.
- [x] `conda run -n pmg python -m pytest -q`
  - Result: 1448 passed, 1 skipped, 42 warnings.

## Changed Files

- [x] `matsimpy/transformation/lattice/transform.py`
- [x] `matsimpy/transformation/composite/sweep.py`
- [x] `matsimpy/transformation/composite/batch.py`
- [x] `matsimpy/transformation/lattice/scale.py`
- [x] `matsimpy/transformation/structural/molecular.py`
- [x] `tests/transformation/test_transformation_regressions.py`
- [x] `tests/code/test_composite_sweep.py`

## Stop Condition

Complete. Every review finding is addressed, all checklist items are closed, targeted validation passed, and the full test suite passed.
