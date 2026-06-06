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

    def test_internal_positions_array_is_read_only(self):
        crystal = Crystal(
            ["Na", "Cl"],
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5.64),
        )
        molecule = Molecule(["H"], [[0.0, 0.0, 0.0]])

        with self.assertRaises(ValueError):
            crystal._positions[0, 0] = 0.25
        with self.assertRaises(ValueError):
            molecule._positions[0, 0] = 0.25


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
