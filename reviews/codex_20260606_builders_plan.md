# Builders Modules Implementation Plan

Date: 2026-06-06

Status: Completed (2026-06-06)

Source review: `reviews/codex_20260606_builders_review.md`

## Objective

Make MatSimPy builders fail explicitly or construct physically correct structures for the reviewed edge cases, with tests that validate geometry, symmetry, composition, and public API exports rather than only object type and atom count.

## Scope

In scope:

- `matsimpy/builders/surface/adsorbate.py`
- `matsimpy/builders/surface/slab.py`
- `matsimpy/builders/bulk/symmetry.py`
- `matsimpy/builders/bulk/prototype.py`
- `matsimpy/builders/nanostructure/twisted.py`
- `matsimpy/builders/alloy/ordered.py`
- `matsimpy/builders/alloy/random.py`
- `matsimpy/builders/alloy/heusler.py`
- `matsimpy/builders/alloy/__init__.py`
- `matsimpy/builders/molecule/geometry.py`
- Focused tests under `tests/builders/`

Out of scope:

- Full crystallographic slab/symmetry engine replacement unless required and explicitly approved
- New external dependencies unless reference-backed correctness requires them
- Calculator, storage, IO, core, DFT, MatterSim, or transformation work
- Broad documentation rewrites unrelated to changed builder contracts

## Success Criteria

- [x] Adsorbate height is measured along the slab normal for non-(001) slabs.
- [x] `from_space_group()` either returns a structure validated as the requested group or raises a clear error.
- [x] Twisted multilayer builders preserve Cartesian positions and intended layer spacing.
- [x] Unsupported intermetallic structure types do not silently return pure FCC structures.
- [x] Random alloy count allocation is deterministic, bounded by available sites, and compositionally defensible for small cells.
- [x] Magic-angle builder docs/behavior are aligned with real angle semantics or explicit simplified behavior.
- [x] Single-site prototypes reject unrepresentable multi-element formula strings.
- [x] Slab builders report or validate projected slab/vacuum geometry where practical.
- [x] Low-severity validation/export gaps are covered by focused tests.
- [x] Targeted builders tests and full test suite pass.

## Priority Order

1. Fix high-severity silent scientific corruption: adsorbate normal placement, space-group validation, twisted multilayer coordinates, unsupported intermetallic fallback.
2. Fix medium-severity composition/geometry contracts: random alloy counts, magic-angle semantics, prototype formula handling, slab geometric validation.
3. Fix low-severity robustness/API gaps: molecule linear validation, ordered alloy index validation, Heusler re-export.
4. Add semantic tests and validation evidence for each corrected contract.

## Phase 1: Baseline Evidence

- [x] Run `conda run -n pmg python -m pytest tests/builders -q`.
- [x] Reproduce and record high-risk cases:
  - [x] non-(001) adsorbate height measured along global z instead of slab normal.
  - [x] `from_space_group(225, ...)` returning detected SG 221.
  - [x] `build_twisted_multilayer()` producing unrealistic Cartesian z-range.
  - [x] `generate_intermetallic(..., "L1_0", ...)` returning pure first element.
- [x] Identify exact existing tests that should be preserved for happy paths.

Acceptance:

- Baseline behavior and current pass state are known before implementation.

## Phase 2: Surface Adsorbate Normal Placement

- [x] Compute slab unit normal from `slab.lattice.lattice_vectors[2]`.
- [x] Project slab atom Cartesian positions onto the normal.
- [x] Use `max_projection + height` as the adsorbate normal coordinate.
- [x] Preserve in-plane site placement using slab `a`/`b` vectors without assuming global z alignment.
- [x] Validate `height` is finite and non-negative or positive according to current documented semantics.
- [x] Preserve current behavior for (001)-like slabs where normal aligns with global z.
- [x] Add tests for:
  - [x] `(1, 1, 1)` slab adsorbate separation along normal equals requested height.
  - [x] `(1, 1, 0)` slab adsorbate separation along normal equals requested height.
  - [x] existing simple slab adsorbate placement still works.
  - [x] invalid height raises clear error.

## Phase 3: Space-Group Builder Validation

- [x] Inspect current `from_space_group()` expansion/fallback paths.
- [x] Stop deriving operations from the detected symmetry when it differs from the requested space group unless that path is explicitly validated.
- [x] After generated structure construction, re-run space-group detection with the requested tolerance.
- [x] If detected group does not match requested group, raise `ValueError` explaining that the given positions/lattice cannot generate the requested group.
- [x] Prefer requested-group operations from a reliable source if already available in dependencies.
- [x] Add tests for:
  - [x] SG 225 NaCl-like mismatch returns error or validated correct group.
  - [x] SG 227 and SG 194 known examples validate as requested.
  - [x] fallback path cannot silently return a different space group.

## Phase 4: Twisted Multilayer Cartesian/Fractional Handling

