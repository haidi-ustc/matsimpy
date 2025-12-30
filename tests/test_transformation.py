"""Tests for transformation module."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.transformation import (
    translate, translate_to_origin,
    rotate, rotate_around_axis,
    substitute, substitute_all,
    make_supercell,
    chain, apply_transformations
)

class TestTranslation(unittest.TestCase):
    """Tests for translation transformations."""
    
    def setUp(self):
        """Set up test molecules."""
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        self.crystal = Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(10))
    
    def test_translate_functional(self):
        """Test functional translation (returns new object)."""
        original_pos = self.molecule.positions[0].copy()
        new_molecule = translate(self.molecule, [1, 1, 1])
        
        # Original should be unchanged
        np.testing.assert_array_almost_equal(self.molecule.positions[0], original_pos)
        # New should be translated
        np.testing.assert_array_almost_equal(new_molecule.positions[0], original_pos + [1, 1, 1])
        self.assertIsNot(self.molecule, new_molecule)
    
    def test_translate_always_returns_new(self):
        """Test that translate always returns a new object."""
        original_pos = self.molecule.positions[0].copy()
        result = translate(self.molecule, [1, 1, 1])
        
        # Should be different object
        self.assertIsNot(self.molecule, result)
        # Original should be unchanged
        np.testing.assert_array_almost_equal(self.molecule.positions[0], original_pos)
        # Result should be translated
        np.testing.assert_array_almost_equal(result.positions[0], original_pos + [1, 1, 1])
    
    def test_translate_crystal(self):
        """Test translation of crystal."""
        original_cart = self.crystal.cart_positions[0].copy()
        new_crystal = translate(self.crystal, [1, 1, 1])
        
        np.testing.assert_array_almost_equal(new_crystal.cart_positions[0], original_cart + [1, 1, 1])
    
    def test_translate_to_origin(self):
        """Test translate to origin."""
        # Move molecule away from origin
        self.molecule = self.molecule.translate([5, 5, 5], inplace=False)
        centered = translate_to_origin(self.molecule)
        
        com = centered.get_center_of_mass()
        np.testing.assert_array_almost_equal(com, [0, 0, 0], decimal=5)
    
    def test_translate_invalid_vector(self):
        """Test translation with invalid vector."""
        with self.assertRaises(ValueError):
            translate(self.molecule, [1, 1])  # Not 3D

class TestRotation(unittest.TestCase):
    """Tests for rotation transformations."""
    
    def setUp(self):
        """Set up test molecules."""
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    def test_rotate_functional(self):
        """Test functional rotation."""
        original_pos = self.molecule.positions[1].copy()
        # Rotate around origin (not COM)
        new_molecule = rotate(self.molecule, angle=90, axis=[0, 0, 1], center=[0, 0, 0])
        
        # Original should be unchanged
        np.testing.assert_array_almost_equal(self.molecule.positions[1], original_pos)
        # New should be rotated
        self.assertIsNot(self.molecule, new_molecule)
        # O atom should have moved (from [1.2, 0, 0] to approximately [0, 1.2, 0])
        np.testing.assert_array_almost_equal(new_molecule.positions[1], [0, 1.2, 0], decimal=3)
    
    def test_rotate_always_returns_new(self):
        """Test that rotate always returns a new object."""
        original_pos = self.molecule.positions[1].copy()
        # Rotate around origin (not COM)
        result = rotate(self.molecule, angle=90, axis=[0, 0, 1], center=[0, 0, 0])
        
        self.assertIsNot(self.molecule, result)
        # Original should be unchanged
        np.testing.assert_array_almost_equal(self.molecule.positions[1], original_pos)
        # O atom should be rotated in result
        np.testing.assert_array_almost_equal(result.positions[1], [0, 1.2, 0], decimal=3)
    
    def test_rotate_around_center(self):
        """Test rotation around custom center."""
        # Molecule at [1, 1, 1], rotate around origin
        self.molecule = self.molecule.translate([1, 1, 1], inplace=False)
        rotated = rotate(self.molecule, angle=180, axis=[0, 0, 1], center=[0, 0, 0])
        
        # Should be rotated around origin
        self.assertIsNotNone(rotated)

class TestSubstitution(unittest.TestCase):
    """Tests for substitution transformations."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    def test_substitute_single(self):
        """Test substituting a single atom."""
        new_crystal = substitute(self.crystal, 0, 'Ge')
        
        self.assertEqual(new_crystal.species[0], 'Ge')
        self.assertEqual(new_crystal.species[1], 'O')
        self.assertIsNot(self.crystal, new_crystal)
    
    def test_substitute_multiple(self):
        """Test substituting multiple atoms."""
        new_crystal = substitute(self.crystal, [0, 1], ['Ge', 'S'])
        
        self.assertEqual(new_crystal.species[0], 'Ge')
        self.assertEqual(new_crystal.species[1], 'S')
    
    def test_substitute_all(self):
        """Test substituting all atoms of a species."""
        new_crystal = substitute_all(self.crystal, 'Si', 'Ge')
        
        self.assertEqual(new_crystal.species[0], 'Ge')
        self.assertEqual(new_crystal.species[1], 'O')
    
    def test_substitute_always_returns_new(self):
        """Test that substitute always returns a new object."""
        original_species = list(self.crystal.species)
        result = substitute(self.crystal, 0, 'Ge')
        
        self.assertIsNot(self.crystal, result)
        # Original should be unchanged
        self.assertEqual(self.crystal.species[0], original_species[0])
        # Result should be substituted
        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], original_species[1])

