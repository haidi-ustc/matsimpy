## Task 6 Report: Replace Masking Resource Loaders

### Changes
- Added `matsimpy/calculator/vasp/_resources.py` with `load_vasp_resource(path, *, required=True)`.
- Replaced VASP `inputs.py` and `sets.py` `_safe_loadfn` usage with the focused loader.
- Made packaged VASP JSON/YAML/hash/stat resources required by default.
- Updated `POTCAR_STATS_PATH` to the packaged `vasp_potcar_stats.json` resource.
- Kept `_gen_potcar_summary_stats(append=True)` optional only for a missing user append file; malformed append files now raise `FormatError` with a chained cause.
- Added direct loader tests and extended the installed-copy packaging contract to import and load the VASP resource module.

### TDD Evidence
- RED: `conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m pytest tests/calculator/test_vasp_resources.py -q`
  - Result before implementation: 7 failures from missing `matsimpy.calculator.vasp._resources` and existing `_safe_loadfn` exposure.
- GREEN: same command after implementation.
  - Result: 7 passed.

### Verification
- Targeted VASP and packaging contract:
  - `conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m pytest tests/calculator/test_vasp_resources.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_sets.py tests/calculator/test_vasp_imports.py tests/test_packaging_runtime_contracts.py -q`
  - Result: 69 passed, 9 warnings.
- Static compile:
  - `conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m compileall -q matsimpy/calculator/vasp/_resources.py matsimpy/calculator/vasp/inputs.py matsimpy/calculator/vasp/sets.py tests/calculator/test_vasp_resources.py tests/test_packaging_runtime_contracts.py`
  - Result: passed.
- Diff whitespace:
  - `git diff --check`
  - Result: passed.
- Full suite:
  - `conda run -n pmg /opt/miniconda3/envs/pmg/bin/python -m pytest -q`
  - Result: 1727 passed, 83 skipped, 58 warnings, 2 failed.
  - Failures match the known linked-worktree baseline: `tests/calculator/test_gaussian.py::TestGaussianOutput::test_from_file` and `tests/calculator/test_gaussian.py::TestGaussianOutput::test_optional_pymatgen_reference`, both due to missing `tests/calculator/fixtures/gaussian/methane.log`.

### Concerns
- No task-related failures observed.
- The full suite still has the known unrelated missing Gaussian fixture failures.