- [x] Keep combined layer coordinates in Cartesian coordinates through the build loop.
- [x] Construct final `Crystal(..., coords_are_cartesian=True)` or explicitly convert to fractional using the final lattice.
- [x] Validate `layer_spacing` is finite and positive.
- [x] Validate `n_layers` is a positive integer.
- [x] Preserve existing atom counts and layer species ordering.
- [x] Add tests for:
  - [x] three-layer z separations match requested `layer_spacing`.
  - [x] final Cartesian z-range is on intended cell scale, not multiplied by lattice length.
  - [x] final lattice c length is consistent with layer count/spacing.
  - [x] existing two-layer twisted structures still construct.

## Phase 5: Intermetallic Builder Contract

- [x] Define supported `structure_type` values explicitly.
- [x] Implement documented `L1_0` if feasible with a simple ordered tetragonal/binary prototype.
- [x] For unsupported structures, raise `NotImplementedError` or `ValueError` instead of returning pure FCC.
- [x] Validate `elements` length against composition and structure type.
- [x] Validate `composition` compatibility with supported prototypes.
- [x] Preserve existing `L1_2` and `B2` behavior.
- [x] Add tests for:
  - [x] `L1_0` if implemented.
  - [x] unsupported structure type raises.
  - [x] composition mismatch raises.
  - [x] missing/extra element counts raise.
  - [x] supported structures contain all expected elements.

## Phase 6: Random Alloy Count Allocation

- [x] Replace independent `round(conc * n_sites)` allocation with floor plus largest-remainder distribution.
- [x] Ensure total substitution count never exceeds available sites.
- [x] Decide small-cell policy:
  - [x] allocate closest representable integer counts deterministically; or
  - [x] raise when requested fractions cannot be represented within a tolerance.
- [x] Preserve seed determinism.
- [x] Validate concentration values are finite, non-negative, and sum to at most one.
- [x] Add tests for:
  - [x] 3 target sites with `[0.5, 0.5]` does not sample 4 sites.
  - [x] 2 target sites with `[0.25, 0.25]` follows chosen small-cell policy.
  - [x] deterministic counts and site choices under seed.
  - [x] invalid concentration sums/values raise clear errors.

## Phase 7: Magic-Angle Builder Contract

- [x] Decide whether `build_magic_angle_twisted()` should implement real commensurate magic-angle behavior or be renamed/re-documented as simplified.
- [x] Validate `n` and `m` are positive integers.
- [x] Compute and expose the rotation angle deterministically, possibly via metadata or return documentation.
- [x] If real magic-angle support is retained, implement a validated commensurate angle formula and choose defaults targeting about 1.1 degrees.
- [x] If simplified behavior is retained, update docs/tests so defaults are not advertised as magic angle.
- [x] Add tests for:
  - [x] known `(n, m)` angle values.
  - [x] default angle contract.
  - [x] invalid indices.

## Phase 8: Prototype Formula Handling

- [x] Detect parsed multi-element formulas on single-site prototypes such as `fcc`, `bcc`, and `sc`.
- [x] Reject unrepresentable formulas with clear `ValueError`.
- [x] Preserve valid single-element prototype construction.
- [x] Preserve valid multi-site prototype formula mapping.
- [x] Direct users to alloy builders for random/ordered solid solutions in error text if appropriate.
- [x] Add tests for:
  - [x] `from_prototype("fcc", "CuNi", ...)` raises.
  - [x] `from_prototype("bcc", "FeCr", ...)` raises.
  - [x] valid single-element formulas still work.
  - [x] valid compound prototypes still include all expected elements.

## Phase 9: Slab Geometric Validation

- [x] After slab construction, compute projected atom extents along the slab normal.
- [x] Report or validate actual slab thickness and vacuum thickness.
- [x] Ensure requested minimum vacuum is satisfied along the c-normal.
- [x] Add optional metadata or helper output only if existing APIs support it cleanly.
- [x] Add tests for:
  - [x] skewed/non-cubic lattice slab vacuum projection.
  - [x] high-index surface projected thickness/vacuum.
  - [x] existing simple slab atom count/type behavior remains unchanged.

## Phase 10: Low-Severity Validation And Exports

### Linear molecule builder

- [x] Validate `axis` shape is exactly 3.
- [x] Validate `axis` values are finite.
- [x] Reject zero-norm axis.
- [x] Validate bond lengths are finite and positive.
- [x] Add tests for zero axis, malformed axis, NaN axis, zero length, and negative length.

### Ordered alloy index validation

- [x] Reject negative indices at builder level or delegate all validation consistently to `substitute()`.
- [x] Reject non-integer indices clearly.
- [x] Add tests for negative and non-integer pattern indices.

### Heusler export

- [x] Add `build_inverse_heusler_quaternary` to `matsimpy.builders.alloy.__init__` exports if public.
- [x] Add package-level import/export tests for Heusler builders.

## Phase 11: Documentation And Examples

