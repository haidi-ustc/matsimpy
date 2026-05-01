# Core Architecture Review — May 2026

## Summary

The immutability refactor is a net improvement: freeze/thaw complexity is gone, cache invalidation bugs are eliminated, and the `from_dict`/`_extra_dict_fields` extension hook pattern is clean. Six issues below range from a correctness bug to API polish items.

---

## 1. Critical: `_neighbor_tree` Mutates an "Immutable" Object

**Location:** `matsimpy/core/crystal.py:1406-1416`

`get_neighbor_list()` rebuilds the KD-tree cache by mutating `self._neighbor_tree`, `self._neighbor_tree_cutoff`, etc. directly on the Crystal instance:

```python
# crystal.py:1412-1416 — mutates self on an "immutable" object
self._neighbor_tree = cKDTree(positions)
self._neighbor_tree_cutoff = cutoff
self._neighbor_tree_positions = positions
self._neighbor_tree_use_pbc = use_pbc
self._neighbor_tree_pbc = tuple(self.pbc)
```

**Why it's a problem:** The immutability contract says a Crystal, once constructed, never changes observable state. But `get_neighbor_list` has a side effect — it changes five private attributes. If two threads share a Crystal and both call `get_neighbor_list` with different cutoffs, they race. The comment at line 1397-1402 argues this is safe because mutations return new objects, but that's reasoning about callers, not about the object itself.

**Fix:** Use a module-level LRU cache keyed by `(id(crystal), cutoff, use_pbc, pbc_tuple)` instead of instance attributes. Or accept that this is a memoization cache and document it as the one exception to immutability:

```python
# Preferred: module-level cache, no instance mutation
_neighbor_tree_cache: Dict[Tuple[int, float, bool, tuple], cKDTree] = {}

def get_neighbor_list(self, cutoff, ...):
    cache_key = (id(self), cutoff, use_pbc, tuple(self.pbc))
    if cache_key not in _neighbor_tree_cache:
        positions = self._get_periodic_images(cutoff) if use_pbc else self.cart_positions
        _neighbor_tree_cache[cache_key] = cKDTree(positions)
    tree = _neighbor_tree_cache[cache_key]
    # ... query tree
```

Trade-off: the cache now lives forever (potential memory leak for long-running processes). If that's a concern, use `functools.lru_cache` on a standalone function or `weakref.WeakKeyDictionary`.

---

## 2. Mutable `site_properties` and `pbc` Leak Internal State

**Location:** `matsimpy/core/crystal.py:206,208`

```python
self.site_properties = site_properties or []   # mutable list
self.pbc = pbc if pbc is not None else [True, True, True]  # mutable list
```

Users can write `crystal.site_properties[0]['charge'] = 5` or `crystal.pbc[0] = False`, mutating the "immutable" object. The mutation methods defensively copy both (`list(self.site_properties)`, `list(self.pbc)`), so new objects are safe. But the original object is not.

**Why it's a problem:** It breaks the immutability mental model. A user who mutates `site_properties` in-place gets a different `as_dict()` output on the "same" object. The `__hash__` doesn't include `site_properties`, so two Crystals that differ only in mutated `site_properties` will hash equal but serialize differently.

**Fix:** Store tuples and return copies on read, or store tuples and return them directly:

```python
# In __init__:
self._site_properties = tuple(site_properties) if site_properties else ()
self._pbc = tuple(pbc if pbc is not None else (True, True, True))

@property
def site_properties(self) -> Tuple[Dict[str, Any], ...]:
    return self._site_properties  # immutable tuple, dicts inside are still mutable but at least the list isn't

@property
def pbc(self) -> Tuple[bool, bool, bool]:
    return self._pbc
```

---

## 3. `Molecule.get_center_of_mass` Uses `hasattr` Guard Instead of Compute-Once Pattern

**Location:** `matsimpy/core/molecule.py:255`

```python
def get_center_of_mass(self) -> List[float]:
    if not hasattr(self, "_cached_com") or self._cached_com is None:
        ...
        self._cached_com = center_of_mass.tolist()
    return self._cached_com
```

Every other cache (`_formula`, `_composition`) is initialized to `None` in `__init__` and checked with `is None`. COM uses `hasattr` which is slower and inconsistent.

**Why it's a problem:** Minor — functionally correct since the structure is immutable. But `hasattr` triggers a full MRO attribute lookup (__dict__ → class dict → parent dicts) on every call when the cache is populated. And it's a different pattern from the other two caches, so a reader has to understand two mechanisms.

**Fix:** Initialize `self._cached_com = None` in `Molecule.__init__` and use the standard `if self._cached_com is None` check.

