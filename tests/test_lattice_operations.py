"""Tests for lattice operations."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.transformation.lattice import (
    apply_strain,
    apply_deformation,
    scale_lattice,
    set_volume,
    optimize_lattice,
    rotate_lattice,
    transform_lattice,
    standardize_cell
)


class TestLatticeStrain(unittest.TestCase):
    """Tests for strain and deformation operations."""
    
    def setUp(self):
        """Set up test crystal."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    def test_apply_strain_tensile(self):
        """Test applying tensile strain."""
        # 1% tensile strain in x direction
        strain = [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]]
        strained = apply_strain(self.crystal, strain)
        
        # Lattice should be larger in x
        self.assertGreater(strained.lattice.a, self.crystal.lattice.a)
        # Should be new object
        self.assertIsNot(strained, self.crystal)
    
    def test_apply_strain_hydrostatic(self):
        """Test hydrostatic strain."""
        # Uniform 1% strain
        strain = [[0.01, 0, 0], [0, 0.01, 0], [0, 0, 0.01]]
        strained = apply_strain(self.crystal, strain)
        
        # All lattice constants should increase
        self.assertGreater(strained.lattice.a, self.crystal.lattice.a)
        self.assertGreater(strained.lattice.b, self.crystal.lattice.b)
        self.assertGreater(strained.lattice.c, self.crystal.lattice.c)
    
    def test_apply_strain_shear(self):
        """Test shear strain."""
        # Shear strain
        strain = [[0, 0.05, 0], [0.05, 0, 0], [0, 0, 0]]
        strained = apply_strain(self.crystal, strain)
        
        self.assertIsNotNone(strained)
    
    def test_apply_strain_inplace(self):
        """Test in-place strain."""
        original_a = self.crystal.lattice.a
        strain = [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]]
        result = apply_strain(self.crystal, strain, inplace=True)
        
        self.assertIs(result, self.crystal)
        self.assertGreater(self.crystal.lattice.a, original_a)
    
    def test_apply_deformation(self):
        """Test applying deformation."""
        # Simple deformation
        deformation = [[1.01, 0, 0], [0, 1, 0], [0, 0, 1]]
        deformed = apply_deformation(self.crystal, deformation)
        
        self.assertGreater(deformed.lattice.a, self.crystal.lattice.a)
    
    def test_apply_deformation_with_positions(self):
        """Test deformation with atomic positions."""
        deformation = [[1.1, 0, 0], [0, 1, 0], [0, 0, 1]]
        deformed = apply_deformation(self.crystal, deformation, deform_positions=True)
        
        self.assertIsNotNone(deformed)
    
    def test_apply_deformation_without_positions(self):
        """Test deformation without moving atoms."""
        deformation = [[1.1, 0, 0], [0, 1, 0], [0, 0, 1]]
        deformed = apply_deformation(self.crystal, deformation, deform_positions=False)
        
        # Fractional coordinates should be the same
        np.testing.assert_array_almost_equal(deformed.positions, self.crystal.positions)


