# Core / Transformation / Builders / IO / Storage Stability Plan

## Requirements Summary

Current development focus is stability for the foundational MatSimPy modules: `core`, `transformation`, `builders`, `io`, and `storage`. The goal is to find and fix contract-breaking issues, including missing public functions in these focused modules, without broad feature expansion, UI work, visualization work, AI/ML work, or speculative refactors.

Evidence anchors:
- Core structures intentionally expose immutable/read-only backing arrays and compute-once caches: `matsimpy/core/structure.py:127-152`, `matsimpy/core/structure.py:212-223`, plus similar read-only guards in `matsimpy/core/crystal.py:204-214` and `matsimpy/core/lattice.py:162-165`.
- Transformations rely on validated `Crystal`/`Molecule` inputs via `_validate_structure`: `matsimpy/transformation/base.py:9-20`.
- Transformation batch and pipeline code currently swallows parallel failures and falls back to sequential work: `matsimpy/transformation/composite/pipeline.py:185-206`; batch processing records exceptions into `BatchResult`: `matsimpy/transformation/composite/batch.py:134-184`.
- Pipeline persistence serializes function module/name and kwargs, then imports them dynamically on load: `matsimpy/transformation/composite/pipeline.py:216-305`.
- Builders contain optional-dependency and partial-support paths that must be explicit and tested, e.g. PyXtal in `matsimpy/builders/bulk/random.py:35-63`, spglib fallback in `matsimpy/builders/bulk/symmetry.py:12-18` and `matsimpy/builders/bulk/symmetry.py:80-95`, and known partial builders from grep (`prototype.py`, `surface/adsorbate.py`, `molecule/geometry.py`).
- IO centralizes format detection in `matsimpy/io/utils.py:9-23` and high-level dispatch in `matsimpy/io/core.py:53-130` and `matsimpy/io/core.py:176-220`.
- Storage is an optional Maggma-backed module with lazy import behavior in `matsimpy/storage/__init__.py:1-34` and broad exception/logging paths in `matsimpy/storage/maggma_store.py:163-300`.
- Existing tests already cover the target areas under `tests/core`, `tests/transformation`, `tests/builders`, `tests/io`, and `tests/storage`; the plan should harden gaps rather than replace coverage.

## Acceptance Criteria

1. Targeted tests for `tests/core`, `tests/transformation`, `tests/builders`, `tests/io`, and `tests/storage` pass independently and in the full suite.
2. Public core objects remain immutable from external callers: species/positions/lattice inputs cannot mutate existing structures after construction or after transformations.
3. Every transformation returns a valid `Crystal` or `Molecule`, preserves expected atom counts/lattice semantics, and never mutates its input unless a documented API explicitly promises in-place behavior.
4. Transformation batch/pipeline error behavior is deterministic: sequential vs parallel mode produces equivalent successful outputs and equivalent failure metadata, without silent data loss.
5. Pipeline `save`/`load` round-trips all supported kwargs and rejects unsupported callables/kwargs with clear errors.
6. Builders either produce valid core structures or fail with precise `ValueError`/`ImportError`/`NotImplementedError` messages; optional dependency absence must not break importing the parent builder package.
7. IO format detection, explicit format overrides, read/write round-trips, and wrong-format errors are consistent across VASP/POSCAR, CIF, XSF, JSON, XYZ, PDB, MOL, and ASE-supported paths.
8. Storage can be imported without Maggma installed and raises a clear install hint only when Maggma-backed functionality is invoked.
9. No new dependencies are added unless they fix a runtime contract mismatch and are documented in `pyproject.toml` extras/base dependencies.
10. `python -m compileall matsimpy` passes after changes.
11. Missing functions that are part of the current public module contract, referenced by existing examples/tests, exported from package `__init__` files, or needed to complete documented builder/transformation/IO/storage workflows are implemented and covered by tests.

## Non-Goals

- No new visualization, UI menu, AI/ML, calculator, or docs-heavy feature work.
- No broad redesign of the data model.
- No migration away from existing optional dependencies unless a concrete stability defect requires it.
- No new storage backend unless needed as a minimal test double; prefer mocking existing Maggma interfaces.
- No implementation of speculative missing functions from UI, AI, visualization, or roadmap-only menus unless they are required to stabilize one of the focused modules.

