"""Tests for Site position validation."""
import unittest
import numpy as np
import warnings

from matsimpy.core.site import Site, CrystalSite
from matsimpy.core import Lattice

class TestSitePositionValidation(unittest.TestCase):
    """Test position validation in Site class."""
    
    
    
    
    
    
    
    
    
    
    
    
    def test_position_boundary_with_warning(self):
        """Test that values just above threshold trigger warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Site([1.1e6, 0, 0], 'C')  # Just above 1e6
            
            # Should raise warning
            self.assertEqual(len(w), 1)
    
    
    def test_position_wrong_type_raises_error(self):
        """Test that non-list/array position raises error."""
        with self.assertRaises(TypeError):
            Site("invalid", 'C')
        
        with self.assertRaises(TypeError):
            Site(123, 'C')
    
    def test_position_non_numeric_raises_error(self):
        """Test that non-numeric elements raise error."""
        with self.assertRaises(TypeError):
            Site(['a', 'b', 'c'], 'C')
        
        with self.assertRaises(TypeError):
            Site([1, 2, 'three'], 'C')
    

class TestCrystalSitePositionValidation(unittest.TestCase):
    """Test position validation in CrystalSite class."""
    
    def setUp(self):
        """Set up test lattice."""
        self.lattice = Lattice.cubic(10.0)
    
    
    
    def test_fractional_position_with_inf(self):
        """Test that inf in fractional coordinates raises error."""
        with warnings.catch_warnings():
            # Suppress RuntimeWarning from dot product with inf values
            warnings.filterwarnings("ignore", category=RuntimeWarning, message="invalid value encountered in dot")
            with self.assertRaises(ValueError):
                CrystalSite([np.inf, 0.5, 0.5], 'Si', self.lattice)
    
    


class TestPositionValidationIntegration(unittest.TestCase):
    """Test position validation in real-world scenarios."""
    
    def test_site_from_dict_validates(self):
        """Test that from_dict also validates positions."""
        # Valid site
        d = {
            "@module": "matsimpy.core.site",
            "@class": "Site",
            "position": [0, 0, 0],
            "specie": "C",
            "properties": {}
        }
        site = Site.from_dict(d)
        self.assertEqual(site.specie, 'C')
        
        # Invalid site with NaN
        d_invalid = d.copy()
        d_invalid["position"] = [np.nan, 0, 0]
        
        with self.assertRaises(ValueError):
            Site.from_dict(d_invalid)
    
    

if __name__ == '__main__':
    unittest.main()

