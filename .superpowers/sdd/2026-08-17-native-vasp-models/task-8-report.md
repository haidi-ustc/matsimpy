# Task 8 Report: VASP Boundary and Adversarial Validation

## Summary

- Added a package-wide AST contract proving every Python file under `matsimpy/calculator/vasp` has zero executable `pymatgen` imports.
- Added a subprocess runtime contract proving `matsimpy.calculator.vasp`, `inputs`, `outputs`, and `sets` import while `ase` and `pymatgen` are blocked.
- Added adversarial unsupported-path tests for non-native structures, `reduce_structure`, and unsupported monoclinic standardization mode.
- Fixed one scoped boundary defect: initial `VaspInputSet`/`DictSet` construction now rejects non-`Crystal` structures instead of silently clearing them.
- Fixed one scoped installed-package defect: VASP JSON/YAML data files are now included in setuptools package data.

## Changed Files

- `pyproject.toml`
- `matsimpy/calculator/vasp/sets.py`
- `tests/calculator/test_vasp_imports.py`
- `tests/calculator/test_vasp_sets.py`
- `tests/test_packaging_runtime_contracts.py`
- `.superpowers/sdd/2026-08-17-native-vasp-models/task-8-report.md`

## TDD / Adversarial Evidence

- RED: `conda run -n pmg python -m pytest tests/calculator/test_vasp_sets.py -q`
  - Result: failed as expected on `test_dictset_rejects_non_native_structure`; `DictSet("not a structure", ...)` was accepted.
- GREEN: `conda run -n pmg python -m pytest tests/calculator/test_vasp_sets.py -q`
  - Result: `8 passed, 4 warnings`.
- RED: `conda run -n pmg python -m pytest tests/test_packaging_runtime_contracts.py::test_vasp_data_files_are_included_in_package_metadata -q`
  - Result: failed as expected with `KeyError: 'matsimpy.calculator.vasp'`.
- GREEN: `conda run -n pmg python -m pytest tests/test_packaging_runtime_contracts.py::test_vasp_data_files_are_included_in_package_metadata -q`
  - Result: `1 passed`.

## Import Boundary Evidence

- `conda run -n pmg python -m pytest tests/calculator/test_vasp_imports.py tests/test_packaging_runtime_contracts.py -q`
  - Result before scoped fixes: `21 passed, 1 warning`.
- `conda run -n pmg python -m pytest tests/calculator/test_vasp_imports.py tests/test_packaging_runtime_contracts.py tests/calculator/test_vasp_sets.py -q`
  - Result after scoped boundary fix: `29 passed, 5 warnings`.
- `rg -n "^[[:space:]]*(from|import)[[:space:]]+pymatgen" matsimpy/calculator/vasp`
  - Result: no executable import matches.
- AST scan over `matsimpy/calculator/vasp/*.py`
  - Result: `[]`.
- Literal plan scan `rg -n "(^|[[:space:]])(from|import)[[:space:]]+pymatgen" matsimpy/calculator/vasp`
  - Result: only attribution/docstring/comment mentions; no executable imports. The AST contract is the enforced boundary.

## Installed Import Evidence

- Initial installed-copy smoke:
  - Command shape: `tmp=$(mktemp -d); conda run -n pmg python -m pip install --no-deps --quiet --target "$tmp/site" . && cd "$tmp" && PYTHONPATH="$tmp/site" conda run -n pmg python -c '...blocked ase/pymatgen; import matsimpy.calculator.vasp...'`
  - Result: failed with missing installed data file `matsimpy/calculator/vasp/incar_parameters.json`.
- Final installed-copy smoke:
  - Same command shape.
  - Result: `installed vasp imports ok`.

## Focused Suite

- `conda run -n pmg python -m pytest tests/calculator/test_vasp_imports.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_outputs.py tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_native_outputs.py tests/electronic_structure tests/symmetry tests/core/test_entries.py tests/core/test_trajectory.py tests/core/test_units.py tests/io/test_volumetric_data.py tests/io/test_wannier90.py tests/test_packaging_runtime_contracts.py -q`
  - Result: `161 passed, 25 warnings`.
  - Migrated VASP paths had zero skips.

## Static and Full-Suite Verification

- `conda run -n pmg python -m compileall -q matsimpy`
  - Result: passed, exit 0.
- `git diff --check`
  - Result: passed, exit 0.
- `conda run -n pmg python -m ruff check matsimpy tests`
  - Result: failed with `Found 1669 errors`; this is existing repo-wide lint debt, not a missing `ruff` install. Task 8 did not attempt broad lint cleanup.
- `conda run -n pmg python -m pytest -q`
  - Result: `2 failed, 1704 passed, 83 skipped, 56 warnings`.
  - Failures match the recorded baseline exactly:
    - `tests/calculator/test_gaussian.py::TestGaussianOutput::test_from_file`
    - `tests/calculator/test_gaussian.py::TestGaussianOutput::test_optional_pymatgen_reference`
  - Both fail with `FileNotFoundError` for missing `tests/calculator/fixtures/gaussian/methane.log`.

## Risks

- Full-repo pytest is not green only because of the documented pre-existing Gaussian fixture gap.
- Full-repo ruff remains red due broad pre-existing style/lint debt.
- The package boundary blocks executable `pymatgen` imports under `matsimpy/calculator/vasp`; legal attribution strings and reference comments still mention pymatgen.

## Commit

- Commit SHA: 6130910eafcc3bbb61e1990a3aa0a669a7deb3e6
