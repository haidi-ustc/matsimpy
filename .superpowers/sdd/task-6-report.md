# Task 6 report: native volumetric data and Wannier UNK

## Status

Implemented native `VolumetricData` and `Unk`, rebased VASP volumetric subclasses and
`Wavecar.write_unks` onto them, and retained VASP parsing/writing in `outputs.py`.

## RED evidence

Command:

`pytest tests/io/test_volumetric.py tests/io/test_wannier.py -v`

Result: exit 2 during collection. Both imports failed as intended:
`ModuleNotFoundError: No module named 'matsimpy.io.volumetric'` and
`ModuleNotFoundError: No module named 'matsimpy.io.wannier'`.

## GREEN evidence

Initial native contracts:

`pytest tests/io/test_volumetric.py tests/io/test_wannier.py -v`

Result: 6 passed.

Pinned-oracle focused parity:

`pytest tests/calculator/test_vasp_outputs_parity.py -k 'volumetric or unk' -m requires_pymatgen -v`

Result: 2 passed. This verifies axis averages, radial integration, spin data,
arithmetic, and byte-identical collinear/noncollinear UNK files.

Final affected suite:

`pytest tests/io/test_volumetric.py tests/io/test_wannier.py tests/calculator/test_vasp_outputs.py tests/calculator/test_vasp_outputs_parity.py tests/architecture/test_vasp_no_pymatgen.py -v`

Result: 25 passed, 1 xfailed. The xfail is the pre-existing architecture scan whose
strict condition still sees legacy pymatgen references elsewhere in the VASP module;
the blocked-pymatgen runtime import test passes.

## Implementation notes

- Validates non-empty, same-shaped 3D grids.
- Provides grid metadata, interpolation, spin decomposition, axis averages,
  scalar/grid arithmetic, periodic radial integration, and Monty round trips.
- Preserves `data_aug` through arithmetic and serialization.
- Writes Wannier90 Fortran unformatted records in complex128 Fortran order.
- `Wavecar.write_unks` continues to emit spin-separated and `NC` filenames through
  the now-unconditional native `Unk` import.

## Concerns

- Verification ran under the available Python 3.12 environment. The added source
  uses syntax compatible with Python 3.9.

## Correctness follow-up RED evidence

`pytest tests/io/test_volumetric.py tests/calculator/test_vasp_outputs.py -q`
failed 4 of 17 tests: zero-length dimensions were accepted, fractional rounding
gave incorrect nearest images for a skew lattice, a radius of 100 counted periodic
images 523482.125 times after normalization, and a supplied distance matrix was
ignored by integration.

An additional focused RED run,
`pytest tests/calculator/test_vasp_outputs.py::test_chgcar_native_arithmetic_and_serialization -q`,
showed that `Chgcar.__init__` discarded a validated supplied cache (observed 0.5,
expected 0 for an all-99 distance grid).

## Correctness follow-up GREEN evidence

`pytest tests/io/test_volumetric.py tests/io/test_wannier.py tests/calculator/test_vasp_outputs.py tests/calculator/test_vasp_outputs_parity.py tests/architecture/test_vasp_no_pymatgen.py -q`
completed with 29 passed and 1 pre-existing architecture xfail.

Minimum-image distances now use an exact closest-lattice-vector search. Fractional
rounding supplies an upper bound; the smallest singular value of the lattice gives
a rigorous Euclidean search radius containing every translation that could improve
that bound. Each grid sample consequently has exactly one distance and is counted
at most once. Supplied per-site caches are shape-validated, reused, and retained by
VASP subclasses.

Pinned pymatgen parity still holds below the periodic boundary. At radius 1 for the
2x2x2 cubic fixture, pymatgen returns 0.875 because it counts multiple images of
boundary samples; the approved unique-sample minimum-image semantics return the
mathematically expected 4 / 8 = 0.5. The parity regression documents this intentional
oracle discrepancy.
