# Core Immutability Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Structure/Crystal/Molecule fully immutable — all mutation methods return new objects, delete freeze/thaw, fix cache bugs.

**Architecture:** Remove species/positions setters and `_formula_dirty` flag from Structure ABC. Replace with compute-once caches. All mutation methods construct and return new instances. Subclasses (Crystal, Molecule) apply distance validation before constructing the new object, eliminating rollback patterns entirely.

**Tech Stack:** Python 3.x, NumPy, scipy, unittest

---

### Task 1: Rewrite mutability tests to immutability tests

**Files:**
- Delete: `tests/test_mutability.py`
- Create: `tests/test_immutability.py`

This is the TDD foundation. Write tests that assert the new immutable behavior before touching implementation code.

- [ ] **Step 1: Delete old mutability test file**

```bash
rm tests/test_mutability.py
```

- [ ] **Step 2: Create `tests/test_immutability.py` with failing tests**

```python
"""Tests for immutable Structure/Crystal/Molecule behavior.

All mutation methods must return new objects without modifying the original.
"""
import unittest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice


class TestImmutabilityCrystal(unittest.TestCase):
    """Crystal mutation methods return new objects, original unchanged."""

    def setUp(self):
        self.crystal = Crystal(
            ["Na", "Cl"],
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5.64),
        )

    def test_add_atom_returns_new_object(self):
        original_species = self.crystal.species
        original_len = len(self.crystal)
        result = self.crystal.add_atom("H", [0.1, 0.0, 0.0])
        self.assertIsNot(result, self.crystal)
        self.assertEqual(len(self.crystal), original_len)
        self.assertEqual(self.crystal.species, original_species)
        self.assertEqual(len(result), original_len + 1)
        self.assertIn("H", result.species)

    def test_remove_atom_returns_new_object(self):
        original_species = self.crystal.species
        original_len = len(self.crystal)
        result = self.crystal.remove_atom(0)
        self.assertIsNot(result, self.crystal)
        self.assertEqual(len(self.crystal), original_len)
        self.assertEqual(self.crystal.species, original_species)
        self.assertEqual(len(result), original_len - 1)

    def test_substitute_returns_new_object(self):
        original_species = self.crystal.species
        result = self.crystal.substitute(0, "K")
        self.assertIsNot(result, self.crystal)
        self.assertEqual(self.crystal.species, original_species)
        self.assertIn("K", result.species)
        self.assertNotIn("Na", result.species)

    def test_substitute_all_returns_new_object(self):
        original_species = self.crystal.species
        result = self.crystal.substitute_all("Na", "K")
        self.assertIsNot(result, self.crystal)
        self.assertEqual(self.crystal.species, original_species)
        self.assertIn("K", result.species)
        self.assertNotIn("Na", result.species)

    def test_sort_atoms_returns_new_object(self):
        original_species = self.crystal.species
        result = self.crystal.sort_atoms("alphabet")
        self.assertIsNot(result, self.crystal)
        self.assertEqual(self.crystal.species, original_species)

    def test_make_supercell_returns_new_object(self):
        original_len = len(self.crystal)
        result = self.crystal.make_supercell([2, 2, 2])
        self.assertIsNot(result, self.crystal)
        self.assertEqual(len(self.crystal), original_len)
        self.assertEqual(len(result), original_len * 8)

    def test_perturb_returns_new_object(self):
        original_positions = self.crystal.positions.copy()
        result = self.crystal.perturb(0.1, seed=42)
        self.assertIsNot(result, self.crystal)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))
        self.assertFalse(np.allclose(original_positions, result.positions))

    def test_wrap_returns_new_object(self):
        species = ["Fe", "O"]
        positions = [[1.5, 2.3, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        original_frac = crystal.frac_positions.copy()
        result = crystal.wrap()
        self.assertIsNot(result, crystal)
        self.assertTrue(np.allclose(crystal.frac_positions, original_frac))

    def test_chained_mutations(self):
        result = (
            self.crystal
            .add_atom("H", [0.1, 0.0, 0.0])
            .substitute(0, "K")
            .sort_atoms("element")
        )
        self.assertIsNot(result, self.crystal)
        self.assertEqual(len(result), 3)
        self.assertEqual(len(self.crystal), 2)


class TestImmutabilityMolecule(unittest.TestCase):
    """Molecule mutation methods return new objects, original unchanged."""

    def setUp(self):
        self.mol = Molecule(
            ["O", "H", "H"],
            [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]],
        )

    def test_add_atom_returns_new_object(self):
        original_len = len(self.mol)
        result = self.mol.add_atom("H", [2.0, 0.0, 0.0])
        self.assertIsNot(result, self.mol)
        self.assertEqual(len(self.mol), original_len)
        self.assertEqual(len(result), original_len + 1)

    def test_remove_atom_returns_new_object(self):
        original_len = len(self.mol)
        result = self.mol.remove_atom(0)
        self.assertIsNot(result, self.mol)
        self.assertEqual(len(self.mol), original_len)
        self.assertEqual(len(result), original_len - 1)

    def test_substitute_returns_new_object(self):
        original_species = self.mol.species
        result = self.mol.substitute(0, "N")
        self.assertIsNot(result, self.mol)
        self.assertEqual(self.mol.species, original_species)
        self.assertEqual(result.species[0], "N")

    def test_translate_returns_new_object(self):
        original_positions = self.mol.positions.copy()
        result = self.mol.translate([1.0, 0.0, 0.0])
        self.assertIsNot(result, self.mol)
        self.assertTrue(np.allclose(self.mol.positions, original_positions))
        self.assertTrue(np.allclose(result.positions, original_positions + [1.0, 0.0, 0.0]))

    def test_rotate_returns_new_object(self):
        original_positions = self.mol.positions.copy()
        result = self.mol.rotate(90, [0, 0, 1])
        self.assertIsNot(result, self.mol)
        self.assertTrue(np.allclose(self.mol.positions, original_positions))
        self.assertFalse(np.allclose(original_positions, result.positions))

    def test_perturb_returns_new_object(self):
        original_positions = self.mol.positions.copy()
        result = self.mol.perturb(0.1, seed=42)
        self.assertIsNot(result, self.mol)
        self.assertTrue(np.allclose(self.mol.positions, original_positions))

    def test_to_crystal_returns_new_crystal(self):
        result = self.mol.to_crystal()
        self.assertIsInstance(result, Crystal)
        self.assertIsNot(result, self.mol)
        self.assertEqual(len(result), 3)

    def test_chained_mutations(self):
        result = (
            self.mol
            .add_atom("C", [1.5, 0.0, 0.0])
            .translate([1.0, 0.0, 0.0])
            .substitute(0, "N")
        )
        self.assertIsNot(result, self.mol)
        self.assertEqual(len(result), 4)
        self.assertEqual(len(self.mol), 3)


class TestImmutabilityCache(unittest.TestCase):
    """Caches are computed once and never invalidated."""

    def test_formula_cache_never_changes(self):
        crystal = Crystal(
            ["Na", "Cl"],
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5.64),
        )
        formula1 = crystal.formula
        # Even after getting a mutated copy, original formula is unchanged
        _ = crystal.add_atom("H", [0.1, 0.0, 0.0])
        formula2 = crystal.formula
        self.assertEqual(formula1, formula2)

    def test_composition_cache_never_changes(self):
        crystal = Crystal(
            ["Na", "Cl"],
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5.64),
        )
        comp1 = crystal.composition
        _ = crystal.add_atom("H", [0.1, 0.0, 0.0])
        comp2 = crystal.composition
        self.assertIs(comp1, comp2)


class TestNoFreezeMechanism(unittest.TestCase):
    """Freeze/unfreeze/FrozenStructureError no longer exist."""

    def test_no_frozen_structure_error(self):
        with self.assertRaises(ImportError):
            from matsimpy.core.structure import FrozenStructureError

    def test_no_freeze_method(self):
        crystal = Crystal(
            ["Na", "Cl"],
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5.64),
        )
        self.assertFalse(hasattr(crystal, "freeze"))
        self.assertFalse(hasattr(crystal, "unfreeze"))
        self.assertFalse(hasattr(crystal, "is_frozen"))


class TestNoPositionsSetter(unittest.TestCase):
    """positions property is read-only."""

    def test_positions_setter_raises_attribute_error(self):
        crystal = Crystal(
            ["Na", "Cl"],
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5.64),
        )
        with self.assertRaises(AttributeError):
            crystal.positions = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]


class TestNoSpeciesSetter(unittest.TestCase):
    """species property is read-only."""

    def test_species_setter_raises_attribute_error(self):
        crystal = Crystal(
            ["Na", "Cl"],
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5.64),
        )
        with self.assertRaises(AttributeError):
            crystal.species = ["K", "Br"]


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run new tests — expect ALL failures**

```bash
python -m pytest tests/test_immutability.py -v
```

Expected: Every test FAILS. `add_atom` modifies in-place, `freeze`/`unfreeze` exist, `FrozenStructureError` is importable, setters work.

- [ ] **Step 4: Commit the failing test suite**

```bash
git add tests/test_immutability.py tests/test_mutability.py
git commit -m "test: add immutability TDD test suite, remove old mutability tests"
```

---

### Task 2: Refactor Structure base class

**Files:**
- Modify: `matsimpy/core/structure.py`

Replace the freeze/setter/dirty-flag architecture with compute-once caches and immutable-return mutation methods.

- [ ] **Step 1: Remove `FrozenStructureError` class**

Delete lines 47-48:
```python
class FrozenStructureError(RuntimeError):
    """Raised when a frozen structure is mutated."""
    pass
