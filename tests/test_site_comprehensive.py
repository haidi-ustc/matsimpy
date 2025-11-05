"""Comprehensive tests for Site and CrystalSite classes."""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Site, CrystalSite, Lattice, Element


class TestSiteComprehensive(unittest.TestCase):
    """Comprehensive tests for Site class."""
    
    def test_site_init_default(self):
        """Test site initialization with defaults."""
        site = Site([0, 0, 0])
        self.assertEqual(site.specie, 'X')
        self.assertEqual(site.properties, {})
    
    def test_site_init_with_specie_string(self):
        """Test site with string specie."""
        site = Site([0, 0, 0], specie='Fe')
        self.assertEqual(site.specie, 'Fe')
    
    def test_site_init_with_specie_int(self):
        """Test site with integer specie (atomic number)."""
        site = Site([0, 0, 0], specie=26)  # Fe
        self.assertEqual(site.specie, 'Fe')
    
    def test_site_init_with_specie_element(self):
        """Test site with Element object."""
        site = Site([0, 0, 0], specie=Element('Fe'))
        self.assertEqual(site.specie, 'Fe')
    
    def test_site_init_with_properties(self):
        """Test site with properties."""
        site = Site([0, 0, 0], specie='Fe', properties={'magmom': 2.5})
        self.assertEqual(site.properties['magmom'], 2.5)
    
    def test_site_position_setter(self):
        """Test position setter."""
        site = Site([0, 0, 0])
        site.position = [1, 2, 3]
        np.testing.assert_array_equal(site.position, [1, 2, 3])
    
    def test_site_position_setter_invalid(self):
        """Test position setter with invalid input."""
        site = Site([0, 0, 0])
        with self.assertRaises(ValueError):
            site.position = [1, 2]  # Wrong length
    
    def test_site_specie_setter(self):
        """Test specie setter."""
        site = Site([0, 0, 0])
        site.specie = 'Fe'
        self.assertEqual(site.specie, 'Fe')
    
    def test_site_specie_setter_element(self):
        """Test specie setter with Element."""
        site = Site([0, 0, 0])
        site.specie = Element('Fe')
        self.assertEqual(site.specie, 'Fe')
    
    def test_site_properties_setter(self):
        """Test properties setter."""
        site = Site([0, 0, 0])
        site.properties = {'charge': 2}
        self.assertEqual(site.properties['charge'], 2)
    
    def test_site_properties_setter_invalid(self):
        """Test properties setter with invalid input."""
        site = Site([0, 0, 0])
        with self.assertRaises(TypeError):
            site.properties = "not_a_dict"
    
    def test_site_as_dict(self):
        """Test dictionary representation."""
        site = Site([0, 0, 0], specie='Fe', properties={'magmom': 2.5})
        d = site.as_dict()
        self.assertIn('position', d)
        self.assertIn('specie', d)
        self.assertIn('properties', d)
    
    def test_site_from_dict(self):
        """Test creation from dictionary."""
        d = {
            'position': [0, 0, 0],
            'specie': 'Fe',
            'properties': {'magmom': 2.5}
        }
        site = Site.from_dict(d)
        self.assertEqual(site.specie, 'Fe')
        self.assertEqual(site.properties['magmom'], 2.5)
    
    def test_site_repr(self):
        """Test representation."""
        site = Site([0, 0, 0], specie='Fe')
        repr_str = repr(site)
        self.assertIn('Site', repr_str)
        self.assertIn('Fe', repr_str)
    
    def test_site_str(self):
        """Test string representation."""
        site = Site([0, 0, 0], specie='Fe')
        str_repr = str(site)
        self.assertIn('Fe', str_repr)


class TestCrystalSiteComprehensive(unittest.TestCase):
    """Comprehensive tests for CrystalSite class."""
    
    def test_crystalsite_init_fractional(self):
        """Test CrystalSite initialization with fractional coordinates."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        self.assertEqual(site.specie, 'Fe')
        np.testing.assert_array_almost_equal(site.frac_position, [0.5, 0.5, 0.5])
    
    def test_crystalsite_init_cartesian(self):
        """Test CrystalSite initialization with cartesian coordinates."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([5, 5, 5], 'Fe', lattice, coords_are_cartesian=True)
        
        np.testing.assert_array_almost_equal(site.cart_position, [5, 5, 5])
    
    def test_crystalsite_coordinate_conversion(self):
        """Test coordinate conversion."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        # Convert fractional to cartesian
        cart = site.cart_position
        self.assertAlmostEqual(cart[0], 5.0, places=5)
        
        # Convert back
        frac_back = site._convert_to_fractional()
        np.testing.assert_array_almost_equal(site.frac_position, frac_back, decimal=6)
    
    def test_crystalsite_lattice_setter(self):
        """Test lattice setter."""
        lattice1 = Lattice.cubic(10.0)
        lattice2 = Lattice.cubic(20.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice1)
        
        site.lattice = lattice2
        self.assertEqual(site.lattice.a, 20.0)
    
    def test_crystalsite_lattice_setter_list(self):
        """Test lattice setter with list."""
        lattice_vectors = [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice_vectors)
        
        self.assertIsInstance(site.lattice, Lattice)
        self.assertEqual(site.lattice.a, 10.0)
    
    def test_crystalsite_lattice_setter_invalid(self):
        """Test lattice setter with invalid input."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        with self.assertRaises(TypeError):
            site.lattice = "not_a_lattice"
    
    def test_crystalsite_as_dict(self):
        """Test dictionary representation."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        d = site.as_dict()
        self.assertIn('lattice', d)
        self.assertIn('position', d)
    
    def test_crystalsite_from_dict(self):
        """Test creation from dictionary."""
        d = {
            'position': [0.5, 0.5, 0.5],
            'specie': 'Fe',
            'properties': {},
            'lattice': {
                'lattice_vectors': [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
            }
        }
        site = CrystalSite.from_dict(d)
        self.assertEqual(site.specie, 'Fe')
        self.assertIsInstance(site.lattice, Lattice)
    
    def test_crystalsite_repr(self):
        """Test representation."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        repr_str = repr(site)
        self.assertIn('CrystalSite', repr_str)
        self.assertIn('Fe', repr_str)
    
    def test_crystalsite_str(self):
        """Test string representation."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        str_repr = str(site)
        self.assertIn('Fe', str_repr)


if __name__ == '__main__':
    unittest.main()

