# Core Modules Implementation Plan

Date: 2026-06-06

Status: Planned

Source review: `reviews/20260606_core_modules_review.md`

## Objective

Stabilize MatSimPy core behavior for invalid neighbor cutoffs, periodic self-neighbor filtering, hash/equality contracts, dummy species mass-derived APIs, anonymous formulas with too many species, graph ring error handling, and large-graph BFS performance.

This plan intentionally follows two user constraints:

- Dummy species must be handled gracefully.
- `anonymous_formula` generally cannot support more than 26 anonymous symbols; above that limit it should fail clearly rather than inventing labels or crashing.

## Scope

In scope:

- `matsimpy/core/molecule.py`
- `matsimpy/core/crystal.py`
- `matsimpy/core/graph.py`
- `matsimpy/core/neighbors.py`
- `matsimpy/core/composition.py`
- `matsimpy/core/lattice.py`
- `matsimpy/core/structure.py`
- `matsimpy/core/site.py`
- Focused tests under `tests/core/`

Out of scope:

- New chemistry semantics for dummy elements beyond safe handling of zero-mass paths
- Supporting anonymous formulas above 26 species
- Large new graph algorithm rewrites beyond replacing list-backed BFS queues and tightening obvious contracts
- IO, storage, calculator, MatterSim, builders, transformations, and DFT work

## Success Criteria

- [ ] Negative, NaN, and infinite cutoffs are rejected consistently in molecule, crystal, and graph APIs.
- [ ] Periodic neighbor queries do not report self-neighbors through periodic images.
- [ ] Graph adjacency matrices do not contain self-loops from periodic image self-neighbors.
- [ ] Hash/equality behavior obeys Python's contract: equal objects have equal hashes, or tolerance-equal objects are unhashable.
- [ ] Dummy-only zero-mass compositions and molecules fail with clear domain-specific `ValueError`s for mass-derived APIs.
- [ ] Mixed dummy/real compositions and molecules behave predictably and do not divide by zero.
- [ ] `anonymous_formula` with more than 26 unique species raises a clear `ValueError` documenting the supported limit.
- [ ] `find_rings()` does not silently hide unexpected NetworkX failures.
- [ ] Graph BFS queues use `collections.deque` where current list queues create avoidable quadratic behavior.
- [ ] Targeted core tests and full test suite pass.

## Priority Order

1. Fix cutoff validation and periodic self-neighbor filtering because these affect physical correctness.
2. Resolve hash/equality consistency because it affects dictionaries, sets, caching, and reproducibility.
3. Add graceful dummy species zero-mass handling.
4. Add controlled `anonymous_formula` limit behavior for more than 26 unique species.
5. Harden ring-detection errors.
6. Replace list-backed BFS queues with `deque`.

## Phase 1: Baseline Evidence

- [ ] Run `conda run -n pmg python -m compileall -q matsimpy/core`.
- [ ] Run `conda run -n pmg python -m pytest tests/core --disable-warnings -q`.
- [ ] Reproduce and record current edge cases:
  - [ ] `Molecule(...).get_neighbor_list(-1)` returns invalid neighbors.
  - [ ] `Crystal(...).get_neighbor_list(-1)` returns invalid neighbors.
  - [ ] One-atom periodic crystal can report itself as neighbor.
  - [ ] `CrystalGraph` can contain diagonal self-loop.
  - [ ] Equal lattices/sites/structures can hash differently at tolerance boundaries.
  - [ ] `Composition("X").mass_fractions()` raises raw divide-by-zero.
  - [ ] Dummy-only `Molecule.get_center_of_mass()` raises raw divide-by-zero.
  - [ ] `anonymous_formula` above 26 unique species raises `IndexError`.

Acceptance:

- Baseline behavior and current pass state are known before implementation.

## Phase 2: Shared Cutoff Validation

- [ ] Add or reuse a shared cutoff validator, preferably in `matsimpy/core/neighbors.py` or `_validation.py`.
- [ ] Validator contract:
  - [ ] Accept finite non-negative numeric cutoffs.
  - [ ] Allow zero only where zero-radius queries are meaningful.
  - [ ] Reject negative values with `ValueError`.
  - [ ] Reject NaN and infinity with `ValueError`.
  - [ ] Reject non-numeric values with `TypeError` or clear `ValueError`, matching existing style.
- [ ] Apply validator to:
  - [ ] `Molecule.get_neighbor_list()`
  - [ ] `Molecule.get_all_neighbor_lists()` if not already fully covered
  - [ ] `Crystal.get_neighbor_list()`
  - [ ] graph constructors/factory paths that accept cutoffs
  - [ ] graph helper methods using cutoff values directly
- [ ] Add regression tests for molecule, crystal, and graph APIs.

Acceptance:

- Invalid cutoff values cannot produce neighbor lists or graphs.
- Existing positive cutoff behavior remains unchanged.

## Phase 3: Periodic Self-Neighbor Filtering

