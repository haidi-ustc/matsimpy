"""Tests for Molecule to_code/from_code methods."""
import unittest
import tempfile
from pathlib import Path

from matsimpy.core import Molecule

class TestMoleculeCode(unittest.TestCase):
    """Tests for Molecule DFT code interface."""
    
    def setUp(self):
        """Set up test molecules."""
        self.species = ['C', 'O', 'O']
        self.positions = [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]
        self.molecule = Molecule(self.species, self.positions)
    
    def test_molecule_to_code_quantum_espresso(self):
        """Test writing DFT code input using to_code interface."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            temp_file = f.name
        
        try:
            self.molecule.to_code('quantum_espresso', temp_file)
            self.assertTrue(Path(temp_file).exists())
            
            # Verify file content
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertIn('&system', content)
                self.assertIn('ATOMIC_POSITIONS', content)
                self.assertIn('CELL_PARAMETERS', content)
                # Verify molecule species are present
                self.assertIn('C', content)
                self.assertIn('O', content)
        finally:
            Path(temp_file).unlink()
    
    def test_molecule_to_code_qe_alias(self):
        """Test writing using 'qe' alias."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            temp_file = f.name
        
        try:
            self.molecule.to_code('qe', temp_file)
            self.assertTrue(Path(temp_file).exists())
        finally:
            Path(temp_file).unlink()
    
    def test_molecule_to_code_invalid_code(self):
        """Test to_code with invalid code name."""
        with self.assertRaises(ValueError):
            self.molecule.to_code('invalid_code', 'test.in')
    
    def test_molecule_from_code_not_implemented(self):
        """Test from_code raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            Molecule.from_code('quantum_espresso', 'test.out')
    
    def test_molecule_to_code_vasp_not_implemented(self):
        """Test to_code with VASP (not yet implemented)."""
        with self.assertRaises(NotImplementedError):
            self.molecule.to_code('vasp', 'test.in')

if __name__ == '__main__':
    unittest.main()

