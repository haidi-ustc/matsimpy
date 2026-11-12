"""Tests for Element __getattr__ enhanced error handling."""
import unittest

from matsimpy.core.periodic_table import Element

class TestElementGetAttr(unittest.TestCase):
    """Test __getattr__ method for better error messages."""
    
    def setUp(self):
        """Set up test elements."""
        self.element = Element('Fe')
    
    
    
    
    
    
    
    def test_different_elements_error_messages(self):
        """Test error messages for different elements."""
        h = Element('H')
        c = Element('C')
        
        # Both should raise AttributeError with helpful messages
        with self.assertRaises(AttributeError) as context_h:
            _ = h.nonexistent
        
        with self.assertRaises(AttributeError) as context_c:
            _ = c.nonexistent
        
        # Both should mention "Element" and available attributes
        self.assertIn("Element", str(context_h.exception))
        self.assertIn("Element", str(context_c.exception))
        self.assertIn("Available", str(context_h.exception))
        self.assertIn("Available", str(context_c.exception))


class TestElementGetAttrEdgeCases(unittest.TestCase):
    """Test edge cases for __getattr__."""
    
    
    def test_dunder_attributes(self):
        """Test that dunder attributes work normally."""
        element = Element('Fe')
        
        # These should not trigger __getattr__
        self.assertIsNotNone(element.__class__)
        # Note: __dict__ doesn't exist when using __slots__ (which Element uses for optimization)
        # This is expected behavior - __slots__ prevents __dict__ creation
        with self.assertRaises(AttributeError):
            _ = element.__dict__
    
    


if __name__ == '__main__':
    unittest.main()

