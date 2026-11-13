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
    
    
    def test_build_linear_positions(self):
        """Test linear molecule positions."""
        mol = build_linear(['H', 'H'], [0.74])
        
        # First atom at origin
        np.testing.assert_array_almost_equal(mol.positions[0], [0, 0, 0])
        # Second atom along x-axis
        self.assertAlmostEqual(mol.positions[1][0], 0.74, places=5)
    
    
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

    def test_build_bent_chain_is_a_trans_zigzag(self):
        """Chains always turned the same way: a 6-atom 90-degree chain closed into a square."""
        mol = build_bent(['C'] * 6, [1.5] * 5, [90.0] * 4)
        distances = np.linalg.norm(mol.positions[:, None] - mol.positions[None], axis=-1)
        np.fill_diagonal(distances, np.inf)
        self.assertAlmostEqual(distances.min(), 1.5, places=6)
        # every 1-4 distance is the trans one, sqrt(5) * 1.5 for 90-degree angles
        for i in range(3):
            self.assertAlmostEqual(distances[i, i + 3], np.sqrt(5) * 1.5, places=6)

    def test_build_bent_rejects_nan(self):
        with self.assertRaises(ValueError):
            build_bent(['O', 'H', 'H'], [float('nan'), 0.96], [104.5])
        with self.assertRaises(ValueError):
            build_bent(['O', 'H', 'H'], [0.96, 0.96], [float('nan')])

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

    def test_bond_length_is_validated(self):
        """A negative bond length used to mirror the molecule silently."""
        for bad in (-1.09, 0.0, float('nan')):
            with self.assertRaises(ValueError):
                build_tetrahedral('C', ['H'] * 4, bad)
            with self.assertRaises(ValueError):
                build_trigonal_planar('B', ['F'] * 3, bad)


try:
    import rdkit  # noqa: F401
    _HAS_RDKIT = True
except ImportError:
    _HAS_RDKIT = False


@unittest.skipUnless(_HAS_RDKIT, "rdkit (optional extra 'builders') not installed")
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
