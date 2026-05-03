"""Tests for Element __getattr__ enhanced error handling."""
import unittest

from matsimpy.core.periodic_table import Element

class TestElementGetAttr(unittest.TestCase):
    """Test __getattr__ method for better error messages."""
    
    def setUp(self):
        """Set up test elements."""
        self.element = Element('Fe')
    
    def test_existing_property_works(self):
        """Test that existing properties work normally."""
        self.assertEqual(self.element.atomic_no, 26)
        self.assertEqual(self.element.symbol, 'Fe')
        self.assertIsNotNone(self.element.name)
    
    def test_invalid_attribute_raises_error(self):
        """Test that invalid attribute raises AttributeError."""
        with self.assertRaises(AttributeError):
            _ = self.element.invalid_attribute
    
    def test_error_message_includes_class_name(self):
        """Test that error message includes class name."""
        with self.assertRaises(AttributeError) as context:
            _ = self.element.nonexistent_attr
        
        self.assertIn("Element", str(context.exception))
    
    def test_error_message_includes_attribute_name(self):
        """Test that error message includes the requested attribute name."""
        with self.assertRaises(AttributeError) as context:
            _ = self.element.fake_property
        
        self.assertIn("fake_property", str(context.exception))
    
    def test_error_message_lists_available_attributes(self):
        """Test that error message lists available attributes."""
        with self.assertRaises(AttributeError) as context:
            _ = self.element.unknown_attr
        
        error_msg = str(context.exception)
        self.assertIn("Available data attributes:", error_msg)
        # Should contain some known attributes
        self.assertIn("Atomic no", error_msg)
    
    def test_getattr_returns_data_dict_values(self):
        """Test that __getattr__ can access _data dictionary values directly."""
        # Access via property
        atomic_no = self.element.atomic_no
        
        # Access directly via __getattr__ (if attribute name matches _data key)
        # Note: This only works if the key exists in _data but not as a property
        self.assertEqual(atomic_no, 26)
    
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

class TestElementDataAccess(unittest.TestCase):
    """Test accessing element data through __getattr__."""
    
    def setUp(self):
        """Set up test elements."""
        self.element = Element('C')
    
    def test_access_data_keys_directly(self):
        """Test accessing _data dictionary keys directly via __getattr__."""
        # If a key exists in _data but not as a property, __getattr__ should return it
        atomic_no = self.element.atomic_no
        self.assertEqual(atomic_no, 6)
    
    def test_property_takes_precedence(self):
        """Test that defined properties take precedence over __getattr__."""
        # atomic_no is defined as a property, so it should work normally
        self.assertEqual(self.element.atomic_no, 6)
        
        # symbol is a regular attribute, should work
        self.assertEqual(self.element.symbol, 'C')
    
    def test_multiple_invalid_attributes(self):
        """Test multiple invalid attribute accesses."""
        invalid_attrs = ['attr1', 'attr2', 'attr3', 'xyz', 'test']
        
        for attr in invalid_attrs:
            with self.assertRaises(AttributeError) as context:
                getattr(self.element, attr)
            
            # Each should have a helpful error message
            self.assertIn(attr, str(context.exception))
            self.assertIn("Available", str(context.exception))

class TestElementGetAttrEdgeCases(unittest.TestCase):
    """Test edge cases for __getattr__."""
    
    def test_private_attributes_not_affected(self):
        """Test that private attributes work normally."""
        element = Element('Fe')
        
        # Private attributes should work
        self.assertIsNotNone(element._data)
        self.assertEqual(element.symbol, 'Fe')
    
    def test_dunder_attributes(self):
        """Test that dunder attributes work normally."""
        element = Element('Fe')
        
        # These should not trigger __getattr__
        self.assertIsNotNone(element.__class__)
        # Note: __dict__ doesn't exist when using __slots__ (which Element uses for optimization)
        # This is expected behavior - __slots__ prevents __dict__ creation
        with self.assertRaises(AttributeError):
            _ = element.__dict__
    
    def test_error_with_typo_in_property_name(self):
        """Test helpful error when user makes typo in property name."""
        element = Element('Fe')
        
        # User tries to access 'atomic_num' instead of 'atomic_no'
        with self.assertRaises(AttributeError) as context:
            _ = element.atomic_num
        
        error_msg = str(context.exception)
        self.assertIn("atomic_num", error_msg)
        self.assertIn("Available", error_msg)
        # The error message should list the correct attribute name
        self.assertIn("Atomic no", error_msg)
    
    def test_case_sensitive_attribute_access(self):
        """Test that attribute access is case-sensitive."""
        element = Element('Fe')
        
        # Correct case works
        _ = element.atomic_no
        
        # Wrong case should fail with helpful message
        with self.assertRaises(AttributeError) as context:
            _ = element.ATOMIC_NO
        
        self.assertIn("ATOMIC_NO", str(context.exception))

