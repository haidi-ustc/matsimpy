"""Tests for Composition cache behavior and error handling."""
import unittest

from matsimpy.core.composition import Composition

class TestCompositionErrorHandling(unittest.TestCase):
    """Test enhanced error handling in Composition."""
    
    def test_empty_formula_raises_error(self):
        """Test that empty formula raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Composition('')
        
        self.assertIn("empty", str(context.exception).lower())
    
    
    


class TestCompositionIntegration(unittest.TestCase):
    """Integration tests for Composition behavior."""
    
    def test_multiple_calculations_use_cache(self):
        """Test that multiple calculations benefit from caching."""
        comp = Composition('Fe2O3')
        
        # These should all use cached elements
        mass = comp.mass
        fractions = comp.mass_fractions()
        mole_fractions = comp.mole_fractions()
        
        # Mass should be cached
        self.assertEqual(comp._cached_mass, mass)
    

if __name__ == '__main__':
    unittest.main()
