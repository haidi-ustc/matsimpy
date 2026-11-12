"""Comprehensive tests for Composition class."""
import unittest


from matsimpy.core import Composition

class TestCompositionComprehensive(unittest.TestCase):
    """Comprehensive tests for Composition class."""
    
    
    
    def test_composition_invalid_sort_by(self):
        """Test invalid sort_by parameter."""
        with self.assertRaises(ValueError):
            Composition('H2O', sort_by='invalid')
    
    
    def test_composition_nested_groups(self):
        """Test nested groups in formula."""
        comp = Composition('Ca(OH)2(CO3)')
        self.assertEqual(comp['Ca'], 1)
        self.assertEqual(comp['O'], 5)  # 2 from OH + 3 from CO3
        self.assertEqual(comp['H'], 2)
        self.assertEqual(comp['C'], 1)
    
    
    
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
    
    
    def test_composition_from_json(self):
        """Test JSON deserialization."""
        comp = Composition('H2O')
        json_str = comp.to_json()
        comp2 = Composition.from_json(json_str)
        self.assertEqual(comp, comp2)
    
    
    def test_composition_as_dict_uses_processed_formula(self):
        """as_dict stores the processed formula, not raw input."""
        # Input "OH2" with element sorting produces "H2O"
        comp = Composition("OH2", sort_by="element")
        d = comp.as_dict()
        self.assertEqual(d["formula"], "H2O")  # processed, not raw "OH2"
        # Round-trip: from_dict(as_dict()) preserves the formula
        comp2 = Composition.from_dict(d)
        self.assertEqual(comp2.formula, "H2O")
        self.assertEqual(str(comp2), "H2O")

    def test_composition_from_dict(self):
        """Test creation from dictionary."""
        d = {'formula': 'H2O'}
        comp = Composition.from_dict(d)
        self.assertEqual(comp.formula, 'H2O')

    
    
    

    def test_reduced_formula_already_reduced(self):
        """Already reduced: Fe2O3 stays Fe2O3."""
        comp = Composition("Fe2O3")
        self.assertEqual(comp.reduced_formula, "Fe2O3")

    def test_reduced_formula_ternary(self):
        """Ternary: Ca2Mg2Si4O12 -> CaMgSi2O6 (GCD=2)."""
        comp = Composition("Ca2Mg2Si4O12")
        self.assertEqual(comp.reduced_formula, "CaMgSi2O6")

    def test_anonymous_formula_binary(self):
        """Fe2O3 -> A3B2 (O=8->A, Fe=26->B)."""
        comp = Composition("Fe2O3")
        # O (atomic_no=8) sorts first -> A with count 3 -> A3
        # Fe (atomic_no=26) sorts second -> B with count 2 -> B2
        self.assertEqual(comp.anonymous_formula, "A3B2")

    def test_anonymous_formula_same_atomic_number(self):
        """Elements with distinct atomic numbers but same stoichiometry."""
        comp = Composition("NaCl")
        # Na=11->A, Cl=17->B (sorted by atomic_no ascending: Na first, Cl second)
        self.assertEqual(comp.anonymous_formula, "AB")


if __name__ == '__main__':
    unittest.main()
