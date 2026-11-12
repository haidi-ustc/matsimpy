"""Comprehensive tests for Molecule class."""
import unittest
import numpy as np

from matsimpy.core import Molecule, Crystal

class TestMoleculeComprehensive(unittest.TestCase):
    """Comprehensive tests for Molecule class."""
    
    
    
    
    
    
    
    def test_molecule_translate_returns_new(self):
        """Test translation returns new molecule, original unchanged."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        original_pos = molecule.positions.copy()
        result = molecule.translate([1, 1, 1])
        self.assertIsNot(result, molecule)
        np.testing.assert_array_almost_equal(molecule.positions, original_pos)
        np.testing.assert_array_almost_equal(result.positions, original_pos + [1, 1, 1])
    
    def test_molecule_translate_return_new(self):
        """Test translation returning new molecule (default)."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        original_pos = molecule.positions.copy()
        new_molecule = molecule.translate([1, 1, 1])
        
        # Original should be unchanged
        np.testing.assert_array_almost_equal(molecule.positions, original_pos)
        # New should be translated
        self.assertIsNot(new_molecule, molecule)
        np.testing.assert_array_almost_equal(new_molecule.positions, original_pos + [1, 1, 1])
    
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
    
    def test_molecule_rotate_return_new(self):
        """Test rotation returning new molecule (default)."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        original_pos = molecule.positions.copy()
        new_molecule = molecule.rotate(90, [0, 0, 1])  # Rotate 90 degrees around z-axis
        
        # Original should be unchanged
        np.testing.assert_array_almost_equal(molecule.positions, original_pos)
        # New should be rotated
        self.assertIsNot(new_molecule, molecule)
        self.assertFalse(np.allclose(original_pos, new_molecule.positions))
    
    def test_molecule_rotate_original_cache_preserved(self):
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        com1 = molecule.get_center_of_mass()
        rotated = molecule.rotate(90, [0, 0, 1])
        com1_again = molecule.get_center_of_mass()
        self.assertEqual(com1, com1_again)
    
    def test_molecule_to_crystal(self):
        """Test conversion to crystal with default vacuum."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        crystal = molecule.to_crystal()
        self.assertIsInstance(crystal, Crystal)
        self.assertIsNotNone(crystal.lattice)
        self.assertEqual(len(crystal), 2)
        # Check that vacuum padding was applied (box should be larger than molecule)
        self.assertGreater(crystal.lattice.a, 1.4 + 15.0)  # molecule size + vacuum
        # Check that PBC is set to [False, False, False] for non-periodic molecules
        self.assertEqual(crystal.pbc, (False, False, False))
    
    
    def test_molecule_moment_of_inertia(self):
        """Test moment of inertia calculation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        moment = molecule.get_moment_of_inertia()
        self.assertEqual(moment.shape, (3, 3))
        # Should be symmetric
        np.testing.assert_array_almost_equal(moment, moment.T)
    
    
    
    
    
    
    def test_molecule_as_dict_with_properties(self):
        """Test dictionary with site properties."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        site_properties = [{'charge': 0}, {'charge': -1}]
        molecule = Molecule(species, positions, site_properties=site_properties)
        
        d = molecule.as_dict()
        self.assertIn('site_properties', d)
    
    
    
    
    def test_molecule_repr(self):
        """Test representation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        repr_str = repr(molecule)
        self.assertIn('Molecule', repr_str)

if __name__ == '__main__':
    unittest.main()
