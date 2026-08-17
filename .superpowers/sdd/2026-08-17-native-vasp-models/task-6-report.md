# Task 6 Report: VASP Native Outputs Cutover

## Files Changed

- `matsimpy/calculator/vasp/outputs.py`
  - Replaced guarded pymatgen advanced-output imports with native MatSimPy imports.
  - Removed `_HAS_PYMATGEN_ES`, dummy fallback symbols/classes, and `ParseError` dependency.
  - Made `VaspParseError` inherit from `matsimpy.exceptions.FormatError`.
  - Kept `Vasprun.get_computed_entry()`, `get_trajectory()`, `complete_dos`, `complete_dos_normalized`, and `get_band_structure()` on native return classes.
  - Made complete DOS projected data use site indexes as keys because native `CrystalSite` objects are unhashable.
  - Passed `None` for absent band projections so native `BandStructure` constructors do not receive empty projection maps.
  - Kept VASP volumetric subclasses inheriting from native `matsimpy.io.common.VolumetricData`.
  - Kept `Wavecar.write_unks()` using native `matsimpy.io.wannier90.Unk`.
  - Renamed the VASP HDF5 orbital mapping from `vasp_to_pmg_orb` to `vasp_orbital_names`.

- `tests/calculator/test_vasp_native_outputs.py`
  - Added a native integration contract for `Vasprun` advanced outputs.
  - Added an AST import-boundary test proving `outputs.py` does not import pymatgen.

## Behavior Implemented

- `Vasprun.get_computed_entry()` returns native `ComputedStructureEntry` by default.
- `Vasprun.get_trajectory()` returns native `Trajectory`.
- `Vasprun.complete_dos` and `complete_dos_normalized` return native `CompleteDos`.
- Band structure construction uses native `BandStructure` / `BandStructureSymmLine` and native branch reconstruction imports.
- VASP volumetric readers use native `VolumetricData` as their base class.
- UNK file writes use native `Unk`.
- Production `matsimpy/calculator/vasp/outputs.py` no longer imports pymatgen.

## Test Commands and Results

- Red check before implementation:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_native_outputs.py -q`
  - Result: failed as expected with 2 failures. `get_computed_entry()` entered pymatgen's `ComputedStructureEntry`, and the AST test detected pymatgen imports.

- Focused native contract:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_native_outputs.py -q`
  - Result: 2 passed, 2 warnings.

- Requested VASP output suite:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_native_outputs.py tests/calculator/test_vasp_outputs.py -q`
  - Result: 13 passed, 14 warnings.

- Relevant import-boundary suite:
  - `conda run -n pmg python -m pytest tests/calculator/test_vasp_imports.py -q`
  - Result: 11 passed, 1 warning.

## Commit

- Commit SHA: 4798966be50446d1acfe48fcfc5da6554067f92c

## Remaining Risks

- Existing fixture runs emit POTCAR lookup warnings because matching POTCAR files are not present in the fixture directory; this is pre-existing parser behavior and did not fail tests.
- The new complete DOS projected-data keys are site indexes, not site objects, because native `CrystalSite` is intentionally unhashable.
