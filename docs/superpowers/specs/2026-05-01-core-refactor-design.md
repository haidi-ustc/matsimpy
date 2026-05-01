# Core Immutability Refactor Design

## Goal

Make `matsimpy/core` structures fully immutable by default. All mutation methods return new objects. Eliminate freeze/thaw complexity, cache invalidation bugs, and fragile rollback patterns.

## Motivation: Current Bugs

1. **Dual-state cache management.** `_formula_dirty` and `_cached_formula` are separate flags. Some paths set one, some set the other. `Molecule.add_atom` rollback restores `_formula_dirty` but not `_cached_formula`.

2. **COM cache only invalidated in Molecule, not Structure base.** `Structure.add_atom` and `Structure.remove_atom` don't touch `_cached_com`. Subclasses bypassing setters with `_species`/`_positions` miss COM invalidation.

3. **Fragile rollback patterns.** `Crystal.add_atom` and `Molecule.add_atom` snapshot ~10 fields for rollback. Adding a new cached field requires remembering to update rollback in 2+ places.

4. **`_formula_dirty` not paired with `_cached_formula = None`.** `Structure.add_atom` sets `_formula_dirty = True` but not `_cached_formula = None`. Works via property check but direct access sees stale data.

5. **Freeze guard position matters.** `Molecule.add_atom` checks freeze before distance validation. Two-tier check (subclass + parent) is confusing but currently safe.

6. **Neighbor tree cache invalidation lives only in Crystal.** `Structure.positions` setter checks for `_neighbor_tree`, but base mutation methods don't. Potential for stale tree.

7. **Frozen positions getter creates garbage.** Every access creates a new read-only view. In tight loops this allocates repeatedly.

8. **Cross-class cache awareness.** Base `Structure` has `hasattr` checks for subclass caches (`_cached_com`, `_neighbor_tree`). Adding a new cached property to a subclass requires updating the base class.

## Principles

1. **Structures are immutable after construction.** No setters, no in-place mutation.
2. **All mutation methods return new objects.** `add_atom`, `remove_atom`, `substitute`, etc. create and return new instances.
3. **Caches computed once, never invalidated.** No dirty flags, no `None` resets.
4. **No freeze/thaw.** Immutability is structural, not a runtime toggle.
5. **Core depends on nothing above it.** Core never imports from transformation, io, calculator, etc.

## Structure Base Class

```python
class Structure(ABC, MSONable):
    """Abstract base for immutable atomic structures."""

    def __init__(self, species, positions, lattice=None):
        self._species = tuple(species_list)       # canonical tuple[str]
        self._positions = self._validate_positions(positions)  # Cartesian
        self.lattice = lattice
        self._formula = None                       # computed once
        self._composition = None                   # computed once

    @property
    def species(self) -> Tuple[str, ...]:
        return self._species

    @property
    def positions(self) -> np.ndarray:
        return self._positions  # no view() needed, immutable anyway

    @property
    def formula(self) -> str:
        if self._formula is None:
            self._formula = self._compute_formula()
        return self._formula

    @property
    def composition(self) -> Composition:
        if self._composition is None:
            self._composition = Composition(self.formula)
        return self._composition

    def add_atom(self, species, position) -> "Structure": ...
    def remove_atom(self, index) -> "Structure": ...
    def substitute(self, indices, new_species) -> "Structure": ...
    def substitute_all(self, old, new) -> "Structure": ...
    def sort_atoms(self, sort_by) -> "Structure": ...

    def copy(self) -> "Structure":
        return self.from_dict(self.as_dict())
```

No `_frozen`, no `_formula_dirty`, no `_check_frozen`, no species/positions setters.
Caches are `None`-or-computed, set once, read forever.

## Crystal Subclass

