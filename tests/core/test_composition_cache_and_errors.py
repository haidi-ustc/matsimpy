"""Tests for Composition cache behavior and error handling."""
import unittest

from matsimpy.core.composition import Composition, _get_element_cached

class TestCompositionErrorHandling(unittest.TestCase):
    """Test enhanced error handling in Composition."""
    
    def test_empty_formula_raises_error(self):
        """Test that empty formula raises ValueError."""
        with self.assertRaises(ValueError) as context:
            Composition('')
        
        self.assertIn("empty", str(context.exception).lower())
    
    def test_whitespace_only_formula_raises_error(self):
        """Test that whitespace-only formula raises error."""
        with self.assertRaises(ValueError):
            Composition('   ')
    
    def test_invalid_formulas_raise_error(self):
        """Test that various invalid formulas raise ValueError."""
        invalid_formulas = ['H2O@#$', 'H2 O', 'H2O!', 'Fe*2', 'Si-O2', 'C+H4']
        for formula in invalid_formulas:
            with self.assertRaises(ValueError):
                Composition(formula)
    
    def test_valid_formulas_pass(self):
        """Test that valid formulas work."""
        valid_formulas = ['H2O', 'Fe2O3', 'Ca(OH)2', 'NaCl', 'Si']
        
        for formula in valid_formulas:
            comp = Composition(formula)
            self.assertIsInstance(comp, Composition)

class TestCompositionCaching(unittest.TestCase):
    """Test caching optimizations."""
    
    def test_mass_caching(self):
        """Test that mass is cached after first calculation."""
        comp = Composition('H2O')
        
        # First call
        mass1 = comp.mass
        
        # Should have cache now
        self.assertIsNotNone(comp._cached_mass)
        
        # Second call should return cached value
        mass2 = comp.mass
        
        self.assertEqual(mass1, mass2)
        self.assertEqual(comp._cached_mass, mass1)
    
    def test_element_caching(self):
        """Test that Element instances are cached."""
        comp = Composition('H2O')
        
        # Calculate mass (populates cache)
        _ = comp.mass
        # Module-level cache should have been used at least once
        info = _get_element_cached.cache_info()
        self.assertGreaterEqual(info.hits + info.misses, 1)
    
    def test_element_cache_reused(self):
        """Test that cached elements are reused."""
        # Calling twice should hit lru_cache and return the same object.
        elem_h1 = _get_element_cached("H")
        elem_h2 = _get_element_cached("H")
        self.assertIs(elem_h1, elem_h2)
    
    def test_mass_uses_cache_after_first_calculation(self):
        """Test that repeated mass calculations use the cached value."""
        comp = Composition('Fe2O3')

        mass = comp.mass
        for _ in range(100):
            self.assertEqual(comp.mass, mass)

        self.assertEqual(comp._cached_mass, mass)

class TestCompositionHelperMethod(unittest.TestCase):
    """Test _get_sorted_element_counts helper method."""
    
    def test_helper_sorts_alphabetically(self):
        """Test alphabetical sorting."""
        counts = {'O': 2, 'H': 1, 'C': 3}
        sorted_counts = Composition._get_sorted_element_counts(counts, 'alphabet')
        
        self.assertEqual(sorted_counts[0][0], 'C')
        self.assertEqual(sorted_counts[1][0], 'H')
        self.assertEqual(sorted_counts[2][0], 'O')
    
    def test_helper_sorts_by_element(self):
        """Test sorting by atomic number."""
        counts = {'O': 2, 'H': 1, 'C': 3}  # H(1), C(6), O(8)
        sorted_counts = Composition._get_sorted_element_counts(counts, 'element')
        
        self.assertEqual(sorted_counts[0][0], 'H')
        self.assertEqual(sorted_counts[1][0], 'C')
        self.assertEqual(sorted_counts[2][0], 'O')
    
    def test_helper_raises_on_invalid_sort(self):
        """Test that invalid sort_by raises error."""
        counts = {'H': 1}
        
        with self.assertRaises(ValueError) as context:
            Composition._get_sorted_element_counts(counts, 'invalid')
        
        self.assertIn("None, 'alphabet', or 'element'", str(context.exception))

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
    
    def test_different_sort_methods_work(self):
        """Test different sorting methods."""
        comp_alpha = Composition('Fe2O3', sort_by='alphabet')
        comp_elem = Composition('Fe2O3', sort_by='element')
        
        # Both should work
        self.assertIsInstance(comp_alpha.formula, str)
        self.assertIsInstance(comp_elem.formula, str)
        
        # HTML and LaTeX should work with both
        for comp in [comp_alpha, comp_elem]:
            html = comp.to_html()
            latex = comp.to_latex()
            self.assertIn('Fe', html)
            self.assertIn('Fe', latex)

if __name__ == '__main__':
    unittest.main()
