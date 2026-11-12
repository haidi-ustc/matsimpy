"""Comprehensive tests for Site and CrystalSite classes."""
import unittest
import numpy as np

from matsimpy.core import Site, CrystalSite, Lattice

class TestSiteComprehensive(unittest.TestCase):
    """Comprehensive tests for Site class."""
    
    
    
    
    

    def test_site_init_rejects_invalid_specie(self):
        """Test site initialization rejects invalid atomic numbers."""
        with self.assertRaises(ValueError):
            Site([0, 0, 0], specie=123)

    def test_site_init_rejects_invalid_properties(self):
        """Test site initialization rejects non-dict properties."""
        with self.assertRaises(TypeError):
            Site([0, 0, 0], properties="not_a_dict")
    
    
    def test_site_rejects_wrong_length_position(self):
        with self.assertRaises(ValueError):
            Site([1, 2])
    
    
    
    
    
    

    
    def test_site_repr(self):
        """Test representation (concise format)."""
        site = Site([0, 0, 0], specie='Fe')
        repr_str = repr(site)
        # __repr__ should be concise: "Fe @ [0.0, 0.0, 0.0] (cartesian)"
        self.assertIn('Fe', repr_str)
        self.assertIn('@', repr_str)
        self.assertIn('cartesian', repr_str)
    
    def test_site_str(self):
        """Test string representation (verbose format)."""
        site = Site([0, 0, 0], specie='Fe')
        str_repr = str(site)
        # __str__ should be verbose: "Site(position=[...], specie='Fe', ...)"
        self.assertIn('Site', str_repr)
        self.assertIn('Fe', str_repr)

class TestCrystalSiteComprehensive(unittest.TestCase):
    """Comprehensive tests for CrystalSite class."""
    
    
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
        frac_back = CrystalSite(cart, 'Fe', lattice, coords_are_cartesian=True).frac_position
        np.testing.assert_array_almost_equal(site.frac_position, frac_back, decimal=6)
    
    
    def test_crystalsite_accepts_lattice_as_list(self):
        lattice_vectors = [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice_vectors)
        
        self.assertIsInstance(site.lattice, Lattice)
        self.assertEqual(site.lattice.a, 10.0)
    
    def test_crystalsite_rejects_invalid_lattice(self):
        with self.assertRaises(TypeError):
            CrystalSite([0.5, 0.5, 0.5], 'Fe', "not_a_lattice")
    
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
        """Test representation (concise format)."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        repr_str = repr(site)
        # __repr__ should be concise: "Fe @ [0.5, 0.5, 0.5] (frac)"
        self.assertIn('Fe', repr_str)
        self.assertIn('@', repr_str)
        self.assertIn('frac', repr_str)
    
    def test_crystalsite_str(self):
        """Test string representation (verbose format)."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        
        str_repr = str(site)
        # __str__ should be verbose: "CrystalSite(position=[...], specie='Fe', lattice=..., ...)"
        self.assertIn('CrystalSite', str_repr)
        self.assertIn('Fe', str_repr)
    


    
    def test_crystalsite_wrap_returns_new_instance(self):
        """wrap() returns a new CrystalSite; original is left unchanged."""
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([1.5, -0.3, 0.5], 'Fe', lattice)

        result = site.wrap()

        # Must be a different object (immutable pattern)
        self.assertIsNot(result, site)
        # Wrapped result has correct fractional coordinates
        np.testing.assert_array_almost_equal(
            result.frac_position, [0.5, 0.7, 0.5], decimal=6
        )
        # Original is unchanged
        np.testing.assert_array_almost_equal(
            site.frac_position, [1.5, -0.3, 0.5], decimal=6
        )


if __name__ == '__main__':
    unittest.main()
