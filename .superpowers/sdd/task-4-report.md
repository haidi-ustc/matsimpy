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