class TestSupercell(unittest.TestCase):
    """Tests for supercell generation."""
    
    def setUp(self):
        """Set up test crystal."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.unit_cell = from_prototype('diamond', 'Si', 5.0)
    
    def test_make_supercell_2x2x2(self):
        """Test creating 2x2x2 supercell."""
        supercell = make_supercell(self.unit_cell, [2, 2, 2])
        
        # Diamond structure has 2 atoms in primitive cell, so 2x2x2 supercell = 2 * 8 = 16 atoms
        self.assertEqual(len(supercell), 16)  # 2 atoms × 2^3 = 16 atoms
        # For primitive rhombohedral cell, supercell scales the primitive lattice parameter
        expected_a = 2 * self.unit_cell.lattice.a
        self.assertAlmostEqual(supercell.lattice.a, expected_a, places=5)
        self.assertIsNot(self.unit_cell, supercell)
    
    def test_make_supercell_always_returns_new(self):
        """Test that transformation function always returns a new object."""
        original_nsites = len(self.unit_cell)
        result = make_supercell(self.unit_cell, [2, 2, 2])
        
        # Transformation function always returns a new object
        self.assertIsNot(self.unit_cell, result)
        # Original should not be modified
        self.assertEqual(len(self.unit_cell), original_nsites)
        # Diamond structure has 2 atoms in primitive cell, so 2x2x2 supercell = 2 * 8 = 16 atoms
        self.assertEqual(len(result), 16)
    
    def test_make_supercell_invalid_matrix(self):
        """Test supercell with invalid matrix."""
        with self.assertRaises(ValueError):
            make_supercell(self.unit_cell, [2, 2])  # Invalid shape

class TestComposite(unittest.TestCase):
    """Tests for composite transformations."""
    
    def setUp(self):
        """Set up test molecule."""
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    def test_chain_transformations(self):
        """Test chaining multiple transformations."""
        from matsimpy.transformation import translate, rotate
        
        def translate_func(s):
            return translate(s, [1, 1, 1])
        
        def rotate_func(s):
            return rotate(s, 90, [0, 0, 1])
        
        transformed = chain(self.molecule, [translate_func, rotate_func])
        
        self.assertIsNot(self.molecule, transformed)
        # Should be both translated and rotated
        self.assertIsNotNone(transformed)
    
    def test_apply_transformations(self):
        """Test apply_transformations utility."""
        from matsimpy.transformation import translate
        
        def translate_func(s):
            return translate(s, [1, 1, 1])
        
        transformed = apply_transformations(self.molecule, translate_func)
        
        self.assertIsNot(self.molecule, transformed)

if __name__ == '__main__':
    unittest.main()

