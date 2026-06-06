# IO Modules Implementation Plan

Date: 2026-06-06

Status: Completed (2026-06-06)

Source review: `reviews/codex_20260606_review_io_modules.md`

## Objective

Make MatSimPy IO safer and more consistent by eliminating silent atom/frame loss, aligning advertised format contracts with high-level read/write behavior, hardening malformed-input validation, and documenting or enforcing limitations for CIF and tolerant parsing.

## Scope

In scope:

- `matsimpy/io/ase.py`
- `matsimpy/io/mol.py`
- `matsimpy/io/pdb.py`
- `matsimpy/io/cif.py`
- `matsimpy/io/vasp.py`
- `matsimpy/io/xyz.py`
- `matsimpy/io/latex.py`
- `matsimpy/io/core.py`
- `matsimpy/io/utils.py`
- Focused tests under `tests/io/`

Out of scope:

- Full crystallographic CIF engine unless explicitly chosen during implementation
- New external parser dependencies unless the dependency tradeoff is separately reviewed
- Broad test-suite cleanup unrelated to IO contracts
- Calculator, storage, transformation, builders, or DFT work

## Success Criteria

- [ ] ASE, MOL, PDB, and XYZ multiframe readers no longer silently drop declared atoms or frames in strict/default mode.
- [ ] High-level `.ase` molecule behavior is internally consistent: either read/write round-trips or `.ase` is no longer advertised as molecule-compatible.
- [ ] `read_PDB(..., as_crystal=True)` fails clearly when `CRYST1` is absent or invalid.
- [ ] PDB fallback element inference handles common two-letter elements.
- [ ] CIF occupancy and symmetry limitations are either supported or rejected explicitly.
- [ ] CIF loop tokenization validates quoted/malformed row widths.
- [ ] VASP negative scale factors follow POSCAR volume semantics.
- [ ] LaTeX export escapes ordinary user text by default.
- [ ] Format aliases and compatibility metadata are centralized enough to avoid reader/writer drift.
- [ ] Targeted IO tests and full test suite pass.

## Priority Order

1. Fix silent data-loss paths: ASE count validation, MOL count validation, PDB malformed atom handling, XYZ multiframe strictness.
2. Resolve advertised format contract drift: `.ase` molecule behavior and registry/high-level normalization.
3. Harden PDB crystal mode and element inference.
4. Define CIF policy for occupancy, symmetry, and loop tokenization.
5. Implement VASP negative scale factor semantics.
6. Add LaTeX escaping.
7. Consolidate registry/alias metadata and advertised-format round-trip tests.

## Phase 1: Baseline And Policy Decisions

- [ ] Run `conda run -n pmg python -m pytest tests/io -q`.
- [ ] Reproduce the focused review cases:
  - [ ] `.ase` molecule high-level write/read mismatch.
  - [ ] ASE declared atom count greater than coordinate lines.
  - [ ] MOL declared atom count greater than valid atom lines.
  - [ ] PDB `as_crystal=True` without `CRYST1`.
  - [ ] PDB malformed ATOM/HETATM line among valid records.
- [ ] Decide package-level parser policy:
  - [ ] Default readers are strict and raise on malformed declared records.
  - [ ] Optional tolerant mode may be added only when skipped-line behavior is explicit and tested.
- [ ] Decide `.ase` molecule contract:
  - [ ] Option A: allow `read_ASE()` to return `Molecule` when lattice metadata is absent.
  - [ ] Option B: mark `.ase` as crystal-only and reject molecule writes through high-level `write()`.
- [ ] Decide CIF policy:
  - [ ] Option A: support occupancy/symmetry expansion.
  - [ ] Option B: reject unsupported partial occupancy and non-P1/asymmetric-unit CIFs with explicit errors.

Acceptance:

- Baseline evidence and contract decisions are known before code changes.
- Strict/default parser behavior is consistent across affected readers.

## Phase 2: ASE Contract And Strictness

- [ ] Update `read_ASE()` to reject `n_atoms <= 0`.
- [ ] Require enough lines for the declared atom count.
- [ ] Raise on every malformed coordinate line instead of continuing.
- [ ] Verify parsed species/positions count equals declared header count.
- [ ] Implement the chosen `.ase` molecule contract.
- [ ] Add high-level `.ase` molecule round-trip test if molecule support remains advertised.
- [ ] Add tests for missing coordinate lines, malformed coordinate records, and invalid atom counts.
- [ ] Add tests for explicit `format="ase"` and extension-driven `.ase` read/write consistency.

Acceptance:

- ASE reader cannot return a smaller structure than the declared atom count.
- High-level `.ase` compatibility matches registry metadata.

## Phase 3: MOL Strict Atom Block Validation

- [ ] Treat each declared atom line as required.
- [ ] Raise on short atom lines before parsing.
- [ ] Raise on malformed coordinate or element fields.
- [ ] Verify parsed atom count equals counts-line `n_atoms`.
- [ ] Preserve valid V2000 molecule round-trip behavior.
- [ ] Add tests for malformed declared atom blocks and missing atom lines.

Acceptance:

- MOL reader cannot silently import fewer atoms than declared.

## Phase 4: PDB Strictness, Crystal Mode, And Elements

- [ ] Make malformed ATOM/HETATM coordinate records raise by default.
- [ ] If tolerant mode is added, require `strict=False` and expose skipped-line diagnostics or warnings.
- [ ] Make `read_PDB(..., as_crystal=True)` raise `ValueError` when no valid `CRYST1` record exists.
- [ ] Harden invalid `CRYST1` parsing errors.
- [ ] Implement element inference that tries valid two-letter symbols before one-letter symbols when element columns are absent.
- [ ] Add tests for:
  - [ ] `as_crystal=True` without `CRYST1`.
  - [ ] malformed atom coordinate line among valid atoms.
  - [ ] two-letter elements such as `CL`, `NA`, `FE`, and `MG` without element columns.
  - [ ] valid molecule and crystal PDB read/write paths.

Acceptance:

- PDB crystal requests return `Crystal` or raise, never silently degrade to `Molecule`.
- Malformed PDB records do not silently drop atoms in default mode.

## Phase 5: CIF Policy And Parser Hardening

- [ ] Parse `_atom_site_occupancy` when present.
- [ ] If partial occupancy is unsupported, reject any non-1.0 occupancy with a clear error.
- [ ] Preserve or store full occupancy as site properties only if consistent with core `Crystal` semantics.
- [ ] Detect non-P1 symmetry or symmetry operation loops.
- [ ] If symmetry expansion is unsupported, reject non-P1/asymmetric-unit CIFs with a clear error instead of importing too few atoms.
- [ ] Replace simple loop row splitting with quote-aware tokenization.
- [ ] Validate loop token counts and row widths.
- [ ] Add tests for:
  - [ ] missing occupancy defaults.
  - [ ] partial occupancy rejection or preservation.
  - [ ] non-P1 symmetry/asymmetric unit rejection or expansion.
  - [ ] quoted loop values.
  - [ ] malformed loop row widths.
  - [ ] existing simple P1 CIF round-trips.

Acceptance:

- CIF reader does not pretend unsupported occupancy/symmetry data are fully represented.
- CIF loop parsing cannot silently misalign columns due to quoted values.

## Phase 6: VASP Negative Scale Factor

- [ ] Implement POSCAR negative scale semantics: negative scale means target cell volume.
- [ ] Preserve positive scale and vector parsing behavior.
- [ ] Validate negative scale against non-positive or zero-volume lattice vectors.
- [ ] Add tests for:
  - [ ] unit vectors with scale `-27.0` producing volume `27.0`.
  - [ ] non-unit basis vectors rescaled to requested volume.
  - [ ] positive scale behavior unchanged.

Acceptance:

- Negative POSCAR scale factors import with correct target volume, not negated vectors.

## Phase 7: XYZ Multiframe Strictness

- [ ] Mirror `read_XYZ()` validation in `read_XYZ_multiframe()`.
- [ ] Reject non-positive atom counts.
- [ ] Reject incomplete frames.
- [ ] Raise on malformed coordinate lines in the middle of a trajectory.
- [ ] Decide whether to add `strict=False` tolerant scanning for legacy behavior.
- [ ] Add tests for corrupted middle frame, incomplete final frame, non-integer frame count, and non-positive atom count.

Acceptance:

- Multiframe XYZ imports do not silently truncate corrupted trajectories in default mode.

## Phase 8: LaTeX Escaping

- [ ] Add a shared LaTeX text escaping helper for ordinary user text.
- [ ] Escape captions, labels, column names, and default/custom cell text unless explicitly marked as raw LaTeX.
- [ ] Decide raw formatter policy:
  - [ ] Formatter output is escaped by default.
  - [ ] Add an explicit raw wrapper or option for trusted LaTeX.
- [ ] Add tests for `&`, `%`, `_`, `#`, braces, and backslashes in captions/labels/cells.
- [ ] Preserve current numeric formatting output.

Acceptance:

- User-provided text cannot accidentally break table structure in default LaTeX exports.

## Phase 9: Registry And High-Level API Normalization

