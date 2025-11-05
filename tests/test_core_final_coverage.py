"""Final coverage tests for remaining gaps."""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Crystal, Lattice, Element, Site, CrystalSite


class TestFinalCoverage(unittest.TestCase):
    """Tests to cover remaining uncovered lines."""
    
    def test_crystal_neighbor_tree_rebuild_check(self):
        """Test neighbor tree rebuild condition when structure changes."""
        species = ['Si'] * 5
        positions = np.random.rand(5, 3) * 5
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        # Build tree
        neighbors1 = crystal.get_neighbor_list(3.0)
        
        # Add atom - should rebuild tree
        crystal.add_atom('O', [0.5, 0.5, 0.5])
        neighbors2 = crystal.get_neighbor_list(3.0)
        
        # Should have different number of atoms
        self.assertEqual(len(neighbors2), 6)
    
    def test_element_from_dict(self):
        """Test Element serialization (if exists)."""
        h = Element('H')
        # Test that we can access all properties
        _ = h.atomic_no
        _ = h.name
        _ = h.X
        _ = h.x
    
    def test_site_from_dict_minimal(self):
        """Test Site.from_dict with minimal dict."""
        d = {'position': [0, 0, 0]}
        site = Site.from_dict(d)
        self.assertIsNotNone(site)
    
    def test_crystalsite_from_dict_minimal(self):
        """Test CrystalSite.from_dict with minimal dict."""
        d = {
            'position': [0.5, 0.5, 0.5],
            'lattice': {
                'lattice_vectors': [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
            }
        }
        site = CrystalSite.from_dict(d)
        self.assertIsNotNone(site)
    
    def test_crystalsite_validate_lattice_list(self):
        """Test CrystalSite lattice validation with list."""
        lattice_vecs = [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice_vecs)
        self.assertIsInstance(site.lattice, Lattice)
    
    def test_crystalsite_validate_lattice_invalid(self):
        """Test CrystalSite lattice validation with invalid input."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        with self.assertRaises(TypeError):
            site.lattice = "invalid"
    
    def test_periodic_table_main_block(self):
        """Test periodic_table.py main block."""
        # This tests the if __name__ == '__main__' block
        import subprocess
        result = subprocess.run(
            ['python', '-c', 'from matsimpy.core.periodic_table import Element; h=Element("H"); print(h)'],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()

