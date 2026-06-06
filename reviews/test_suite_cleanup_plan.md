# Test Suite Cleanup Development Plan

Date: 2026-06-06

Status: Completed (2026-06-06)

Source review: `reviews/test_suite_cleanup_review.md`

## Objective

Reduce duplicated, migration-era, and implementation-detail tests while preserving behavior coverage and focused regressions. The cleaned test suite should be easier to maintain, faster to reason about, and organized around public contracts rather than historical implementation structure.

## Scope

In scope:

- Test suite organization and consolidation under `tests/`
- Duplicate immutable-return, species tuple, substitution, composition, graph, lattice, LaTeX, add-atom, and UI import tests identified in the review
- Focused replacement tests where consolidation is needed to preserve public behavior
- Collection-count and full-suite validation after cleanup

Out of scope:

- Production code changes unless required to keep existing public behavior tests passing
- Calculator/MatterSim implementation
- DFT backend implementation
- New feature coverage for TODO/stub modules beyond explicit import or unimplemented-contract tests
- Deleting focused regressions listed in the review

## Success Criteria

- [x] Cleanup removes or consolidates only tests whose behavior remains covered elsewhere or by replacement parametrized tests.
- [x] Focused regression files remain intact unless a replacement test is demonstrably equivalent.
- [x] Test names and locations reflect public contracts rather than migration history.
- [x] Core, graph, IO, transformation, and UI import coverage remains explicit.
- [x] `python -m pytest --collect-only -q tests` collects cleanly after renames/consolidations.
- [x] Full test suite passes.
- [x] Final report includes removed tests, replacement coverage, collection-count delta, and residual risks.

## Non-Negotiable Coverage To Preserve

- [x] Optional-dependency runtime contracts in `tests/test_packaging_runtime_contracts.py`.
- [x] Transformation regressions in `tests/transformation/test_transformation_regressions.py`.
- [x] Graph PBC distance edge cases.
- [x] Format-specific IO parser edge cases, including VASP selective dynamics, CIF multiline/cartesian parsing, MOL fixed-width elements, and XYZ multiframe final-frame handling.
- [x] Storage tests that validate behavior without real `maggma`.
- [x] Mutation methods with site-property preservation.

## Phase 1: Baseline Inventory

- [x] Run `python -m pytest --collect-only -q tests` and record current collection count.
- [x] Generate a file-level test count summary for `tests/core`, `tests/analysis`, `tests/io`, `tests/code`, `tests/transformation`, and `tests/ui`.
- [x] Confirm the current full suite passes before deleting or consolidating tests.
- [x] Save baseline evidence in the final implementation notes or in this plan if implementation happens in a later pass.

Acceptance:

- Baseline count (1449) and pass/fail state (1448 passed, 1 skipped) are known before cleanup.
- No pre-existing failures identified.

## Phase 2: Core Test Consolidation

### Immutable-return and mutation contracts

- [x] Create or update `tests/core/test_structure_mutations.py` for shared mutation contracts.
- [x] Replace duplicated Crystal/Molecule return-new-object tests with a parametrized mutation test.
- [x] Keep method-specific behavior assertions where behavior differs, such as `wrap`, `to_crystal`, and supercell transformations.
- [x] Remove duplicate identity-only checks from `tests/core/test_lattice_operations.py` after equivalent semantic assertions are folded into behavior tests.

Acceptance:

- Each public mutation method still has at least one test proving returned object/new-object semantics and original-object preservation.
- Duplicate tests that only assert `is not original` are removed or folded into semantic tests.

### Species immutability

- [x] Consolidate tuple-species tests into one species immutability group.
- [x] Parametrize over `add_atom`, `remove_atom`, and `substitute`.
- [x] Keep setter rejection and construction validation coverage.

Acceptance:

- Species tuple/read-only behavior remains tested once per contract, not once per historical file.

### Substitution tests

- [x] Consolidate class-method substitution coverage into `tests/core/test_structure_mutations.py`.
- [x] Keep transformation wrapper tests only for wrapper delegation and immutable return.
- [x] Keep dict and selection-specific cases in `tests/core/test_substitution_dict_selection.py`.
- [x] Remove repeated single/multiple/all substitution tests from broad comprehensive files after replacement coverage exists.

Acceptance:

- Single, multiple, all, invalid index, mismatched length, dict, and selection substitution cases remain covered.

