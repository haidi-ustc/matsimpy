# Task 4 — Native band structures

## RED evidence

- `pytest tests/electronic_structure/test_bandstructure.py -v` failed during collection with `ImportError: cannot import name 'BandStructure'` before implementation.
- After the initial implementation, focused tests exposed the branch-boundary edge case (`X-X` instead of `X-M`).
- A parser integration regression test, `test_vasprun_returns_native_band_structure`, failed with `AttributeError` because the VASP adapter still used pymatgen's `reciprocal_lattice` property rather than native `get_reciprocal_lattice()`.

## GREEN evidence

- Native containers cover validated band/projection shapes, spin normalization, metallic Fermi crossing, VBM/CBM/gap, Kpoint conversion and serialization, line labels/branches, Monty reconstruction, and multi-branch band/projection reconstruction.
- VASP outputs now import native band types unconditionally and return them without a pymatgen electronic-structure dependency.
- `pytest tests/electronic_structure/test_bandstructure.py tests/calculator/test_vasp_outputs.py -v`: 17 passed.
- `pytest tests/calculator/test_vasp_outputs_parity.py -k band -m requires_pymatgen -v`: 1 passed, 1 deselected.
- `pytest tests/electronic_structure tests/calculator/test_vasp_outputs_parity.py -q`: 21 passed.

## Review notes

- Line branches split at repeated labeled coordinates; distinct adjacent labeled endpoints remain one valid two-point branch.
- Reconstruction preserves labels, all spin channels, projections, structure reference, and optional Fermi override.
- `ruff` was unavailable in the environment; `compileall` and `git diff --check` were used alongside tests.

## Review-fix RED evidence

- Four dependency-free regressions failed before the fix: empty symmetry-line k-points raised `IndexError`, zero bands were accepted, consecutive distinct labels were not split, and Cartesian k-points lost fractional-coordinate labels.
- The new real `Vasprun.get_band_structure()` parity initially exposed a test-side spin-enum mismatch; using each implementation's own `Spin` enum made the comparison genuine.

## Review-fix GREEN evidence

- Branches now split whenever the current and previous k-points are labeled, matching pinned pymatgen 2025.6.14 indices and names even when adjacent coordinates differ.
- Empty k-point and zero-band inputs raise explicit `ValueError`s. Cartesian inputs are converted to fractional coordinates before label matching.
- The existing `tests/calculator/fixtures/vasp/vasprun.xml` genuinely exercises both parsers' `get_band_structure()` integration. It produces ordinary 24-k-point band structures with no labels, projections, or branches; the parity test compares their class selection, Fermi energy, reciprocal lattice, k-points/labels, all spin bands, empty projections/branches, and the complete gap dictionary. The synthetic pinned-oracle parity test separately covers symmetry-line labels and branch endpoints/names.
- `pytest tests/electronic_structure/test_bandstructure.py tests/calculator/test_vasp_outputs.py -v`: 21 passed.
- `pytest tests/calculator/test_vasp_outputs_parity.py -k band -m requires_pymatgen -v`: 2 passed, 1 deselected.
- `pytest tests/architecture/test_vasp_no_pymatgen.py -v`: 1 passed, 1 expected failure.
