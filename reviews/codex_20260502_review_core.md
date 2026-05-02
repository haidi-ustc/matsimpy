# Deep Review: `matsimpy/core`

Date: 2026-05-02  
Scope: `matsimpy/core`  
Update: added concrete solution guidance for every issue.

## Summary

This review identifies correctness issues, hidden bugs, design flaws, and extensibility risks in `matsimpy/core`. Every issue below includes evidence, impact, and a recommended solution.

## Severity ranking

| Severity | Issue | Category | Confidence | Primary solution |
|---|---|---|---|---|
| Critical | Elements 104-118 are unusable despite existing in `periodic_table.json` | Correctness | High | Generate element ordering from JSON by atomic number; add `Rf`-`Og` tests. |
| High | `Structure.__eq__` / `__hash__` contract is broken for near-equal coordinates | Hidden bug | High | Make approximate equality unhashable, or split exact equality from `almost_equals`. |
| High | Crystal graph distance matrices silently return `inf` for atom pairs farther than 20 Å | Correctness | High | Compute true all-pairs distances; remove hard-coded neighbor cutoff. |
| High | `site_properties` length mismatches are silently ignored; dicts remain mutable/aliased | Hidden bug / design | High | **Done**: validate length, deep-copy on input, expose copy-on-read metadata. |
| Medium | `Crystal.__init__` does not validate `pbc` or `lattice` consistently | Correctness | High | Centralize validators and use them in all construction paths. |
| Medium | PBC neighbor model is incomplete for skewed cells and same-index periodic neighbors | Correctness / design | Medium | Replace image heuristic with robust minimum-image/cell-list logic and image shifts. |
| Medium | `Composition` accepts zero-count formulas like `H0` and normalizes them incorrectly | Correctness | High | Reject zero counts and zero group multipliers during parsing. |
| Medium | Species validation is inconsistent across `Structure`, `Site`, `Composition`, and `Element` | Design | High | Introduce one shared species normalization/validation function. |
| Medium | Core mutation methods embed arbitrary chemistry policy, e.g. hard 0.5 Å minimum distance | Extensibility | Medium | Move reasonableness checks behind optional validation policies. |
| Low | Serialization returns tuples in several places despite docs saying lists | Compatibility | Medium | Normalize serialized values to JSON-native lists/dicts. |
| Low | `Crystal`, `Molecule`, and `Structure` mix domain state with I/O, converters, calculators, DFT adapters | Extensibility | High | Move adapters into service modules or thin optional wrappers. |

---

## 1. Correctness issues

### Critical: Elements 104-118 are blocked

**Status: Fixed**  

**Evidence**
- `matsimpy/core/periodic_table.py:43-147` defines `ELEMENTS` only through `Lr` (103 elements).
- `matsimpy/core/periodic_table.py:149` builds `_ELEMENTS_SET` from that truncated list.
- `matsimpy/core/periodic_table.py:259-260` rejects symbols outside `_ELEMENTS_SET`.
- `matsimpy/core/periodic_table.py:333-335` limits `Element.from_Z()` to `len(ELEMENTS)`.
- `matsimpy/core/composition.py:35-36` derives valid symbols from this same list.

**Impact**
Elements `Rf` through `Og` are present in `periodic_table.json` but unusable through `Element`, `Element.from_Z`, and `Composition`.

**Solution**
1. Replace the hard-coded `ELEMENTS` list with a generated list from `_pdt`, sorted by each record's atomic number.
2. Build `_ELEMENTS_SET` from that generated list.
3. Keep dummy elements (`X`) separate so they do not affect atomic-number indexing.
4. Add regression tests for `Element("Rf")`, `Element("Og")`, `Element.from_Z(118)`, and `Composition("Og")`.

**Implementation sketch**
```python
ELEMENTS = [
    symbol
    for symbol, data in sorted(_pdt.items(), key=lambda item: item[1]["Atomic no"])
]
_ELEMENTS_SET = set(ELEMENTS)
```

---

### High: Crystal graph distance matrices are wrong beyond 20 Å

