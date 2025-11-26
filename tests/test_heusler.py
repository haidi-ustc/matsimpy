"""Tests for Heusler alloy builders."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.builders.alloy.heusler import (
    build_heusler,
    build_full_heusler,
    build_half_heusler,
    build_inverse_heusler,
)


class TestHeuslerAlloys(unittest.TestCase):
    """Tests for Heusler alloy builders."""
    
    def test_full_heusler_structure(self):
        """Test full Heusler alloy structure."""
        # Cu₂MnAl - the original Heusler
        crystal = build_full_heusler('Cu', 'Mn', 'Al', 5.95)
        
        # Check structure properties
        self.assertEqual(len(crystal), 16)  # Conventional cell
        # Formula preserves original species order: Cu, Mn, Al
        self.assertEqual(crystal.formula, 'Cu8Mn4Al4')
        
        # Check lattice
        self.assertAlmostEqual(crystal.lattice.a, 5.95, places=2)
        self.assertAlmostEqual(crystal.lattice.b, 5.95, places=2)
        self.assertAlmostEqual(crystal.lattice.c, 5.95, places=2)
    
    def test_half_heusler_structure(self):
        """Test half-Heusler alloy structure."""
        # NiMnSb
        crystal = build_half_heusler('Ni', 'Mn', 'Sb', 5.93)
        
        # Check structure properties
        self.assertEqual(len(crystal), 3)  # Primitive cell
        # Formula preserves original species order: Ni, Mn, Sb
        self.assertEqual(crystal.formula, 'NiMnSb')
        
        # Check lattice
        self.assertAlmostEqual(crystal.lattice.a, 5.93, places=2)
    
    def test_inverse_heusler_structure(self):
        """Test inverse Heusler alloy structure."""
        # Mn₂CoAl
        crystal = build_inverse_heusler('Mn', 'Co', 'Al', 5.85)
        
        # Check structure properties
        self.assertEqual(len(crystal), 16)  # Conventional cell
        # Formula preserves original species order: Mn, Co, Al
        self.assertEqual(crystal.formula, 'Mn8Co4Al4')
        
        # Check lattice
        self.assertAlmostEqual(crystal.lattice.a, 5.85, places=2)
    
    def test_build_heusler_generic_full(self):
        """Test generic build_heusler function with full type."""
        crystal = build_heusler('Co', 'Mn', 'Si', 5.65, 'full')
        
        self.assertEqual(len(crystal), 16)
        self.assertEqual(crystal.formula, 'Co8Mn4Si4')
    
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
    
    def test_full_heusler_composition(self):
        """Test that full Heusler has correct 2:1:1 composition."""
        crystal = build_full_heusler('X', 'Y', 'Z', 6.0)
        
        # Count atoms
        x_count = sum(1 for s in crystal.species if s == 'X')
        y_count = sum(1 for s in crystal.species if s == 'Y')
        z_count = sum(1 for s in crystal.species if s == 'Z')
        
        # In conventional cell: 8 X, 4 Y, 4 Z
        self.assertEqual(x_count, 8)
        self.assertEqual(y_count, 4)
        self.assertEqual(z_count, 4)
    
    def test_half_heusler_composition(self):
        """Test that half-Heusler has correct 1:1:1 composition."""
        crystal = build_half_heusler('X', 'Y', 'Z', 6.0)
        
        # Count atoms
        x_count = sum(1 for s in crystal.species if s == 'X')
        y_count = sum(1 for s in crystal.species if s == 'Y')
        z_count = sum(1 for s in crystal.species if s == 'Z')
        
        # In primitive cell: 1 X, 1 Y, 1 Z
        self.assertEqual(x_count, 1)
        self.assertEqual(y_count, 1)
        self.assertEqual(z_count, 1)
    
    def test_inverse_heusler_composition(self):
        """Test that inverse Heusler has correct 2:1:1 composition."""
        crystal = build_inverse_heusler('X', 'Y', 'Z', 6.0)
        
        # Count atoms
        x_count = sum(1 for s in crystal.species if s == 'X')
        y_count = sum(1 for s in crystal.species if s == 'Y')
        z_count = sum(1 for s in crystal.species if s == 'Z')
        
        # In conventional cell: 8 X, 4 Y, 4 Z
        self.assertEqual(x_count, 8)
        self.assertEqual(y_count, 4)
        self.assertEqual(z_count, 4)


if __name__ == '__main__':
    unittest.main()

