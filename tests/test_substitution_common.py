"""Tests for common substitution methods in Crystal and Molecule classes."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Crystal, Molecule, Lattice


class TestMoleculeSubstitution(unittest.TestCase):
    """Tests for substitution methods in Molecule class."""
    
    def setUp(self):
        """Set up test molecules."""
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    def test_substitute_single(self):
        """Test substituting a single atom."""
        original_species = list(self.molecule.species)
        self.molecule.substitute(0, 'N')
        
        self.assertEqual(self.molecule.species[0], 'N')
        self.assertEqual(self.molecule.species[1], original_species[1])
        # Sites should be updated
        self.assertEqual(len(self.molecule.sites), 2)
        self.assertEqual(self.molecule.sites[0].specie, 'N')
    
    def test_substitute_multiple(self):
        """Test substituting multiple atoms."""
        self.molecule.substitute([0, 1], ['N', 'S'])
        
        self.assertEqual(self.molecule.species[0], 'N')
        self.assertEqual(self.molecule.species[1], 'S')
        self.assertEqual(self.molecule.sites[0].specie, 'N')
        self.assertEqual(self.molecule.sites[1].specie, 'S')
    
    def test_substitute_all(self):
        """Test substituting all atoms of a species."""
        molecule = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        molecule.substitute_all('C', 'N')
        
        self.assertEqual(molecule.species[0], 'N')
        self.assertEqual(molecule.species[1], 'N')
        self.assertEqual(molecule.species[2], 'O')
    
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
        original_formula = self.molecule.formula
        self.molecule.substitute(0, 'N')
        
        # Formula should be recalculated
        new_formula = self.molecule.formula
        self.assertNotEqual(original_formula, new_formula)
        self.assertEqual(new_formula, 'NO')  # C replaced with N


class TestCrystalSubstitution(unittest.TestCase):
    """Tests for substitution methods in Crystal class."""
    
    def setUp(self):
        """Set up test crystals."""
        self.crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
    
    def test_substitute_single(self):
        """Test substituting a single atom."""
        original_species = list(self.crystal.species)
        self.crystal.substitute(0, 'Ge')
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[1], original_species[1])
        # Sites should be updated
        self.assertEqual(len(self.crystal.sites), 2)
        self.assertEqual(self.crystal.sites[0].specie, 'Ge')
    
    def test_substitute_multiple(self):
        """Test substituting multiple atoms."""
        crystal = Crystal(['Si', 'Si', 'O'], 
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], 
                         Lattice.cubic(10))
        crystal.substitute([0, 1], ['Ge', 'Ge'])
        
        self.assertEqual(crystal.species[0], 'Ge')
        self.assertEqual(crystal.species[1], 'Ge')
        self.assertEqual(crystal.species[2], 'O')
    
    def test_substitute_all(self):
        """Test substituting all atoms of a species."""
        crystal = Crystal(['Si', 'Si', 'O'], 
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], 
                         Lattice.cubic(10))
        crystal.substitute_all('Si', 'Ge')
        
        self.assertEqual(crystal.species[0], 'Ge')
        self.assertEqual(crystal.species[1], 'Ge')
        self.assertEqual(crystal.species[2], 'O')
    
    def test_substitute_neighbor_tree_invalidation(self):
        """Test that substitution invalidates neighbor tree."""
        # Build neighbor tree
        self.crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(self.crystal._neighbor_tree)
        
        # Substitute atom
        self.crystal.substitute(0, 'Ge')
        
        # Neighbor tree should be invalidated
        self.assertIsNone(self.crystal._neighbor_tree)
    
    def test_substitute_cache_invalidation(self):
        """Test that substitution invalidates formula cache."""
        original_formula = self.crystal.formula
        self.crystal.substitute(0, 'Ge')
        
        # Formula should be recalculated
        new_formula = self.crystal.formula
        self.assertNotEqual(original_formula, new_formula)


class TestSubstitutionConsistency(unittest.TestCase):
    """Tests for consistency between class methods and transformation module."""
    
    def test_substitute_consistency(self):
        """Test that class method and transformation module produce same result."""
        from matsimpy.transformation import substitute
        
        # Test with class method
        mol1 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        mol1.substitute(0, 'N')
        
        # Test with transformation module (inplace)
        mol2 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        substitute(mol2, 0, 'N', inplace=True)
        
        # Results should be the same
        self.assertEqual(mol1.species, mol2.species)
        self.assertEqual(mol1.positions.tolist(), mol2.positions.tolist())
    
    def test_substitute_all_consistency(self):
        """Test that substitute_all is consistent."""
        from matsimpy.transformation import substitute_all
        
        # Test with class method
        mol1 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mol1.substitute_all('C', 'N')
        
        # Test with transformation module (inplace)
        mol2 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        substitute_all(mol2, 'C', 'N', inplace=True)
        
        # Results should be the same
        self.assertEqual(mol1.species, mol2.species)


if __name__ == '__main__':
    unittest.main()