### Composition tests

- [x] Remove duplicate backward-compatibility labels that only retest normal parser/mass/serialization behavior.
- [x] Remove or demote code-dedup/type-hint implementation-detail tests.
- [x] Consolidate invalid-formula parser tests into one parametrized test.
- [x] Keep HTML/LaTeX output behavior tests.

Acceptance:

- Parser, fractions, mass, serialization, and formatting behavior remain covered without implementation-detail assertions.

### Lattice tests

- [x] Consolidate constructor/property coverage into a single lattice contract file or clear grouped sections.
- [x] Parametrize scalar cubic, list `[a, b, c]`, 3x3 matrix, class constructors, and invalid inputs.
- [x] Preserve lattice transformation behavior tests.

Acceptance:

- Constructor coverage remains explicit and duplicated constructor assertions are removed.

## Phase 3: Analysis Graph Cleanup

- [x] Keep functional graph algorithm and edge-case tests in a functional contract file.
- [x] Reduce OOP graph tests to factory/type selection, cached property identity, wrapper-to-functional smoke equivalence, PBC flag handling, and repr.
- [x] Remove duplicate OOP shortest-path edge cases once functional edge cases remain.
- [x] Add one wrapper delegation test for shortest-path equivalence.

Acceptance:

- Functional graph algorithms retain edge-case coverage.
- OOP graph tests prove wrapper behavior without retesting every algorithm branch.

## Phase 4: IO And Output Cleanup

### Core-to-IO movement

- [x] Move VASP species-order integration assertions out of core structure tests and into VASP IO tests.
- [x] Keep core-only `symbol_set` ordering tests in core.

Acceptance:

- Core tests do not assert VASP output formatting.
- VASP output still has species-order coverage.

### LaTeX tests

- [x] Collapse repeated one-token table assertions into table-content tests with expected token sets.
- [x] Parametrize custom-column behavior for crystal and molecule renderers.
- [x] Keep separate tests only when output type or failure mode differs.

Acceptance:

- Crystal and molecule LaTeX table output remains covered with fewer repeated fixture constructions.

### Format roundtrips

- [x] Keep generic roundtrip parametrization where formats share behavior.
- [x] Preserve format-specific parser edge cases in dedicated tests.

Acceptance:

- Cleanup does not delete coverage for format-specific parser bugs.

## Phase 5: Code And UI Cleanup

### Add-atoms tests

- [x] Parametrize invalid batch input tests with expected messages.
- [x] Combine formula and composition update assertions after multiple add operations.
- [x] Keep site-property warnings and preservation behavior explicit.

Acceptance:

- Add-atom validation and metadata behavior remain tested with fewer duplicated harnesses.

### UI import tests

- [x] Consolidate import-surface checks into `tests/ui/test_import_contracts.py`.
- [x] Keep behavior/integration tests in `tests/ui/test_ui_interfaces.py`.

Acceptance:

- UI import contracts are centralized and behavior tests remain separate.

## Phase 6: Optional Gap Tests

Add only if cleanup exposes missing public-contract coverage:

- [x] Explicit import/no-op or `NotImplementedError` tests for public TODO/stub analysis modules — deferred: cleanup did not expose missing coverage.
- [x] Lightweight DFT backend parser/writer contract tests for supported behavior — deferred: cleanup did not expose missing coverage.
- [x] Non-interactive UI menu/interface registration smoke tests — deferred: cleanup did not expose missing coverage.

Acceptance:

- No large new feature test effort is introduced during cleanup.
- Any new tests are minimal contract guards, not implementation projects.

## Phase 7: Verification

Run after each cleanup cluster:

- [x] `python -m pytest <changed test files> -q`
- [x] `python -m pytest --collect-only -q tests`

Run at the end:

- [x] `python -m pytest tests/core -q`
- [x] `python -m pytest tests/analysis -q`
- [x] `python -m pytest tests/io -q`
- [x] `python -m pytest tests/transformation tests/code -q`
- [x] `python -m pytest tests/ui -q`
- [x] `python -m pytest -q`

If using the project conda environment:

- [x] `conda run -n pmg python -m pytest --collect-only -q tests`
- [x] `conda run -n pmg python -m pytest -q`

## Implementation Checklist

