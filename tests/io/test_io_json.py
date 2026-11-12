"""Tests for JSON IO module."""
import unittest

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.io import to_json, from_json

class TestJSONIo(unittest.TestCase):
    """Tests for JSON serialization."""
    
    def setUp(self):
        """Set up test structures."""
        self.species = ['Si', 'O']
        self.positions = [[0, 0, 0], [0.25, 0.25, 0.25]]
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(self.species, self.positions, self.lattice)
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    
    
    
    
    def test_from_json_molecule(self):
        """Test JSON serialization for molecules."""
        json_str = to_json(self.molecule)
        molecule2 = from_json(json_string=json_str)
        
        self.assertIsInstance(molecule2, Molecule)
        self.assertEqual(len(molecule2), 2)
    
    def test_from_json_both_params_error(self):
        """Test error when both json_string and filename provided."""
        with self.assertRaises(ValueError):
            from_json(json_string='{}', filename='test.json')
    
    def test_from_json_neither_param_error(self):
        """Test error when neither json_string nor filename provided."""
        with self.assertRaises(ValueError):
            from_json()
    
    def test_from_json_file_not_found(self):
        """Test error for non-existent file."""
        with self.assertRaises(FileNotFoundError):
            from_json(filename='nonexistent.json')
    
    def test_to_json_invalid_object(self):
        """Test error for non-serializable object."""
        with self.assertRaises(TypeError):
            to_json("not a structure")
    
    

if __name__ == '__main__':
    unittest.main()