```

- [ ] **Step 2: Replace `__init__` cache fields**

Replace lines 188-194:
```python
        # Frozen state flag (Wave 1: initialization should not freeze)
        self._frozen = False

        # Add cache attributes
        self._cached_composition: Optional[Composition] = None
        self._cached_formula: Optional[str] = None
        self._formula_dirty = True
```

With:
```python
        # Compute-once caches (never invalidated — structure is immutable)
        self._composition: Optional[Composition] = None
        self._formula: Optional[str] = None
```

- [ ] **Step 3: Delete freeze/unfreeze methods**

Delete lines 196-213 (the entire block containing `freeze()`, `unfreeze()`, `is_frozen`, `_check_frozen`):
```python
    # Wave 1: freezing functionality
    def freeze(self) -> None:
        """Make structure immutable. Raises FrozenStructureError on subsequent mutation attempts."""
        self._frozen = True

    def unfreeze(self) -> None:
        """Allow mutations again."""
        self._frozen = False

    @property
    def is_frozen(self) -> bool:
        """Check if the structure is currently frozen."""
        return getattr(self, '_frozen', False)

    def _check_frozen(self) -> None:
        """Raise FrozenStructureError if the structure is frozen."""
        if getattr(self, '_frozen', False):
            raise FrozenStructureError("Structure is frozen. Call unfreeze() to allow modifications.")
```

- [ ] **Step 4: Delete `species` setter**

Replace the `species` property (lines 215-250) with read-only version:
```python
    @property
    def species(self) -> Tuple[str, ...]:
        """Get the species as a tuple of strings."""
        return self._species
```

(Keep the getter, delete the setter entirely.)

- [ ] **Step 5: Replace `positions` property — remove freeze guard and setter**

Replace the `positions` getter (lines 332-357):
```python
    @property
    def positions(self) -> np.ndarray:
        """
        Get atomic positions as numpy array.

        Returns:
            np.ndarray: Array of positions with shape (n_atoms, 3).
        """
        return self._positions
```

Delete the `positions` setter (lines 359-405) entirely.

- [ ] **Step 6: Update `formula` property to compute-once pattern**

Replace lines 484-525:
```python
    @property
    def formula(self) -> str:
        if self._formula is None:
            self._formula = self._compute_formula()
        return self._formula

    def _compute_formula(self) -> str:
        element_counter = Counter(self.species)
        seen = set()
        formula = ""
        for element in self.species:
            if element not in seen:
                count = element_counter[element]
                formula += element + (str(count) if count > 1 else "")
                seen.add(element)
        return formula
```

- [ ] **Step 7: Update `composition` property to compute-once pattern**

Replace lines 684-719:
```python
    @property
    def composition(self) -> Composition:
        if self._composition is None:
            self._composition = Composition(self.formula)
        return self._composition
```

- [ ] **Step 8: Rewrite `add_atom` to return new instance**

Replace the entire `add_atom` method (lines 742-827) with:
```python
    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
    ) -> "Structure":
        # Handle single atom case
        if isinstance(species, str):
            species = [species]
            position = [position]

        if len(species) != len(position):
            raise ValueError(
                f"Number of species ({len(species)}) must match "
                f"number of positions ({len(position)})"
            )

        if not species:
            return self.copy()

        positions_array = np.array(position, dtype=np.float64)
        if positions_array.ndim == 1:
            if len(positions_array) != 3:
                raise ValueError("Position must be a 3D coordinate")
            positions_array = positions_array.reshape(1, 3)
        elif positions_array.ndim == 2:
            if positions_array.shape[1] != 3:
                raise ValueError("Positions must be 3D coordinates")
        else:
            raise ValueError(
                "Position must be a 3D coordinate or list of 3D coordinates"
            )

        new_species = list(self.species)
        new_species.extend(species)
        new_positions = np.vstack([self._positions, positions_array])

        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": new_species,
            "positions": new_positions.tolist(),
            **self._extra_dict_fields(),
        })
