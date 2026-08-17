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

## Round 1 Fix Evidence

Status: complete

Implemented review fixes:

- Tightened `HighSymmetryKpath` support from all cubic crystal systems to primitive-cubic space groups only. Cubic `I`, `F`, and diamond `Fd` examples now raise `NotImplementedError` naming the detected space group.
- Preserved the labeled `M` start for the disconnected top-level `M-R` path while still suppressing duplicate starts inside continuous path segments.
- Restored legacy positional construction semantics for `SymmetryAnalyzer(1e-4, 5.0)`.
- Replaced greedy same-species site assignment in `StructureMatcher` with deterministic per-species backtracking over periodic fractional-distance candidates.

Regression RED:

- `conda run -n pmg python -m pytest tests/calculator/test_input_generator.py tests/symmetry/test_matcher.py tests/symmetry/test_kpath.py tests/symmetry/test_symmetry.py -q`
  - Result: 6 failed, 32 passed.
  - Failures covered non-greedy matcher assignment, missing disconnected `M` label, bcc/fcc/diamond cubic k-path acceptance, and legacy positional `SymmetryAnalyzer` angle tolerance.

Verification:

- Focused Task 5: `conda run -n pmg python -m pytest tests/calculator/test_input_generator.py tests/symmetry/test_matcher.py tests/symmetry/test_kpath.py tests/symmetry/test_symmetry.py -q`
  - Result: 38 passed.
- Full symmetry: `conda run -n pmg python -m pytest tests/symmetry -q`
  - Result: 37 passed.
- Compile: `conda run -n pmg python -m py_compile matsimpy/calculator/input_generator.py matsimpy/symmetry/analyzer.py matsimpy/symmetry/matcher.py matsimpy/symmetry/kpath.py matsimpy/symmetry/__init__.py tests/calculator/test_input_generator.py tests/symmetry/test_matcher.py tests/symmetry/test_kpath.py tests/symmetry/test_symmetry.py`
  - Result: passed.
- Whitespace: `git diff --check`
  - Result: passed.

Remaining concern:

- Primitive-cubic detection uses the first character of the spglib international space-group symbol as the lattice centering evidence. This deliberately excludes `Im-3m`, `Fm-3m`, and `Fd-3m` from the primitive-cubic table.