## Work Plan

## Execution Checklist

Status markers:
- `[x]` implemented and covered by targeted regression tests.
- `[~]` intentionally deferred or accepted partial support for this stabilization phase.
- `[ ]` still pending in the current working tree or final verification pass.

### Completed and Verified

- [x] Baseline targeted module tests and `compileall` were run in the `pmg` conda environment.
- [x] Base install runtime dependency mismatch fixed by moving `pyyaml` into base dependencies so `matsimpy.config` can import in a normal install.
- [x] Installed CLI entry point now degrades cleanly when `prompt-toolkit` is absent and reports the `MatSimPy[cli]` install hint at invocation time.
- [x] Legacy `.workflow` pipelines no longer reference missing `requirements.txt` or `main.py`; they now use editable install and pytest gates.
- [x] `fragment_molecule()` implemented for covalent-fragment splitting and covered by regression tests.
- [x] `generate_conformers()` implemented through the existing RDKit optional dependency boundary and covered by regression tests.
- [x] `get_niggli_reduced()` implemented through `spglib.niggli_reduce()` and covered by regression tests.
- [x] `ParameterSweep(mode="custom")` implemented with explicit `custom_combinations` and covered by regression tests.
- [x] `create_simple_interface()` implemented for a conservative two-slab builder path and covered by regression tests.
- [x] Structured adsorbate support added for `Crystal`/`Molecule` adsorbates and covered by regression tests.
- [x] Builder package export updated so `create_simple_interface` is available from `matsimpy.builders`.
- [x] Storage optional dependency boundary tightened so missing Maggma is quiet on import and actionable when `DataStorage` is constructed.
- [x] Interface builder module documentation now matches the implemented conservative z-stacking contract instead of advertising a placeholder.
- [x] IO converter input validation now rejects unsupported MatSimPy input types before optional ASE/pymatgen imports, so caller errors are deterministic even in base installs.
- [x] Storage public contract now has Maggma-free mocked tests for deterministic IDs, retrieve/delete/count/clear, and JSON close flushing.

### Accepted Deferred Scope

- [~] `Structure.get_neighbor_list()` remains abstract/unsupported at the base class level; concrete neighbor behavior belongs in typed structure implementations or explicit downstream helpers.
- [~] `Crystal.from_code()` and `Molecule.from_code()` DFT/code-output parsing remains outside this stability pass because it is a broad IO/parser feature, not a current contract blocker.
- [~] Non-triatomic `build_bent()` support remains explicit partial support unless a current example or test requires broader molecular geometry generation.
- [~] Internal unknown prototype lattice-type guards remain accepted partial support; broad prototype expansion is not part of the current stabilization stage.
- [~] Broad interface matching, strain minimization, coincidence-site lattice search, UI, visualization, and AI/ML features remain out of scope for this phase.

### Final Validation

- [x] Targeted packaging/builder/storage follow-up tests passed: `6 passed`.
- [x] `conda run -n pmg python -m compileall matsimpy` passed.
- [x] `conda run -n pmg python -m pytest -q` passed: `1380 passed, 35 skipped, 3 warnings`.
- [x] Commit the checklist and follow-up stability fixes with Lore trailers.
- [x] Targeted converter/interface follow-up tests passed: `19 passed`.
- [x] `conda run -n pmg python -m compileall matsimpy/io matsimpy/builders/interface` passed.
- [x] Targeted Maggma-free plus existing storage tests passed: `19 passed`.
- [x] `conda run -n pmg python -m compileall matsimpy/storage` passed.

### Phase 0 — Baseline and Failure Inventory

Run the smallest useful checks first, then expand only where failures point:

```bash
conda run -n pmg python -m pytest tests/core tests/transformation tests/builders tests/io tests/storage -q
conda run -n pmg python -m compileall matsimpy
```

Capture failures by module and classify each as:
- contract defect,
- optional dependency boundary defect,
- missing public function,
- test expectation drift,
- known partial feature that should be explicitly marked.

For missing functions, classify them into two buckets:
- Implement now: public/exported functions in the focused modules, functions referenced by existing tests/examples, or functions required for core cross-module workflows.
- Mark unsupported/defer: roadmap-only, UI-only, visualization-only, AI-only, or broad new capability requests unrelated to current stability.

