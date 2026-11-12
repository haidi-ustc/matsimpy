"""Tests for high-level I/O interface (read/write functions)."""
import os
import unittest
import tempfile

from matsimpy.io import read, write
from matsimpy.core import Crystal, Molecule, Lattice

class TestHighLevelIO(unittest.TestCase):
    """Tests for high-level read/write functions."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'Si'], 
            [[0,0,0], [0.25,0.25,0.25]], 
            Lattice.cubic(5.43)
        )
        self.molecule = Molecule(
            ['H', 'O', 'H'], 
            [[0,0,0], [0.96,0,0], [-0.24,0.93,0]]
        )
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    
    
    
    
    
    
    def test_read_with_explicit_format(self):
        """Test reading with explicitly specified format."""
        filename = os.path.join(self.temp_dir, 'test.txt')
        write(self.crystal, filename, format='vasp')
        crystal_read = read(filename, format='vasp')
        self.assertIsInstance(crystal_read, Crystal)
    
    
    

    def test_write_incompatible_format_molecule(self):
        """Test writing molecule to crystal-only format raises errors."""
        filename = os.path.join(self.temp_dir, 'test.vasp')
        from matsimpy.exceptions import StructureTypeError
        with self.assertRaises(StructureTypeError):
            write(self.molecule, filename)
    
    def test_read_unknown_format(self):
        """Test reading with unknown format raises error."""
        filename = os.path.join(self.temp_dir, 'test.unknown')
        # Create file first so FileNotFoundError doesn't occur
        with open(filename, 'w') as f:
            f.write('test content')
        with self.assertRaises(ValueError):
            read(filename)
    
    def test_write_unknown_format(self):
        """Test writing with unknown format raises error."""
        filename = os.path.join(self.temp_dir, 'test.unknown')
        with self.assertRaises(ValueError):
            write(self.crystal, filename)
    
    
    


if __name__ == '__main__':
    unittest.main()

