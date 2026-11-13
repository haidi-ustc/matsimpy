"""Tests for lattice operations."""
import unittest
import numpy as np
from matsimpy.transformation.lattice import (
    apply_strain,
    apply_deformation,
    scale_lattice,
    optimize_lattice,
    rotate_lattice,
    standardize_cell
)

class TestLatticeStrain(unittest.TestCase):
    """Tests for strain and deformation operations."""
    
    def setUp(self):
        """Set up test crystal."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    
    
    
    def test_apply_strain_always_returns_new(self):
        """Test that apply_strain always returns a new object."""
        original_a = self.crystal.lattice.a
        strain = [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]]
        result = apply_strain(self.crystal, strain)
        
        self.assertIsNot(result, self.crystal)
        # Original should be unchanged
        self.assertEqual(self.crystal.lattice.a, original_a)
        # Result should be strained
        self.assertGreater(result.lattice.a, original_a)
    
    
    
    def test_apply_deformation_without_positions(self):
        """Test deformation without moving atoms."""
        deformation = [[1.1, 0, 0], [0, 1, 0], [0, 0, 1]]
        deformed = apply_deformation(self.crystal, deformation, deform_positions=False)
        
        # The cell is deformed but the atoms keep their Cartesian positions
        np.testing.assert_array_almost_equal(deformed.cart_positions, self.crystal.cart_positions)
        np.testing.assert_array_almost_equal(
            deformed.lattice.matrix, self.crystal.lattice.matrix @ np.array(deformation).T
        )

class TestLatticeScaling(unittest.TestCase):
    """Tests for scaling and volume operations."""
    
    def setUp(self):
        """Set up test crystal."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    
    
    def test_scale_lattice_always_returns_new(self):
        """Test that scale_lattice always returns a new object."""
        original_a = self.crystal.lattice.a
        result = scale_lattice(self.crystal, 1.1)
        
        self.assertIsNot(result, self.crystal)
        # Original should be unchanged
        self.assertEqual(self.crystal.lattice.a, original_a)
        # Result should be scaled
        self.assertAlmostEqual(result.lattice.a, original_a * 1.1, places=5)
    
    
    
    
    def test_optimize_lattice_volume(self):
        """Test optimizing lattice to target volume."""
        optimized = optimize_lattice(self.crystal, target_volume=200.0)
        
        self.assertAlmostEqual(optimized.volume, 200.0, places=2)
    
    def test_optimize_lattice_density(self):
        """Test optimizing lattice to target density."""
        # Silicon density ~2.33 g/cm³
        optimized = optimize_lattice(self.crystal, target_density=2.33)
        
        self.assertIsNotNone(optimized)
        # Check that optimization did something (volume changed)
        self.assertNotEqual(optimized.volume, self.crystal.volume)
    
    def test_optimize_lattice_no_target(self):
        """Test optimize_lattice requires target."""
        with self.assertRaises(ValueError):
            optimize_lattice(self.crystal)

class TestLatticeTransform(unittest.TestCase):
    """Tests for lattice transformation operations."""
    
    def setUp(self):
        """Set up test crystal."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    
    
    def test_rotate_lattice_without_atoms(self):
        """Test rotating only lattice."""
        angle = np.pi / 4
        R = np.eye(3)
        
        rotated = rotate_lattice(self.crystal, R, rotate_atoms=False)
        
        # Fractional positions should be same
        np.testing.assert_array_almost_equal(rotated.positions, self.crystal.positions)
    
    
    
    
    def test_standardize_cell_to_primitive(self):
        """Test converting to primitive cell."""
        # For a simple cubic with 1 atom, should stay the same or reduce
        primitive = standardize_cell(self.crystal, to_primitive=True)
        
        self.assertIsNotNone(primitive)
        self.assertLessEqual(len(primitive.species), len(self.crystal.species))

if __name__ == '__main__':
    unittest.main()

