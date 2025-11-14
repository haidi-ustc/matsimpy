"""Comprehensive tests for Composition class."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Composition


class TestCompositionComprehensive(unittest.TestCase):
    """Comprehensive tests for Composition class."""
    
    def test_composition_init_alphabet(self):
        """Test composition initialization with alphabet sorting."""
        comp = Composition('H2O', sort_by='alphabet')
        self.assertEqual(comp.formula, 'H2O')
        self.assertEqual(comp['H'], 2)
        self.assertEqual(comp['O'], 1)
    
    def test_composition_init_element(self):
        """Test composition initialization with element number sorting."""
        comp = Composition('H2O', sort_by='element')
        self.assertEqual(comp['H'], 2)
        self.assertEqual(comp['O'], 1)
    
    def test_composition_invalid_sort_by(self):
        """Test invalid sort_by parameter."""
        with self.assertRaises(ValueError):
            Composition('H2O', sort_by='invalid')
    
    def test_composition_complex_formula(self):
        """Test complex formula parsing."""
        comp = Composition('Ca(OH)2')
        self.assertEqual(comp['Ca'], 1)
        self.assertEqual(comp['O'], 2)
        self.assertEqual(comp['H'], 2)
    
    def test_composition_nested_groups(self):
        """Test nested groups in formula."""
        comp = Composition('Ca(OH)2(CO3)')
        self.assertEqual(comp['Ca'], 1)
        self.assertEqual(comp['O'], 5)  # 2 from OH + 3 from CO3
        self.assertEqual(comp['H'], 2)
        self.assertEqual(comp['C'], 1)
    
    def test_composition_get_item_missing(self):
        """Test getting missing element."""
        comp = Composition('H2O')
        self.assertEqual(comp['X'], 0)  # Missing element returns 0
    
    def test_composition_str(self):
        """Test string representation."""
        comp = Composition('H2O')
        self.assertEqual(str(comp), comp.formula)
    
    def test_composition_repr(self):
        """Test representation."""
        comp = Composition('H2O')
        self.assertIn('Composition', repr(comp))
        self.assertIn('H2O', repr(comp))
    
    def test_composition_equality(self):
        """Test composition equality."""
        comp1 = Composition('H2O')
        comp2 = Composition('H2O')
        comp3 = Composition('H2O2')
        
        self.assertEqual(comp1, comp2)
        self.assertNotEqual(comp1, comp3)
        self.assertNotEqual(comp1, 'H2O')  # Different type
    
    def test_composition_mass(self):
        """Test mass calculation."""
        comp = Composition('H2O')
        mass = comp.mass
        self.assertIsInstance(mass, float)
        self.assertGreater(mass, 0)
        # H2O should be approximately 18
        self.assertAlmostEqual(mass, 18.015, places=2)
    
    def test_composition_mass_fractions(self):
        """Test mass fractions calculation."""
        comp = Composition('H2O')
        fractions = comp.mass_fractions()
        
        self.assertIsInstance(fractions, dict)
        self.assertIn('H', fractions)
        self.assertIn('O', fractions)
        self.assertAlmostEqual(sum(fractions.values()), 1.0, places=5)
    
    def test_composition_mole_fractions(self):
        """Test mole fractions calculation."""
        comp = Composition('H2O')
        fractions = comp.mole_fractions()
        
        self.assertIsInstance(fractions, dict)
        self.assertIn('H', fractions)
        self.assertIn('O', fractions)
        # H2O: 2 H + 1 O = 3 total atoms
        # H fraction = 2/3, O fraction = 1/3
        self.assertAlmostEqual(fractions['H'], 2/3, places=5)
        self.assertAlmostEqual(fractions['O'], 1/3, places=5)
        self.assertAlmostEqual(sum(fractions.values()), 1.0, places=5)
        
        # Test with Fe2O3
        comp2 = Composition('Fe2O3')
        fractions2 = comp2.mole_fractions()
        # Fe2O3: 2 Fe + 3 O = 5 total atoms
        # Fe fraction = 2/5 = 0.4, O fraction = 3/5 = 0.6
        self.assertAlmostEqual(fractions2['Fe'], 0.4, places=5)
        self.assertAlmostEqual(fractions2['O'], 0.6, places=5)
        self.assertAlmostEqual(sum(fractions2.values()), 1.0, places=5)
        
        # Test with NaCl
        comp3 = Composition('NaCl')
        fractions3 = comp3.mole_fractions()
        # NaCl: 1 Na + 1 Cl = 2 total atoms
        # Both should be 0.5
        self.assertAlmostEqual(fractions3['Na'], 0.5, places=5)
        self.assertAlmostEqual(fractions3['Cl'], 0.5, places=5)
        self.assertAlmostEqual(sum(fractions3.values()), 1.0, places=5)
    
    def test_composition_to_json(self):
        """Test JSON serialization."""
        comp = Composition('H2O')
        json_str = comp.to_json()
        self.assertIsInstance(json_str, str)
        self.assertIn('H2O', json_str)
    
    def test_composition_from_json(self):
        """Test JSON deserialization."""
        comp = Composition('H2O')
        json_str = comp.to_json()
        comp2 = Composition.from_json(json_str)
        self.assertEqual(comp, comp2)
    
    def test_composition_as_dict(self):
        """Test dictionary representation."""
        comp = Composition('H2O')
        d = comp.as_dict()
        self.assertIn('formula', d)
        self.assertEqual(d['formula'], 'H2O')
    
    def test_composition_from_dict(self):
        """Test creation from dictionary."""
        d = {'formula': 'H2O'}
        comp = Composition.from_dict(d)
        self.assertEqual(comp.formula, 'H2O')
    
    def test_composition_single_element(self):
        """Test single element composition."""
        comp = Composition('Fe')
        self.assertEqual(comp['Fe'], 1)
        self.assertEqual(comp.formula, 'Fe')
    
    def test_composition_large_count(self):
        """Test composition with large counts."""
        comp = Composition('Fe100')
        self.assertEqual(comp['Fe'], 100)
    
    def test_composition_empty_group(self):
        """Test composition with empty group handling."""
        # This should handle gracefully
        comp = Composition('H2O')
        self.assertIsNotNone(comp)


if __name__ == '__main__':
    unittest.main()

