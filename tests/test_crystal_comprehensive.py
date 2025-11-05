"""Comprehensive tests for Crystal class."""
import os
import sys
import unittest
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Crystal, Lattice, Element


class TestCrystalComprehensive(unittest.TestCase):
    """Comprehensive tests for Crystal class."""
    
    def test_crystal_init_fractional(self):
        """Test crystal initialization with fractional coordinates."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertEqual(len(crystal), 2)
        np.testing.assert_array_almost_equal(crystal.frac_positions, positions)
    
    def test_crystal_init_cartesian(self):
        """Test crystal initialization with cartesian coordinates."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [5, 5, 5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice, coords_are_cartesian=True)
        
        np.testing.assert_array_almost_equal(crystal.cart_positions, positions)
    
    def test_crystal_coordinate_conversion(self):
        """Test coordinate conversion."""
        species = ['Si']
        positions = [[0.5, 0.5, 0.5]]  # Fractional
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        # Convert to cartesian and back
        cart = crystal.cart_positions
        frac_back = crystal._convert_to_fractional()
        
        np.testing.assert_array_almost_equal(positions, frac_back, decimal=6)
    
    def test_crystal_volume(self):
        """Test volume calculation."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertEqual(crystal.volume, 1000.0)
    
    def test_crystal_density(self):
        """Test density calculation."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        density = crystal.density()
        self.assertGreater(density, 0)
    
    def test_crystal_pbc(self):
        """Test periodic boundary conditions."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice, pbc=[True, False, True])
        
        self.assertEqual(crystal.pbc, [True, False, True])
    
    def test_crystal_pbc_default(self):
        """Test default PBC."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertEqual(crystal.pbc, [True, True, True])
    
    def test_crystal_site_properties(self):
        """Test site properties."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        site_properties = [{'magmom': 2.0}, {'charge': -2}]
        crystal = Crystal(species, positions, lattice, site_properties=site_properties)
        
        self.assertEqual(len(crystal.site_properties), 2)
        self.assertEqual(crystal.sites[0].properties['magmom'], 2.0)
    
    def test_crystal_sites(self):
        """Test sites property."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertEqual(len(crystal.sites), 2)
        self.assertEqual(crystal.sites[0].specie, 'Si')
    
    def test_crystal_getitem(self):
        """Test indexing."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        site = crystal[0]
        self.assertEqual(site.specie, 'Si')
    
    def test_crystal_add_atom(self):
        """Test adding atom."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        crystal.add_atom('O', [0.5, 0.5, 0.5])
        self.assertEqual(len(crystal), 2)
        self.assertEqual(len(crystal.sites), 2)
    
    def test_crystal_remove_atom(self):
        """Test removing atom."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        crystal.remove_atom(0)
        self.assertEqual(len(crystal), 1)
        self.assertEqual(crystal.species[0], 'O')
    
    def test_crystal_from_file_poscar(self):
        """Test reading POSCAR file using from_file."""
        poscar_file = Path(__file__).parent / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = Crystal.from_file(str(poscar_file))
            self.assertIsInstance(crystal, Crystal)
            self.assertGreater(len(crystal), 0)
    
    def test_crystal_to_file_poscar(self):
        """Test writing POSCAR file using to_file."""
        import tempfile
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name
        
        try:
            crystal.to_file(temp_file)
            # Verify file was created
            self.assertTrue(Path(temp_file).exists())
            # Read back to verify
            crystal2 = Crystal.from_file(temp_file)
            self.assertEqual(len(crystal2), len(crystal))
        finally:
            Path(temp_file).unlink()
    
    
    def test_crystal_str(self):
        """Test string representation."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        str_repr = str(crystal)
        self.assertIn('Crystal', str_repr)
        self.assertIn('atoms', str_repr)
    
    def test_crystal_repr(self):
        """Test representation."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        repr_str = repr(crystal)
        self.assertIn('Crystal', repr_str)
    
    def test_crystal_as_dict(self):
        """Test dictionary representation."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        d = crystal.as_dict()
        self.assertIn('species', d)
        self.assertIn('positions', d)
        self.assertIn('lattice', d)
        self.assertIn('pbc', d)
    
    def test_crystal_from_dict(self):
        """Test creation from dictionary."""
        d = {
            'species': ['Si', 'O'],
            'positions': [[0, 0, 0], [0.5, 0.5, 0.5]],
            'lattice': {
                'lattice_vectors': [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
            },
            'pbc': [True, True, True],
            'site_properties': []
        }
        crystal = Crystal.from_dict(d)
        self.assertEqual(len(crystal), 2)
    
    def test_crystal_neighbor_list_small_cutoff(self):
        """Test neighbor list with small cutoff."""
        species = ['Si'] * 4
        positions = [[0, 0, 0], [0.1, 0, 0], [0, 0.1, 0], [0, 0, 0.1]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        neighbors = crystal.get_neighbor_list(1.0)
        self.assertIsInstance(neighbors, dict)
        self.assertEqual(len(neighbors), 4)
    
    def test_crystal_periodic_images(self):
        """Test periodic images generation."""
        species = ['Si'] * 2
        positions = [[0, 0, 0], [0.9, 0, 0]]  # Close to boundary
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        images = crystal._get_periodic_images(5.0)
        self.assertGreater(len(images), len(crystal.cart_positions))


if __name__ == '__main__':
    unittest.main()