```

Add a helper `_extra_dict_fields` that subclasses override:
```python
    def _extra_dict_fields(self) -> Dict[str, Any]:
        """Return extra fields for from_dict reconstruction. Override in subclasses."""
        return {}
```

- [ ] **Step 9: Rewrite `remove_atom` to return new instance**

Replace the entire `remove_atom` method (lines 829-871) with:
```python
    def remove_atom(self, index: int) -> "Structure":
        if not (0 <= index < len(self.species)):
            raise IndexError("Invalid atom index.")

        species_list = list(self.species)
        species_list.pop(index)
        new_positions = np.delete(self._positions, index, axis=0)

        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": species_list,
            "positions": new_positions.tolist(),
            **self._extra_dict_fields(),
        })
```

- [ ] **Step 10: Rewrite `substitute` to return new instance**

Replace the `substitute` method (lines 874-949) with:
```python
    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> "Structure":
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        if isinstance(indices, int):
            indices = [indices]

        if isinstance(new_species, dict):
            new_species_list = []
            for idx in indices:
                old_spec = self.species[idx]
                if old_spec not in new_species:
                    raise KeyError(
                        f"Species '{old_spec}' at index {idx} "
                        f"not found in substitution mapping"
                    )
                new_species_list.append(new_species[old_spec])
            new_species = new_species_list

        if isinstance(new_species, str):
            new_species = [new_species] * len(indices)

        if len(indices) != len(new_species):
            raise ValueError(
                f"Number of indices ({len(indices)}) must match "
                f"number of new species ({len(new_species)})"
            )

        species_list = list(self.species)
        for idx, new_spec in zip(indices, new_species):
            species_list[idx] = new_spec

        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": species_list,
            "positions": self._positions.tolist(),
            **self._extra_dict_fields(),
        })
```

- [ ] **Step 11: Rewrite `substitute_all` to return new instance**

Replace the `substitute_all` method (lines 951-976) with:
```python
    def substitute_all(self, old_species: str, new_species: str) -> "Structure":
        species_list = [
            new_species if s == old_species else s for s in self.species
        ]
        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": species_list,
            "positions": self._positions.tolist(),
            **self._extra_dict_fields(),
        })
```

- [ ] **Step 12: Rewrite `sort_atoms` to return new instance**

Replace the `sort_atoms` method (lines 978-1052) with:
```python
    def sort_atoms(self, sort_by: str = "element") -> "Structure":
        atoms = list(zip(range(len(self.species)), self.species, self._positions))

        if sort_by == "element":
            elements = self.elements
            sorted_atoms = sorted(
                atoms,
                key=lambda a: (
                    elements[a[0]].atomic_no,
                    a[2][0], a[2][1], a[2][2],
                ),
            )
        elif sort_by == "alphabet":
            sorted_atoms = sorted(
                atoms, key=lambda a: (a[1], a[2][0], a[2][1], a[2][2])
            )
        else:
            raise ValueError("sort_by must be 'element' or 'alphabet'")

        sorted_species = [a[1] for a in sorted_atoms]
        sorted_positions = np.array([a[2] for a in sorted_atoms])

        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": sorted_species,
            "positions": sorted_positions.tolist(),
            **self._extra_dict_fields(),
        })
```

- [ ] **Step 13: Run immutability tests for Structure**

```bash
python -m pytest tests/test_immutability.py -v -k "Crystal"
```

Expected: Crystal tests should start passing. `TestNoFreezeMechanism` and `TestNoSpeciesSetter`/`TestNoPositionsSetter` should pass.

- [ ] **Step 14: Commit**

```bash
git add matsimpy/core/structure.py
git commit -m "refactor(core): make Structure immutable — remove freeze, setters, dirty flags"
```

---

### Task 3: Refactor Crystal subclass

**Files:**
- Modify: `matsimpy/core/crystal.py`

- [ ] **Step 1: Update `__init__` to not store neighbor tree cache fields**

Keep the neighbor tree fields (they're for parameterized caching, not mutation invalidation — they cache per-cutoff which is fine for immutable structures).

No change needed to `__init__` — the `_neighbor_tree*` fields are for cutoff-based caching, not mutation-based invalidation. Just remove any `_check_frozen()` calls.

- [ ] **Step 2: Delete `_invalidate_neighbor_tree` method**

Delete lines 218-228:
```python
    def _invalidate_neighbor_tree(self) -> None:
        """
        Invalidate neighbor tree cache.

        Called when structure changes (add/remove atoms, substitute, etc.).
        """
        self._neighbor_tree = None
        self._neighbor_tree_positions = None
        self._neighbor_tree_cutoff = None
        self._neighbor_tree_use_pbc = None
        self._neighbor_tree_pbc = None
```

- [ ] **Step 3: Delete `_update_coordinates_after_modification` method**

Delete lines 265-272:
```python
    def _update_coordinates_after_modification(self) -> None:
        """
        Update fractional and Cartesian coordinates after modification.

        Ensures consistency between frac_positions and cart_positions.
        """
        self.frac_positions = self.positions
        self.cart_positions = self._convert_to_cartesian()
```

- [ ] **Step 4: Override `_extra_dict_fields` in Crystal**

Add to Crystal class:
```python
    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "lattice": self.lattice.as_dict(),
            "pbc": list(self.pbc),
            "site_properties": list(self.site_properties) if self.site_properties else [],
        }