class TestElementGetAttrMultipleElements(unittest.TestCase):
    """Test __getattr__ with multiple different elements."""
    
    def test_all_elements_have_getattr(self):
        """Test that __getattr__ works for various elements."""
        symbols = ['H', 'C', 'N', 'O', 'Fe', 'Cu', 'Au', 'U']
        
        for symbol in symbols:
            element = Element(symbol)
            
            # Valid property should work
            _ = element.atomic_no
            
            # Invalid attribute should raise helpful error
            with self.assertRaises(AttributeError) as context:
                _ = element.invalid_test_attr
            
            error_msg = str(context.exception)
            self.assertIn("Element", error_msg)
            self.assertIn("invalid_test_attr", error_msg)
            self.assertIn("Available", error_msg)
    
    def test_error_messages_are_consistent(self):
        """Test that error messages are consistent across elements."""
        h = Element('H')
        fe = Element('Fe')
        
        # Try same invalid attribute on different elements
        with self.assertRaises(AttributeError) as context_h:
            _ = h.test_attr
        
        with self.assertRaises(AttributeError) as context_fe:
            _ = fe.test_attr
        
        # Both should have similar structure
        msg_h = str(context_h.exception)
        msg_fe = str(context_fe.exception)
        
        # Both should mention the attribute and available attributes
        self.assertIn("test_attr", msg_h)
        self.assertIn("test_attr", msg_fe)
        self.assertIn("Available", msg_h)
        self.assertIn("Available", msg_fe)

class TestElementGetAttrIntegration(unittest.TestCase):
    """Integration tests for __getattr__ with other Element features."""
    
    def test_getattr_with_element_from_Z(self):
        """Test __getattr__ works with Element created from atomic number."""
        element = Element.from_Z(26)  # Iron
        
        # Valid attributes work
        self.assertEqual(element.atomic_no, 26)
        self.assertEqual(element.symbol, 'Fe')
        
        # Invalid attributes raise helpful error
        with self.assertRaises(AttributeError) as context:
            _ = element.invalid_attr
        
        self.assertIn("invalid_attr", str(context.exception))
        self.assertIn("Available", str(context.exception))
    
    def test_getattr_with_cached_element(self):
        """Test __getattr__ works with cached Element instances."""
        # Create element
        element1 = Element.get_element('Fe')
        
        # Get cached element
        element2 = Element.get_element('Fe')
        
        # Both should have same behavior
        for elem in [element1, element2]:
            with self.assertRaises(AttributeError) as context:
                _ = elem.nonexistent_attr
            
            self.assertIn("nonexistent_attr", str(context.exception))
    
    def test_hasattr_behavior(self):
        """Test that hasattr() works correctly with __getattr__."""
        element = Element('Fe')
        
        # Existing attributes
        self.assertTrue(hasattr(element, 'atomic_no'))
        self.assertTrue(hasattr(element, 'symbol'))
        
        # Non-existing attributes
        self.assertFalse(hasattr(element, 'invalid_attr'))
        self.assertFalse(hasattr(element, 'nonexistent'))
    
    def test_getattr_function_behavior(self):
        """Test getattr() built-in function with Element."""
        element = Element('Fe')
        
        # With default value for invalid attribute
        result = getattr(element, 'invalid_attr', 'default')
        self.assertEqual(result, 'default')
        
        # Without default value should raise AttributeError
        with self.assertRaises(AttributeError) as context:
            getattr(element, 'invalid_attr')
        
        self.assertIn("invalid_attr", str(context.exception))

if __name__ == '__main__':
    unittest.main()