### Phase 1 — Core Contract Hardening

Focus files:
- `matsimpy/core/structure.py`
- `matsimpy/core/crystal.py`
- `matsimpy/core/molecule.py`
- `matsimpy/core/lattice.py`
- `tests/core/*`

Actions:
1. Add/strengthen regression tests for construction from mutable input arrays/lists, external position/lattice mutation attempts, `copy()`, `as_dict`/`from_dict`, equality/hash stability, and cache correctness after derived operations.
2. Verify all mutation-like helpers construct fresh objects through the intended internal constructors and do not leak writable array views.
3. Implement any missing public helpers required by current core tests, exports, serialization contracts, or documented examples.
4. Fix only defects that violate public behavior; avoid large rewrites of `Structure`, `Crystal`, or `Molecule`.

Done when core tests prove immutability, serialization, equality/hash, and common constructor paths.

### Phase 2 — Transformation Correctness and Determinism

Focus files:
- `matsimpy/transformation/base.py`
- `matsimpy/transformation/atomic/*`
- `matsimpy/transformation/chemical/substitution.py`
- `matsimpy/transformation/geometric/*`
- `matsimpy/transformation/lattice/*`
- `matsimpy/transformation/structural/*`
- `matsimpy/transformation/composite/pipeline.py`
- `matsimpy/transformation/composite/batch.py`
- `tests/transformation/*`

Actions:
1. Build a transformation contract matrix: input type, expected output type, atom-count changes, lattice changes, valid error cases, and whether unsupported paths intentionally raise `NotImplementedError`.
2. Add regression tests for sequential and parallel `TransformationPipeline.apply_batch` equivalence; if parallel fallback is retained, assert the warning and result semantics explicitly.
3. Add `BatchProcessor` tests for `skip`, `raise`, and `log` handling so broad `except Exception` paths cannot hide failures unexpectedly.
4. Strengthen pipeline persistence tests for numpy arrays, tuples, nested kwargs, bad function modules, unsupported non-JSON kwargs, and callable loading errors.
5. Implement missing transformation functions that are exported, documented, or referenced by current tests/examples, using existing validation and immutable-return patterns.
6. Fix transformation functions that mutate inputs, return invalid structure types, or produce inconsistent metadata/errors.

Done when transformations are reproducible, input-safe, and deterministic across batch modes.

### Phase 3 — Builder Boundary and Output Validity

Focus files:
- `matsimpy/builders/bulk/*`
- `matsimpy/builders/alloy/*`
- `matsimpy/builders/defects/*`
- `matsimpy/builders/molecule/*`
- `matsimpy/builders/nanostructure/*`
- `matsimpy/builders/surface/*`
- `tests/builders/*`

Actions:
1. Audit each builder for optional top-level imports, invalid parameter handling, and partial-support `NotImplementedError` paths.
2. Add tests that parent package imports succeed when optional packages such as PyXtal/spglib/RDKit-like dependencies are unavailable.
3. For each builder family, assert generated structures are valid core objects with expected species, positions shape, lattice presence/absence, and no writable internal arrays.
4. Normalize error messages for unsupported parameters and optional extras: install hints should name the extra/package and the specific feature.
5. Implement missing builder functions when they are exported, documented, referenced by current examples/tests, or needed by cross-module smoke workflows.
6. Avoid implementing broad missing feature branches unless a current documented example depends on them; otherwise mark unsupported paths clearly.

Done when builders either generate valid structures or fail cleanly without import-time surprise.

### Phase 4 — IO Round-Trip and Format Contract

Focus files:
- `matsimpy/io/utils.py`
- `matsimpy/io/core.py`
- `matsimpy/io/json.py`
- `matsimpy/io/vasp.py`, `cif.py`, `xsf.py`, `xyz.py`, `pdb.py`, `mol.py`, `ase.py`, `converters.py`
- `tests/io/*`