- [ ] In periodic crystal neighbor logic, skip periodic image entries whose reduced atom index equals the query atom index.
- [ ] Preserve valid periodic neighbors for distinct atoms.
- [ ] Ensure distances for distinct periodic images still use minimum-image/periodic logic.
- [ ] Clear the diagonal explicitly in `CrystalGraph.adjacency_matrix` after neighbor-derived adjacency construction.
- [ ] Add regression tests for:
  - [ ] one-atom periodic crystal with cutoff larger than cell vector returns no self-neighbor.
  - [ ] `CrystalGraph(...).adjacency_matrix` diagonal remains zero.
  - [ ] multi-atom periodic crystal still reports valid distinct neighbors.

Acceptance:

- Periodic images of the same atom do not become self-neighbor entries or graph self-loops.

## Phase 4: Hash/Equality Contract

- [ ] Audit `__eq__` and `__hash__` on:
  - [ ] `Lattice`
  - [ ] `Structure`
  - [ ] `Site`
  - [ ] `CrystalSite`
- [ ] Choose a single contract:
  - [ ] Preferred: set `__hash__ = None` for objects whose equality is tolerance-based and not mathematically compatible with stable hashing.
  - [ ] Alternative: make equality compare the same canonical quantized representation used by hashing.
- [ ] Preserve hashability only where equality is exact or canonical quantization is proven consistent.
- [ ] Add tests for tolerance-boundary equal objects:
  - [ ] equal lattices are either unhashable or have identical hashes.
  - [ ] equal sites are either unhashable or have identical hashes.
  - [ ] equal structures are either unhashable or have identical hashes.
- [ ] Add tests that set/dict behavior is consistent with the chosen contract.

Acceptance:

- Python hash/equality invariants are not violated.
- Any loss of hashability is intentional and documented in tests.

## Phase 5: Graceful Dummy Species And Zero-Mass Handling

Policy:

- Dummy species such as `X`, `A`, and `Z` may remain accepted by validation.
- Mass-derived APIs must not raise raw `ZeroDivisionError`.
- Dummy-only or otherwise all-zero-mass inputs should raise clear `ValueError`s.
- Mixed dummy/real inputs should use real atomic masses where mathematically valid and either:
  - ignore zero-mass dummy species in weighted mass calculations only if documented; or
  - include zero mass naturally in formulas where total mass remains positive.

Implementation tasks:

- [ ] Add a shared helper for total-mass validation where useful.
- [ ] In `Composition.mass_fractions()`:
  - [ ] If total mass is zero, raise `ValueError("Cannot compute mass fractions for composition with zero total mass")` or equivalent.
  - [ ] For mixed dummy/real compositions, return zero fraction for dummy species and normalized real-species fractions.
- [ ] In `Molecule.get_center_of_mass()`:
  - [ ] If total mass is zero, raise `ValueError("Cannot compute center of mass for molecule with only zero-mass species")` or equivalent.
  - [ ] For mixed dummy/real molecules, compute weighted center using available real masses.
- [ ] In molecule moment-of-inertia paths:
  - [ ] Reuse the center-of-mass mass validation.
  - [ ] Raise a clear `ValueError` for all-zero-mass molecules.
  - [ ] Keep mixed dummy/real behavior deterministic.
- [ ] Add tests for:
  - [ ] `Composition("X").mass_fractions()` clear `ValueError`.
  - [ ] dummy-only molecule center of mass clear `ValueError`.
  - [ ] dummy-only molecule inertia clear `ValueError`.
  - [ ] mixed dummy/real mass fractions do not divide by zero.
  - [ ] mixed dummy/real center of mass is computed from real mass contributions.

Acceptance:

- Dummy species are allowed as placeholders, but mass-derived APIs fail gracefully when mass information is insufficient.

## Phase 6: `anonymous_formula` Limit

Policy:

- `anonymous_formula` supports at most 26 unique species using `A` through `Z`.
- Compositions with more than 26 unique species are unsupported and should raise a clear `ValueError`.
- Do not implement Excel-style `AA`, `AB`, ... labels unless the public contract is deliberately expanded later.

Implementation tasks:

- [ ] Count unique species before indexing `string.ascii_uppercase`.
- [ ] Raise `ValueError("anonymous_formula supports at most 26 unique species")` or equivalent when the count is greater than 26.
- [ ] Preserve current anonymous formula output for 1-26 unique species.
- [ ] Add tests for:
  - [ ] exactly 26 unique species succeeds.
  - [ ] 27 unique species raises clear `ValueError`.
  - [ ] common binary/ternary anonymous formulas remain unchanged.

Acceptance:

- The method no longer crashes with `IndexError`.
- The unsupported >26 case is documented by tests and error message.

## Phase 7: Ring Detection Error Handling

- [ ] Inspect current `find_rings()` exception handling.
- [ ] Replace broad `except Exception: return []` with narrower handling.
- [ ] Let unexpected NetworkX errors propagate by default.
- [ ] If graceful mode is needed, add an explicit `strict` parameter:
  - [ ] `strict=True` default raises unexpected errors.
  - [ ] `strict=False` warns and returns `[]`.
