"""Comprehensive tests for Molecule class."""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Molecule, Crystal, Lattice


class TestMoleculeComprehensive(unittest.TestCase):
    """Comprehensive tests for Molecule class."""
    
    def test_molecule_init(self):
        """Test molecule initialization."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        self.assertEqual(len(molecule), 2)
        self.assertEqual(molecule.species, ('C', 'O'))
        self.assertIsNone(molecule.lattice)
    
    def test_molecule_sites(self):
        """Test sites property."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        self.assertEqual(len(molecule.sites), 2)
        self.assertEqual(molecule.sites[0].specie, 'C')
    
    def test_molecule_getitem(self):
        """Test indexing."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        site = molecule[0]
        self.assertEqual(site.specie, 'C')
    
    def test_molecule_center_of_mass(self):
        """Test center of mass calculation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        com = molecule.get_center_of_mass()
        self.assertEqual(len(com), 3)
        self.assertIsInstance(com[0], float)
    
    def test_molecule_center_of_mass_caching(self):
        """Test center of mass caching."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        com1 = molecule.get_center_of_mass()
        com2 = molecule.get_center_of_mass()
        self.assertIs(com1, com2)  # Should be cached
    
    def test_molecule_center_of_mass_invalidation(self):
        """Test center of mass cache invalidation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        com1 = molecule.get_center_of_mass()
        molecule.translate([1, 1, 1])
        com2 = molecule.get_center_of_mass()
        # Should be different (not cached)
        self.assertNotEqual(com1[0], com2[0])
    
    def test_molecule_translate(self):
        """Test translation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        original_pos = molecule.positions.copy()
        molecule.translate([1, 1, 1])
        new_pos = molecule.positions
        
        np.testing.assert_array_almost_equal(new_pos, original_pos + [1, 1, 1])
    
    def test_molecule_rotate(self):
        """Test rotation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        original_pos = molecule.positions.copy()
        molecule.rotate(90, [0, 0, 1])  # Rotate 90 degrees around z-axis
        new_pos = molecule.positions
        
        # Positions should change after rotation
        self.assertFalse(np.allclose(original_pos, new_pos))
    
    def test_molecule_rotate_cache_invalidation(self):
        """Test that rotation invalidates center of mass cache."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        com1 = molecule.get_center_of_mass()
        # Verify cache exists
        self.assertTrue(hasattr(molecule, '_cached_com'))
        molecule.rotate(90, [0, 0, 1])
        # Cache should be invalidated
        self.assertFalse(hasattr(molecule, '_cached_com'))
        com2 = molecule.get_center_of_mass()
        # Should recalculate (may be same or different depending on rotation)
        self.assertIsNotNone(com2)
    
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
    
    def test_molecule_to_crystal_with_vacuum(self):
        """Test conversion to crystal with specified vacuum padding."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        crystal = molecule.to_crystal(vacuum=20.0)
        self.assertIsInstance(crystal, Crystal)
        # Check that custom vacuum was applied
        self.assertGreater(crystal.lattice.a, 1.4 + 20.0)  # molecule size + vacuum
    
    def test_molecule_moment_of_inertia(self):
        """Test moment of inertia calculation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        moment = molecule.get_moment_of_inertia()
        self.assertEqual(moment.shape, (3, 3))
        # Should be symmetric
        np.testing.assert_array_almost_equal(moment, moment.T)
    
    def test_molecule_neighbor_list(self):
        """Test neighbor list for single atom."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        neighbors = molecule.get_neighbor_list(0, cutoff=2.0)
        self.assertIsInstance(neighbors, list)
        self.assertIn(1, neighbors)  # O should be neighbor of C
    
    def test_molecule_neighbor_list_no_neighbors(self):
        """Test neighbor list with cutoff too small."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [10.0, 0, 0]]  # Far apart
        molecule = Molecule(species, positions)
        
        neighbors = molecule.get_neighbor_list(0, cutoff=1.0)
        self.assertEqual(len(neighbors), 0)
    
    def test_molecule_all_neighbor_lists(self):
        """Test all neighbor lists."""
        species = ['C', 'O', 'N']
        positions = [[0, 0, 0], [1.4, 0, 0], [0, 1.4, 0]]
        molecule = Molecule(species, positions)
        
        all_neighbors = molecule.get_all_neighbor_lists(cutoff=2.0)
        self.assertEqual(len(all_neighbors), 3)
        self.assertIsInstance(all_neighbors[0], list)
    
    def test_molecule_site_properties(self):
        """Test molecule with site properties."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        site_properties = [{'charge': 0}, {'charge': -1}]
        molecule = Molecule(species, positions, site_properties=site_properties)
        
        self.assertEqual(molecule.sites[0].properties['charge'], 0)
        self.assertEqual(molecule.sites[1].properties['charge'], -1)
    
    def test_molecule_as_dict(self):
        """Test dictionary representation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        d = molecule.as_dict()
        self.assertIn('species', d)
        self.assertIn('positions', d)
        self.assertNotIn('lattice', d)
    
    def test_molecule_as_dict_with_properties(self):
        """Test dictionary with site properties."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        site_properties = [{'charge': 0}, {'charge': -1}]
        molecule = Molecule(species, positions, site_properties=site_properties)
        
        d = molecule.as_dict()
        self.assertIn('site_properties', d)
    
    def test_molecule_from_dict(self):
        """Test creation from dictionary."""
        d = {
            'species': ['C', 'O'],
            'positions': [[0, 0, 0], [1.4, 0, 0]]
        }
        molecule = Molecule.from_dict(d)
        self.assertEqual(len(molecule), 2)
    
    def test_molecule_from_dict_with_properties(self):
        """Test creation from dictionary with properties."""
        d = {
            'species': ['C', 'O'],
            'positions': [[0, 0, 0], [1.4, 0, 0]],
            'site_properties': [{'charge': 0}, {'charge': -1}]
        }
        molecule = Molecule.from_dict(d)
        self.assertEqual(molecule.sites[0].properties['charge'], 0)
    
    def test_molecule_str(self):
        """Test string representation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        str_repr = str(molecule)
        self.assertIn('Molecule', str_repr)
        self.assertIn('atoms', str_repr)
    
    def test_molecule_repr(self):
        """Test representation."""
        species = ['C', 'O']
        positions = [[0, 0, 0], [1.4, 0, 0]]
        molecule = Molecule(species, positions)
        
        repr_str = repr(molecule)
        self.assertIn('Molecule', repr_str)


if __name__ == '__main__':
    unittest.main()

