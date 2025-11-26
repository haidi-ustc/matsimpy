"""Tests for molecule builders."""
import unittest
import numpy as np
from matsimpy.core import Molecule
from matsimpy.builders.molecule import (
    build_linear,
    build_bent,
    build_trigonal_planar,
    build_tetrahedral
)

class TestLinearMolecule(unittest.TestCase):
    """Tests for linear molecule generation."""
    
    def test_build_linear_co2(self):
        """Test building CO2."""
        co2 = build_linear(['O', 'C', 'O'], [1.16, 1.16])
        
        self.assertEqual(len(co2.species), 3)
        self.assertEqual(co2.species[0], 'O')
        self.assertEqual(co2.species[1], 'C')
        self.assertEqual(co2.species[2], 'O')
    
    def test_build_linear_positions(self):
        """Test linear molecule positions."""
        mol = build_linear(['H', 'H'], [0.74])
        
        # First atom at origin
        np.testing.assert_array_almost_equal(mol.positions[0], [0, 0, 0])
        # Second atom along x-axis
        self.assertAlmostEqual(mol.positions[1][0], 0.74, places=5)
    
    def test_build_linear_custom_axis(self):
        """Test linear molecule along custom axis."""
        mol = build_linear(['H', 'H'], [0.74], axis=[0, 1, 0])
        
        # Along y-axis
        self.assertAlmostEqual(mol.positions[1][1], 0.74, places=5)
        self.assertAlmostEqual(mol.positions[1][0], 0.0, places=5)
    
    def test_build_linear_invalid_bonds(self):
        """Test with wrong number of bond lengths."""
        with self.assertRaises(ValueError):
            build_linear(['H', 'H'], [0.74, 0.74])  # Too many bonds

class TestBentMolecule(unittest.TestCase):
    """Tests for bent molecule generation."""
    
    def test_build_bent_h2o(self):
        """Test building H2O."""
        h2o = build_bent(['O', 'H', 'H'], [0.96, 0.96], [104.5])
        
        self.assertEqual(len(h2o.species), 3)
        self.assertEqual(h2o.species[0], 'O')
        self.assertEqual(h2o.species[1], 'H')
        self.assertEqual(h2o.species[2], 'H')
    
    def test_build_bent_angle(self):
        """Test bent molecule angle."""
        # 90 degree bent molecule
        mol = build_bent(['O', 'H', 'H'], [1.0, 1.0], [90.0])
        
        # Central atom at origin
        np.testing.assert_array_almost_equal(mol.positions[0], [0, 0, 0])
        # Check angle is approximately 90 degrees
        v1 = mol.positions[1] - mol.positions[0]
        v2 = mol.positions[2] - mol.positions[0]
        angle = np.degrees(np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))))
        self.assertAlmostEqual(angle, 90.0, places=1)

class TestTrigonalPlanar(unittest.TestCase):
    """Tests for trigonal planar molecule generation."""
    
    def test_build_trigonal_planar_bf3(self):
        """Test building BF3."""
        bf3 = build_trigonal_planar('B', ['F', 'F', 'F'], 1.31)
        
        self.assertEqual(len(bf3.species), 4)
        self.assertEqual(bf3.species[0], 'B')
        self.assertIn('F', bf3.species)
    
    def test_build_trigonal_planar_geometry(self):
        """Test trigonal planar geometry."""
        mol = build_trigonal_planar('C', ['H', 'H', 'H'], 1.0)
        
        # All atoms in xy-plane
        for pos in mol.positions:
            self.assertAlmostEqual(pos[2], 0.0, places=5)
        
        # Central atom at origin
        np.testing.assert_array_almost_equal(mol.positions[0], [0, 0, 0])
    
    def test_build_trigonal_planar_invalid(self):
        """Test with wrong number of peripheral atoms."""
        with self.assertRaises(ValueError):
            build_trigonal_planar('B', ['F', 'F'], 1.31)  # Only 2 atoms

class TestTetrahedral(unittest.TestCase):
    """Tests for tetrahedral molecule generation."""
    
    def test_build_tetrahedral_ch4(self):
        """Test building CH4."""
        ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
        
        self.assertEqual(len(ch4.species), 5)
        self.assertEqual(ch4.species[0], 'C')
        self.assertEqual(sum(1 for s in ch4.species if s == 'H'), 4)
    
    def test_build_tetrahedral_bond_lengths(self):
        """Test tetrahedral bond lengths."""
        mol = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.0)
        
        # All bonds should be approximately 1.0
        for i in range(1, 5):
            distance = np.linalg.norm(mol.positions[i] - mol.positions[0])
            self.assertAlmostEqual(distance, 1.0, places=5)
    
    def test_build_tetrahedral_invalid(self):
        """Test with wrong number of peripheral atoms."""
        with self.assertRaises(ValueError):
            build_tetrahedral('C', ['H', 'H', 'H'], 1.09)  # Only 3 H

if __name__ == '__main__':
    unittest.main()

