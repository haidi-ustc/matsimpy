# Task 7 Report: Native VASP Input Sets Cutover

## Files Changed
- `matsimpy/calculator/vasp/sets.py`
  - Replaced production pymatgen imports/fallbacks with native `InputGenerator`, `SymmetryAnalyzer`, `HighSymmetryKpath`, `StructureMatcher`, `Crystal`, and `CrystalSite`.
  - Made VASP input sets accept native `Crystal` structures only.
  - Switched irreducible reciprocal mesh and k-path generation to native symmetry APIs.
  - Removed runtime citation decorators and the `VaspInputGenerator` compatibility alias.
  - Replaced NMR quadrupole lookup in `MPNMRSet` with native `Element.get_nmr_quadrupole_moment()`.
  - Made unsupported native paths fail clearly for `reduce_structure` and NEB CIF export.
- `matsimpy/calculator/vasp/inputs.py`
  - Replaced `lattice.reciprocal_lattice.volume` with `lattice.get_reciprocal_lattice().volume`.
  - Replaced pymatgen-shaped face-centering detection with native `SymmetryAnalyzer`.
  - Updated KPOINTS annotations to native `Crystal` and `HighSymmetryKpath`.
- `matsimpy/core/periodic_table.py`
  - Added `Element.get_nmr_quadrupole_moment(isotope=None) -> float` backed by existing `"NMR Quadrupole Moment"` JSON values.
- `tests/calculator/test_vasp_sets.py`
  - Removed the permissive DictSet skip.
  - Added native DictSet input generation, native IR mesh, source import-contract, and quadrupole lookup tests.
- `tests/core/test_periodic_table_comprehensive.py`
  - Added explicit/default/missing NMR quadrupole moment coverage.

## Behavior
- Production VASP `sets.py` and `inputs.py` do not import pymatgen.
- Basic `DictSet` construction now produces native `Incar`/`Poscar` output from `Crystal`.
- Explicit reciprocal-density KPOINTS generation uses native reciprocal lattice and native symmetry irreducible mesh.
- `MPNMRSet(mode="efg")` reads quadrupole moments from native periodic-table data.
- Unsupported native behavior now raises focused errors instead of guarded pymatgen fallbacks:
  - `reduce_structure`
  - NEB CIF/path CIF export

## Commands and Results
- Red test run:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_inputs.py -q`
  - Result: failed as expected on remaining pymatgen imports, missing quadrupole API, reciprocal-lattice access, and empty KPOINTS config.
- Targeted green run:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_inputs.py -q`
  - Result: `29 passed, 4 warnings`
- Task 7 verification:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_imports.py tests/core/test_periodic_table_comprehensive.py -q`
  - Result: `81 passed, 5 warnings`
- Syntax check:
  - `conda run -n pmg python -m py_compile matsimpy/calculator/vasp/sets.py matsimpy/calculator/vasp/inputs.py matsimpy/core/periodic_table.py`
  - Result: exit 0
- Diff hygiene:
  - `git diff --check`
  - Result: exit 0
- Import contract:
  - AST scan of `matsimpy/calculator/vasp/sets.py` and `matsimpy/calculator/vasp/inputs.py`
  - Result: both returned `[]` for pymatgen imports.

## Commit
- `951ce882bafb61f48201d3b2506841a0464681b7`
- Intent: `Generate VASP inputs through MatSimPy symmetry and core models`

## Risks / Notes
- Full repository test suite was not run.
- Native high-symmetry k-path support remains intentionally limited by the existing native `HighSymmetryKpath` implementation.
- Native NEB CIF export is explicitly unsupported and raises `NotImplementedError`.
- Existing deprecation warnings for `DictSet` and `Kpoints.automatic()` remain.

## Fix Round 1

### Files Changed
- `matsimpy/core/lattice.py`
  - Added native `Lattice.is_hexagonal()` metric/angle classification.
- `matsimpy/calculator/vasp/inputs.py`
  - Replaced accidental truthy `lattice.hexagonal` constructor checks with `lattice.is_hexagonal()`.
  - Removed broad exception suppression from `_has_face_centered_lattice()` so native symmetry failures propagate.
- `tests/calculator/test_vasp_inputs.py`
  - Added regressions proving tetragonal all-even meshes select Monkhorst-Pack in both `automatic_density()` and `automatic_density_by_lengths()`.
  - Added a regression proving symmetry-analysis failures propagate from automatic-density generation.

### Commands and Results
- Red run:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_inputs.py -q`
  - Result: failed as expected because tetragonal all-even meshes selected Gamma and symmetry failures were swallowed.
- Focused green run:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_inputs.py -q`
  - Result: `27 passed, 2 warnings`
- Task 7 verification:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_imports.py tests/core/test_periodic_table_comprehensive.py -q`
  - Result: `84 passed, 5 warnings`
- Lattice/VASP focused verification:
  - `conda run -n pmg python -m pytest tests/core/test_lattice_comprehensive.py tests/calculator/test_vasp_inputs.py -q`
  - Result: `64 passed, 2 warnings`
- Syntax check:
  - `conda run -n pmg python -m py_compile matsimpy/calculator/vasp/inputs.py matsimpy/core/lattice.py`
  - Result: exit 0
- Diff hygiene:
  - `git diff --check`
  - Result: exit 0
- Search:
  - `rg -n "\.hexagonal|is_hexagonal|_has_face_centered_lattice|except Exception" matsimpy/calculator/vasp/inputs.py matsimpy/calculator/vasp/sets.py matsimpy/core/lattice.py tests/calculator/test_vasp_inputs.py`
  - Result: no remaining `lattice.hexagonal` boolean checks in Task 7 production code.
