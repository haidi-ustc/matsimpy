## Task 5 Report

Status: complete

Commit: included in the Task 5 implementation commit; final hash is reported by the executor response.

## Implemented

- Added native `InputGenerator` base as an abstract `MSONable`.
- Added native `StructureMatcher.fit(first, second)` comparing composition, lattice lengths/angles, and periodic fractional sites independent of site order.
- Extended `SymmetryAnalyzer` with optional bound `Crystal` construction and spglib-backed:
  - `get_ir_reciprocal_mesh`
  - `get_primitive_standard_structure`
  - `get_conventional_standard_structure`
- Added exact optional-dependency error for symmetry operations: `spglib is required; install MatSimPy[analysis]`.
- Added `HighSymmetryKpath` with a provenance-tagged native primitive-cubic path table:
  - `Γ-X-M-Γ-R-X`
  - `M-R`
- Exported `StructureMatcher` and `HighSymmetryKpath` from `matsimpy.symmetry`.

## Verification

- RED: `conda run -n pmg python -m pytest tests/calculator/test_input_generator.py tests/symmetry/test_matcher.py tests/symmetry/test_kpath.py tests/symmetry/test_symmetry.py -q`
  - Result: failed during collection because `matsimpy.calculator.input_generator`, `matsimpy.symmetry.matcher`, and `matsimpy.symmetry.kpath` did not exist.
- Focused GREEN: `conda run -n pmg python -m pytest tests/calculator/test_input_generator.py tests/symmetry/test_matcher.py tests/symmetry/test_kpath.py tests/symmetry/test_symmetry.py -q`
  - Result: 32 passed.
- Full symmetry: `conda run -n pmg python -m pytest tests/symmetry -q`
  - Result: 31 passed.
- Compile: `conda run -n pmg python -m py_compile matsimpy/calculator/input_generator.py matsimpy/symmetry/analyzer.py matsimpy/symmetry/matcher.py matsimpy/symmetry/kpath.py matsimpy/symmetry/__init__.py tests/calculator/test_input_generator.py tests/symmetry/test_matcher.py tests/symmetry/test_kpath.py tests/symmetry/test_symmetry.py`
  - Result: passed.
- Whitespace: `git diff --check`
  - Result: passed.

## Concerns

- `HighSymmetryKpath` intentionally supports only spglib-detected cubic systems. Unsupported crystal systems raise `NotImplementedError` with the detected crystal system rather than fabricating a path.
- The native path table is explicitly provenance-tagged as a minimal primitive-cubic table; it is not a canonical spglib path because spglib has no canonical high-symmetry path API.