```

- [ ] **Step 5: Rewrite `add_atom` to return new Crystal**

Replace the entire `add_atom` method (lines 351-656) with a version that validates distances then constructs and returns a new Crystal:
```python
    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
        site_properties: Optional[Union[dict, List[dict]]] = None,
        coords_are_cartesian: bool = False,
    ) -> "Crystal":
        # Parse and normalize position input
        if isinstance(position, list):
            if len(position) == 0:
                new_positions = []
            elif isinstance(position[0], (int, float)):
                new_positions = [position]
            else:
                new_positions = position
        else:
            new_positions = [position]

        # Convert to fractional coordinates if needed
        if new_positions:
            new_pos_array = np.array(new_positions, dtype=np.float64)
            if coords_are_cartesian:
                new_frac_positions = np.dot(new_pos_array, self.lattice.inv_matrix)
                new_cart_positions = new_pos_array
            else:
                new_frac_positions = new_pos_array
                new_cart_positions = np.dot(new_frac_positions, self.lattice.matrix)
        else:
            new_frac_positions = np.array([]).reshape(0, 3)
            new_cart_positions = np.array([]).reshape(0, 3)

        # Check for duplicates within new positions
        if len(new_cart_positions) > 1:
            distances_condensed = pdist(new_cart_positions)
            if np.any(distances_condensed < 1e-6):
                distances_square = squareform(distances_condensed)
                np.fill_diagonal(distances_square, np.inf)
                i, j = np.where(distances_square < 1e-6)
                pos_list = (new_frac_positions.tolist()
                    if isinstance(new_frac_positions, np.ndarray)
                    else new_frac_positions)
                raise ValueError(
                    f"Duplicate positions detected in new atoms: "
                    f"positions {i[0]} and {j[0]} are at the same location "
                    f"({pos_list[i[0]]})."
                )
            if np.any(distances_condensed < 0.5):
                min_dist = np.min(distances_condensed)
                distances_square = squareform(distances_condensed)
                np.fill_diagonal(distances_square, np.inf)
                i, j = np.where(np.abs(distances_square - min_dist) < 1e-10)
                pos_list = (new_frac_positions.tolist()
                    if isinstance(new_frac_positions, np.ndarray)
                    else new_frac_positions)
                raise ValueError(
                    f"Atoms being added are too close: distance between "
                    f"positions {i[0]} and {j[0]} is {min_dist:.6f} Angstrom. "
                    f"Minimum allowed distance is 0.5 Angstrom."
                )

        # Check each new position against existing atoms (with PBC)
        if len(self.frac_positions) > 0 and len(new_cart_positions) > 0:
            existing_cart = self.cart_positions
            if not any(self.pbc):
                distances = cdist(new_cart_positions, existing_cart)
                min_distances = np.min(distances, axis=1)
                for idx, min_dist in enumerate(min_distances):
                    pos_repr = (new_frac_positions[idx].tolist()
                        if isinstance(new_frac_positions[idx], np.ndarray)
                        else new_frac_positions[idx])
                    if min_dist < 1e-6:
                        raise ValueError(
                            f"Cannot add atom at position {pos_repr}: "
                            f"atom already exists at this location "
                            f"(distance: {min_dist:.6f} Angstrom)."
                        )
                    elif min_dist < 0.5:
                        raise ValueError(
                            f"Cannot add atom at position {pos_repr}: "
                            f"too close to existing atom "
                            f"(distance: {min_dist:.6f} Angstrom)."
                        )
            else:
                new_frac_array = np.array(new_frac_positions)
                existing_frac_array = np.array(self.frac_positions)
                frac_diffs = (
                    new_frac_array[:, np.newaxis, :]
                    - existing_frac_array[np.newaxis, :, :]
                )
                pbc_mask = np.array(self.pbc, dtype=bool)
                if np.any(pbc_mask):
                    frac_diffs[:, :, pbc_mask] = (
                        frac_diffs[:, :, pbc_mask]
                        - np.round(frac_diffs[:, :, pbc_mask])
                    )
                cart_diffs = np.dot(frac_diffs, self.lattice.matrix)
                distances = np.linalg.norm(cart_diffs, axis=2)
                min_distances = np.min(distances, axis=1)
                for idx, min_dist in enumerate(min_distances):
                    pos_repr = (new_frac_positions[idx].tolist()
                        if isinstance(new_frac_positions[idx], np.ndarray)
                        else new_frac_positions[idx])
                    if min_dist < 1e-6:
                        raise ValueError(
                            f"Cannot add atom at position {pos_repr}: "
                            f"atom already exists at this location "
                            f"(distance: {min_dist:.6f} Angstrom)."
                        )
                    elif min_dist < 0.5:
                        raise ValueError(
                            f"Cannot add atom at position {pos_repr}: "
                            f"too close to existing atom "
                            f"(distance: {min_dist:.6f} Angstrom)."
                        )

        # Build new species/positions
        if isinstance(species, str):
            species_list = [species]
        else:
            species_list = list(species)

        new_species = list(self.species) + species_list
        if new_frac_positions.size > 0:
            if new_frac_positions.ndim == 1:
                new_frac_positions = new_frac_positions.reshape(1, 3)
            new_frac = np.vstack([self.frac_positions, new_frac_positions])
        else:
            new_frac = self.frac_positions.copy()

        n_atoms_before = len(self.species)
        n_atoms_added = len(new_species) - n_atoms_before

        # Handle site_properties
        new_site_props = list(self.site_properties) if self.site_properties else []
        if site_properties is not None:
            if isinstance(site_properties, dict):
                site_properties_list = [site_properties] * n_atoms_added
            else:
                site_properties_list = list(site_properties)
            if len(site_properties_list) != n_atoms_added:
                raise ValueError(
                    f"Number of site_properties ({len(site_properties_list)}) "
                    f"must match number of atoms added ({n_atoms_added})"
                )
            if not new_site_props:
                new_site_props = [{}] * n_atoms_before
            new_site_props.extend(site_properties_list)
        elif new_site_props:
            new_site_props.extend([{}] * n_atoms_added)

        return Crystal(
            new_species,
            new_frac.tolist(),
            self.lattice,
            pbc=list(self.pbc),
            coords_are_cartesian=False,
            site_properties=new_site_props if new_site_props else None,
        )
```

- [ ] **Step 6: Rewrite `remove_atom` to return new Crystal**

Replace the `remove_atom` method (lines 658-718) with:
```python
    def remove_atom(self, indices: Union[int, List[int], "AtomSelection"]) -> "Crystal":
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        if isinstance(indices, int):
            indices = [indices]
        elif not isinstance(indices, list):
            raise TypeError(
                f"indices must be int, list of int, or AtomSelection, "
                f"got {type(indices)}"
            )

        n_atoms = len(self.species)
        for idx in indices:
            if not (0 <= idx < n_atoms):
                raise IndexError(
                    f"Atom index {idx} is out of range [0, {n_atoms - 1}]"
                )

        indices_to_remove = sorted(set(indices), reverse=True)

        species_list = list(self.species)
        new_frac = self.frac_positions.copy()
        new_site_props = (
            list(self.site_properties) if self.site_properties else []
        )

        for idx in indices_to_remove:
            species_list.pop(idx)
            new_frac = np.delete(new_frac, idx, axis=0)
            if new_site_props and len(new_site_props) > idx:
                new_site_props.pop(idx)

        return Crystal(
            species_list,
            new_frac.tolist(),
            self.lattice,
            pbc=list(self.pbc),
            coords_are_cartesian=False,
            site_properties=new_site_props if new_site_props else None,
        )
