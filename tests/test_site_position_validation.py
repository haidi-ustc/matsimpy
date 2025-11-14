"""Tests for Site position validation."""
import os
import sys
import unittest
import numpy as np
import warnings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core.site import Site, CrystalSite
from matsimpy.core import Lattice


class TestSitePositionValidation(unittest.TestCase):
    """Test position validation in Site class."""
    
    def test_valid_position_list(self):
        """Test that valid position list works."""
        site = Site([0, 0, 0], 'C')
        self.assertTrue(np.allclose(site.position, [0, 0, 0]))
    
    def test_valid_position_array(self):
        """Test that valid numpy array works."""
        position = np.array([1.5, 2.3, 3.7])
        site = Site(position, 'C')
        self.assertTrue(np.allclose(site.position, position))
    
    def test_position_with_floats(self):
        """Test position with floating-point numbers."""
        site = Site([1.23, -4.56, 7.89], 'C')
        self.assertTrue(np.allclose(site.position, [1.23, -4.56, 7.89]))
    
    def test_position_with_ints(self):
        """Test position with integers."""
        site = Site([1, 2, 3], 'C')
        self.assertTrue(np.allclose(site.position, [1.0, 2.0, 3.0]))
    
    def test_position_nan_raises_error(self):
        """Test that NaN in position raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Site([np.nan, 0, 0], 'C')
        self.assertIn("finite", str(context.exception).lower())
    
    def test_position_inf_raises_error(self):
        """Test that inf in position raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Site([np.inf, 0, 0], 'C')
        self.assertIn("finite", str(context.exception).lower())
    
    def test_position_negative_inf_raises_error(self):
        """Test that -inf in position raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Site([0, -np.inf, 0], 'C')
        self.assertIn("finite", str(context.exception).lower())
    
    def test_position_with_nan_array(self):
        """Test that numpy array with NaN raises ValueError."""
        position = np.array([1.0, np.nan, 3.0])
        with self.assertRaises(ValueError) as context:
            Site(position, 'C')
        self.assertIn("finite", str(context.exception).lower())
    
    def test_position_large_values_warning(self):
        """Test that very large coordinates trigger warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Site([1e7, 0, 0], 'C')
            
            # Check that warning was raised
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, UserWarning))
            self.assertIn("large", str(w[0].message).lower())
    
    def test_position_negative_large_values_warning(self):
        """Test that large negative coordinates trigger warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Site([0, -1e7, 0], 'C')
            
            self.assertEqual(len(w), 1)
            self.assertIn("large", str(w[0].message).lower())
    
    def test_position_boundary_no_warning(self):
        """Test that values just below threshold don't trigger warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Site([9.9e5, 0, 0], 'C')  # Just below 1e6
            
            # Should not raise warning
            self.assertEqual(len(w), 0)
    
    def test_position_boundary_with_warning(self):
        """Test that values just above threshold trigger warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Site([1.1e6, 0, 0], 'C')  # Just above 1e6
            
            # Should raise warning
            self.assertEqual(len(w), 1)
    
    def test_position_wrong_length_raises_error(self):
        """Test that position with wrong number of elements raises error."""
        with self.assertRaises(ValueError):
            Site([0, 0], 'C')  # Only 2 elements
        
        with self.assertRaises(ValueError):
            Site([0, 0, 0, 0], 'C')  # 4 elements
    
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
    
    def test_position_setter_validates(self):
        """Test that position setter also validates."""
        site = Site([0, 0, 0], 'C')
        
        # Valid update
        site.position = [1, 2, 3]
        self.assertTrue(np.allclose(site.position, [1, 2, 3]))
        
        # Invalid update with NaN
        with self.assertRaises(ValueError):
            site.position = [np.nan, 0, 0]
        
        # Position should not have changed
        self.assertTrue(np.allclose(site.position, [1, 2, 3]))


class TestCrystalSitePositionValidation(unittest.TestCase):
    """Test position validation in CrystalSite class."""
    
    def setUp(self):
        """Set up test lattice."""
        self.lattice = Lattice.cubic(10.0)
    
    def test_valid_fractional_position(self):
        """Test valid fractional coordinates."""
        site = CrystalSite([0.5, 0.5, 0.5], 'Si', self.lattice)
        self.assertTrue(np.allclose(site.frac_coords, [0.5, 0.5, 0.5]))
    
    def test_fractional_position_with_nan(self):
        """Test that NaN in fractional coordinates raises error."""
        with self.assertRaises(ValueError):
            CrystalSite([np.nan, 0.5, 0.5], 'Si', self.lattice)
    
    def test_fractional_position_with_inf(self):
        """Test that inf in fractional coordinates raises error."""
        with warnings.catch_warnings():
            # Suppress RuntimeWarning from dot product with inf values
            warnings.filterwarnings("ignore", category=RuntimeWarning, message="invalid value encountered in dot")
            with self.assertRaises(ValueError):
                CrystalSite([np.inf, 0.5, 0.5], 'Si', self.lattice)
    
    def test_large_fractional_coordinates_warning(self):
        """Test that very large fractional coordinates trigger warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            CrystalSite([1e7, 0, 0], 'Si', self.lattice)
            
            self.assertEqual(len(w), 1)
            self.assertIn("large", str(w[0].message).lower())
    
    def test_cartesian_conversion_validation(self):
        """Test that Cartesian coordinates are also validated."""
        # Create site with valid fractional coords
        site = CrystalSite([0.5, 0.5, 0.5], 'Si', self.lattice)
        
        # Cartesian should be valid (no NaN/inf)
        self.assertTrue(np.all(np.isfinite(site.cart_position)))


