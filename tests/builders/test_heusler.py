"""Tests for Heusler alloy builders."""
import unittest

from matsimpy.builders.alloy.heusler import (
    build_heusler,
)

class TestHeuslerAlloys(unittest.TestCase):
    """Tests for Heusler alloy builders."""
    
    
    
    
    
    def test_build_heusler_generic_half(self):
        """Test generic build_heusler function with half type."""
        crystal = build_heusler('Co', 'Ti', 'Sb', 5.90, 'half')
        
        self.assertEqual(len(crystal), 3)
        # Formula preserves original species order: Co, Ti, Sb
        self.assertEqual(crystal.formula, 'CoTiSb')
    
    def test_build_heusler_generic_inverse(self):
        """Test generic build_heusler function with inverse type."""
        crystal = build_heusler('Mn', 'V', 'Al', 5.80, 'inverse')
        
        self.assertEqual(len(crystal), 16)
        # Formula preserves original species order: Mn, V, Al
        self.assertEqual(crystal.formula, 'Mn8V4Al4')
    
    def test_build_heusler_invalid_type(self):
        """Test that invalid Heusler type raises error."""
        with self.assertRaises(ValueError):
            build_heusler('Cu', 'Mn', 'Al', 5.95, 'invalid')
    
    
    

if __name__ == '__main__':
    unittest.main()

