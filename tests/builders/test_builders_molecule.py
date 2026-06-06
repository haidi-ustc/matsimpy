"""Tests for molecule builders."""
import unittest
import numpy as np
from matsimpy.core import Molecule
from matsimpy.builders.molecule import (
    build_linear,
    build_bent,
    build_trigonal_planar,
    build_tetrahedral,
    build_from_smiles,
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

    def test_build_linear_zero_axis_raises(self):
        with self.assertRaises(ValueError):
            build_linear(['H', 'H'], [0.74], axis=[0, 0, 0])

    def test_build_linear_nan_axis_raises(self):
        with self.assertRaises(ValueError):
            build_linear(['H', 'H'], [0.74], axis=[float('nan'), 0, 0])

    def test_build_linear_negative_length_raises(self):
        with self.assertRaises(ValueError):
            build_linear(['H', 'H'], [-0.5])

    def test_build_linear_wrong_axis_shape_raises(self):
        with self.assertRaises(ValueError):
            build_linear(['H', 'H'], [0.74], axis=[1, 0])

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

    def test_build_bent_chain_four_atoms(self):
        """Test chain-like bent molecule with more than three atoms."""
        mol = build_bent(['C', 'C', 'C', 'C'], [1.4, 1.5, 1.6], [120.0, 110.0])

        self.assertIsInstance(mol, Molecule)
        self.assertEqual(len(mol.species), 4)
        for i, expected in enumerate([1.4, 1.5, 1.6]):
            distance = np.linalg.norm(mol.positions[i + 1] - mol.positions[i])
            self.assertAlmostEqual(distance, expected, places=6)

        for center_idx, expected in [(1, 120.0), (2, 110.0)]:
            v1 = mol.positions[center_idx - 1] - mol.positions[center_idx]
            v2 = mol.positions[center_idx + 1] - mol.positions[center_idx]
            angle = np.degrees(
                np.arccos(
                    np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                )
            )
            self.assertAlmostEqual(angle, expected, places=6)

    def test_build_bent_uses_plane_normal(self):
        """Test that plane_normal orients the generated molecule plane."""
        mol = build_bent(['O', 'H', 'H'], [1.0, 1.0], [90.0], plane_normal=[0, 1, 0])

        normal = np.cross(
            mol.positions[1] - mol.positions[0],
            mol.positions[2] - mol.positions[0],
        )
        normal = normal / np.linalg.norm(normal)
        self.assertAlmostEqual(abs(np.dot(normal, [0, 1, 0])), 1.0, places=6)

    def test_build_bent_validates_geometry_inputs(self):
        """Test bent molecule input validation."""
        with self.assertRaises(ValueError):
            build_bent(['O', 'H'], [1.0], [])
        with self.assertRaises(ValueError):
            build_bent(['O', 'H', 'H'], [1.0], [90.0])
        with self.assertRaises(ValueError):
            build_bent(['O', 'H', 'H'], [1.0, 1.0], [])
        with self.assertRaises(ValueError):
            build_bent(['O', 'H', 'H'], [0.0, 1.0], [90.0])
        with self.assertRaises(ValueError):
            build_bent(['O', 'H', 'H'], [1.0, 1.0], [180.0])
        with self.assertRaises(ValueError):
            build_bent(['O', 'H', 'H'], [1.0, 1.0], [90.0], plane_normal=[0, 0, 0])

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


class TestSmilesMolecule(unittest.TestCase):
    """Tests for RDKit-backed SMILES molecule generation."""

    def test_build_from_smiles_water_matches_rdkit_atom_count(self):
        """SMILES builder should return explicit-hydrogen RDKit geometry."""
        from rdkit import Chem

        water = build_from_smiles('O', optimize=True)
        rdkit_water = Chem.AddHs(Chem.MolFromSmiles('O'))

        self.assertIsInstance(water, Molecule)
        self.assertEqual(len(water), rdkit_water.GetNumAtoms())
        self.assertEqual(water.species.count('O'), 1)
        self.assertEqual(water.species.count('H'), 2)
        self.assertEqual(water.positions.shape, (3, 3))

    def test_build_from_smiles_invalid(self):
        """Invalid SMILES strings should fail cleanly."""
        with self.assertRaises(ValueError):
            build_from_smiles('not-a-smiles')

if __name__ == '__main__':
    unittest.main()
