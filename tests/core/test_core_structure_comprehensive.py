"""
Comprehensive tests for Structure class in core module.

This test suite covers:
- Initialization with various input types
- All methods and properties
- Edge cases and error handling
- Integration with other core classes
"""
import unittest
from matsimpy.core import Molecule


class TestStructureProperties(unittest.TestCase):
    """Test Structure properties and caching."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.species = ['H', 'O', 'H']
        self.positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        self.struct = Molecule(self.species, self.positions)
    
    
    
    def test_species_immutability(self):
        """Test that species tuple is immutable."""
        with self.assertRaises(AttributeError):
            self.struct.species.append('C')
    
    
    
    
    
    
    

    
class TestStructureSorting(unittest.TestCase):
    """Test Structure sorting methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.species = ['O', 'H', 'C', 'N']
        self.positions = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]]
        self.struct = Molecule(self.species, self.positions)


    
    def test_sort_atoms_invalid_method(self):
        """Test sorting with invalid method raises ValueError."""
        with self.assertRaises(ValueError):
            self.struct.sort_atoms('invalid')
    


if __name__ == '__main__':
    unittest.main()

