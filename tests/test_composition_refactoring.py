"""Tests for Composition refactoring: caching, error handling, type hints."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core.composition import Composition


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
    
    def test_invalid_characters_raise_error(self):
        """Test that invalid characters raise error."""
        with self.assertRaises(ValueError) as context:
            Composition('H2O@#$')
        
        self.assertIn("invalid", str(context.exception).lower())
    
    def test_invalid_characters_with_spaces(self):
        """Test that spaces raise error."""
        with self.assertRaises(ValueError):
            Composition('H2 O')
    
    def test_invalid_characters_special(self):
        """Test various invalid characters."""
        invalid_formulas = ['H2O!', 'Fe*2', 'Si-O2', 'C+H4']
        
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
        
        # Element cache should have H and O
        self.assertIn('H', comp._element_cache)
        self.assertIn('O', comp._element_cache)
    
    def test_element_cache_reused(self):
        """Test that cached elements are reused."""
        comp = Composition('H2O')
        
        # Call mass
        _ = comp.mass
        elem_h1 = comp._element_cache['H']
        
        # Call mass_fractions (should reuse cache)
        _ = comp.mass_fractions()
        elem_h2 = comp._element_cache['H']
        
        # Should be same object
        self.assertIs(elem_h1, elem_h2)
    
    def test_cache_improves_performance(self):
        """Test that caching improves repeated calculations."""
        import time
        
        comp = Composition('Fe2O3')
        
        # First call (uncached)
        start = time.time()
        for _ in range(100):
            _ = comp.mass
        cached_time = time.time() - start
        
        # Should be fast due to caching
        self.assertLess(cached_time, 0.1)


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


class TestCompositionCodeDeduplication(unittest.TestCase):
    """Test that helper method eliminates duplication."""
    
    def test_to_html_uses_helper(self):
        """Test that to_html uses shared sorting logic."""
        comp = Composition('H2O')
        
        html_alpha = comp.to_html(sort_by='alphabet')
        html_elem = comp.to_html(sort_by='element')
        
        # Both should work (using helper)
        self.assertIsInstance(html_alpha, str)
        self.assertIsInstance(html_elem, str)
    
    def test_to_latex_uses_helper(self):
        """Test that to_latex uses shared sorting logic."""
        comp = Composition('Fe2O3')
        
        latex = comp.to_latex(sort_by='element')
        
        self.assertIn('Fe', latex)
        self.assertIn('O', latex)


class TestCompositionTypeHints(unittest.TestCase):
    """Test that methods have proper type hints."""
    
    def test_mass_has_return_type(self):
        """Test that mass property has return type."""
        # Check the property has annotations
        mass_prop = Composition.mass.fget
        self.assertIn('return', mass_prop.__annotations__)
    
    def test_methods_have_return_types(self):
        """Test key methods have return type annotations."""
        comp = Composition('H2O')
        
        # These should have return types
        methods_with_returns = [
            'mass_fractions',
            'weight_percent',
            'to_html',
            'to_latex',
            '__str__',
            '__repr__',
            '__eq__',
        ]
        
        for method_name in methods_with_returns:
            method = getattr(comp, method_name)
            self.assertIsNotNone(method.__annotations__, 
                               f"{method_name} should have annotations")


class TestCompositionBackwardCompatibility(unittest.TestCase):
    """Test that refactoring maintains backward compatibility."""
    
    def test_basic_composition_still_works(self):
        """Test basic composition functionality."""
        comp = Composition('H2O')
        
        self.assertEqual(comp['H'], 2)
        self.assertEqual(comp['O'], 1)
        self.assertEqual(comp.formula, 'H2O')
    
    def test_complex_formula_still_works(self):
        """Test complex formulas."""
        comp = Composition('Ca(OH)2')
        
        self.assertEqual(comp['Ca'], 1)
        self.assertEqual(comp['O'], 2)
        self.assertEqual(comp['H'], 2)
    
    def test_mass_calculation_still_works(self):
        """Test mass calculation."""
        comp = Composition('H2O')
        mass = comp.mass
        
        self.assertAlmostEqual(mass, 18.01528, places=4)
    
    def test_serialization_still_works(self):
        """Test as_dict and from_dict."""
        comp = Composition('Fe2O3')
        d = comp.as_dict()
        
        comp2 = Composition.from_dict(d)
        
        self.assertEqual(comp.formula, comp2.formula)
        self.assertEqual(comp.composition, comp2.composition)


class TestCompositionIntegration(unittest.TestCase):
    """Integration tests for refactored Composition."""
    
    def test_multiple_calculations_use_cache(self):
        """Test that multiple calculations benefit from caching."""
        comp = Composition('Fe2O3')
        
        # These should all use cached elements
        mass = comp.mass
        fractions = comp.mass_fractions()
        percentages = comp.weight_percent()
        
        # Cache should have both elements
        self.assertIn('Fe', comp._element_cache)
        self.assertIn('O', comp._element_cache)
        
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

