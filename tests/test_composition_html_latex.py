"""Tests for Composition HTML and LaTeX output."""
import unittest
import re

from matsimpy.core import Composition

class TestCompositionHTML(unittest.TestCase):
    """Tests for HTML output of Composition."""
    
    def test_simple_formula_html(self):
        """Test simple formula HTML output."""
        c = Composition('H2O')
        html = c.to_html()
        self.assertEqual(html, 'H<sub>2</sub>O')
    
    def test_multiple_elements_html(self):
        """Test formula with multiple elements HTML output."""
        c = Composition('Fe2O3')
        html = c.to_html()
        self.assertEqual(html, 'Fe<sub>2</sub>O<sub>3</sub>')
    
    def test_single_atom_html(self):
        """Test formula with single atoms HTML output."""
        c = Composition('NaCl')
        html = c.to_html()
        self.assertEqual(html, 'ClNa')  # Alphabetically sorted
    
    def test_complex_formula_html(self):
        """Test complex formula HTML output."""
        c = Composition('Ca(OH)2')
        html = c.to_html()
        self.assertIn('Ca', html)
        self.assertIn('<sub>2</sub>', html)  # Should have H2
        self.assertIn('O', html)
    
    def test_element_sorting_html(self):
        """Test HTML output with element number sorting."""
        c = Composition('Fe2O3', sort_by='element')
        html = c.to_html()
        # Should still have proper HTML formatting
        self.assertIn('<sub>', html)
        self.assertIn('Fe', html)
        self.assertIn('O', html)

class TestCompositionLaTeX(unittest.TestCase):
    """Tests for LaTeX output of Composition."""
    
    def test_simple_formula_latex(self):
        """Test simple formula LaTeX output."""
        c = Composition('H2O')
        latex = c.to_latex()
        self.assertEqual(latex, 'H$_{2}$O')
    
    def test_multiple_elements_latex(self):
        """Test formula with multiple elements LaTeX output."""
        c = Composition('Fe2O3')
        latex = c.to_latex()
        self.assertEqual(latex, 'Fe$_{2}$O$_{3}$')
    
    def test_single_atom_latex(self):
        """Test formula with single atoms LaTeX output."""
        c = Composition('NaCl')
        latex = c.to_latex()
        self.assertEqual(latex, 'ClNa')  # Alphabetically sorted, no subscripts
    
    def test_complex_formula_latex(self):
        """Test complex formula LaTeX output."""
        c = Composition('Ca(OH)2')
        latex = c.to_latex()
        self.assertIn('Ca', latex)
        self.assertIn('$_{2}$', latex)  # Should have subscript 2
        self.assertIn('O', latex)
    
    def test_element_sorting_latex(self):
        """Test LaTeX output with element number sorting."""
        c = Composition('Fe2O3', sort_by='element')
        latex = c.to_latex()
        # Should still have proper LaTeX formatting
        self.assertIn('$_{', latex)
        self.assertIn('Fe', latex)
        self.assertIn('O', latex)

class TestCompositionOutputConsistency(unittest.TestCase):
    """Tests for consistency between HTML and LaTeX output."""
    
    def test_output_consistency(self):
        """Test that HTML and LaTeX output have same elements."""
        formulas = ['H2O', 'Fe2O3', 'Ca(OH)2', 'NaCl', 'C6H12O6']
        
        for formula in formulas:
            c = Composition(formula)
            html = c.to_html()
            latex = c.to_latex()
            
            # Extract elements from both (remove formatting)
            html_elements = set(re.findall(r'([A-Z][a-z]*)', html))
            latex_elements = set(re.findall(r'([A-Z][a-z]*)', latex))
            
            self.assertEqual(html_elements, latex_elements,
                           f"Elements mismatch for {formula}: HTML={html_elements}, LaTeX={latex_elements}")
    
    def test_no_subscripts_for_count_one(self):
        """Test that count of 1 doesn't create subscripts."""
        c = Composition('NaCl')
        html = c.to_html()
        latex = c.to_latex()
        
        # Neither should have subscripts for count 1
        self.assertNotIn('<sub>1</sub>', html)
        self.assertNotIn('$_{1}$', latex)

if __name__ == '__main__':
    unittest.main()

