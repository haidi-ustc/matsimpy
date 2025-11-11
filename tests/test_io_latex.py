"""Tests for LaTeX table export functionality."""
import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.io.latex import (
    crystals_to_latex_table,
    molecules_to_latex_table,
    structures_to_latex_table,
    save_latex_table,
)


class TestCrystalsToLatexTable(unittest.TestCase):
    """Test crystals_to_latex_table function."""
    
    def setUp(self):
        """Set up test crystals."""
        self.crystals = [
            Crystal(['Si'], [[0, 0, 0]], Lattice(5.43)),
            Crystal(['Fe'], [[0, 0, 0]], Lattice(2.87)),
            Crystal(['Al'], [[0, 0, 0]], Lattice(4.05)),
        ]
    
    def test_basic_table_generation(self):
        """Test basic table generation."""
        latex = crystals_to_latex_table(self.crystals)
        
        # Check LaTeX structure
        self.assertIn(r'\begin{table}', latex)
        self.assertIn(r'\end{table}', latex)
        self.assertIn(r'\begin{tabular}', latex)
        self.assertIn(r'\end{tabular}', latex)
        self.assertIn(r'\toprule', latex)
        self.assertIn(r'\bottomrule', latex)
    
    def test_table_has_caption(self):
        """Test that table has caption."""
        latex = crystals_to_latex_table(self.crystals, caption="Test Caption")
        
        self.assertIn(r'\caption{Test Caption}', latex)
    
    def test_table_has_label(self):
        """Test that table has label."""
        latex = crystals_to_latex_table(self.crystals, label="tab:test")
        
        self.assertIn(r'\label{tab:test}', latex)
    
    def test_table_includes_formulas(self):
        """Test that formulas are included."""
        latex = crystals_to_latex_table(self.crystals)
        
        self.assertIn('Si', latex)
        self.assertIn('Fe', latex)
        self.assertIn('Al', latex)
    
    def test_table_includes_ids(self):
        """Test that IDs are numbered correctly."""
        latex = crystals_to_latex_table(self.crystals)
        
        # Should have IDs 1, 2, 3
        lines = latex.split('\n')
        data_lines = [l for l in lines if '&' in l and 'toprule' not in l.lower() and 'midrule' not in l.lower() and 'bottomrule' not in l.lower() and 'ID' not in l]
        
        self.assertGreaterEqual(len(data_lines), 3)
    
    def test_table_includes_lattice_params(self):
        """Test that lattice parameters are included."""
        latex = crystals_to_latex_table(self.crystals)
        
        # Should have lattice parameter 'a='
        self.assertIn('$a=', latex)
    
    def test_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
        with self.assertRaises(ValueError) as context:
            crystals_to_latex_table([])
        
        self.assertIn("empty", str(context.exception).lower())
    
    def test_custom_columns(self):
        """Test custom column selection."""
        latex = crystals_to_latex_table(
            self.crystals, 
            include_columns=['ID', 'Formula', 'Atoms']
        )
        
        self.assertIn('Formula', latex)
        self.assertIn('Atoms', latex)
    
    def test_volume_column(self):
        """Test volume column."""
        latex = crystals_to_latex_table(
            self.crystals,
            include_columns=['ID', 'Formula', 'Volume']
        )
        
        self.assertIn('Volume', latex)


class TestMoleculesToLatexTable(unittest.TestCase):
    """Test molecules_to_latex_table function."""
    
    def setUp(self):
        """Set up test molecules."""
        self.molecules = [
            Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]]),
            Molecule(['H', 'H', 'O'], [[0, 0, 0], [0.76, 0.59, 0], [-0.76, 0.59, 0]]),
            Molecule(['N', 'H', 'H', 'H'], [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]),
        ]
    
    def test_basic_table_generation(self):
        """Test basic table generation."""
        latex = molecules_to_latex_table(self.molecules)
        
        # Check LaTeX structure
        self.assertIn(r'\begin{table}', latex)
        self.assertIn(r'\end{table}', latex)
        self.assertIn(r'\toprule', latex)
        self.assertIn(r'\bottomrule', latex)
    
    def test_table_includes_formulas(self):
        """Test that molecular formulas are included."""
        latex = molecules_to_latex_table(self.molecules)
        
        # Formulas should be in LaTeX format
        self.assertIn('C', latex)
        self.assertIn('O', latex)
        self.assertIn('H', latex)
    
    def test_table_with_mass_column(self):
        """Test table with mass column."""
        latex = molecules_to_latex_table(
            self.molecules,
            include_columns=['ID', 'Formula', 'Mass']
        )
        
        self.assertIn('Mass', latex)
    
    def test_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
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
    
    def test_only_crystals(self):
        """Test with only crystals."""
        crystals_only = [s for s in self.structures if isinstance(s, Crystal)]
        latex = structures_to_latex_table(crystals_only, separate_by_type=True)
        
        # Should only have one table (crystals)
        self.assertEqual(latex.count(r'\begin{table}'), 1)
        self.assertIn('Crystals', latex)
    
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


class TestLatexFormatting(unittest.TestCase):
    """Test LaTeX formatting details."""
    
    def test_formula_latex_formatting(self):
        """Test that formulas use LaTeX subscripts."""
        crystal = Crystal(['Fe', 'Fe', 'O', 'O', 'O'], 
                         [[0,0,0], [0.5,0,0], [0.25,0,0], [0.75,0,0], [0.5,0.5,0]], 
                         Lattice(10))
        
        latex = crystals_to_latex_table([crystal])
        
        # Should have LaTeX subscript notation
        self.assertIn('$_', latex)  # LaTeX subscript
    
    def test_angstrom_symbol(self):
        """Test that Angstrom symbol is included."""
        crystal = Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))
        
        latex = crystals_to_latex_table([crystal])
        
        self.assertIn(r'\AA', latex)  # LaTeX Angstrom symbol


class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""
    
    def test_single_crystal(self):
        """Test with single crystal."""
        crystal = [Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))]
        latex = crystals_to_latex_table(crystal)
        
        self.assertIn(r'\begin{table}', latex)
        self.assertIn('Si', latex)
    
    def test_single_molecule(self):
        """Test with single molecule."""
        molecule = [Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])]
        latex = molecules_to_latex_table(molecule)
        
        self.assertIn(r'\begin{table}', latex)


if __name__ == '__main__':
    unittest.main()