Actions:
1. Add/strengthen round-trip tests using temporary files for representative `Crystal` and `Molecule` objects.
2. Verify `detect_format`, alias handling, explicit `format=...`, and unsupported extension errors across all registry entries.
3. Test crystal-vs-molecule incompatibility paths in high-level `write()` and ambiguous read options where relevant.
4. Normalize exception type/message where readers/writers disagree on the same public error.
5. Ensure optional converter dependencies are lazy and emit install hints at call time, not import time.
6. Implement missing reader/writer/converter functions that are present in the IO registry, exported from `matsimpy.io`, or referenced by existing format tests.

Done when high-level `read()`/`write()` behavior matches the registry and format-specific tests round-trip reliably.

### Phase 5 — Storage Optional Dependency and Data Contract

Focus files:
- `matsimpy/storage/__init__.py`
- `matsimpy/storage/maggma_store.py`
- `tests/storage/test_storage.py`

Actions:
1. Add tests that `import matsimpy.storage` succeeds without Maggma and that accessing `MatSimPyStore` raises a clear install hint.
2. Mock Maggma stores for `store_data`, `retrieve_data`, `delete_data`, `count_documents`, `clear_store`, and context-manager close behavior.
3. Verify `doc_id` generation is deterministic for serializable payloads and metadata does not corrupt MSONable data.
4. Check errors are not swallowed: storage methods may log, but must re-raise or return the documented sentinel consistently.
5. Ensure destructive methods (`delete_data`, `clear_store`) are tested with explicit criteria and never run against real external services in unit tests.
6. Implement missing storage methods only when they are part of the current `DataStorage`/`MatSimPyStore` public contract or required by tests; otherwise leave unsupported operations explicit.

Done when storage is safe to import, deterministic under mocks, and clearly separated from real Maggma/external side effects.

### Phase 6 — Cross-Module Integration Smoke Tests

Add a small integration test set that exercises the user workflow across the focused modules:

1. Build a crystal with `builders`.
2. Apply representative transformations.
3. Serialize and deserialize through JSON and at least one crystal format.
4. Store/retrieve through a mocked storage backend.
5. Assert final structure equality/near-equality, immutability, and metadata integrity.
6. Include at least one implemented formerly-missing function in the smoke path when the baseline inventory finds such a gap.

Keep this suite small so it can run in normal CI without optional external services.

## Priority Order

1. Core immutability/serialization regressions.
2. Transformation input-safety and batch/pipeline determinism.
3. Missing public functions in focused modules that block tests, examples, exports, or cross-module workflows.
4. IO registry/read-write contract.
5. Builder optional-dependency/import boundaries and output validity.
6. Storage optional-dependency and mocked data-contract behavior.
7. Cross-module smoke tests.

## Risks and Mitigations

- Risk: Optional dependencies are installed in the developer environment, hiding import-boundary bugs. Mitigation: use monkeypatch/import-block tests and clean subprocess import checks.
- Risk: Parallel transformation tests are flaky under multiprocessing spawn. Mitigation: keep data small, avoid lambdas for pickled workers, and assert fallback warning behavior separately.
- Risk: IO round-trips have unavoidable formatting tolerances. Mitigation: compare species, atom counts, lattice matrices, and positions with explicit numerical tolerances instead of raw file text.
- Risk: Builder partial features may tempt broad implementation. Mitigation: only fix current documented examples and public contracts; otherwise test and label unsupported paths.
- Risk: Storage tests might touch real services. Mitigation: mock Maggma interfaces and require no external network/service credentials.

## Verification Steps

Targeted gates:

```bash
conda run -n pmg python -m pytest tests/core -q
conda run -n pmg python -m pytest tests/transformation -q
conda run -n pmg python -m pytest tests/builders -q
conda run -n pmg python -m pytest tests/io -q
conda run -n pmg python -m pytest tests/storage -q
conda run -n pmg python -m compileall matsimpy
```

Full gate:

```bash
conda run -n pmg python -m pytest -q
```

Optional base-import smoke after dependency-boundary fixes:

```bash
conda run -n pmg python -c "import matsimpy; import matsimpy.core; import matsimpy.transformation; import matsimpy.builders; import matsimpy.io; import matsimpy.storage"
```

## Stop Condition

Stop this stabilization phase when the targeted module tests and compileall pass, full pytest remains green, all newly discovered high/medium contract defects in these five modules are fixed or documented as accepted partial support, and no import-time optional-dependency failures remain for parent packages.