- [ ] Add tests for:
  - [ ] normal ring detection still returns expected rings.
  - [ ] acyclic graph returns `[]`.
  - [ ] monkeypatched NetworkX failure raises or warns according to strict mode.

Acceptance:

- Algorithm failure is distinguishable from a genuinely ring-free graph.

## Phase 8: Graph BFS Performance Cleanup

- [ ] Replace `list.pop(0)` BFS queues with `collections.deque`.
- [ ] Apply to connected components, shortest path, graph traversal, and related BFS helpers.
- [ ] Keep traversal order stable where tests rely on it.
- [ ] Consider diameter improvement only if a small local change is safe:
  - [ ] Avoid repeated avoidable work.
  - [ ] Do not introduce a broad algorithm rewrite in this pass.
- [ ] Add or update tests to ensure graph correctness remains unchanged.
- [ ] Optionally add a lightweight performance regression smoke test that avoids brittle timing.

Acceptance:

- BFS implementations avoid quadratic queue shifting without changing graph results.

## Phase 9: Optional Minor Clarity Fixes

Only include if touched code makes these low-risk:

- [ ] Add explicit angle validation in `Lattice.from_parameters()` for clearer invalid geometry errors.
- [ ] Improve `Molecule.from_ase()` error wording when converter returns a non-`Molecule`.

Acceptance:

- Minor clarity fixes do not expand scope or destabilize core behavior.

## Verification Plan

Run targeted tests during implementation:

- [ ] `conda run -n pmg python -m pytest tests/core/test_molecule_comprehensive.py tests/core/test_molecule_enhancements.py -q`
- [ ] `conda run -n pmg python -m pytest tests/core/test_crystal_comprehensive.py tests/core/test_crystal_helpers.py -q`
- [ ] `conda run -n pmg python -m pytest tests/core/test_lattice_comprehensive.py tests/core/test_lattice_convenient_constructors.py -q`
- [ ] `conda run -n pmg python -m pytest tests/core/test_site_comprehensive.py tests/core/test_hash_robustness.py -q`
- [ ] `conda run -n pmg python -m pytest tests/core/test_composition_comprehensive.py tests/core/test_composition_cache_and_errors.py -q`
- [ ] `conda run -n pmg python -m pytest tests/core/test_graph_oop.py tests/analysis/test_graph_enhancements.py tests/analysis/test_graph_oop.py -q`
- [ ] `conda run -n pmg python -m pytest tests/core -q`

Run broader checks before completion:

- [ ] `conda run -n pmg python -m compileall -q matsimpy/core`
- [ ] `conda run -n pmg python -m pytest tests/test_packaging_runtime_contracts.py -q`
- [ ] `conda run -n pmg python -m pytest -q`

Manual evidence to collect:

- [ ] Negative and non-finite cutoffs raise clear errors.
- [ ] One-atom periodic crystal has no self-neighbor under large cutoff.
- [ ] `CrystalGraph` adjacency diagonal is zero.
- [ ] Hash/equality boundary case no longer violates Python contract.
- [ ] Dummy-only mass APIs raise clear `ValueError`.
- [ ] Mixed dummy/real mass APIs behave deterministically.
- [ ] 27-element `anonymous_formula` raises clear `ValueError`.
- [ ] Ring-detection algorithm failure is surfaced.

## Implementation Checklist

- [ ] Record baseline core compile/test status.
- [ ] Implement shared cutoff validation.
- [ ] Apply cutoff validation to molecule, crystal, and graph APIs.
- [ ] Add cutoff validation tests.
- [ ] Filter periodic self-neighbor image entries.
- [ ] Clear `CrystalGraph` adjacency diagonal.
- [ ] Add periodic self-neighbor tests.
- [ ] Fix hash/equality contract by disabling hash or aligning equality/hash canonicalization.
- [ ] Add hash/equality boundary tests.
- [ ] Add graceful zero-mass checks for dummy-only compositions and molecules.
- [ ] Add mixed dummy/real mass behavior tests.
- [ ] Add explicit `anonymous_formula` >26 `ValueError`.
- [ ] Add 26/27 unique-species anonymous formula tests.
- [ ] Harden `find_rings()` exception handling.
- [ ] Add ring error-handling tests.
- [ ] Replace list-backed BFS queues with `deque`.
- [ ] Run targeted tests after each cluster.
- [ ] Run core test suite.
- [ ] Run compileall for `matsimpy/core`.
- [ ] Run full pytest.
- [ ] Update this plan with completion notes and final verification evidence.

## Risk Controls

- Do not change dummy species validation to reject placeholders globally.
- Do not implement anonymous labels beyond `Z`; use a clear error above 26 species.
- Do not silently ignore invalid cutoffs.
- Do not preserve hashability if it violates equality contracts.
- Do not hide graph algorithm errors behind empty results.
- Keep graph performance edits mechanical and behavior-preserving.
- Keep site-property and structure immutability behavior untouched unless tests require a direct contract fix.

## Stop Condition

Stop when all high and medium findings are fixed, the low-priority BFS cleanup is completed or explicitly deferred with rationale, targeted core tests pass, full pytest passes, and this plan is updated with completion notes plus validation evidence.