---

## 4. `_positions` Semantics Differ Between Subclasses

**Location:** `matsimpy/core/structure.py:177`, `matsimpy/core/crystal.py:191-204`

In `Structure.__init__`, `self._positions` is Cartesian. In `Crystal.__init__`, `self._positions` is **fractional** (passed to `super().__init__` as fractional). `Crystal.positions` overrides to return `self.cart_positions` (Cartesian), restoring the Cartesian contract. But `self._positions` itself means different things depending on the subclass.

**Why it's a problem:** Any code in `Structure` that accesses `self._positions` directly (bypassing the `.positions` property) gets different coordinate systems. Currently, `Structure` methods use `self._positions` in:
- `add_atom` (line 852): `np.vstack([self._positions, positions_array])` — for a Crystal, stacks fractional + Cartesian (BUG if coords_are_cartesian=True is passed to the base class, but Crystal overrides this method)
- `remove_atom` (line 879): `np.delete(self._positions, index, axis=0)` — same issue
- `sort_atoms` (line 969): uses `self._positions` in sort

Since Crystal and Molecule both override all mutation methods, the base class code paths are never called for Crystals. But if a future subclass inherits `Structure.add_atom` without overriding, it will mix coordinate systems.

**Fix:** Either rename `_positions` to `_cart_positions` in Structure and have Crystal store fractional separately, or add a class-level flag:

```python
class Structure(ABC):
    _positions_are_fractional: bool = False  # overridden in Crystal
```

This is low-severity since both subclasses override all mutation methods. Worth cleaning up if a third Structure subclass is ever added.

---

## 5. Doc Bug: `inplace=True` Still Referenced in Transformation Module

**Location:** `matsimpy/transformation/__init__.py:39`

```python
# For in-place modification, use structure methods directly
>>> molecule.translate([1, 1, 1], inplace=True)  # Molecule class method
```

`inplace` was deleted from all mutation methods. This docstring is stale.

---

## 6. Duplicated Mutation Logic Across Three Classes

`Structure.add_atom`, `Crystal.add_atom`, and `Molecule.add_atom` each contain ~70% duplicated logic: normalize species input, validate positions, check for duplicates, check proximity to existing atoms, build new species/positions arrays, construct return value. The Crystal and Molecule versions add site_properties handling and coordinate system awareness.

The base class uses `from_dict` + `_extra_dict_fields` as the reconstruction mechanism — clean and extensible. But Crystal and Molecule override `add_atom`/`remove_atom` entirely, reimplementing the base logic plus subclass-specific handling. This means a bug fixed in one class may persist in another.

**Suggestion (future):** Extract shared validation logic into `_validate_new_atoms(species, positions, existing_positions, pbc=None, lattice=None)` on Structure, called by all three `add_atom` implementations. Not urgent — the code works — but if a fourth structure type is added, this duplication would become a real maintenance burden.

---

## What's Working Well

1. **Dependency hygiene.** `core/__init__.py` only imports intra-core. All cross-module imports (io, calculator, symmetry, transformation, builders, code) are lazy inside methods. No import-time dependency inversion.

2. **`_extra_dict_fields` + `_filter_per_atom_data` + `_reorder_per_atom_data` pattern.** Clean extension mechanism for subclasses to hook into base-class mutation methods. Crystal and Molecule use it correctly. Adding a new Structure subclass with per-atom data requires implementing exactly three methods.

3. **Compute-once caches.** `_formula`, `_composition` are set once and never invalidated. No dirty flags remain. The immutability guarantee makes this correct by construction.

4. **Read-only position views.** `positions.view()` with `writeable=False` prevents accidental mutation.

5. **Hash-based calculation staleness.** `_needs_calculation()` compares `hash(self)` to the stored hash. Immutability means the hash never changes for a given object, so this is reliable.

6. **ASE-compatible API surface.** `.calc` setter, `get_potential_energy()`, `get_forces()`, `get_stress()` follow the ASE conventions users expect.

---

## Priority Ranking

| Priority | Issue | Impact |
|----------|-------|--------|
| **P1** | `_neighbor_tree` mutates immutable object | Thread safety, model integrity |
| **P2** | Mutable `site_properties`/`pbc` | Breaks immutability contract |
| **P3** | `_cached_com` uses `hasattr` not `None` init | Inconsistency, minor perf |
| **P4** | `_positions` semantics differ per subclass | Future bug risk |
| **P5** | Stale `inplace` docstring | User confusion |
| **P6** | Duplicated mutation logic | Maintenance cost |