```

- [ ] **Step 7: Rewrite `substitute` to return new Crystal**

Replace the `substitute` method (lines 720-757) with:
```python
    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> "Crystal":
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        if isinstance(indices, int):
            indices = [indices]

        if isinstance(new_species, dict):
            new_species_list = []
            for idx in indices:
                old_spec = self.species[idx]
                if old_spec not in new_species:
                    raise KeyError(
                        f"Species '{old_spec}' at index {idx} "
                        f"not found in substitution mapping"
                    )
                new_species_list.append(new_species[old_spec])
            new_species = new_species_list

        if isinstance(new_species, str):
            new_species = [new_species] * len(indices)

        if len(indices) != len(new_species):
            raise ValueError(
                f"Number of indices ({len(indices)}) must match "
                f"number of new species ({len(new_species)})"
            )

        species_list = list(self.species)
        for idx, new_spec in zip(indices, new_species):
            species_list[idx] = new_spec

        return Crystal(
            species_list,
            self.frac_positions.tolist(),
            self.lattice,
            pbc=list(self.pbc),
            coords_are_cartesian=False,
            site_properties=(
                list(self.site_properties) if self.site_properties else None
            ),
        )
```

- [ ] **Step 8: Rewrite `sort_atoms` to return new Crystal**

Replace the `sort_atoms` override (lines 1129-1152) with:
```python
    def sort_atoms(self, sort_by: str = "element") -> "Crystal":
        atoms = list(zip(
            range(len(self.species)), self.species, self.frac_positions
        ))

        if sort_by == "element":
            elements = self.elements
            sorted_atoms = sorted(
                atoms,
                key=lambda a: (
                    elements[a[0]].atomic_no,
                    a[2][0], a[2][1], a[2][2],
                ),
            )
        elif sort_by == "alphabet":
            sorted_atoms = sorted(
                atoms, key=lambda a: (a[1], a[2][0], a[2][1], a[2][2])
            )
        else:
            raise ValueError("sort_by must be 'element' or 'alphabet'")

        sorted_species = [a[1] for a in sorted_atoms]
        sorted_frac = np.array([a[2] for a in sorted_atoms])
        sorted_indices = [a[0] for a in sorted_atoms]

        new_site_props = None
        if self.site_properties:
            new_site_props = [self.site_properties[i] for i in sorted_indices]

        return Crystal(
            sorted_species,
            sorted_frac.tolist(),
            self.lattice,
            pbc=list(self.pbc),
            coords_are_cartesian=False,
            site_properties=new_site_props,
        )
```

- [ ] **Step 9: Update `wrap` to return new Crystal**

Replace the `wrap` method (lines 1186-1222) with:
```python
    def wrap(self) -> "Crystal":
        new_frac = self.frac_positions % 1.0
        return Crystal(
            list(self.species),
            new_frac.tolist(),
            self.lattice,
            pbc=list(self.pbc),
            coords_are_cartesian=False,
            site_properties=(
                list(self.site_properties) if self.site_properties else None
            ),
        )
```

- [ ] **Step 10: Update `make_supercell` to remove `inplace`**

Replace the `make_supercell` method (lines 1933-1991) with:
```python
    def make_supercell(
        self,
        scaling_matrix: Union[List[int], List[List[int]], np.ndarray],
    ) -> "Crystal":
        from ..transformation.structural import make_supercell

        return make_supercell(self, scaling_matrix)
```

- [ ] **Step 11: Update `perturb` to remove `inplace`**

Replace the `perturb` method (lines 1993-2104) with:
```python
    def perturb(
        self,
        amplitude: float,
        indices: Optional[Union[List[int], "AtomSelection"]] = None,
        seed: Optional[int] = None,
        perturb_positions: bool = True,
        perturb_lattice: bool = False,
        amplitude_lattice: Optional[float] = None,
    ) -> "Crystal":
        if not perturb_positions and not perturb_lattice:
            raise ValueError(
                "At least one of perturb_positions or perturb_lattice must be True"
            )

        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        result = self

        if perturb_positions:
            from ..transformation.atomic import perturb_positions
            result = perturb_positions(result, amplitude, indices=indices, seed=seed)

        if perturb_lattice:
            from ..transformation.lattice import perturb_lattice
            lattice_amp = (
                amplitude_lattice if amplitude_lattice is not None else amplitude
            )
            result = perturb_lattice(result, lattice_amp, seed=seed)

        return result
```

- [ ] **Step 12: Run Crystal immutability tests**

```bash
python -m pytest tests/test_immutability.py -v -k "Crystal"
```

Expected: All Crystal tests pass.

- [ ] **Step 13: Commit**

```bash
git add matsimpy/core/crystal.py
git commit -m "refactor(core): make Crystal immutable — remove inplace, rollback, freeze guards"
```

---

### Task 4: Refactor Molecule subclass

**Files:**
- Modify: `matsimpy/core/molecule.py`

- [ ] **Step 1: Update `__init__` to use compute-once COM cache**

The `_cached_com` field stays as `None` (computed once, never invalidated). Remove any reference to `_check_frozen`.

No change to `__init__` needed — the COM cache pattern is already compute-once.

- [ ] **Step 2: Override `_extra_dict_fields` in Molecule**

Add to Molecule class:
```python
    def _extra_dict_fields(self) -> Dict[str, Any]:
        if self.site_properties:
            return {"site_properties": list(self.site_properties)}
        return {}
```

- [ ] **Step 3: Rewrite `add_atom` to return new Molecule**

Replace the entire `add_atom` method (lines 346-493) with:
```python
    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
        site_properties: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    ) -> "Molecule":
        # Parse position input
        if isinstance(position, list):
            if len(position) == 0:
                new_positions = []
            elif isinstance(position[0], (int, float)):
                new_positions = [position]
            else:
                new_positions = position
        else:
            new_positions = [position]

        # Check for duplicates within new positions
        if len(new_positions) > 1:
            new_positions_array = np.array(new_positions, dtype=np.float64)
            for i in range(len(new_positions_array)):
                for j in range(i + 1, len(new_positions_array)):
                    dist = np.linalg.norm(
                        new_positions_array[i] - new_positions_array[j]
                    )
                    if dist < 1e-6:
                        raise ValueError(
                            f"Duplicate positions detected in new atoms: "
                            f"positions {i} and {j} are at the same location "
                            f"({new_positions[i]})."
                        )
                    elif dist < 0.5:
                        raise ValueError(
                            f"Atoms being added are too close: distance between "
                            f"positions {i} and {j} is {dist:.6f} Angstrom. "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )

        # Check each new position against existing atoms
        if len(self.positions) > 0:
            for idx, new_pos in enumerate(new_positions):
                if len(new_pos) == 3:
                    new_pos_array = np.array(new_pos, dtype=np.float64).reshape(1, 3)
                    min_distance = np.min(cdist(new_pos_array, self.positions))
                    if min_distance < 1e-6:
                        raise ValueError(
                            f"Cannot add atom at position {new_pos}: "
                            f"atom already exists at this location "
                            f"(distance: {min_distance:.6f} Angstrom)."
                        )
                    elif min_distance < 0.5:
                        raise ValueError(
                            f"Cannot add atom at position {new_pos}: "
                            f"too close to existing atom "
                            f"(distance: {min_distance:.6f} Angstrom)."
                        )

        # Normalize species
        if isinstance(species, str):
            species_list = [species]
        else:
            species_list = list(species)

        if not species_list:
            return self.copy()

        new_species = list(self.species) + species_list
        new_positions_arr = (
            np.vstack([self.positions, np.array(new_positions, dtype=np.float64)])
            if new_positions
            else self.positions.copy()
        )

        n_atoms_before = len(self.species)
        n_atoms_added = len(new_species) - n_atoms_before

        # Handle site_properties
        new_site_props = (
            list(self.site_properties) if self.site_properties else []
        )
        if site_properties is not None:
            if isinstance(site_properties, dict):
                site_properties_list = [site_properties] * n_atoms_added
            else:
                site_properties_list = list(site_properties)
            if len(site_properties_list) != n_atoms_added:
                raise ValueError(
                    f"Number of site_properties ({len(site_properties_list)}) "
                    f"must match number of atoms added ({n_atoms_added})"
                )
            if not new_site_props:
                new_site_props = [{}] * n_atoms_before
            new_site_props.extend(site_properties_list)
        elif new_site_props:
            new_site_props.extend([{}] * n_atoms_added)

        return Molecule(
            new_species,
            new_positions_arr.tolist(),
            site_properties=new_site_props if new_site_props else None,
        )
