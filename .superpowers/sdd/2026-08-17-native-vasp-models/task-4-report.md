## Status

Complete.

## Commit

- `9986e4a` Own VASP grid and Wannier data formats inside MatSimPy

## Changes

- Added `matsimpy.io.VolumetricData` backed by native `Crystal` structures and native `Spin` keys for derived spin channels.
- Added validated periodic 3D volumetric grid metadata, axis grids, periodic trilinear sampling, and linear add/subtract operations.
- Added `matsimpy.io.Unk` with exact supported collinear and noncollinear data ranks and SciPy `FortranFile` write records matching `Wavecar.write_unks`.
- Exported `VolumetricData` and `Unk` from `matsimpy.io`.

## Verification

- RED: `conda run -n pmg python -m pytest tests/io/test_volumetric_data.py tests/io/test_wannier90.py -q` failed on missing `VolumetricData` and `Unk` imports.
- RED adjustment: `conda run -n pmg python -m pytest tests/io/test_volumetric_data.py::test_volumetric_data_preserves_augmentation_payload -q` failed until `data_aug` passed through as auxiliary payload.
- GREEN: `conda run -n pmg python -m pytest tests/io/test_volumetric_data.py tests/io/test_wannier90.py -q` passed, 14 tests.
- IO suite: `conda run -n pmg python -m pytest tests/io -q` passed, 164 tests.
- Syntax: `conda run -n pmg python -m compileall -q matsimpy/io/common.py matsimpy/io/wannier90.py tests/io/test_volumetric_data.py tests/io/test_wannier90.py` passed.
- Diff hygiene: `git diff --cached --check` passed before commit.

## Concerns

- Full repository pytest was not run; Task 4 validation used the focused tests plus the complete `tests/io` suite.
- `Wavecar.write_unks` still imports `Unk` from pymatgen; this task only adds native support for the later cutover.

## Fix Round 1

### Changes

- Tightened SOC detection to require the expected `diff_x`, `diff_y`, and `diff_z` vector channels.
- Changed collinear spin detection to require `diff`, and made `spin_data` raise for SOC grids instead of fabricating `Spin.up`/`Spin.down`.
- Rejected volumetric arrays with zero grid extents.
- Validated `Unk.ik` as a positive integer while rejecting bools and floats without coercion.
- Validated raw UNK input as complex before casting to `complex128`.
- Rejected UNK arrays with zero band or grid extents.

### Verification

- RED: `conda run -n pmg python -m pytest tests/io/test_volumetric_data.py tests/io/test_wannier90.py -q` failed with 15 expected regression failures covering SOC semantics, zero extents, `ik` validation, raw complex validation, and zero UNK extents.
- GREEN: `conda run -n pmg python -m pytest tests/io/test_volumetric_data.py tests/io/test_wannier90.py -q` passed, 29 tests.
- IO suite: `conda run -n pmg python -m pytest tests/io -q` passed, 179 tests.
- Syntax: `conda run -n pmg python -m compileall -q matsimpy/io/common.py matsimpy/io/wannier90.py tests/io/test_volumetric_data.py tests/io/test_wannier90.py` passed.