- [x] Document normal-direction adsorbate placement (in source docstrings).
- [x] Document `from_space_group()` validation/failure behavior.
- [x] Document supported intermetallic structures.
- [x] Document random alloy count allocation policy for small cells.
- [x] Document magic-angle builder semantics or rename/deprecation path.
- [x] Document single-site prototype formula limitations.

## Verification Plan

- [x] `python -m pytest tests/builders/test_builders_surface.py -q`
- [x] `python -m pytest tests/builders/test_builders_bulk_symmetry.py tests/builders/test_builders_bulk.py -q`
- [x] `python -m pytest tests/builders/test_builders_nanostructure.py -q`
- [x] `python -m pytest tests/builders/test_builders_alloy.py tests/builders/test_heusler.py -q`
- [x] `python -m pytest tests/builders/test_builders_molecule.py -q`
- [x] `python -m pytest tests/builders -q`
- [x] `python -m compileall matsimpy/builders`
- [x] `python -m pytest tests/test_packaging_runtime_contracts.py -q`
- [x] `python -m pytest -q`

Manual evidence to collect:

- [ ] Adsorbate-slab gap along slab normal equals requested height for non-(001) slabs.
- [ ] `from_space_group()` generated output validates as requested group or raises.
- [ ] Twisted multilayer z-range and layer spacing remain physically scaled.
- [ ] Unsupported intermetallic request raises instead of returning pure FCC.
- [ ] Random alloy small-cell cases are bounded and deterministic.
- [ ] Single-site prototype with binary formula raises clearly.

## Implementation Checklist

- [x] Record baseline builders test status.
- [x] Fix adsorbate normal-direction placement.
- [x] Add non-(001) adsorbate distance tests.
- [x] Fix or validate `from_space_group()` requested group behavior.
- [x] Add space-group validation/failure tests.
- [x] Fix twisted multilayer Cartesian/fractional handling.
- [x] Add twisted multilayer spacing tests.
- [x] Fix unsupported intermetallic fallback.
- [x] Add intermetallic unsupported/composition tests.
- [x] Fix random alloy count allocation.
- [x] Add small-cell alloy allocation tests.
- [x] Align magic-angle builder semantics with implementation.
- [x] Add angle-contract tests.
- [x] Reject unrepresentable multi-element formulas in single-site prototypes.
- [x] Add prototype formula tests.
- [x] Add slab projected geometry validation.
- [x] Add slab thickness/vacuum tests.
- [x] Add linear molecule validation.
- [x] Add ordered alloy index validation.
- [x] Export quaternary inverse Heusler builder or mark private.
- [x] Run targeted builders tests.
- [x] Run compileall for `matsimpy/builders`.
- [x] Run full pytest.
- [x] Update this plan with completion notes and final verification evidence.

## Risk Controls

- Do not silently substitute global-axis shortcuts for normal-direction geometry.
- Do not return wrong-space-group structures from an API named for a requested space group.
- Do not interpret Cartesian coordinates as fractional coordinates.
- Do not keep fallback builders that silently drop requested species.
- Prefer explicit unsupported errors over approximate scientific behavior without validation.
- Keep dependency use conservative; if using external crystallographic references, add tests and document the boundary.

## Stop Condition

Stop when all high findings are fixed, medium findings are fixed or explicitly deferred with rationale, low findings are covered where low-risk, targeted builders tests pass, full pytest passes, and this plan is updated with completion notes plus validation evidence.

## Completion Notes (2026-06-06)

### Baseline
- Before: 138 builders tests passed
- After: 158 builders tests passed (+20 new tests)
- Full suite: 1401 passed, 1 skipped

### Files Changed (15)
Source:
- `matsimpy/builders/surface/adsorbate.py` — normal-direction placement
- `matsimpy/builders/surface/slab.py` — projected vacuum validation
- `matsimpy/builders/bulk/symmetry.py` — post-construction space-group validation
- `matsimpy/builders/bulk/prototype.py` — single-site multi-element rejection
- `matsimpy/builders/nanostructure/twisted.py` — Cartesian fix, magic-angle validation, layer_spacing/n_layers validation
- `matsimpy/builders/alloy/ordered.py` — L1_0 support, unsupported raises NotImplementedError, negative index check
- `matsimpy/builders/alloy/random.py` — floor-plus-largest-remainder allocation
- `matsimpy/builders/alloy/__init__.py` — Heusler quaternary re-export
- `matsimpy/builders/molecule/geometry.py` — build_linear axis/bond validation

Tests:
- `tests/builders/test_builders_surface.py` — adsorbate normal distance, invalid height, slab vacuum
- `tests/builders/test_builders_bulk_symmetry.py` — SG validation/raise tests
- `tests/builders/test_builders_bulk.py` — prototype multi-element rejection
- `tests/builders/test_builders_nanostructure.py` — multilayer spacing, magic-angle validation
- `tests/builders/test_builders_alloy.py` — intermetallic unsupported/composition, random alloy small-cell, ordered alloy negative index
- `tests/builders/test_builders_molecule.py` — linear molecule validation
- `tests/builders/test_heusler.py` — Heusler export
