# Builders Modules Comprehensive Review

**Date:** 2026-06-06  
**Scope:** `matsimpy/builders/**` public builder modules and `tests/builders/**` coverage.  
**Focus:** correctness, robustness, failure scenarios, recommended fixes, severity, and test coverage gaps.

## Validation Evidence

- Ran `python -m pytest tests/builders -q`: **138 passed**.
- The findings below are therefore mostly untested edge cases or semantic correctness gaps not caught by the current suite.
- Representative reproduction snippets were run locally for the highest-risk findings.

## Summary

| Severity | Count | Areas |
| --- | ---: | --- |
| High | 4 | surface adsorbates, space-group builders, twisted multilayers, intermetallic builders |
| Medium | 4 | random alloy count allocation, magic-angle contract, prototype formula handling, slab generation limitations |
| Low | 3 | input validation/export robustness |

---

## HIGH Severity Findings

### 1. Adsorbate height is measured along global z instead of the slab surface normal

- **File/module location:** `matsimpy/builders/surface/adsorbate.py:45-52`
- **Issue description:** `add_adsorbate()` determines the top surface with `max(cart_z)` and places the adsorbate at `surface_z + height` along the global z-axis. For generated non-(001) slabs, the slab normal is encoded in the lattice c-vector and is not generally aligned with global z.
- **Why it is problematic:** The documented `height` is meant to be height above the surface. On tilted surfaces such as `(1,1,1)`, the adsorbate can be placed below or inside the slab when measured along the actual surface normal.
- **Example scenario where it could fail:** For a simple-cubic `(1,1,1)` slab with `height=2.0`, a local reproduction showed the actual gap along the slab normal was approximately `-3.91 Å`, while the global z gap was `2.0 Å`.
- **Recommended fix:** Compute the unit surface normal from `slab.lattice.lattice_vectors[2]`, project slab atoms onto that normal, place the adsorbate at `max_projection + height`, and construct the in-plane anchor using the a/b lattice vectors without discarding their normal component.
- **Severity level:** High
- **Test coverage gaps:** Existing surface tests cover atom counts and simple placement but do not assert normal-direction distances for non-(001) Miller slabs. Add tests for `(1,1,1)` and `(1,1,0)` slabs validating the adsorbate-surface separation along the lattice c-vector normal.

### 2. `from_space_group()` can return a structure with the wrong space group

- **File/module location:** `matsimpy/builders/bulk/symmetry.py:80-90`, `matsimpy/builders/bulk/symmetry.py:322-422`, `matsimpy/builders/bulk/symmetry.py:425-513`
- **Issue description:** The implementation asks spglib to detect symmetry from the input positions, then applies those detected operations. When detected symmetry differs from the requested space group, the fallback still derives operations from the same input structure and returns a crystal without final validation.
- **Why it is problematic:** The public API name and docs promise generation from a requested space group, but callers can receive a crystal belonging to a different group without an error.
- **Example scenario where it could fail:** `from_space_group(225, ['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], lattice=Lattice.cubic(5.64))` returned a 2-atom structure detected as space group **221**, not requested **225**.
- **Recommended fix:** Use a source of symmetry operations for the requested group, or delegate to a library that can expand Wyckoff/asymmetric-unit positions by requested group. After generation, always validate the resulting structure against the requested space group and raise a clear `ValueError` if expansion cannot satisfy it.
- **Severity level:** High
- **Test coverage gaps:** Current bulk symmetry tests do not assert that generated structures are re-analyzed as the requested group for mismatched/asymmetric inputs. Add negative tests expecting failure or exact validation for SG 225/227/194 examples.

### 3. `build_twisted_multilayer()` reinterprets Cartesian coordinates as fractional

- **File/module location:** `matsimpy/builders/nanostructure/twisted.py:314-337`
- **Issue description:** The function combines `result.positions` and `new_layer.positions`, which are Cartesian for `Crystal`, then constructs `Crystal(combined_species, combined_positions, new_lattice)` without `coords_are_cartesian=True`.
- **Why it is problematic:** Cartesian Å coordinates are interpreted as fractional coordinates, inflating positions by the lattice matrix and corrupting layer spacing/cell geometry.
- **Example scenario where it could fail:** A 3-layer graphene-like input with `layer_spacing=3.35` produced a z-range around `2447 Å` instead of approximately `6.7 Å`.
- **Recommended fix:** Keep a Cartesian working array through the combine loop and construct with `coords_are_cartesian=True`, or explicitly convert combined Cartesian positions to fractional using the new lattice before constructing the `Crystal`.
- **Severity level:** High
- **Test coverage gaps:** Existing tests only assert type and atom count for multilayers. Add tests that assert Cartesian z-layer separations, lattice c length, and that `cart_positions` remain within the intended cell scale.

### 4. Unknown or documented intermetallic structures silently return pure FCC