class TestLatticeScaling(unittest.TestCase):
    """Tests for scaling and volume operations."""
    
    def setUp(self):
        """Set up test crystal."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    def test_scale_lattice_uniform(self):
        """Test uniform scaling."""
        scaled = scale_lattice(self.crystal, 1.1)
        
        # All dimensions should scale
        self.assertAlmostEqual(scaled.lattice.a, self.crystal.lattice.a * 1.1, places=5)
        self.assertAlmostEqual(scaled.lattice.b, self.crystal.lattice.b * 1.1, places=5)
        self.assertAlmostEqual(scaled.lattice.c, self.crystal.lattice.c * 1.1, places=5)
    
    def test_scale_lattice_anisotropic(self):
        """Test anisotropic scaling."""
        scaled = scale_lattice(self.crystal, [1.1, 1.0, 0.9])
        
        self.assertAlmostEqual(scaled.lattice.a, self.crystal.lattice.a * 1.1, places=5)
        self.assertAlmostEqual(scaled.lattice.b, self.crystal.lattice.b * 1.0, places=5)
        self.assertAlmostEqual(scaled.lattice.c, self.crystal.lattice.c * 0.9, places=5)
    
    def test_scale_lattice_inplace(self):
        """Test in-place scaling."""
        original_a = self.crystal.lattice.a
        result = scale_lattice(self.crystal, 1.1, inplace=True)
        
        self.assertIs(result, self.crystal)
        self.assertAlmostEqual(self.crystal.lattice.a, original_a * 1.1, places=5)
    
    def test_set_volume(self):
        """Test setting specific volume."""
        target_volume = 200.0
        scaled = set_volume(self.crystal, target_volume)
        
        self.assertAlmostEqual(scaled.volume, target_volume, places=2)
    
    def test_set_volume_larger(self):
        """Test scaling to larger volume."""
        original_volume = self.crystal.volume
        scaled = set_volume(self.crystal, original_volume * 2)
        
        self.assertGreater(scaled.volume, original_volume)
        self.assertAlmostEqual(scaled.volume, original_volume * 2, places=2)
    
    def test_set_volume_smaller(self):
        """Test scaling to smaller volume."""
        original_volume = self.crystal.volume
        scaled = set_volume(self.crystal, original_volume * 0.5)
        
        self.assertLess(scaled.volume, original_volume)
        self.assertAlmostEqual(scaled.volume, original_volume * 0.5, places=2)
    
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
    
    def test_rotate_lattice(self):
        """Test rotating lattice."""
        # 90 degree rotation around z
        angle = np.pi / 2
        R = np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1]
        ])
        
        rotated = rotate_lattice(self.crystal, R)
        
        self.assertIsNotNone(rotated)
        self.assertIsNot(rotated, self.crystal)
    
    def test_rotate_lattice_with_atoms(self):
        """Test rotating lattice and atoms together."""
        angle = np.pi / 4
        R = np.eye(3)  # Identity for simplicity
        
        rotated = rotate_lattice(self.crystal, R, rotate_atoms=True)
        
        self.assertEqual(len(rotated.species), len(self.crystal.species))
    
    def test_rotate_lattice_without_atoms(self):
        """Test rotating only lattice."""
        angle = np.pi / 4
        R = np.eye(3)
        
        rotated = rotate_lattice(self.crystal, R, rotate_atoms=False)
        
        # Fractional positions should be same
        np.testing.assert_array_almost_equal(rotated.positions, self.crystal.positions)
    
    def test_transform_lattice(self):
        """Test general lattice transformation."""
        # Simple scaling transformation
        T = np.diag([1.1, 1.0, 0.9])
        
        transformed = transform_lattice(self.crystal, T)
        
        self.assertIsNotNone(transformed)
    
    def test_transform_lattice_with_positions(self):
        """Test transformation with position transform."""
        T = np.diag([1.1, 1.1, 1.1])
        
        transformed = transform_lattice(self.crystal, T, transform_positions=True)
        
        self.assertIsNotNone(transformed)
    
    def test_standardize_cell(self):
        """Test cell standardization."""
        standardized = standardize_cell(self.crystal)
        
        # Should return valid crystal
        self.assertIsNotNone(standardized)
        self.assertEqual(len(standardized.species), len(self.crystal.species))
    
    def test_standardize_cell_to_primitive(self):
        """Test converting to primitive cell."""
        # For a simple cubic with 1 atom, should stay the same or reduce
        primitive = standardize_cell(self.crystal, to_primitive=True)
        
        self.assertIsNotNone(primitive)
        self.assertLessEqual(len(primitive.species), len(self.crystal.species))


class TestLatticeInplace(unittest.TestCase):
    """Tests for in-place lattice operations."""
    
    def setUp(self):
        """Set up test crystal."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.crystal = from_prototype('diamond', 'Si', 5.43)
    
    def test_apply_strain_inplace(self):
        """Test in-place strain."""
        original_id = id(self.crystal)
        strain = [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]]
        result = apply_strain(self.crystal, strain, inplace=True)
        
        self.assertEqual(id(result), original_id)
    
    def test_scale_lattice_inplace(self):
        """Test in-place scaling."""
        original_id = id(self.crystal)
        result = scale_lattice(self.crystal, 1.1, inplace=True)
        
        self.assertEqual(id(result), original_id)
    
    def test_set_volume_inplace(self):
        """Test in-place volume setting."""
        original_id = id(self.crystal)
        result = set_volume(self.crystal, 200.0, inplace=True)
        
        self.assertEqual(id(result), original_id)
    
    def test_apply_deformation_inplace(self):
        """Test in-place deformation."""
        original_id = id(self.crystal)
        deformation = [[1.01, 0, 0], [0, 1, 0], [0, 0, 1]]
        result = apply_deformation(self.crystal, deformation, inplace=True)
        
        self.assertEqual(id(result), original_id)


if __name__ == '__main__':
    unittest.main()

