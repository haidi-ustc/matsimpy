"""Tests for high-level I/O interface (read/write functions)."""
import os
import unittest
import tempfile
from pathlib import Path

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
    
    def test_write_crystal_vasp(self):
        """Test writing crystal to VASP format."""
        filename = os.path.join(self.temp_dir, 'test.vasp')
        write(self.crystal, filename)
        self.assertTrue(os.path.exists(filename))
    
    def test_write_crystal_cif(self):
        """Test writing crystal to CIF format."""
        filename = os.path.join(self.temp_dir, 'test.cif')
        write(self.crystal, filename, title='Test')
        self.assertTrue(os.path.exists(filename))
    
    def test_write_molecule_xyz(self):
        """Test writing molecule to XYZ format."""
        filename = os.path.join(self.temp_dir, 'test.xyz')
        write(self.molecule, filename)
        self.assertTrue(os.path.exists(filename))
    
    def test_read_crystal_vasp(self):
        """Test reading crystal from VASP format."""
        filename = os.path.join(self.temp_dir, 'test.vasp')
        write(self.crystal, filename)
        crystal_read = read(filename)
        self.assertIsInstance(crystal_read, Crystal)
        self.assertEqual(len(crystal_read), len(self.crystal))
        self.assertEqual(crystal_read.formula, self.crystal.formula)
    
    def test_read_crystal_cif(self):
        """Test reading crystal from CIF format."""
        filename = os.path.join(self.temp_dir, 'test.cif')
        write(self.crystal, filename)
        crystal_read = read(filename)
        self.assertIsInstance(crystal_read, Crystal)
        self.assertEqual(len(crystal_read), len(self.crystal))
    
    def test_read_molecule_xyz(self):
        """Test reading molecule from XYZ format."""
        filename = os.path.join(self.temp_dir, 'test.xyz')
        write(self.molecule, filename)
        molecule_read = read(filename)
        self.assertIsInstance(molecule_read, Molecule)
        self.assertEqual(len(molecule_read), len(self.molecule))
        self.assertEqual(molecule_read.formula, self.molecule.formula)
    
    def test_read_with_explicit_format(self):
        """Test reading with explicitly specified format."""
        filename = os.path.join(self.temp_dir, 'test.txt')
        write(self.crystal, filename, format='vasp')
        crystal_read = read(filename, format='vasp')
        self.assertIsInstance(crystal_read, Crystal)
    
    def test_write_with_explicit_format(self):
        """Test writing with explicitly specified format."""
        filename = os.path.join(self.temp_dir, 'test.txt')
        write(self.crystal, filename, format='cif')
        self.assertTrue(os.path.exists(filename))
        # Should be readable as CIF
        crystal_read = read(filename, format='cif')
        self.assertIsInstance(crystal_read, Crystal)
    
    def test_read_nonexistent_file(self):
        """Test reading non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            read('/nonexistent/file.vasp')
    
    def test_write_incompatible_format_crystal(self):
        """Test writing crystal to molecule-only format raises error."""
        filename = os.path.join(self.temp_dir, 'test.xyz')
        with self.assertRaises(ValueError):
            write(self.crystal, filename)
    
    def test_write_incompatible_format_molecule(self):
        """Test writing molecule to crystal-only format raises error."""
        filename = os.path.join(self.temp_dir, 'test.vasp')
        with self.assertRaises(ValueError):
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
    
    def test_roundtrip_crystal_vasp(self):
        """Test roundtrip: write then read crystal in VASP format."""
        filename = os.path.join(self.temp_dir, 'test.vasp')
        write(self.crystal, filename)
        crystal_read = read(filename)
        self.assertEqual(crystal_read.formula, self.crystal.formula)
        self.assertEqual(len(crystal_read), len(self.crystal))
    
    def test_roundtrip_molecule_xyz(self):
        """Test roundtrip: write then read molecule in XYZ format."""
        filename = os.path.join(self.temp_dir, 'test.xyz')
        write(self.molecule, filename)
        molecule_read = read(filename)
        self.assertEqual(molecule_read.formula, self.molecule.formula)
        self.assertEqual(len(molecule_read), len(self.molecule))
    
    def test_write_with_kwargs(self):
        """Test writing with additional kwargs passed to writer."""
        filename = os.path.join(self.temp_dir, 'test.cif')
        write(self.crystal, filename, title='Custom Title')
        # Should not raise error
        self.assertTrue(os.path.exists(filename))

    def test_write_crystal_json(self):
        """write(crystal, *.json) must not raise ValueError."""
        filename = os.path.join(self.temp_dir, 'test.json')
        write(self.crystal, filename)
        self.assertTrue(os.path.exists(filename))

    def test_write_crystal_pdb(self):
        """write(crystal, *.pdb) must not raise ValueError."""
        filename = os.path.join(self.temp_dir, 'test.pdb')
        write(self.crystal, filename)
        self.assertTrue(os.path.exists(filename))

    def test_write_crystal_ase(self):
        """write(crystal, *.ase) must not raise ValueError."""
        filename = os.path.join(self.temp_dir, 'test.ase')
        write(self.crystal, filename)
        self.assertTrue(os.path.exists(filename))

    def test_roundtrip_crystal_json(self):
        """write+read roundtrip via JSON preserves species and atom count."""
        filename = os.path.join(self.temp_dir, 'test.json')
        write(self.crystal, filename)
        crystal_read = read(filename)
        self.assertIsInstance(crystal_read, Crystal)
        self.assertEqual(len(crystal_read), len(self.crystal))
        self.assertEqual(crystal_read.formula, self.crystal.formula)

if __name__ == '__main__':
    unittest.main()