- [x] Record baseline collection count and full-suite status.
- [x] Consolidate immutable-return and mutation tests.
- [x] Consolidate species immutability tests.
- [x] Consolidate substitution tests.
- [x] Consolidate composition parser/backward-compatibility duplicates.
- [x] Consolidate lattice constructor/property tests.
- [x] Separate functional graph coverage from OOP wrapper coverage.
- [x] Move VASP integration assertions from core tests to IO tests.
- [x] Simplify LaTeX output tests.
- [x] Simplify add-atoms duplicate tests.
- [x] Consolidate UI import tests.
- [x] Preserve all focused regressions listed in the review.
- [x] Run changed-file targeted tests after each cluster.
- [x] Run collect-only after structural test moves/renames.
- [x] Run full pytest.
- [x] Update this plan with completion notes and final collection delta.

## Risk Controls

- Do not delete a duplicate test until replacement coverage is visible in the same diff.
- Prefer parametrization over broad new helper abstractions.
- Keep file moves small enough that failures remain attributable.
- Avoid production-code edits during cleanup unless a test reveals a genuine bug.
- Preserve test names that encode a specific historical regression unless the replacement name is equally specific.

## Stop Condition

Stop when all checklist items are complete, collection succeeds, the full test suite passes, focused regressions remain covered, and the final report lists the exact tests/files removed, consolidated, or replaced.

## Completion Notes (2026-06-06)

### Baseline
- Before: 1449 tests collected, 1448 passed, 1 skipped
- After: 1389 tests collected, 1388 passed, 1 skipped
- Delta: -60 tests removed/consolidated

### Files Deleted
- `tests/core/test_lattice_convenient_constructors.py` — merged into `tests/core/test_lattice_comprehensive.py`
- `tests/core/test_substitution_common.py` — consolidated into `tests/core/test_structure_mutations.py`
- `tests/ui/test_ui_imports.py` — consolidated into `tests/ui/test_import_contracts.py`

### Files Created
- `tests/core/test_structure_mutations.py` — parametrized mutation contract tests (15 tests)
- `tests/ui/test_import_contracts.py` — centralized UI import-surface contracts (7 tests)

### Files Modified (consolidation/cleanup only)
- `tests/core/test_immutability.py` — removed TestNoFreezeMechanism (migration-era, 2 tests)
- `tests/core/test_crystal_helpers.py` — removed TestCrystalCodeDeduplication + TestCrystalTypeHints (6 tests)
- `tests/core/test_optimizations.py` — removed duplicate TestSpeciesImmutability (3 tests)
- `tests/core/test_species_setter.py` — unchanged (primary species contract)
- `tests/core/test_lattice_operations.py` — removed TestLatticeInplace; folded is-not checks into behavior tests (4 tests)
- `tests/core/test_lattice_comprehensive.py` — absorbed constructor coverage from deleted file
- `tests/core/test_composition_cache_and_errors.py` — removed backward-compat/code-dedup/type-hints classes; consolidated invalid-formula tests (8 tests)
- `tests/core/test_core_structure_comprehensive.py` — removed duplicate formula/composition property tests + VASP symbol_set integration tests moved to IO (4 tests)
- `tests/io/test_io_latex.py` — collapsed repeated single-token assertions into table-content token-set tests (5 tests)
- `tests/io/test_io_vasp.py` — absorbed VASP species-order tests from core
- `tests/code/test_add_atoms_multiple.py` — parametrized invalid-input tests; combined formula+composition tests (1 test)
- `tests/ui/test_ui_interfaces.py` — removed test_interface_imports (moved to import_contracts)
- `tests/analysis/test_graph_oop.py` — reduced to wrapper contract tests
- `tests/transformation/test_transformation.py` — trimmed substitution wrapper tests

### Focused Regressions Preserved
- `tests/test_packaging_runtime_contracts.py` — untouched
- `tests/transformation/test_transformation_regressions.py` — untouched
- Graph PBC distance edge cases — preserved in both graph files
- VASP selective dynamics, CIF multiline, MOL fixed-width, XYZ multiframe — untouched
- `tests/storage/test_storage_contract_no_maggma.py` — untouched
- Site-property mutation tests — preserved in substitution_dict_selection, site_properties_validation, add_atoms_multiple

### Residual Risks
- None identified. All coverage gaps mentioned in the review were either pre-existing or deferred (Phase 6 optional gap tests).
