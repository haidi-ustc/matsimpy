

  # MatSimPy Stability Implementation Plan

  ## Summary

  Stabilize the foundational MatSimPy modules: core, transformation, builders, io, and storage. Implement missing
  functions only when they are part of the current public contract, exported APIs, existing examples/tests, or
  required cross-module workflows.

  Current stage explicitly excludes UI feature work, visualization work, AI/ML feature work, calculator expansion,
  and roadmap-only menu implementation. CLI work is only included where an existing installed command or package
  entry point creates a stability problem.

  For builder implementation, use ASE and pymatgen as behavioral references where appropriate, but keep MatSimPy’s
  public API and core object model as the source of truth.

  Checklist status:
  - [x] Completed and validated.
  - [~] Accepted partial support or intentionally deferred for this stability stage.
  - [ ] Still pending.

  ## Key Implementation Changes

  ### 1. Baseline and Inventory

  - [x] Run targeted baseline in pmg:
      - conda run -n pmg python -m pytest tests/core tests/transformation tests/builders tests/io tests/storage -q
      - conda run -n pmg python -m compileall matsimpy

  - [x] Inventory failures and missing functions into:
      - contract defect
      - optional-dependency boundary defect
      - missing public function to implement
      - test expectation drift
      - accepted partial support to mark explicitly

  - [x] Implement missing functions when they are exported, documented, used by tests/examples, or required for core
    -> transform -> IO -> storage workflows.
    Completed examples: `fragment_molecule`, `generate_conformers`, `get_niggli_reduced`,
    `ParameterSweep(mode="custom")`, `create_simple_interface`, and structured adsorbate support.

  - [x] Defer missing functions that are UI-only, visualization-only, AI-only, or roadmap/menu-only.

  ### 2. Core Hardening

  - [x] Strengthen immutability tests for Structure, Crystal, Molecule, and Lattice.
  - [x] Verify mutable constructor inputs cannot mutate created objects later.
  - [x] Verify copy(), equality/hash behavior, cache behavior, and as_dict/from_dict round trips.
  - [~] Implement missing public core helpers required by exports, serialization, examples, or tests.
    No remaining core helper was found that needed implementation in this stability pass.
    `Structure.get_neighbor_list()` remains an explicit abstract base-class contract.
  - [x] Fix only contract-breaking behavior; avoid broad data model redesign.

  ### 3. Transformation Stability

  - [x] Build a transformation contract matrix: input type, output type, atom-count behavior, lattice behavior,
    supported errors.

  - [x] Ensure transformations return valid Crystal or Molecule objects and do not mutate inputs unless explicitly
    documented.

  - [x] Harden TransformationPipeline save/load behavior, including kwargs, invalid callables, bad modules, and
    unsupported persistence inputs.

  - [x] Make sequential and parallel batch behavior deterministic, including equivalent failure metadata.
  - [x] Implement missing transformation functions that are exported, documented, or referenced by current tests/
    examples.
    Completed examples: molecular fragmentation/conformers, Niggli reduction, and custom parameter sweeps.

  - [x] Add regression tests for BatchProcessor error modes: skip, raise, and log.

  ### 4. Builders Stability and Missing Functions

  - [x] Audit builder packages for import-time optional dependency failures.
  - [x] Ensure parent imports succeed without optional packages such as ASE, pymatgen, PyXtal, spglib, RDKit-like
    dependencies, or other extras.

  - [x] Use ASE and pymatgen as references for conventional behavior in bulk cells, slabs, surfaces, adsorbates,
    molecules, prototypes, and coordinate/lattice conventions.

  - [x] Implement MatSimPy builders so they return MatSimPy Crystal or Molecule objects, not ASE or pymatgen
    objects, unless an explicit converter API is being tested.

  - [x] Normalize optional dependency errors with clear install hints naming the required package or extra.
  - [x] Ensure builders either return valid core objects or fail with precise ValueError, ImportError, or
    NotImplementedError.

  - [x] Implement missing builder functions when they are exported, documented, referenced by tests/examples, or
    required by smoke workflows.
    Completed examples: `create_simple_interface` and structured `add_adsorbate` support.

  - [x] For functions modeled after ASE/pymatgen, add tests that verify structural invariants rather than exact
    implementation internals: species, atom count, lattice shape, dimensionality, coordinates, and immutability.

  - [x] Mark unsupported broad feature branches explicitly instead of silently leaving broken behavior.

  ### 5. IO Contract

  - [x] Strengthen read()/write() behavior for format detection, explicit format override, aliases, and unsupported
    extensions.

  - [x] Add or strengthen round-trip tests for JSON, VASP/POSCAR, CIF, XSF, XYZ, PDB, MOL, and ASE paths.
  - [x] Normalize wrong-format and crystal-vs-molecule error behavior.
  - [x] Ensure optional converter dependencies are lazy and fail with install hints at call time.
  - [x] Implement missing reader/writer/converter functions that are exported, in the IO registry, or referenced by
    tests/examples.
    No missing registry/exported reader or writer remains in this pass; converter caller-error ordering was hardened.

  ### 6. Storage Contract

  - [x] Ensure import matsimpy.storage succeeds without Maggma installed.
  - [x] Ensure Maggma-backed functionality raises a clear install hint only when invoked.
  - [x] Mock Maggma behavior for store, retrieve, delete, count, clear, close, and context-manager flows.
  - [x] Verify deterministic doc_id generation for serializable payloads.
  - [x] Verify metadata does not corrupt MSONable data.
  - [x] Implement missing storage methods only when part of the current DataStorage/MatSimPyStore contract.
    No missing storage method was required; added Maggma-free contract tests instead.

  ### 7. Packaging and Runtime Stability

  - [x] Fix matsimpy.config base-install behavior by either moving pyyaml to base dependencies or making YAML import
    lazy with a clear install hint.

  - [x] Fix the installed matsimpy console script so base installs do not crash when prompt-toolkit is absent.
  - [x] Update stale .workflow pipelines so they no longer reference missing requirements.txt or main.py.
  - [~] Treat the generated CLI menu as a stability boundary only: unresolved entries must not be presented as
    executable current functionality.
    Deferred by current stage direction: UI/menu work is not the focus. CLI was touched only for installed
    entry-point stability.

  ### 8. Cross-Module Smoke

  - [~] Add a compact integration smoke test:
      - build a valid structure
      - apply representative transformations
      - serialize/deserialize through JSON and one structure file format
      - store/retrieve through mocked storage
      - verify equality or near-equality, immutability, and metadata integrity
    Partially covered by focused builder, transformation, IO, and mocked storage tests. A single combined
    end-to-end smoke remains useful but was not required to unblock the current stability fixes.

  - [~] Include at least one formerly missing implemented function in the smoke path if baseline inventory finds
    one.

  - [~] Include one builder whose behavior is cross-checked against ASE or pymatgen conventions when the relevant
    optional dependency is available.

  ## Test Plan

  - [x] conda run -n pmg python -m pytest tests/core -q
  - [x] conda run -n pmg python -m pytest tests/transformation -q
  - [x] conda run -n pmg python -m pytest tests/builders -q
  - [x] conda run -n pmg python -m pytest tests/io -q
  - [x] conda run -n pmg python -m pytest tests/storage -q
  - [x] conda run -n pmg python -m compileall matsimpy
  - [x] conda run -n pmg python -m pytest -q
    Latest full gate: `1382 passed, 35 skipped, 3 warnings`.
  - [x] Base import smoke:
      - conda run -n pmg python -c "import matsimpy; import matsimpy.core; import matsimpy.transformation; import
        matsimpy.builders; import matsimpy.io; import matsimpy.storage"
    Import/export scan also passed for `core`, `transformation`, `builders`, `io`, and `storage`; no missing
    `__all__` symbols.

  ## Acceptance Checklist

  - [x] Targeted tests for core, transformation, builders, io, and storage pass.
  - [x] Full pytest remains green.
  - [x] compileall passes.
  - [x] No parent package has import-time optional dependency failures.
  - [x] Missing public functions in focused modules are implemented or explicitly marked unsupported.

  ## Assumptions

  - Use conda env pmg for validation.

  - Prefer small, contract-focused fixes over broad refactors.
  - Add no new dependencies unless required to fix a runtime dependency mismatch; otherwise keep ASE/pymatgen usage
    behind existing optional extras.


