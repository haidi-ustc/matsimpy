"""Tests for common substitution methods in Crystal and Molecule classes."""
import unittest

from matsimpy.core import Crystal, Molecule, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule

class TestMoleculeSubstitution(unittest.TestCase):
    """Tests for substitution methods in Molecule class."""

    def setUp(self):
        """Set up test molecules."""
        self.molecule = make_simple_molecule()

    def test_substitute_single(self):
        """Test substituting a single atom."""
        original_species = list(self.molecule.species)
        result = self.molecule.substitute(0, 'N')

        # Original unchanged
        self.assertEqual(list(self.molecule.species), original_species)
        # Result has substitution
        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], original_species[1])
        # Sites should be updated
        self.assertEqual(len(result.sites), 2)
        self.assertEqual(result.sites[0].specie, 'N')

    def test_substitute_multiple(self):
        """Test substituting multiple atoms."""
        result = self.molecule.substitute([0, 1], ['N', 'S'])

        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], 'S')
        self.assertEqual(result.sites[0].specie, 'N')
        self.assertEqual(result.sites[1].specie, 'S')

    def test_substitute_all(self):
        """Test substituting all atoms of a species."""
        molecule = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        result = molecule.substitute_all('C', 'N')

        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], 'N')
        self.assertEqual(result.species[2], 'O')

    def test_substitute_invalid_index(self):
        """Test substitution with invalid index."""
        with self.assertRaises(IndexError):
            self.molecule.substitute(10, 'N')

    def test_substitute_mismatched_lengths(self):
        """Test substitution with mismatched indices and species."""
        with self.assertRaises(ValueError):
            self.molecule.substitute([0, 1], ['N'])

    def test_substitute_cache_invalidation(self):
        """Test that substitution invalidates formula cache."""
        molecule = Molecule(['C', 'C'], [[0, 0, 0], [1.2, 0, 0]])  # C2
        original_formula = molecule.formula
        self.assertEqual(original_formula, 'C2')

        # Substitution returns a new molecule
        result = molecule.substitute(0, 'N')
        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], 'C')

        # New molecule should have updated formula
        new_formula = result.formula
        self.assertNotEqual(original_formula, new_formula)
        # Formula should contain both C and N (order may vary)
        self.assertIn('C', new_formula)
        self.assertIn('N', new_formula)

class TestCrystalSubstitution(unittest.TestCase):
    """Tests for substitution methods in Crystal class."""

    def setUp(self):
        """Set up test crystals."""
        self.crystal = make_simple_crystal()

    def test_substitute_single(self):
        """Test substituting a single atom."""
        original_species = list(self.crystal.species)
        result = self.crystal.substitute(0, 'Ge')

        # Original unchanged
        self.assertEqual(list(self.crystal.species), original_species)
        # Result has substitution
        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], original_species[1])
        # Sites should be updated
        self.assertEqual(len(result.sites), 2)
        self.assertEqual(result.sites[0].specie, 'Ge')

    def test_substitute_multiple(self):
        """Test substituting multiple atoms."""
        crystal = Crystal(['Si', 'Si', 'O'],
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
                         Lattice.cubic(10))
        result = crystal.substitute([0, 1], ['Ge', 'Ge'])

        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], 'Ge')
        self.assertEqual(result.species[2], 'O')

    def test_substitute_all(self):
        """Test substituting all atoms of a species."""
        crystal = Crystal(['Si', 'Si', 'O'],
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
                         Lattice.cubic(10))
        result = crystal.substitute_all('Si', 'Ge')

        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], 'Ge')
        self.assertEqual(result.species[2], 'O')

    def test_substitute_neighbor_tree_invalidation(self):
        """Test that substitution on the returned object has no neighbor tree."""
        # Build neighbor tree on original
        self.crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(self.crystal._neighbor_cache)

        # Substitute returns a new object without neighbor tree (immutable)
        result = self.crystal.substitute(0, 'Ge')

        # Original should still have neighbor tree
        self.assertIsNotNone(self.crystal._neighbor_cache)
        # Result should have no neighbor tree (freshly created)
        self.assertIsNone(result._neighbor_cache)

    def test_substitute_cache_invalidation(self):
        """Test that substitution invalidates formula cache."""
        crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))  # Si2
        original_formula = crystal.formula
        self.assertEqual(original_formula, 'Si2')

        # Substitution returns a new crystal
        result = crystal.substitute(0, 'Ge')
        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], 'Si')

        # New crystal should have updated formula
        new_formula = result.formula
        self.assertNotEqual(original_formula, new_formula)
        # Formula should contain both Si and Ge (order may vary)
        self.assertIn('Si', new_formula)
        self.assertIn('Ge', new_formula)

class TestSubstitutionConsistency(unittest.TestCase):
    """Tests for consistency between class methods and transformation module."""

    def test_substitute_consistency(self):
        """Test that class method and transformation module produce same result."""
        from matsimpy.transformation import substitute

        # Test with class method
        mol1 = make_simple_molecule()
        mol1_result = mol1.substitute(0, 'N')

        # Test with transformation module
        mol2 = make_simple_molecule()
        mol2_result = substitute(mol2, 0, 'N')

        # Results should be the same
        self.assertEqual(mol1_result.species, mol2_result.species)
        self.assertEqual(mol1_result.positions.tolist(), mol2_result.positions.tolist())

    def test_substitute_all_consistency(self):
        """Test that substitute_all is consistent."""
        from matsimpy.transformation import substitute_all

        # Test with class method
        mol1 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mol1_result = mol1.substitute_all('C', 'N')

        # Test with transformation module
        mol2 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mol2_result = substitute_all(mol2, 'C', 'N')

        # Results should be the same
        self.assertEqual(mol1_result.species, mol2_result.species)

if __name__ == '__main__':
    unittest.main()