**Evidence**
- `matsimpy/core/graph.py:741-747` computes `CrystalGraph.distance_matrix` using `get_neighbor_list(cutoff=20.0)`.
- `matsimpy/core/graph.py:921-922` makes functional `get_distance_matrix()` use the same hard-coded 20 Å cutoff.

**Impact**
Valid atom pairs farther than 20 Å are reported as `inf`, corrupting distance-based analysis.

**Solution**
1. Do not implement all-pairs distance matrices through neighbor lists.
2. For non-PBC crystals, use `scipy.spatial.distance.cdist` directly.
3. For PBC crystals, compute all-pairs minimum-image distances from fractional coordinate differences.
4. Respect partial PBC by wrapping only periodic dimensions.
5. Add tests with atom separations greater than 20 Å.

**Implementation sketch**
```python
def _crystal_distance_matrix(crystal):
    frac = crystal.frac_positions
    diff = frac[:, None, :] - frac[None, :, :]
    pbc = np.array(crystal.pbc, dtype=bool)
    diff[..., pbc] -= np.round(diff[..., pbc])
    cart = diff @ crystal.lattice.matrix
    return np.linalg.norm(cart, axis=-1)
```

---

### Medium: `Composition` accepts zero-count formulas

**Evidence**
- `matsimpy/core/composition.py:217-223` parses digit sequences as integers without rejecting zero.
- `matsimpy/core/composition.py:267-270` adds zero-count elements to the counter.

**Impact**
Invalid formulas like `H0` and `Ca(OH)0` normalize into misleading formulas and can produce zero-mass or partially zero-count compositions.

**Solution**
1. In `parse_int_at`, reject values less than 1.
2. Consider rejecting leading zeros such as `H02`; if kept for compatibility, document the behavior.
3. Do not silently drop zero-count elements; fail on invalid input.
4. Add tests for `H0`, `Ca(OH)0`, and optionally `H02`.

**Implementation sketch**
```python
value = int(formula[start:idx])
if value <= 0:
    raise ValueError("Element and group counts must be positive")
if idx - start > 1 and formula[start] == "0":
    raise ValueError("Counts cannot have leading zeros")
return value, idx
```

---

## 2. Hidden bugs

### High: Approximate equality violates Python hash contract

**Evidence**
- `matsimpy/core/structure.py:590-593` treats positions as equal with `np.allclose(..., atol=1e-7)`.
- `matsimpy/core/structure.py:535-543` hashes rounded positions at 7 decimals.
- Equal objects can hash differently near rounding boundaries.

**Impact**
Equal structures can occupy separate keys in dictionaries and sets. This breaks caching, deduplication, and lookup behavior.

**Solution**
Preferred path:
1. Make `Structure` unhashable if `__eq__` remains approximate: set `__hash__ = None`.
2. Add an explicit `stable_key(tol=...)` or `quantized_key(decimals=...)` for deduplication workflows.
3. Add `almost_equals(other, atol=..., rtol=...)` if exact equality is desired for `__eq__` later.

Alternative path:
1. Make `__eq__` exact/quantized and keep `__hash__` based on the same exact/quantized representation.
2. Move current tolerance behavior to `almost_equals`.

**Regression tests**
- If `a == b`, then `hash(a) == hash(b)` for all tested boundary cases.
- Boundary cases around `0`, `4.9e-8`, `5.1e-8`, and `9e-8`.

---

### High: `site_properties` can be silently inconsistent and externally mutable

**Status: Fixed**  
Implemented shared validation/copy helpers, constructor length checks, defensive copies for `Site.properties` and structure `site_properties`, JSON-native serialization, and regression tests in `tests/test_site_properties_validation.py`.

**Evidence**
- `matsimpy/core/molecule.py:195-198` stores `site_properties` without length validation.
- `matsimpy/core/molecule.py:216-227` ignores mismatched site properties when building sites.
- `matsimpy/core/crystal.py:271-274` and `matsimpy/core/crystal.py:822-844` follow the same pattern.
- `matsimpy/core/site.py:238-240` returns the original properties dict.
- `matsimpy/core/site.py:313-329` exposes the mutable dict directly.

**Impact**
Metadata may be lost, shared between structures/sites, or mutated by external references after object construction.