```

- [ ] **Step 4: Rewrite `remove_atom` to return new Molecule**

Replace the `remove_atom` method (lines 495-569) with:
```python
    def remove_atom(
        self, indices: Union[int, List[int], "AtomSelection"]
    ) -> "Molecule":
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        if isinstance(indices, int):
            indices = [indices]
        elif not isinstance(indices, list):
            raise TypeError(
                f"indices must be int, list of int, or AtomSelection, "
                f"got {type(indices)}"
            )

        n_atoms = len(self.species)
        for idx in indices:
            if not (0 <= idx < n_atoms):
                raise IndexError(
                    f"Atom index {idx} is out of range [0, {n_atoms - 1}]"
                )

        indices_to_remove = sorted(set(indices), reverse=True)

        species_list = list(self.species)
        new_positions = self.positions.copy()
        new_site_props = (
            list(self.site_properties) if self.site_properties else []
        )

        for idx in indices_to_remove:
            species_list.pop(idx)
            new_positions = np.delete(new_positions, idx, axis=0)
            if new_site_props and len(new_site_props) > idx:
                new_site_props.pop(idx)

        return Molecule(
            species_list,
            new_positions.tolist(),
            site_properties=new_site_props if new_site_props else None,
        )
```

- [ ] **Step 5: Rewrite `translate` to remove `inplace`**

Replace the `translate` method (lines 244-289) with:
```python
    def translate(self, vector: List[float]) -> "Molecule":
        new_positions = self.positions + np.array(vector)
        return Molecule(
            list(self.species),
            new_positions.tolist(),
            site_properties=(
                list(self.site_properties) if self.site_properties else None
            ),
        )
```

- [ ] **Step 6: Rewrite `rotate` to remove `inplace`**

Replace the `rotate` method (lines 291-344) with:
```python
    def rotate(self, angle: float, axis: List[float]) -> "Molecule":
        from scipy.spatial.transform import Rotation

        rotation = Rotation.from_rotvec(np.radians(angle) * np.array(axis))
        new_positions = rotation.apply(self.positions)
        return Molecule(
            list(self.species),
            new_positions.tolist(),
            site_properties=(
                list(self.site_properties) if self.site_properties else None
            ),
        )
```

- [ ] **Step 7: Update `perturb` to remove `inplace`**

Replace the `perturb` method (lines 1310-1366) with:
```python
    def perturb(
        self,
        amplitude: float,
        indices: Optional[Union[List[int], "AtomSelection"]] = None,
        seed: Optional[int] = None,
    ) -> "Molecule":
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        from ..transformation.atomic import perturb_positions

        return perturb_positions(self, amplitude, indices=indices, seed=seed)
```

- [ ] **Step 8: Update `substitute` override — remove site reinitialization**

Replace the `substitute` override (lines 571-608) with:
```python
    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> "Molecule":
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        if isinstance(indices, int):
            indices = [indices]

        if isinstance(new_species, dict):
            new_species_list = []
            for idx in indices:
                old_spec = self.species[idx]
                if old_spec not in new_species:
                    raise KeyError(
                        f"Species '{old_spec}' at index {idx} "
                        f"not found in substitution mapping"
                    )
                new_species_list.append(new_species[old_spec])
            new_species = new_species_list

        if isinstance(new_species, str):
            new_species = [new_species] * len(indices)

        if len(indices) != len(new_species):
            raise ValueError(
                f"Number of indices ({len(indices)}) must match "
                f"number of new species ({len(new_species)})"
            )

        species_list = list(self.species)
        for idx, new_spec in zip(indices, new_species):
            species_list[idx] = new_spec

        return Molecule(
            species_list,
            self.positions.tolist(),
            site_properties=(
                list(self.site_properties) if self.site_properties else None
            ),
        )
```

- [ ] **Step 9: Run Molecule immutability tests**

```bash
python -m pytest tests/test_immutability.py -v -k "Molecule"
```

Expected: All Molecule tests pass.

- [ ] **Step 10: Commit**

```bash
git add matsimpy/core/molecule.py
git commit -m "refactor(core): make Molecule immutable — remove inplace, rollback, freeze guards"
```

---

### Task 5: Update Crystal convenience method tests

**Files:**
- Modify: `tests/test_crystal_convenience_methods.py`

All `inplace=True` tests must be rewritten. `inplace=False` tests stay (they already check non-modification).

- [ ] **Step 1: Rewrite `test_make_supercell_inplace`**

Replace with:
```python
    def test_make_supercell_returns_new(self):
        """Test make_supercell returns new object, original unchanged."""
        original_len = len(self.crystal)
        original_lattice_a = self.crystal.lattice.a

        result = self.crystal.make_supercell([2, 2, 2])

        # Original unchanged
        self.assertEqual(len(self.crystal), original_len)
        self.assertAlmostEqual(self.crystal.lattice.a, original_lattice_a, places=5)

        # Result is new object with correct supercell
        self.assertIsNot(result, self.crystal)
        self.assertEqual(len(result), original_len * 8)
        self.assertAlmostEqual(result.lattice.a, original_lattice_a * 2, places=5)
```

- [ ] **Step 2: Delete `test_make_supercell_matrix` (was inplace-only)**

The test `test_make_supercell_matrix` at line 49-57 uses `inplace=True` and checks `self.crystal` was modified. Delete it or rewrite it to not use `inplace`:
```python
    def test_make_supercell_matrix(self):
        """Test make_supercell with matrix scaling."""
        original_len = len(self.crystal)

        scaling_matrix = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
        result = self.crystal.make_supercell(scaling_matrix)

        self.assertEqual(len(result), original_len * 8)
        self.assertEqual(len(self.crystal), original_len)
