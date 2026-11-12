"""Tests for Crystal symmetry methods."""
import unittest
from matsimpy.builders.bulk import from_prototype
from matsimpy.symmetry import get_conventional_cell, get_symmetry_info

class TestCrystalSymmetry(unittest.TestCase):
    """Tests for Crystal symmetry methods."""
    
    def setUp(self):
        """Set up test crystals."""
        self.diamond_si = from_prototype('diamond', 'Si', 5.43)
        self.fcc_cu = from_prototype('fcc', 'Cu', 3.61)
    
    def test_get_symmetry_info(self):
        """Test get_symmetry_info() method."""
        sym_info = get_symmetry_info(self.diamond_si)
        
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
    
    
    
    
    
    
    def test_get_conventional_cell_returns_new_object(self):
        """Test that get_conventional_cell() returns a new object."""
        primitive = self.diamond_si
        conventional = get_conventional_cell(primitive)
        
        self.assertIsNot(primitive, conventional)
        self.assertIsNot(primitive.lattice, conventional.lattice)
    
    def test_get_conventional_cell_symmetry_consistent(self):
        """Test that conventional cell has consistent symmetry."""
        primitive = self.diamond_si
        conventional = get_conventional_cell(primitive)
        
        # Both should have the same space group
        prim_sym = get_symmetry_info(primitive)
        conv_sym = get_symmetry_info(conventional)
        
        self.assertEqual(prim_sym['space_group_number'], conv_sym['space_group_number'])
        self.assertEqual(prim_sym['space_group_symbol'], conv_sym['space_group_symbol'])

if __name__ == '__main__':
    unittest.main()