**Solution**
1. Add a shared `_validate_site_properties(site_properties, n_atoms)` helper.
2. If `site_properties is None`, store an empty immutable tuple.
3. If provided, require `len(site_properties) == n_atoms`.
4. Deep-copy each dict on input and construction paths.
5. In `Site`, deep-copy `properties` in `_validate_properties`.
6. Expose a copied dict or `MappingProxyType` from `Site.properties`.
7. Convert immutable internals back to plain dict/list values in `as_dict()`.

**Implementation sketch**
```python
from copy import deepcopy

if site_properties is None:
    props = ()
else:
    if len(site_properties) != n_atoms:
        raise ValueError("site_properties length must match number of atoms")
    props = tuple(deepcopy(p) for p in site_properties)
```

solved: Yes
---

## 3. Design flaws

### Medium: Crystal construction validation is split and inconsistent

**Evidence**
- `Crystal.set_pbc()` validates PBC at `matsimpy/core/crystal.py:368-376`.
- `Crystal.__init__()` directly stores `tuple(pbc)` at `matsimpy/core/crystal.py:275-277`.
- The constructor uses `lattice.inv_matrix` / `lattice.matrix` without explicit lattice validation.

**Impact**
Invalid PBC values can enter objects, and missing/invalid lattice errors surface as incidental attribute errors rather than domain-specific errors.

**Solution**
1. Add `_validate_lattice(lattice) -> Lattice` and `_validate_pbc(pbc) -> tuple[bool, bool, bool]`.
2. Use them in `Crystal.__init__`, `Crystal._construct`, `Crystal.from_dict`, and `set_pbc`.
3. Reject `None` lattice with `ValueError("Crystal requires a Lattice")`.
4. Normalize `np.bool_` to Python `bool` if accepted.
5. Add tests for invalid PBC length, non-bool PBC, `None` lattice, and serialization round trips.

---

### Medium: PBC neighbor model is incomplete for skewed cells and same-index periodic neighbors

**Evidence**
- `matsimpy/core/crystal.py:1263-1268` chooses image count from periodic lattice-vector norms.
- `matsimpy/core/crystal.py:1443-1444` excludes periodic images whose image index maps to the queried atom itself.

**Impact**
Highly skewed cells can miss valid close images, and one-site periodic structures cannot report periodic self-neighbor coordination.

**Solution**
1. Replace image count based on raw vector norms with a robust bound using reciprocal lattice heights or a tested cell-list algorithm.
2. Distinguish “same atom in same cell” from “same atom in a nonzero periodic image”. Exclude only zero translation.
3. Return richer neighbor records where needed: `(neighbor_index, distance, image_shift)`.
4. Add tests for one-atom periodic crystals, skewed/triclinic cells, and partial PBC slabs/wires.

---

### Medium: Species validation is inconsistent across core classes

**Evidence**
- `Structure.__init__()` accepts any strings at `matsimpy/core/structure.py:184-185`.
- `Site._validate_specie()` only warns on suspicious string length at `matsimpy/core/site.py:215-219`.
- `Composition` validates symbols against `_VALID_ELEMENTS`.
- `Element` validates independently.

**Impact**
Invalid species can live in structures until later code accesses `elements`, `composition`, mass, or converters.

**Solution**
1. Create one shared function, e.g. `normalize_species(specie, allow_dummy=True) -> str`.
2. Use it in `Structure`, `Site`, `CrystalSite`, `Composition`, builders, and converters.
3. Decide policy for dummy species (`X`, vacancies, charged labels) explicitly.
4. For advanced labels, store base element and annotation separately instead of accepting arbitrary strings as elements.
5. Add tests for invalid symbols, dummy symbols, atomic numbers, and `Element` objects through every construction path.

---

## 4. Extensibility risks

### Medium: Structural mutation embeds arbitrary chemistry policy

**Evidence**
- `Molecule.add_atom()` rejects distances below 0.5 Å at `matsimpy/core/molecule.py:459-464`.
- `Crystal.add_atom()` rejects distances below 0.5 Å in several branches.

**Impact**
Core containers cannot represent unusual/high-pressure/intermediate structures or intentionally invalid states for workflows that need them.