- **File/module location:** `matsimpy/builders/alloy/ordered.py:45-91`
- **Issue description:** `generate_intermetallic()` documents examples such as `L1_0`, accepts `composition`, but implements only `L1_2` and `B2`. For any other `structure_type`, it returns `from_prototype("fcc", elements[0], lattice_constant)`, ignoring all other elements and the requested composition.
- **Why it is problematic:** Callers can request a binary compound and receive a pure elemental crystal with no error, which is a silent scientific correctness failure.
- **Example scenario where it could fail:** `generate_intermetallic(['Fe', 'Pt'], 'AB', 'L1_0', 3.85)` returned a crystal containing only `('Fe',)` instead of FePt.
- **Recommended fix:** Implement the documented structures (`L1_0`, etc.) or raise `NotImplementedError`/`ValueError` for unsupported `structure_type` and validate `elements` length plus `composition` compatibility before construction.
- **Severity level:** High
- **Test coverage gaps:** Tests cover implemented happy paths but do not cover documented `L1_0`, unsupported structure types, composition mismatch, or missing element validation.

---

## MEDIUM Severity Findings

### 5. Random alloy concentration rounding can produce impossible or zero substitutions

- **File/module location:** `matsimpy/builders/alloy/random.py:75-89`
- **Issue description:** Counts are computed independently with `int(np.round(conc * n_sites))`. Independent rounding can over-allocate beyond available sites or round all requested substitutions down to zero on small cells.
- **Why it is problematic:** Valid concentration inputs with `sum(concentrations) <= 1.0` can either raise a NumPy sampling error or create an alloy with the wrong composition.
- **Example scenario where it could fail:** With 3 target sites and concentrations `[0.5, 0.5]`, the code tries to sample 4 sites without replacement. With 2 target sites and `[0.25, 0.25]`, both counts round to zero, so no alloying occurs.
- **Recommended fix:** Allocate integer counts using floor plus largest-remainder distribution capped at `n_sites`, or expose/require exact integer counts for small-cell workflows. Raise a domain-specific error when requested fractions cannot be represented within tolerance.
- **Severity level:** Medium
- **Test coverage gaps:** Add tests for small supercells, multi-species concentrations whose fractional counts sum to the site count, and deterministic exact counts under a seed.

### 6. `build_magic_angle_twisted()` does not reliably build magic-angle structures

- **File/module location:** `matsimpy/builders/nanostructure/twisted.py:171-229`
- **Issue description:** The function special-cases every `n == m` pair as `21.8°` and otherwise uses `360 / (n² + nm + m²)`, while the docstring advertises moiré-index-based magic-angle behavior.
- **Why it is problematic:** The default `n=1, m=1` returns a large-angle bilayer, not a magic-angle (~1.1°) structure. Scientific workflows may incorrectly label non-magic structures as magic-angle.
- **Example scenario where it could fail:** A caller using the default `build_magic_angle_twisted(graphene)` receives a 21.8° bilayer despite the function name and docs emphasizing magic-angle structures.
- **Recommended fix:** Either rename/re-document it as a simplified twisted builder, or implement a validated commensurate-angle formula and defaults/candidate pairs that actually target ~1.1°. Validate `n`, `m` as positive integers and expose the calculated angle to callers or metadata.
- **Severity level:** Medium
- **Test coverage gaps:** Tests only check type and atom count. Add angle-specific tests that verify the second layer rotation for known `(n,m)` pairs and reject invalid indices.

### 7. Binary formula handling in single-site prototypes silently drops species

- **File/module location:** `matsimpy/builders/bulk/prototype.py:154-182`, `matsimpy/builders/bulk/prototype.py:228-242`
- **Issue description:** A formula with two parsed elements is allowed even when the prototype has one unique placeholder species. For one-atom primitive prototypes (`fcc`, `bcc`, `sc`), the alternating substitution loop only has one site, so the second element is omitted.
- **Why it is problematic:** A user requesting `from_prototype('fcc', 'CuNi', a)` receives pure Cu rather than a Cu-Ni alloy or an error.
- **Example scenario where it could fail:** `from_prototype('fcc', 'CuNi', 3.6)` produces a one-atom Cu primitive cell, silently dropping Ni.
- **Recommended fix:** Only allow multi-element formula strings for templates with enough distinct sites to represent all parsed elements, or require callers to use alloy builders/supercells for random or ordered solid solutions.
- **Severity level:** Medium
- **Test coverage gaps:** Add tests for compound formula parsing on single-site prototypes and verify an explicit error is raised for unrepresentable formulas.

### 8. Slab generation has no final geometric validation for requested thickness/vacuum