- [ ] Centralize aliases and compatibility metadata in one registry/helper path.
- [ ] Remove duplicated `format_map` logic from `read()` and `write()` where feasible.
- [ ] Ensure explicit `format=...` and extension-driven detection use the same normalization.
- [ ] Add parametrized tests that every registered alias works consistently for explicit and extension-driven read/write paths.
- [ ] Add high-level advertised-format round-trip tests for all read/write-compatible formats.

Acceptance:

- Adding or changing a format requires one metadata update, not separate registry and high-level API edits.

## Phase 10: Documentation And Examples

Only update docs/examples if public semantics change:

- [ ] Document strict parser behavior and any `strict=False` tolerant mode.
- [ ] Document `.ase` molecule support decision.
- [ ] Document CIF limitations or newly supported occupancy/symmetry behavior.
- [ ] Document VASP negative scale support.
- [ ] Document LaTeX escaping and raw-output escape hatch.

Acceptance:

- Public docs do not advertise unsupported IO semantics.

## Verification Plan

Run targeted tests during implementation:

- [ ] `conda run -n pmg python -m pytest tests/io/test_io_ase_mol.py tests/io/test_io_mol.py -q` if separate MOL tests exist.
- [ ] `conda run -n pmg python -m pytest tests/io/test_io_pdb.py -q`
- [ ] `conda run -n pmg python -m pytest tests/io/test_io_cif.py -q`
- [ ] `conda run -n pmg python -m pytest tests/io/test_io_vasp.py -q`
- [ ] `conda run -n pmg python -m pytest tests/io/test_io_xyz.py -q`
- [ ] `conda run -n pmg python -m pytest tests/io/test_io_latex.py -q`
- [ ] `conda run -n pmg python -m pytest tests/io/test_io_high_level.py tests/io/test_io_utils.py -q`
- [ ] `conda run -n pmg python -m pytest tests/io -q`

Run broader checks before completion:

- [ ] `conda run -n pmg python -m compileall matsimpy/io`
- [ ] `conda run -n pmg python -m pytest tests/test_packaging_runtime_contracts.py -q`
- [ ] `conda run -n pmg python -m pytest -q`

Manual evidence to collect:

- [ ] ASE/MOL/PDB malformed declared records raise with clear messages.
- [ ] `.ase` molecule behavior matches the chosen contract.
- [ ] `read_PDB(..., as_crystal=True)` without `CRYST1` raises.
- [ ] PDB two-letter fallback inference maps common symbols correctly.
- [ ] CIF unsupported occupancy/symmetry data are rejected or correctly represented.
- [ ] POSCAR negative scale produces the target volume.
- [ ] LaTeX special characters are escaped in default output.
- [ ] Explicit format aliases and extension-driven formats resolve through one shared path.

## Implementation Checklist

- [ ] Record baseline IO test status.
- [ ] Finalize strict/tolerant parser policy.
- [ ] Finalize `.ase` molecule contract.
- [ ] Finalize CIF support/rejection policy.
- [ ] Fix ASE strict atom-count validation.
- [ ] Fix MOL strict atom-block validation.
- [ ] Fix PDB malformed atom handling.
- [ ] Fix PDB `as_crystal=True` behavior.
- [ ] Fix PDB two-letter element inference.
- [ ] Harden CIF occupancy handling.
- [ ] Harden CIF symmetry handling.
- [ ] Harden CIF quote-aware loop parsing.
- [ ] Implement VASP negative scale semantics.
- [ ] Harden XYZ multiframe strict validation.
- [ ] Implement LaTeX escaping.
- [ ] Consolidate format registry/alias normalization.
- [ ] Add high-level advertised-format round-trip tests.
- [ ] Run targeted IO tests.
- [ ] Run compileall for `matsimpy/io`.
- [ ] Run full pytest.
- [ ] Update this plan with completion notes and final verification evidence.

## Risk Controls

- Do not silently convert strict failures into skipped atoms or frames.
- Do not broaden CIF behavior beyond what is tested.
- Preserve existing valid simple P1 CIF, XYZ, XSF, VASP, PDB, MOL, JSON, and ASE round-trips.
- If tolerant parsing is retained, make it opt-in and visibly report skipped records.
- Avoid adding dependencies unless CIF support cannot be made correct enough without one and the tradeoff is explicitly approved.
- Keep docs/examples synchronized with any tightened public behavior.

## Stop Condition

Stop when all high and medium findings are fixed or explicitly deferred with rationale, targeted IO tests pass, full pytest passes, and this plan is updated with completion notes plus validation evidence.