**Solution**
1. Separate representation from validation policy.
2. Add `validate_geometry: bool = True` for backward compatibility, or better, accept a policy object.
3. Keep duplicate detection configurable separately from “too close” chemistry checks.
4. Document the default policy and escape hatch.

**Implementation sketch**
```python
@dataclass(frozen=True)
class GeometryValidationPolicy:
    duplicate_tol: float = 1e-6
    min_distance: float | None = 0.5
```

---

### Low: Serialization returns tuples despite JSON-list documentation

**Evidence**
- `Crystal.as_dict()` returns `pbc`, `species`, and `site_properties` as tuples at `matsimpy/core/crystal.py:892-900`.
- `Molecule.as_dict()` returns `species` and `site_properties` as tuples at `matsimpy/core/molecule.py:636-644`.

**Impact**
JSON serialization may convert tuples to lists, but direct dictionary consumers see types that contradict docs and may fail strict checks.

**Solution**
1. In all `as_dict()` methods, return plain JSON-native values.
2. Use `list(self.species)`, `list(self.pbc)`, and `[dict(p) for p in self.site_properties]`.
3. Add round-trip tests that assert exact container types, not only values.

---

### Low: Core classes mix domain state with I/O, converters, calculators, DFT adapters

**Evidence**
- `Crystal` includes file I/O, pymatgen/ASE conversion, DFT interfaces, symmetry, supercell, perturbation, and random generation.
- `Molecule` includes file I/O, converters, DFT interfaces, and transformations.

**Impact**
The core layer changes whenever optional integrations change. This increases import risk, test burden, and API coupling.

**Solution**
1. Keep core classes as small domain models: species, positions, lattice, composition, neighbor primitives, serialization.
2. Move adapters into modules such as `matsimpy.io`, `matsimpy.io.converters`, `matsimpy.code`, and `matsimpy.transformation`.
3. Preserve convenience methods as thin wrappers only if they do not import optional dependencies at module import time.
4. Long term, deprecate adapter wrappers from core if API simplification is desired.

---

## Cross-cutting refactor plan

### Phase 1: Lock behavior with regression tests

Add tests before edits for:
1. `Element("Og")`, `Element.from_Z(118)`, and `Composition("Og")`.
2. Structure equality/hash boundary behavior.
3. Crystal distance matrix with pair distances greater than 20 Å.
4. `site_properties` length mismatch and external mutation.
5. Invalid `pbc` and `None` lattice.
6. `Composition("H0")` and `Composition("Ca(OH)0")`.

### Phase 2: Centralize validators

Create an internal module such as `matsimpy/core/_validation.py` with:
- `normalize_species`
- `validate_positions`
- `validate_lattice`
- `validate_pbc`
- `validate_site_properties`

Use these helpers from all constructors, `_construct` paths, `from_dict`, and mutation methods.

### Phase 3: Fix correctness issues in priority order

1. Periodic table source of truth.
2. Composition zero-count parsing.
3. Site property immutability/validation.
4. Distance matrix correctness.
5. PBC neighbor semantics.
6. Hash/equality API decision.

### Phase 4: Reduce coupling

Move non-core adapters behind external modules and retain convenience wrappers only as stable forwarding methods.

## Recommended first PRs

1. **Periodic table + composition parser correctness**
   - Generate `ELEMENTS` from JSON.
   - Reject zero/leading-zero counts.
   - Add targeted tests.

2. **Site metadata validation and immutability**
   - Validate property length.
   - Deep-copy dicts.
   - Return JSON-native serialized values.

3. **Graph distance correctness**
   - Replace hard-coded 20 Å distance matrix logic.
   - Add long-distance and partial-PBC tests.

4. **Equality/hash API decision**
   - Either make structures unhashable or split exact equality from approximate comparison.
   - Update tests and documentation.

5. **Validation cleanup**
   - Centralize species, lattice, PBC, and position validators.
   - Remove duplicated validation paths.

## Verification notes

This document is a review artifact only; no source code changes are included here. Future implementation should be verified with targeted `pytest` runs over core, graph, composition, lattice, mutability, and hash tests after each PR.