- **File/module location:** `matsimpy/builders/surface/slab.py:57-117`
- **Issue description:** `generate_slab()` builds a custom Miller-plane basis and searches translated bulk cells, but it does not verify the resulting atom slab thickness, vacuum thickness along the c-normal, or surface termination after construction.
- **Why it is problematic:** For non-orthogonal cells or high-index surfaces, the search/basis may produce a slab that satisfies internal fractional bounds but not the requested physical slab/vacuum dimensions.
- **Example scenario where it could fail:** A high-index Miller plane with a skewed lattice may generate atoms inside the selection cell but leave less actual vacuum along the slab normal than `min_vacuum_size`, which would affect surface calculations.
- **Recommended fix:** After construction, project atom positions onto the slab normal and assert/report actual slab thickness and vacuum thickness. Consider delegating complex slab generation to a tested crystallographic algorithm or explicitly document supported lattice/index assumptions.
- **Severity level:** Medium
- **Test coverage gaps:** Add tests for skewed/non-cubic lattices and several high-index surfaces, checking projected slab thickness and vacuum rather than only atom count/type.

---

## LOW Severity Findings

### 9. Molecule linear builder accepts zero axis and non-positive bond lengths

- **File/module location:** `matsimpy/builders/molecule/geometry.py:12-45`
- **Issue description:** `build_linear()` normalizes `axis` without checking shape, finiteness, or zero norm, and does not validate bond lengths as positive.
- **Why it is problematic:** A zero axis produces divide-by-zero/NaN behavior before eventual validation, and negative bond lengths create reversed/ambiguous geometries unlike `build_bent()`, which validates positive lengths.
- **Example scenario where it could fail:** `build_linear(['H','H'], [0.74], axis=[0,0,0])` emits invalid normalization behavior instead of a clear builder-level `ValueError`.
- **Recommended fix:** Mirror `build_bent()` validation: require finite 3D non-zero axis and positive finite bond lengths.
- **Severity level:** Low
- **Test coverage gaps:** Add zero-axis, malformed-axis, NaN-axis, zero-length, and negative-length tests.

### 10. Ordered alloy index validation misses negative indices at builder level

- **File/module location:** `matsimpy/builders/alloy/ordered.py:32-42`
- **Issue description:** The builder only checks `idx >= len(base_structure.species)` before delegating to `substitute()`. Negative indices are rejected later by `substitute()`, but the builder-level validation and error message are incomplete.
- **Why it is problematic:** It weakens robustness and makes validation behavior inconsistent with the explicit out-of-range check in this builder.
- **Example scenario where it could fail:** `generate_ordered_alloy(base, {-1: 'Cu'})` bypasses the local check and raises from a lower-level transformation with a different error type/message.
- **Recommended fix:** Check `idx < 0 or idx >= len(base_structure.species)` and raise one clear builder-level `ValueError` or let all index validation be handled by `substitute()` consistently.
- **Severity level:** Low
- **Test coverage gaps:** Add negative-index and non-integer-index tests for ordered alloy patterns.

### 11. Quaternary inverse Heusler builder is not re-exported from alloy package

- **File/module location:** `matsimpy/builders/alloy/heusler.py:218-279`, `matsimpy/builders/alloy/__init__.py:32-49`
- **Issue description:** `build_inverse_heusler_quaternary()` is defined and listed in `heusler.__all__`, but `matsimpy.builders.alloy.__init__` does not import or export it.
- **Why it is problematic:** Users importing from the package-level alloy namespace cannot access a public-looking Heusler builder, and wildcard imports from `matsimpy.builders.alloy` omit it.
- **Example scenario where it could fail:** `from matsimpy.builders.alloy import build_inverse_heusler_quaternary` raises `ImportError` despite the function existing in the submodule.
- **Recommended fix:** Import and include `build_inverse_heusler_quaternary` in `matsimpy/builders/alloy/__init__.py`, or make it private if it is not intended as supported API.
- **Severity level:** Low
- **Test coverage gaps:** Add package-level import/export tests for all functions listed by submodule `__all__`.

---

## Cross-Cutting Test Coverage Recommendations

1. Add semantic validation tests, not only construction/count tests: re-analyze symmetry, verify distances, verify layer spacings, and verify compositions.
2. Add edge-case parameter tests for small supercells, invalid axes, unsupported structures, and non-orthogonal lattices.
3. For scientific builders, add reference comparisons where possible: known space groups, known slab normals/vacuum, ASE or pymatgen nanotube/slab references, and known intermetallic prototypes.
4. Add package API/export tests to prevent public function drift across `__init__.py` files.
5. Prefer explicit failure tests for unsupported capabilities over silent fallback tests.

## Overall Recommendation

**Request changes for correctness-sensitive use.** The builders test suite passes, but several public APIs can silently produce physically or crystallographically incorrect structures. The highest-priority fixes are normal-direction adsorbate placement, requested-space-group validation, Cartesian/fractional handling in twisted multilayers, and intermetallic unsupported-type behavior.
