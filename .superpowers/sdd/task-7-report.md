# Task 7 report: native symmetry services

## Outcome

Implemented and exported `SpacegroupAnalyzer`, `StructureMatcher`, and
`HighSymmKpath`.  spglib remains optional and all operations that require it
raise a targeted installation error.  The implementation supports Python 3.9
syntax and retains MatSimPy's row-vector lattice/fractional-coordinate
conventions.

## RED / GREEN record

- RED: `pytest tests/symmetry/test_vasp_services.py -v` failed during collection
  with `ImportError: cannot import name 'HighSymmKpath' from
  'matsimpy.symmetry'`. This was the expected missing-API failure.
- First GREEN attempt exposed a real backend compatibility issue:
  `spglib.get_ir_reciprocal_mesh()` does not accept `angle_tolerance`.
  Removing that unsupported keyword made the focused suite pass.
- Review added tests for targeted missing-spglib errors, mismatch decisions,
  deterministic labels, every required Bravais key, and optional pymatgen
  standardization/mesh parity.
- Final focused result: 20 passed.
- Final complete symmetry result: 43 passed.
- Optional parity selection: 1 passed, 19 deselected (pymatgen 2025.6.14 is
  installed in the development environment).
- `git diff --check` and `python -m compileall -q matsimpy/symmetry` passed.

## Implementation details