```

- [ ] **Step 3: Rewrite `test_perturb_inplace`**

Replace with:
```python
    def test_perturb_returns_new(self):
        """Test perturb returns new object, original unchanged."""
        original_positions = self.crystal.positions.copy()

        result = self.crystal.perturb(0.1, seed=42)

        self.assertIsNot(result, self.crystal)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))
        self.assertFalse(np.allclose(original_positions, result.positions))
```

- [ ] **Step 4: Rewrite `test_perturb_specific_indices`**

Replace with:
```python
    def test_perturb_specific_indices(self):
        """Test perturb with specific atom indices returns new object."""
        original_positions = self.crystal.positions.copy()

        result = self.crystal.perturb(0.1, indices=[0], seed=42)

        self.assertIsNot(result, self.crystal)
        self.assertTrue(np.allclose(self.crystal.positions, original_positions))
        self.assertFalse(np.allclose(original_positions[0], result.positions[0]))
        self.assertTrue(np.allclose(original_positions[1:], result.positions[1:]))
```

- [ ] **Step 5: Rewrite `test_perturb_reproducibility`**

Replace with:
```python
    def test_perturb_reproducibility(self):
        """Test that perturb is reproducible with same seed."""
        crystal1 = from_prototype('diamond', 'Si', 5.43)
        crystal2 = from_prototype('diamond', 'Si', 5.43)

        result1 = crystal1.perturb(0.1, seed=42)
        result2 = crystal2.perturb(0.1, seed=42)

        self.assertTrue(np.allclose(result1.positions, result2.positions))
```

- [ ] **Step 6: Rewrite `test_perturb_atom_selection`**

Replace with:
```python
    def test_perturb_atom_selection(self):
        """Test perturb with AtomSelection object returns new object."""
        from matsimpy.utils.selection import AtomSelection

        crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5], [0.75, 0.75, 0.75]],
            Lattice.cubic(5.0)
        )
        original_positions = crystal.positions.copy()

        sel = AtomSelection(crystal).by_species('Si')
        result = crystal.perturb(0.1, indices=sel, seed=42)

        self.assertIsNot(result, crystal)
        self.assertTrue(np.allclose(crystal.positions, original_positions))
        self.assertFalse(np.allclose(original_positions[0], result.positions[0]))
        self.assertFalse(np.allclose(original_positions[2], result.positions[2]))
        self.assertTrue(np.allclose(original_positions[1], result.positions[1]))
        self.assertTrue(np.allclose(original_positions[3], result.positions[3]))
```

- [ ] **Step 7: Rewrite all remaining `inplace=True` tests**

Replace `test_perturb_lattice_only`, `test_perturb_both_positions_and_lattice`, `test_perturb_different_amplitudes`, `test_perturb_backward_compatibility`, `test_perturb_lattice_reproducibility`, `test_perturb_both_reproducibility` — each removing `inplace` references and checking `self.assertIsNot(result, self.crystal)` and `self.assertTrue(np.allclose(self.crystal.positions, original_positions))`.

- [ ] **Step 8: Delete `test_perturb_not_inplace`, `test_perturb_lattice_only_not_inplace`, `test_perturb_both_not_inplace`**

These tests used `inplace=False` which is no longer needed (there's no `inplace` parameter). Keep the assertions about original being unchanged and incorporate them into the rewritten tests above.

- [ ] **Step 9: Run Crystal convenience tests**

```bash
python -m pytest tests/test_crystal_convenience_methods.py -v
```

Expected: All tests pass.

- [ ] **Step 10: Commit**

```bash
git add tests/test_crystal_convenience_methods.py
git commit -m "test: update Crystal convenience tests for immutable behavior"
```

---

### Task 6: Update Molecule convenience method tests

**Files:**
- Modify: `tests/test_molecule_convenience_methods.py`

- [ ] **Step 1: Rewrite `test_perturb_inplace`**

Replace with:
```python
    def test_perturb_returns_new(self):
        """Test perturb returns new object, original unchanged."""
        original_positions = self.molecule.positions.copy()

        result = self.molecule.perturb(0.1, seed=42)

        self.assertIsNot(result, self.molecule)
        self.assertTrue(np.allclose(self.molecule.positions, original_positions))
        self.assertFalse(np.allclose(original_positions, result.positions))
```

- [ ] **Step 2: Delete `test_perturb_not_inplace`**

The `inplace` parameter no longer exists. The default-behavior test in Step 1 covers the case.

- [ ] **Step 3: Rewrite `test_perturb_specific_indices`**

Replace with:
```python
    def test_perturb_specific_indices(self):
        """Test perturb with specific atom indices returns new object."""
        original_positions = self.molecule.positions.copy()

        result = self.molecule.perturb(0.1, indices=[0], seed=42)

        self.assertIsNot(result, self.molecule)
        self.assertTrue(np.allclose(self.molecule.positions, original_positions))
        self.assertFalse(np.allclose(original_positions[0], result.positions[0]))
        self.assertTrue(np.allclose(original_positions[1:], result.positions[1:]))
```

- [ ] **Step 4: Rewrite `test_perturb_reproducibility`**

Replace with:
```python
    def test_perturb_reproducibility(self):
        """Test that perturb is reproducible with same seed."""
        molecule1 = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        molecule2 = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])

        result1 = molecule1.perturb(0.1, seed=42)
        result2 = molecule2.perturb(0.1, seed=42)

        self.assertTrue(np.allclose(result1.positions, result2.positions))
```

- [ ] **Step 5: Rewrite `test_perturb_atom_selection`**

Replace with:
```python
    def test_perturb_atom_selection(self):
        """Test perturb with AtomSelection object returns new object."""
        from matsimpy.utils.selection import AtomSelection

        molecule = Molecule(
            ['H', 'O', 'H', 'C'],
            [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0], [1.5, 0, 0]]
        )
        original_positions = molecule.positions.copy()

        sel = AtomSelection(molecule).by_species('H')
        result = molecule.perturb(0.1, indices=sel, seed=42)

        self.assertIsNot(result, molecule)
        self.assertTrue(np.allclose(molecule.positions, original_positions))
        self.assertFalse(np.allclose(original_positions[0], result.positions[0]))
        self.assertFalse(np.allclose(original_positions[2], result.positions[2]))
        self.assertTrue(np.allclose(original_positions[1], result.positions[1]))
        self.assertTrue(np.allclose(original_positions[3], result.positions[3]))
