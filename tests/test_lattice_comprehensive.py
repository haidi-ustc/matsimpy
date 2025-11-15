"""Comprehensive tests for Lattice class."""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Lattice


class TestLatticeComprehensive(unittest.TestCase):
    """Comprehensive tests for Lattice class."""
    
    def test_lattice_init(self):
        """Test lattice initialization."""
        vectors = [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
        lattice = Lattice(vectors)
        self.assertEqual(len(lattice.lattice_vectors), 3)
    
    def test_lattice_validation_non_3d(self):
        """Test validation of non-3D vectors."""
        with self.assertRaises(ValueError):
            Lattice([[1, 0], [0, 1]])  # 2D
    
    def test_lattice_validation_dependent(self):
        """Test validation of linearly dependent vectors."""
        with self.assertRaises(ValueError):
            Lattice([[1, 0, 0], [2, 0, 0], [0, 0, 1]])  # First two are parallel
    
    def test_lattice_matrix(self):
        """Test matrix property."""
        vectors = [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
        lattice = Lattice(vectors)
        matrix = lattice.matrix
        self.assertEqual(matrix.shape, (3, 3))
        np.testing.assert_array_equal(matrix[0], [10, 0, 0])
    
    def test_lattice_inv_matrix(self):
        """Test inverse matrix property."""
        vectors = [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
        lattice = Lattice(vectors)
        inv = lattice.inv_matrix
        result = np.dot(lattice.matrix, inv)
        np.testing.assert_array_almost_equal(result, np.eye(3))
    
    def test_lattice_parameters(self):
        """Test lattice parameter properties."""
        vectors = [[5, 0, 0], [0, 6, 0], [0, 0, 7]]
        lattice = Lattice(vectors)
        
        self.assertEqual(lattice.a, 5.0)
        self.assertEqual(lattice.b, 6.0)
        self.assertEqual(lattice.c, 7.0)
    
    def test_lattice_angles_cubic(self):
        """Test angles for cubic lattice."""
        vectors = [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
        lattice = Lattice(vectors)
        
        self.assertAlmostEqual(lattice.alpha, 90.0, places=5)
        self.assertAlmostEqual(lattice.beta, 90.0, places=5)
        self.assertAlmostEqual(lattice.gamma, 90.0, places=5)
    
    def test_lattice_volume(self):
        """Test volume calculation."""
        vectors = [[2, 0, 0], [0, 3, 0], [0, 0, 4]]
        lattice = Lattice(vectors)
        self.assertEqual(lattice.volume(), 24.0)
    
    def test_lattice_from_parameters(self):
        """Test creation from parameters."""
        lattice = Lattice.from_parameters(a=5.0, b=6.0, c=7.0, 
                                         alpha=90, beta=90, gamma=90)
        self.assertAlmostEqual(lattice.a, 5.0, places=5)
        self.assertAlmostEqual(lattice.b, 6.0, places=5)
        self.assertAlmostEqual(lattice.c, 7.0, places=5)
    
    def test_lattice_from_parameters_non_orthogonal(self):
        """Test creation from non-orthogonal parameters."""
        lattice = Lattice.from_parameters(a=5.0, b=5.0, c=5.0,
                                         alpha=60, beta=60, gamma=60)
        self.assertAlmostEqual(lattice.a, 5.0, places=5)
    
    def test_lattice_cubic(self):
        """Test cubic lattice creation."""
        lattice = Lattice.cubic(10.0)
        self.assertEqual(lattice.a, 10.0)
        self.assertEqual(lattice.b, 10.0)
        self.assertEqual(lattice.c, 10.0)
        self.assertAlmostEqual(lattice.alpha, 90.0, places=5)
    
    def test_lattice_tetragonal(self):
        """Test tetragonal lattice creation."""
        lattice = Lattice.tetragonal(a=5.0, c=10.0)
        self.assertEqual(lattice.a, 5.0)
        self.assertEqual(lattice.b, 5.0)
        self.assertEqual(lattice.c, 10.0)
    
    def test_lattice_orthorhombic(self):
        """Test orthorhombic lattice creation."""
        lattice = Lattice.orthorhombic(a=5.0, b=6.0, c=7.0)
        self.assertEqual(lattice.a, 5.0)
        self.assertEqual(lattice.b, 6.0)
        self.assertEqual(lattice.c, 7.0)
    
    def test_lattice_hexagonal(self):
        """Test hexagonal lattice creation."""
        lattice = Lattice.hexagonal(a=3.0, c=5.0)
        self.assertAlmostEqual(lattice.a, 3.0, places=5)
        self.assertAlmostEqual(lattice.b, 3.0, places=5)
        self.assertAlmostEqual(lattice.c, 5.0, places=5)
        self.assertAlmostEqual(lattice.alpha, 90.0, places=5)
        self.assertAlmostEqual(lattice.beta, 90.0, places=5)
        self.assertAlmostEqual(lattice.gamma, 120.0, places=5)
    
    def test_lattice_rhombohedral(self):
        """Test rhombohedral lattice creation."""
        lattice = Lattice.rhombohedral(a=5.0, alpha=60.0)
        self.assertAlmostEqual(lattice.a, 5.0, places=5)
        self.assertAlmostEqual(lattice.b, 5.0, places=5)
        self.assertAlmostEqual(lattice.c, 5.0, places=5)
        self.assertAlmostEqual(lattice.alpha, 60.0, places=5)
        self.assertAlmostEqual(lattice.beta, 60.0, places=5)
        self.assertAlmostEqual(lattice.gamma, 60.0, places=5)
    
    def test_lattice_monoclinic(self):
        """Test monoclinic lattice creation."""
        lattice = Lattice.monoclinic(a=5.0, b=6.0, c=7.0, beta=90.0)
        self.assertAlmostEqual(lattice.a, 5.0, places=5)
        self.assertAlmostEqual(lattice.b, 6.0, places=5)
        self.assertAlmostEqual(lattice.c, 7.0, places=5)
        self.assertAlmostEqual(lattice.alpha, 90.0, places=5)
        self.assertAlmostEqual(lattice.beta, 90.0, places=5)
        self.assertAlmostEqual(lattice.gamma, 90.0, places=5)
        
        # Test with non-90 beta
        lattice2 = Lattice.monoclinic(a=5.0, b=6.0, c=7.0, beta=120.0)
        self.assertAlmostEqual(lattice2.beta, 120.0, places=5)
    
    def test_lattice_triclinic(self):
        """Test triclinic lattice creation."""
        lattice = Lattice.triclinic(a=5.0, b=6.0, c=7.0, alpha=80.0, beta=90.0, gamma=100.0)
        self.assertAlmostEqual(lattice.a, 5.0, places=5)
        self.assertAlmostEqual(lattice.b, 6.0, places=5)
        self.assertAlmostEqual(lattice.c, 7.0, places=5)
        self.assertAlmostEqual(lattice.alpha, 80.0, places=5)
        self.assertAlmostEqual(lattice.beta, 90.0, places=5)
        self.assertAlmostEqual(lattice.gamma, 100.0, places=5)
    
    def test_lattice_orthorhombic_alias(self):
        """Test orthorhombic alias (correct spelling)."""
        lattice = Lattice.orthorhombic(a=5.0, b=6.0, c=7.0)
        self.assertEqual(lattice.a, 5.0)
        self.assertEqual(lattice.b, 6.0)
        self.assertEqual(lattice.c, 7.0)
        # Should be the same as orthorhombic
        lattice2 = Lattice.orthorhombic(a=5.0, b=6.0, c=7.0)
        np.testing.assert_array_almost_equal(lattice.matrix, lattice2.matrix)
    
    def test_lattice_str(self):
        """Test string representation."""
        lattice = Lattice.cubic(10.0)
        str_repr = str(lattice)
        self.assertIn('Lattice', str_repr)
        self.assertIn('10.0000', str_repr)
    
    def test_lattice_repr(self):
        """Test representation."""
        lattice = Lattice.cubic(10.0)
        repr_str = repr(lattice)
        self.assertIn('Lattice', repr_str)
    
    def test_lattice_as_dict(self):
        """Test dictionary representation."""
        lattice = Lattice.cubic(10.0)
        d = lattice.as_dict()
        self.assertIn('lattice_vectors', d)
        self.assertEqual(len(d['lattice_vectors']), 3)
    
    def test_lattice_from_dict(self):
        """Test creation from dictionary."""
        d = {
            'lattice_vectors': [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
        }
        lattice = Lattice.from_dict(d)
        self.assertEqual(lattice.a, 10.0)
    
    def test_lattice_inv_matrix_caching(self):
        """Test that inverse matrix is cached."""
        lattice = Lattice.cubic(10.0)
        inv1 = lattice.inv_matrix
        inv2 = lattice.inv_matrix
        # Should be same object (cached)
        self.assertIs(lattice._inv_matrix, inv1)
        np.testing.assert_array_equal(inv1, inv2)


if __name__ == '__main__':
    unittest.main()