- Standardization converts `Crystal` to spglib's `(lattice, positions,
  atomic_numbers)` tuple and maps returned atomic numbers back through
  `Element.from_Z`, preventing a site-order change from corrupting species.
- Irreducible reciprocal meshes use stable sorted representative indices and
  exact mapping multiplicities; shifted meshes include the half-grid offset.
- Matching checks exact compositions, lattice length/angle tolerances, then
  tries translations from the least-common species. Each species block uses a
  minimum-image Cartesian cost matrix and SciPy's Hungarian assignment. The
  final threshold is normalized by `(volume / atom_count) ** (1/3)`.
- K-path generation classifies the spglib international setting into all 14
  requested Bravais keys, uses standardized conventional reciprocal lattices,
  and interpolates each independent segment deterministically. Segment
  endpoints carry labels and interiors carry empty strings.

## Attribution and clean-room decisions

No pymatgen source, implementation, or path tables were copied. Pymatgen
2025.6.14 was used only as a black-box oracle in a parity test. The fixed
metric-independent special-point coordinates are attributed in the module to
Setyawan and Curtarolo, *Computational Materials Science* 49, 299 (2010).
For centered/metric-dependent families, this implementation deliberately uses
deterministic conservative conventional-cell paths instead of reproducing an
unattributed third-party conditional table.

## Concerns / limitations

- Full coordinate-and-label parity with pymatgen for every metric-dependent
  Bravais variant is not claimed. The checked-in parity test covers cubic
  standardization and irreducible-mesh weights, while the complete Bravais
  parameterization verifies table integrity. In particular tI, oF/oI/oC, and
  mC currently use deterministic fallback paths rather than the full
  metric-dependent Setyawan-Curtarolo branches. This is scientifically usable
  as a stable sampling path but is the main follow-up if exact pymatgen k-path
  parity is mandatory.
- Site properties are not reconstructed by spglib standardization because
  spglib can change site multiplicity; chemical species are preserved, but a
  policy for propagating arbitrary per-site metadata would need a separate API
  decision.

## Review rework: complete Setyawan--Curtarolo paths

### RED / GREEN record

- RED: the new alias regression failed for `tI`, `oF`, `oI`, `oC`, and `mC`;
  each object was identical to its primitive-family fallback. The pinned
  interpolation regression also failed because the implementation returned
  `ceil(distance * density)` points rather than that many intervals plus both
  endpoints.
- GREEN: all centered families now use their real metric-dependent SC
  definitions, including BCT1/2, ORCF1/2/3, RHL1/2, and MCLC1--5 selection.
  Labels use pymatgen's `\\Gamma`, subscript, and `\\Sigma` spelling, and every
  independent edge includes both endpoints exactly as pymatgen 2025.6.14 does.
- The representative 14-family parity matrix passes for Bravais
  classification, fractional special-point coordinates, path branches,
  interpolated coordinates, endpoint labels, and point counts with explicit
  `path_type="setyawan_curtarolo"` and `coords_are_cartesian=False`.
- Strong dependency-free tests cover all 14 Bravais families and all
  non-boundary metric subvariants. The measure-zero MCLC2 boundary is checked
  directly against the selected public SC definition.

### Attribution

The reworked implementation obtains variant selection, point formulae, and
path strings through the public API of ASE 3.29.0 (`ase.lattice` and
`ase.dft.kpoints`). ASE is distributed under the BSD-2-Clause license and its
Bravais definitions cite Setyawan and Curtarolo, *Computational Materials
Science* 49, 299--312 (2010), Tables 2--19. No pymatgen source or tables were
copied; pymatgen 2025.6.14 is only an optional black-box test oracle. The scope
adapted here is special-point coordinates, SC path branch names, metric variant
classification, and canonical primitive reciprocal metrics.

### Superseded limitation

The earlier limitation claiming conservative fallback paths for `tI`,
`oF`/`oI`/`oC`, and `mC` is superseded by this rework.

## Second review rework: remove ASE runtime and test coupling

### RED / GREEN evidence

- RED: the new subprocess regression blocked imports whose top-level package
  was `ase` or `pymatgen`; importing `matsimpy.symmetry` failed immediately at
  `from ase.cell import Cell` in `kpath.py`.
- GREEN: `kpath.py` is now a self-contained NumPy implementation of the narrow
  3D SC definition subset.  The subprocess imports `matsimpy.symmetry`, builds
  a silicon `Crystal`, constructs `HighSymmKpath` using spglib, and samples its
  path while both oracle packages remain blocked.
- The independent native fixtures no longer construct expected inputs through
  ASE or call production classification.  Numeric standardized primitive cells
  cover all 14 families and BCT1/2, ORCF1/2/3, RHL1/2, and MCLC1/2/3/4/5.
- Pinned pymatgen 2025.6.14 parity checks each metric subvariant's production
  classification, complete special-point label set and coordinates, branches,
  interpolated labels, point count, and interpolated fractional coordinates.
- Fresh complete symmetry result: 98 passed, with no warnings.

### Attribution and licensing

The source header now declares the exact ASE 3.29.0 files, classes/functions,
data scope, MatSimPy modifications, copyright, BSD-2-Clause terms, and the
Setyawan--Curtarolo paper/DOI.  `THIRD_PARTY_NOTICES.md` reproduces the required
BSD-2-Clause notice.  Adapted portions are explicitly identified as third-party
work; pymatgen remains only a test oracle.

### Runtime contract

No dependency metadata was changed.  There are no executable ASE imports in
`matsimpy/symmetry` or its tests; mentions are limited to provenance and the
blocked-import regression.

## Third review rework: matcher and standardization parity

### Root cause and implementation

- The matcher compared lattice lengths and angles in their input row order,
  so axis permutations and general unimodular basis changes were rejected
  before site matching. It now deterministically enumerates bounded integer
  lattice vectors, retains only unimodular transforms satisfying `ltol` and
  `angle_tol`, maps fractional coordinates into each candidate basis, and then
  performs the existing species-grouped translation/Hungarian matching.
- Fractional component rounding does not solve the closest-vector problem for
  skew lattices. Matcher costs now use an exact finite 3D closest-vector search
  bounded by the lattice's smallest singular value. The helper lives in the
  symmetry module and introduces no `io` dependency.

### RED / GREEN and parity evidence

- RED: focused matcher tests rejected both an axis permutation and a
  determinant-one shear while the existing translation/species tests passed.
- GREEN: dependency-free coverage passes for monoclinic/triclinic true minimum
  images, axis permutation, unimodular shear, global translation/site
  permutation, species mismatch, geometric mismatch, and inclusive/exclusive
  lattice tolerance boundaries.
- A pinned pymatgen 2025.6.14 black-box decision matrix agrees on translated,
  permuted, skew, basis-changed, species-negative, and lattice-negative cases.
- Space-group parity now spans diamond-like cubic, binary cubic, tetragonal,
  and hexagonal structures. Primitive and conventional results are checked as
  basis-equivalent lattice/species/fractional-coordinate mappings after
  deterministic matching; shifted and unshifted irreducible meshes compare
  representative coordinates together with weights. The Na/Cl/Ti/O cases
  exercise atomic-number-to-symbol reconstruction.
