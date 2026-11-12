# CLAUDE.md

Guidance for coding agents and contributors working on MatSimPy.

## Layout

```
matsimpy/
  utils, constants, exceptions   L0  helpers, no matsimpy imports
  core                           L1  Crystal, Molecule, Lattice, Composition, Site, Element
  analysis, symmetry, io,        L2  analysis, spglib symmetry / k-paths / prototypes,
  electronic_structure, config       file formats, DOS and bands, configuration
  transformation, builders,      L3  pure functions on structures, structure builders,
  storage                            DataStorage
  calculator                     L4  LennardJones, VASP, Gaussian, LAMMPS, MatterSim
  ai                             L5  optional LLM agent and skills
tests/                           mirrors the package; tests/calculator/fixtures holds real data
```

## Design rules

- **Layering.** A package imports only from lower layers, including imports inside
  functions. `tests/architecture/test_layering.py` enforces this; for example,
  `symmetry` cannot import `io` or `transformation`. Same-layer exceptions are listed
  in `SAME_LAYER_OK` there.
- **Immutability.** Structures, sites, lattices, `Magmom`, `PrototypeInfo` and
  `PrototypeDatabase` are immutable. Arrays are read-only. Every "mutation" (`add_atom`,
  `substitute`, transformations) returns a new object. Do not add setters or in-place
  methods.
- **Stateless calculators.** A calculator takes the structure on every call and returns
  immutable results. It keeps no "last structure" and no mutable results.
- **AI only in `matsimpy.ai`.** Lower layers never call an LLM.
- **Functions, not methods, across layers.** I/O, symmetry and transformations are module
  functions (`matsimpy.io.read(path)`, `matsimpy.symmetry.get_symmetry_info(crystal)`),
  not methods on core classes.
- **Fail loudly.** Raise a specific error instead of returning `{}`, `None` or placeholder
  data.

## Tests

```bash
python -m pytest -q -p no:xdist          # full suite, about 90 s
python -m pytest -q -p no:xdist tests/symmetry
```

- Use one worker (`-p no:xdist`); the parallel run needs more memory than small machines have.
- pymatgen and ASE are optional reference oracles. Tests that use them call
  `pytest.importorskip`, so they are skipped when the package is missing.
- A bug fix comes with a test that fails on the old code.
- README Python blocks are run by `tests/test_readme_examples.py`; mark a block that
  needs files with ` ```python notest `.

## Test data

- **VASP test data comes only from the pymatgen 2026.10.24 test files**, copied
  unmodified. Never write VASP files by hand or generate them in a test. Record every
  new file in `tests/calculator/fixtures/vasp/PROVENANCE.md`.
- **Never use real POTCARs.** They are copyrighted. Use pymatgen's placeholder
  `fake_potcars` only.
- MatSimPy reads only VASP 5 POSCARs in `matsimpy.io` (VASP 4 raises `ValueError`).

## Releases and documentation

- The version is set in `pyproject.toml` only. `matsimpy.__version__` reads it and the
  README `**Version**` line must match it (`tests/test_packaging_runtime_contracts.py`).
- Every user-visible change goes into `CHANGELOG.md`. Changes that can break existing
  code also go into the current `MIGRATION_*.md`.
- Third-party code adapted into MatSimPy needs an entry in `THIRD_PARTY_NOTICES.md`.
  `tests/test_sdist_contents.py` checks that notices, migration notes and fixtures are
  in the sdist.
