"""Tests for Crystal symmetry methods."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype

class TestCrystalSymmetry(unittest.TestCase):
    """Tests for Crystal symmetry methods."""
    
    def setUp(self):
        """Set up test crystals."""
        self.diamond_si = from_prototype('diamond', 'Si', 5.43)
        self.fcc_cu = from_prototype('fcc', 'Cu', 3.61)
    
    def test_get_symmetry_info(self):
        """Test get_symmetry_info() method."""
        sym_info = self.diamond_si.get_symmetry_info()
        
        # Check that all expected keys are present
        self.assertIn('space_group_number', sym_info)
        self.assertIn('space_group_symbol', sym_info)
        self.assertIn('point_group', sym_info)
        self.assertIn('crystal_system', sym_info)
        self.assertIn('hall_symbol', sym_info)
        
        # Check diamond Si has correct space group
        self.assertEqual(sym_info['space_group_number'], 227)
        self.assertEqual(sym_info['space_group_symbol'], 'Fd-3m')
        self.assertEqual(sym_info['crystal_system'], 'Cubic')
    
    def test_get_symmetry_info_fcc(self):
        """Test get_symmetry_info() for FCC structure."""
        sym_info = self.fcc_cu.get_symmetry_info()
        
        # FCC should be space group 225 (Fm-3m)
        self.assertIn('space_group_number', sym_info)
        self.assertIn('space_group_symbol', sym_info)
        self.assertEqual(sym_info['space_group_number'], 225)
        self.assertEqual(sym_info['space_group_symbol'], 'Fm-3m')
    
    def test_get_symmetry_info_custom_tolerance(self):
        """Test get_symmetry_info() with custom tolerance."""
        sym_info = self.diamond_si.get_symmetry_info(symprec=1e-4)
        
        self.assertIn('space_group_number', sym_info)
        self.assertEqual(sym_info['space_group_number'], 227)
    
    def test_get_conventional_cell(self):
        """Test get_conventional_cell() method."""
        # Diamond primitive has 2 atoms, conventional has 8
        primitive = self.diamond_si
        conventional = primitive.get_conventional_cell()
        
        # Check atom count
        self.assertEqual(len(primitive), 2)
        self.assertEqual(len(conventional), 8)
        
        # Check lattice is cubic (conventional)
        self.assertAlmostEqual(conventional.lattice.alpha, 90.0, places=1)
        self.assertAlmostEqual(conventional.lattice.beta, 90.0, places=1)
        self.assertAlmostEqual(conventional.lattice.gamma, 90.0, places=1)
        
        # Check lattice parameter is approximately correct
        # Diamond Si conventional cell should be ~5.43 Å
        self.assertAlmostEqual(conventional.lattice.a, 5.43, places=1)
    
    def test_get_conventional_cell_fcc(self):
        """Test get_conventional_cell() for FCC structure."""
        # FCC primitive has 1 atom, conventional has 4
        primitive = self.fcc_cu
        conventional = primitive.get_conventional_cell()
        
        # Check atom count
        self.assertEqual(len(primitive), 1)
        self.assertEqual(len(conventional), 4)
        
        # Check lattice is cubic
        self.assertAlmostEqual(conventional.lattice.alpha, 90.0, places=1)
    
    def test_get_conventional_cell_preserves_species(self):
        """Test that conventional cell preserves species."""
        primitive = self.diamond_si
        conventional = primitive.get_conventional_cell()
        
        # All atoms should still be Si
        self.assertTrue(all(spec == 'Si' for spec in conventional.species))
    
    def test_get_conventional_cell_returns_new_object(self):
        """Test that get_conventional_cell() returns a new object."""
        primitive = self.diamond_si
        conventional = primitive.get_conventional_cell()
        
        self.assertIsNot(primitive, conventional)
        self.assertIsNot(primitive.lattice, conventional.lattice)
    
    def test_get_conventional_cell_symmetry_consistent(self):
        """Test that conventional cell has consistent symmetry."""
        primitive = self.diamond_si
        conventional = primitive.get_conventional_cell()
        
        # Both should have the same space group
        prim_sym = primitive.get_symmetry_info()
        conv_sym = conventional.get_symmetry_info()
        
        self.assertEqual(prim_sym['space_group_number'], conv_sym['space_group_number'])
        self.assertEqual(prim_sym['space_group_symbol'], conv_sym['space_group_symbol'])

if __name__ == '__main__':
    unittest.main()

