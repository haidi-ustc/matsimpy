"""Tests for Composition HTML and LaTeX output."""
import unittest

from matsimpy.core import Composition

class TestCompositionHTML(unittest.TestCase):
    """Tests for HTML output of Composition."""
    
    def test_simple_formula_html(self):
        """Test simple formula HTML output."""
        c = Composition('H2O')
        html = c.to_html()
        self.assertEqual(html, 'H<sub>2</sub>O')
    
    
    
    def test_complex_formula_html(self):
        """Test complex formula HTML output."""
        c = Composition('Ca(OH)2')
        html = c.to_html()
        self.assertIn('Ca', html)
        self.assertIn('<sub>2</sub>', html)  # Should have H2
        self.assertIn('O', html)
    


if __name__ == '__main__':
    unittest.main()

