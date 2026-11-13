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
  ai                             L5  optional LLM agent: tools, Skills, MCP (docs/ai.md)
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
- **AI tools are marked, not wrapped.** To expose a library function to the agent,
  decorate it with `@tool` from `matsimpy.utils.tooling` (no other import needed) and
  give it type hints and a docstring with an `Args:` section; the schema is derived from
  them. Do not write wrappers in `matsimpy.ai`.
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

### Writing tests

- **Put a test where its code lives.** `tests/<package>/` mirrors `matsimpy/<package>/`.
  Each module or subpackage has one file, `test_<module>.py`; for example,
  `matsimpy/transformation/lattice/` is tested in `tests/transformation/test_lattice.py`.
  Cross-cutting contracts go in `tests/contracts/`. Every test folder has an
  `__init__.py`, so the same file name can appear in two folders
  (`tests/core/test_lattice.py` and `tests/transformation/test_lattice.py`).
- **Never name a test file after a date, version, release, review or "regressions"**
  (no `test_core_review_2026_11.py`, `test_regressions_082.py`). A regression test goes
  into the topic file of the code it covers.
- **Read the existing tests first.** Before adding a test, read the tests for that
  function. Then do one of these:
  - extend or parametrize an existing test;
  - replace an existing test that is weaker;
  - add a new test only for behaviour nothing else checks.

  Delete tests the new one makes redundant. Two tests must not assert the same thing.
  Return-a-new-object checks belong in `tests/core/test_immutability.py` and are not
  repeated elsewhere.
- **One behaviour per test.** The name states the behaviour
  (`test_wrap_leaves_non_periodic_axes_alone`). Use `pytest.mark.parametrize` for input
  variants instead of copies of a test.
- **Use pytest, not unittest.** Write plain pytest functions with fixtures and
  `tmp_path`. Do not add `unittest.TestCase` classes, `tempfile` blocks or
  `if __name__ == "__main__"` guards. When you edit an old unittest file, convert it.
- **Assert values.** Check positions, species and numbers, not only types or lengths.
  A test must never pass by catching the error it should expose: no `try/except`
  around the code under test. A test must still exercise its path after the code
  changes. For example, a distance-matrix test needs data that uses the distance matrix.
- **Add an oracle only if it tells you something new.** Compare with pymatgen or ASE
  when they are an independent reference. Do not recompute MatSimPy's own formula
  with numpy and call that an oracle.
- **Read structures from fixtures.** Read crystals from the real files in
  `tests/calculator/fixtures` instead of hand-writing them, whenever the format allows.

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
- Every user-visible change goes into `CHANGELOG.md`; changes that can break existing
  code are listed there under "Breaking changes".
- Third-party code adapted into MatSimPy needs an entry in `THIRD_PARTY_NOTICES.md`.
  `tests/test_sdist_contents.py` checks that notices, the changelog and fixtures are
  in the sdist.