class TestPositionValidationEdgeCases(unittest.TestCase):
    """Test edge cases for position validation."""
    
    def test_zero_position(self):
        """Test that zero position is valid."""
        site = Site([0, 0, 0], 'C')
        self.assertTrue(np.allclose(site.position, [0, 0, 0]))
    
    def test_very_small_position(self):
        """Test that very small (but valid) positions work."""
        site = Site([1e-10, 1e-10, 1e-10], 'C')
        self.assertTrue(np.allclose(site.position, [1e-10, 1e-10, 1e-10]))
    
    def test_mixed_large_small_warning(self):
        """Test that warning triggers with mixed coordinates."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Site([1e7, 0, 1e-10], 'C')
            
            # Should warn because one coordinate is large
            self.assertEqual(len(w), 1)
    
    def test_all_large_warning(self):
        """Test warning with all large coordinates."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Site([1e7, 2e7, 3e7], 'C')
            
            self.assertEqual(len(w), 1)
    
    def test_multiple_nan_raises_error(self):
        """Test that multiple NaN values still raise error."""
        with self.assertRaises(ValueError):
            Site([np.nan, np.nan, np.nan], 'C')
    
    def test_mixed_nan_inf_raises_error(self):
        """Test that mixed NaN and inf raise error."""
        with self.assertRaises(ValueError):
            Site([np.nan, np.inf, 0], 'C')


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
    
    def test_site_update_position_validates(self):
        """Test that updating position validates."""
        site = Site([0, 0, 0], 'C')
        
        # Update with valid position
        site.position = [1, 1, 1]
        self.assertTrue(np.allclose(site.position, [1, 1, 1]))
        
        # Try to update with invalid position
        with self.assertRaises(ValueError):
            site.position = [np.inf, 0, 0]
    
    def test_multiple_sites_with_validation(self):
        """Test creating multiple sites with validation."""
        # All valid
        sites = [
            Site([0, 0, 0], 'C'),
            Site([1, 1, 1], 'O'),
            Site([2, 2, 2], 'N')
        ]
        self.assertEqual(len(sites), 3)
        
        # One invalid should not affect others
        with self.assertRaises(ValueError):
            Site([np.nan, 0, 0], 'H')
        
        # Previously created sites should be fine
        self.assertEqual(len(sites), 3)


if __name__ == '__main__':
    unittest.main()

