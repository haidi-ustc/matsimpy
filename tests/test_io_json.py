"""Tests for JSON IO module."""
import unittest
import tempfile
import json
import numpy as np
from pathlib import Path

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
    
    def test_to_json_string(self):
        """Test JSON serialization to string."""
        json_str = to_json(self.crystal)
        self.assertIsInstance(json_str, str)
        
        # Should be valid JSON
        data = json.loads(json_str)
        self.assertIn('@class', data)
        self.assertIn('species', data)
    
    def test_to_json_file(self):
        """Test JSON serialization to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            to_json(self.crystal, temp_file)
            
            # Verify file exists and is valid JSON
            self.assertTrue(Path(temp_file).exists())
            with open(temp_file, 'r') as f:
                data = json.load(f)
                self.assertIn('@class', data)
        finally:
            Path(temp_file).unlink()
    
    def test_from_json_string(self):
        """Test JSON deserialization from string."""
        json_str = to_json(self.crystal)
        crystal2 = from_json(json_string=json_str)
        
        self.assertIsInstance(crystal2, Crystal)
        self.assertEqual(len(crystal2), 2)
        self.assertEqual(crystal2.species, ('Si', 'O'))
    
    def test_from_json_file(self):
        """Test JSON deserialization from file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            to_json(self.crystal, temp_file)
            crystal2 = from_json(filename=temp_file)
            
            self.assertIsInstance(crystal2, Crystal)
            self.assertEqual(len(crystal2), 2)
        finally:
            Path(temp_file).unlink()
    
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
    
    def test_json_roundtrip_crystal(self):
        """Test complete roundtrip for Crystal."""
        json_str = to_json(self.crystal)
        crystal2 = from_json(json_string=json_str)
        
        # Verify structure matches
        self.assertEqual(crystal2.species, self.crystal.species)
        np.testing.assert_array_almost_equal(
            crystal2.positions, 
            self.crystal.positions,
            decimal=6
        )
    
    def test_json_roundtrip_molecule(self):
        """Test complete roundtrip for Molecule."""
        json_str = to_json(self.molecule)
        molecule2 = from_json(json_string=json_str)
        
        self.assertEqual(molecule2.species, self.molecule.species)
        np.testing.assert_array_almost_equal(
            molecule2.positions,
            self.molecule.positions,
            decimal=6
        )

if __name__ == '__main__':
    unittest.main()