```python
class Crystal(Structure):
    def __init__(self, species, positions, lattice, pbc=None,
                 coords_are_cartesian=False, site_properties=None):
        # Convert to Cartesian if needed
        super().__init__(species, positions_cart, lattice)
        self._frac_positions = ...      # immutable
        self._sites = ...               # immutable
        self._pbc = tuple(pbc or (True, True, True))
        self._site_properties = tuple(site_properties or ())

    @property
    def frac_positions(self) -> np.ndarray:
        return self._frac_positions

    @property
    def cart_positions(self) -> np.ndarray:
        return self._positions  # alias — positions IS Cartesian

    # Methods returning new Crystal:
    def add_atom(self, species, position, ...) -> "Crystal": ...
    def remove_atom(self, index) -> "Crystal": ...
    def substitute(self, indices, new_species) -> "Crystal": ...
    def substitute_all(self, old, new) -> "Crystal": ...
    def sort_atoms(self, sort_by) -> "Crystal": ...
    def make_supercell(self, scaling_matrix) -> "Crystal": ...
    def perturb(self, amplitude, ...) -> "Crystal": ...
    def wrap(self) -> "Crystal": ...
```

Eliminated: `_update_coordinates_after_modification()`, `_invalidate_neighbor_tree()`,
rollback snapshots, freeze guards, `_neighbor_tree*` invalidation in mutation paths.

## Molecule Subclass

```python
class Molecule(Structure):
    def __init__(self, species, positions, site_properties=None):
        super().__init__(species, positions, None)
        self._sites = ...               # immutable
        self._com = None                # computed once
        self._site_properties = ...

    # Methods returning new Molecule:
    def add_atom(self, species, position, ...) -> "Molecule": ...
    def remove_atom(self, index) -> "Molecule": ...
    def substitute(self, indices, new_species) -> "Molecule": ...
    def substitute_all(self, old, new) -> "Molecule": ...
    def sort_atoms(self, sort_by) -> "Molecule": ...
    def perturb(self, amplitude, ...) -> "Molecule": ...
    def to_crystal(self, vacuum=15.0) -> Crystal: ...
    def translate(self, vector) -> "Molecule": ...
    def rotate(self, angle, axis) -> "Molecule": ...
```

Eliminated: `inplace` parameter on `translate`/`rotate`/`perturb`, rollback snapshots,
freeze guards, COM cache invalidation.

## What Gets Deleted

From `structure.py`:
- `FrozenStructureError` class
- `freeze()` / `unfreeze()` / `is_frozen` / `_check_frozen()`
- `species` setter / `positions` setter
- `_frozen` attribute, `_formula_dirty` attribute
- `_cached_formula` → replaced by `_formula`
- `_cached_composition` → replaced by `_composition`

From `molecule.py`:
- `inplace` parameter on `translate`, `rotate`, `perturb`
- Rollback logic in `add_atom`
- Freeze guards
- `_cached_com` invalidation in all mutation overrides

From `crystal.py`:
- `_update_coordinates_after_modification()`
- `_invalidate_neighbor_tree()`
- Rollback logic in `add_atom`
- Freeze guards
- `_neighbor_tree*` cache invalidation in mutation paths

From `tests/`:
- All `FrozenStructureError` tests in `test_mutability.py`
- All `freeze()` / `unfreeze()` / `is_frozen` assertions
- All `inplace=True` call sites

## What Stays Unchanged

- `lattice.py` — already effectively immutable
- `composition.py` — value object, no changes
- `periodic_table.py` — static reference data
- `site.py` — already value objects, no mutation methods
- `graph.py` — defer to separate effort
- I/O, calculator, symmetry, builders — out of scope for this change

## Error Handling

`FrozenStructureError` is deleted. No replacement needed — there are no mutating methods,
so there's nothing to guard. Construction-time validation (species/positions length,
invalid positions, mixed types) remains as-is.

## Testing Strategy

**New tests:**
1. `add_atom` / `remove_atom` / `substitute` / `substitute_all` / `sort_atoms` return new objects, originals unchanged
2. Crystal: `make_supercell`, `perturb`, `wrap` return new objects
3. Molecule: `perturb`, `to_crystal`, `translate`, `rotate` return new objects, no `inplace`
4. Formula/composition caches compute once, never change
5. Chained mutations: `s.add_atom(...).sort_atoms(...).substitute(...)`
6. Site objects and site properties preserved through mutations
7. Crystal coordinate conversions correct on returned objects

**Tests to delete/update:**
- `test_mutability.py` — all freeze/unfreeze/FrozenStructureError tests
- Any test calling `structure.freeze()` or asserting `FrozenStructureError`
- Any test using `inplace=True`
- Any test relying on in-place mutation — update to use returned objects
