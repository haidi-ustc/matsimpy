"""Tests for IO utils module."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.io.utils import (
    detect_format,
    get_reader_writer,
    is_crystal_format,
    is_molecule_format,
    FORMAT_REGISTRY
)


class TestIOUtils(unittest.TestCase):
    """Tests for IO utility functions."""
    
    def test_detect_format_vasp(self):
        """Test format detection for VASP files."""
        self.assertEqual(detect_format('structure.vasp'), '.vasp')
        self.assertEqual(detect_format('structure.POSCAR'), '.poscar')
        self.assertEqual(detect_format('structure.CONTCAR'), '.contcar')
        self.assertEqual(detect_format('structure.pos'), '.vasp')  # Alias
    
    def test_detect_format_crystal(self):
        """Test format detection for crystal formats."""
        self.assertEqual(detect_format('structure.cif'), '.cif')
        self.assertEqual(detect_format('structure.xsf'), '.xsf')
        self.assertEqual(detect_format('structure.ase'), '.ase')
        self.assertEqual(detect_format('structure.json'), '.json')
    
    def test_detect_format_molecule(self):
        """Test format detection for molecule formats."""
        self.assertEqual(detect_format('molecule.xyz'), '.xyz')
        self.assertEqual(detect_format('molecule.pdb'), '.pdb')
        self.assertEqual(detect_format('molecule.mol'), '.mol')
        self.assertEqual(detect_format('molecule.conf'), '.xyz')  # Alias
    
    def test_detect_format_unknown(self):
        """Test format detection for unknown formats."""
        self.assertIsNone(detect_format('file.unknown'))
        self.assertIsNone(detect_format('file'))
        self.assertIsNone(detect_format(''))
    
    def test_detect_format_case_insensitive(self):
        """Test that format detection is case insensitive."""
        self.assertEqual(detect_format('file.VASP'), '.vasp')
        self.assertEqual(detect_format('file.XYZ'), '.xyz')
        self.assertEqual(detect_format('file.CIF'), '.cif')
    
    def test_get_reader_writer(self):
        """Test getting reader and writer function names."""
        reader, writer = get_reader_writer('.vasp')
        self.assertEqual(reader, 'read_POSCAR')
        self.assertEqual(writer, 'write_POSCAR')
        
        reader, writer = get_reader_writer('.xyz')
        self.assertEqual(reader, 'read_XYZ')
        self.assertEqual(writer, 'write_XYZ')
        
        reader, writer = get_reader_writer('.cif')
        self.assertEqual(reader, 'read_CIF')
        self.assertEqual(writer, 'write_CIF')
    
    def test_get_reader_writer_unknown(self):
        """Test getting reader/writer for unknown format."""
        reader, writer = get_reader_writer('.unknown')
        self.assertIsNone(reader)
        self.assertIsNone(writer)
    
    def test_is_crystal_format(self):
        """Test checking if format is for crystals."""
        self.assertTrue(is_crystal_format('.vasp'))
        self.assertTrue(is_crystal_format('.poscar'))
        self.assertTrue(is_crystal_format('.contcar'))
        self.assertTrue(is_crystal_format('.cif'))
        self.assertTrue(is_crystal_format('.xsf'))
        self.assertTrue(is_crystal_format('.ase'))
        
        self.assertFalse(is_crystal_format('.xyz'))
        self.assertFalse(is_crystal_format('.pdb'))
        self.assertFalse(is_crystal_format('.mol'))
        self.assertFalse(is_crystal_format('.unknown'))
    
    def test_is_molecule_format(self):
        """Test checking if format is for molecules."""
        self.assertTrue(is_molecule_format('.xyz'))
        self.assertTrue(is_molecule_format('.pdb'))
        self.assertTrue(is_molecule_format('.mol'))
        
        self.assertFalse(is_molecule_format('.vasp'))
        self.assertFalse(is_molecule_format('.cif'))
        self.assertFalse(is_molecule_format('.xsf'))
        self.assertFalse(is_molecule_format('.unknown'))
    
    def test_format_registry_completeness(self):
        """Test that FORMAT_REGISTRY contains expected formats."""
        expected_crystal = {'.vasp', '.poscar', '.contcar', '.cif', '.xsf', '.ase', '.json'}
        expected_molecule = {'.xyz', '.pdb', '.mol'}
        
        registry_formats = set(FORMAT_REGISTRY.keys())
        
        # Check all expected formats are present
        for fmt in expected_crystal | expected_molecule:
            self.assertIn(fmt, registry_formats, f"Format {fmt} missing from registry")
        
        # Check all formats have both reader and writer
        for fmt, (reader, writer) in FORMAT_REGISTRY.items():
            self.assertIsNotNone(reader, f"Format {fmt} missing reader")
            self.assertIsNotNone(writer, f"Format {fmt} missing writer")
    
    def test_format_registry_reader_writer_names(self):
        """Test that reader/writer names are valid function names."""
        for fmt, (reader, writer) in FORMAT_REGISTRY.items():
            # Check they start with read_/write_ or from_/to_
            self.assertTrue(
                reader.startswith('read_') or reader.startswith('from_'),
                f"Reader {reader} for {fmt} has invalid name"
            )
            self.assertTrue(
                writer.startswith('write_') or writer.startswith('to_'),
                f"Writer {writer} for {fmt} has invalid name"
            )


if __name__ == '__main__':
    unittest.main()