```

- [ ] **Step 6: Run Molecule convenience tests**

```bash
python -m pytest tests/test_molecule_convenience_methods.py -v
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add tests/test_molecule_convenience_methods.py
git commit -m "test: update Molecule convenience tests for immutable behavior"
```

---

### Task 7: Update translate/rotate/wrap tests

**Files:**
- Modify: `tests/test_molecule_comprehensive.py` (lines 58-143)
- Modify: `tests/test_crystal_comprehensive.py` (lines 318-465)

- [ ] **Step 1: Rewrite `test_molecule_center_of_mass_invalidation`**

The concept of "cache invalidation" no longer applies. Replace (lines 58-68) with:
```python
    def test_molecule_center_of_mass_recalculation(self):
        """Test center of mass recalculates for new molecule after translate."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)

        com1 = molecule.get_center_of_mass()
        translated = molecule.translate([1, 1, 1])
        com2 = translated.get_center_of_mass()
        self.assertNotEqual(com1[0], com2[0])
```

- [ ] **Step 2: Rewrite `test_molecule_translate_inplace`**

Replace (lines 70-82) with:
```python
    def test_molecule_translate_returns_new(self):
        """Test translation returns new molecule, original unchanged."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)

        original_pos = molecule.positions.copy()
        result = molecule.translate([1, 1, 1])

        self.assertIsNot(result, molecule)
        np.testing.assert_array_almost_equal(molecule.positions, original_pos)
        np.testing.assert_array_almost_equal(
            result.positions, original_pos + [1, 1, 1]
        )
```

- [ ] **Step 3: Rewrite `test_molecule_rotate_inplace`**

Replace (lines 99-112) with:
```python
    def test_molecule_rotate_returns_new(self):
        """Test rotation returns new molecule, original unchanged."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)

        original_pos = molecule.positions.copy()
        result = molecule.rotate(90, [0, 0, 1])

        self.assertIsNot(result, molecule)
        self.assertTrue(np.allclose(molecule.positions, original_pos))
        self.assertFalse(np.allclose(original_pos, result.positions))
```

- [ ] **Step 4: Rewrite `test_molecule_rotate_cache_invalidation`**

Replace (lines 129-143) with:
```python
    def test_molecule_rotate_original_cache_preserved(self):
        """Test that rotating returns new molecule, original COM unchanged."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)

        com1 = molecule.get_center_of_mass()
        rotated = molecule.rotate(90, [0, 0, 1])
        com1_again = molecule.get_center_of_mass()
        self.assertEqual(com1, com1_again)
```

- [ ] **Step 5: Rewrite `test_crystal_wrap_method_chaining`**

Replace line 397-398 `self.assertIs(result, crystal)` with `self.assertIsNot(result, crystal)` and add an assertion that original is unchanged.

- [ ] **Step 6: Rewrite `test_crystal_wrap_invalidates_neighbor_tree`**

The neighbor tree is no longer invalidated by wrap (wrap returns a new object). Replace with:
```python
    def test_crystal_wrap_original_unchanged(self):
        """Test that wrap returns new crystal, original unchanged."""
        species = ['Fe', 'O']
        positions = [[1.5, -0.3, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        original_frac = crystal.frac_positions.copy()
        result = crystal.wrap()

        self.assertIsNot(result, crystal)
        self.assertTrue(np.allclose(crystal.frac_positions, original_frac))
```

- [ ] **Step 7: Update all wrap tests to use returned object**

For `test_crystal_wrap_positive`, `test_crystal_wrap_negative`, `test_crystal_wrap_mixed`, `test_crystal_wrap_already_in_range`, `test_crystal_wrap_updates_sites`, `test_crystal_wrap_boundary_values` — change from `crystal.wrap()` (void, modifies in-place) to `result = crystal.wrap()` and assert on `result` not `crystal`.

- [ ] **Step 8: Run translate/rotate/wrap tests**

```bash
python -m pytest tests/test_molecule_comprehensive.py::TestMoleculeComprehensive -v
python -m pytest tests/test_crystal_comprehensive.py -v -k "wrap"
```

Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add tests/test_molecule_comprehensive.py tests/test_crystal_comprehensive.py
git commit -m "test: update translate/rotate/wrap tests for immutable behavior"
```

---

### Task 8: Full test suite run and fix remaining failures

**Files:**
- Various — fix any remaining test failures across the entire test suite

- [ ] **Step 1: Run the full test suite**

```bash
python -m pytest tests/ -v 2>&1 | tail -80
```

- [ ] **Step 2: Identify all failing tests**

```bash
python -m pytest tests/ --tb=short 2>&1 | grep "FAILED"
```

- [ ] **Step 3: Fix each failing test**

For each failure, the fix will be one of:
- Replace `inplace=True` calls with assignment to result variable
- Replace `result = ...; self.assertIs(result, original)` with `self.assertIsNot`
- Replace `crystal.freeze()` / `molecule.freeze()` calls (delete them)
- Replace `FrozenStructureError` imports (delete the import)
- Replace assertions on in-place modified objects with assertions on returned objects

Common patterns to fix:
```
# BEFORE (in-place):
crystal.translate([1,0,0], inplace=True)
self.assertEqual(crystal.positions[0][0], 1.0)

# AFTER (immutable):
result = crystal.translate([1,0,0])
self.assertEqual(result.positions[0][0], 1.0)
```

- [ ] **Step 4: Run full test suite again — expect ALL PASS**

```bash
python -m pytest tests/ -v
```

Expected: Zero failures.

- [ ] **Step 5: Commit fixes**

```bash
git add -A
git commit -m "test: fix remaining tests for immutable core behavior"
```

---

### Task 9: Clean up and verify

**Files:**
- Modify: `matsimpy/core/__init__.py` (remove `FrozenStructureError` export if present)

- [ ] **Step 1: Verify no FrozenStructureError imports remain**

```bash
grep -rn "FrozenStructureError" matsimpy/ tests/ --include="*.py" | grep -v __pycache__
```

Expected: No results.

- [ ] **Step 2: Verify no `_check_frozen` calls remain**

```bash
grep -rn "_check_frozen\|\.freeze()\|\.unfreeze()\|\.is_frozen" matsimpy/ --include="*.py" | grep -v __pycache__
```

Expected: No results.

- [ ] **Step 3: Verify no `_formula_dirty` references remain**

```bash
grep -rn "_formula_dirty" matsimpy/ --include="*.py" | grep -v __pycache__
```

Expected: No results.

- [ ] **Step 4: Verify no `inplace` references in core**

```bash
grep -rn "inplace" matsimpy/core/ --include="*.py" | grep -v __pycache__
```

Expected: No results.

- [ ] **Step 5: Run full test suite one final time**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit final cleanup**

```bash
git add -A
git commit -m "chore: final cleanup — verify no freeze/dirty-flag/inplace references remain"
```
