"""Tests for LaTeX table export functionality."""
import os
import unittest
import tempfile

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.io import (
    crystals_to_latex_table,
    molecules_to_latex_table,
    structures_to_latex_table,
    save_latex_table,
)

class TestCrystalsToLatexTable(unittest.TestCase):
    """Test crystals_to_latex_table function."""

    def setUp(self):
        self.crystals = [
            Crystal(['Si'], [[0, 0, 0]], Lattice(5.43)),
            Crystal(['Fe'], [[0, 0, 0]], Lattice(2.87)),
            Crystal(['Al'], [[0, 0, 0]], Lattice(4.05)),
        ]

    def test_table_content(self):
        latex = crystals_to_latex_table(self.crystals)
        expected_tokens = [
            r'\begin{table}', r'\end{table}', r'\begin{tabular}', r'\end{tabular}',
            r'\toprule', r'\bottomrule', 'Si', 'Fe', 'Al', '$a=', r'\AA',
        ]
        for token in expected_tokens:
            self.assertIn(token, latex)

        lines = latex.split('\n')
        data_lines = [l for l in lines if '&' in l and 'toprule' not in l.lower()
                      and 'midrule' not in l.lower() and 'bottomrule' not in l.lower()
                      and 'ID' not in l]
        self.assertGreaterEqual(len(data_lines), 3)

    def test_custom_columns(self):
        columns = ['ID', 'Formula', 'Atoms']
        latex = crystals_to_latex_table(self.crystals, include_columns=columns)
        for col in columns:
            self.assertIn(col, latex)

    def test_volume_column(self):
        latex = crystals_to_latex_table(self.crystals, include_columns=['ID', 'Formula', 'Volume'])
        self.assertIn('Volume', latex)

    def test_empty_list_raises_error(self):
        with self.assertRaises(ValueError) as context:
            crystals_to_latex_table([])
        self.assertIn("empty", str(context.exception).lower())

class TestMoleculesToLatexTable(unittest.TestCase):
    """Test molecules_to_latex_table function."""

    def setUp(self):
        self.molecules = [
            Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]]),
            Molecule(['H', 'H', 'O'], [[0, 0, 0], [0.76, 0.59, 0], [-0.76, 0.59, 0]]),
            Molecule(['N', 'H', 'H', 'H'], [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]),
        ]

    def test_table_with_mass_column(self):
        latex = molecules_to_latex_table(self.molecules, include_columns=['ID', 'Formula', 'Mass'])
        self.assertIn('Mass', latex)

    def test_empty_list_raises_error(self):
        with self.assertRaises(ValueError):
            molecules_to_latex_table([])

class TestStructuresToLatexTable(unittest.TestCase):
    """Test structures_to_latex_table for mixed structures."""
    
    def setUp(self):
        """Set up mixed structures."""
        self.structures = [
            Crystal(['Si'], [[0, 0, 0]], Lattice(5.43)),
            Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]]),
            Crystal(['Fe'], [[0, 0, 0]], Lattice(2.87)),
            Molecule(['H', 'H', 'O'], [[0, 0, 0], [0.76, 0.59, 0], [-0.76, 0.59, 0]]),
        ]
    
    def test_separate_tables(self):
        """Test creating separate tables for crystals and molecules."""
        latex = structures_to_latex_table(self.structures, separate_by_type=True)
        
        # Should have two tables
        self.assertEqual(latex.count(r'\begin{table}'), 2)
        self.assertEqual(latex.count(r'\end{table}'), 2)
        
        # Should have both crystals and molecules sections
        self.assertIn('Crystals', latex)
        self.assertIn('Molecules', latex)
    
    def test_single_table(self):
        """Test creating single table with type column."""
        latex = structures_to_latex_table(self.structures, separate_by_type=False)
        
        # Should have one table
        self.assertEqual(latex.count(r'\begin{table}'), 1)
        self.assertEqual(latex.count(r'\end{table}'), 1)
        
        # Should have Type column
        self.assertIn('Type', latex)
        self.assertIn('Crystal', latex)
        self.assertIn('Molecule', latex)
    
    
    def test_only_molecules(self):
        """Test with only molecules."""
        molecules_only = [s for s in self.structures if isinstance(s, Molecule) and not isinstance(s, Crystal)]
        latex = structures_to_latex_table(molecules_only, separate_by_type=True)
        
        # Should only have one table (molecules)
        self.assertEqual(latex.count(r'\begin{table}'), 1)
        self.assertIn('Molecules', latex)

class TestSaveLatexTable(unittest.TestCase):
    """Test save_latex_table function."""
    
    def test_save_to_file(self):
        """Test saving table to file."""
        crystals = [
            Crystal(['Si'], [[0, 0, 0]], Lattice(5.43)),
            Crystal(['Fe'], [[0, 0, 0]], Lattice(2.87)),
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.tex')
            
            save_latex_table(crystals, filename, caption="Test Table")
            
            # Check file was created
            self.assertTrue(os.path.exists(filename))
            
            # Check content
            with open(filename, 'r') as f:
                content = f.read()
            
            self.assertIn(r'\begin{table}', content)
            self.assertIn('Test Table', content)

class TestCustomFormatters(unittest.TestCase):
    """Test custom formatters."""
    
    def test_crystal_custom_formatter(self):
        """Test custom formatter for crystals."""
        crystals = [Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))]
        
        def custom_id(crystal, idx):
            return f'C-{idx:03d}'
        
        latex = crystals_to_latex_table(
            crystals,
            include_columns=['ID', 'Formula'],
            custom_formatters={'ID': custom_id}
        )
        
        self.assertIn('C-001', latex)
    
    def test_molecule_custom_formatter(self):
        """Test custom formatter for molecules."""
        molecules = [Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])]
        
        def custom_formula(mol, idx):
            return f'\\textbf{{{mol.formula}}}'
        
        latex = molecules_to_latex_table(
            molecules,
            include_columns=['ID', 'Formula'],
            custom_formatters={'Formula': custom_formula}
        )
        
        self.assertIn(r'\textbf', latex)


class TestMhchemSupport(unittest.TestCase):
    """Test mhchem package support."""
    
    
    
    
    
    def test_structures_mixed_with_mhchem(self):
        """Test mixed structures with mhchem."""
        structures = [
            Crystal(['Si'], [[0,0,0]], Lattice(5.43)),
            Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        ]
        
        latex = structures_to_latex_table(structures, separate_by_type=True, use_mhchem=True)
        
        # Both tables should use \ce{}
        self.assertIn(r'\ce{', latex)
        self.assertEqual(latex.count(r'\ce{'), 2)  # One for each structure
    
    def test_single_table_with_mhchem(self):
        """Test single table mode with mhchem."""
        structures = [
            Crystal(['Si'], [[0,0,0]], Lattice(5.43)),
            Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]])
        ]
        
        latex = structures_to_latex_table(structures, separate_by_type=False, use_mhchem=True)
        
        self.assertIn(r'\ce{', latex)

if __name__ == '__main__':
    unittest.main()
