"""Tests for Lattice convenient constructor syntax."""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Lattice


class TestLatticeCubicConstructor(unittest.TestCase):
    """Test Lattice(scalar) -> cubic lattice."""
    
    def test_cubic_with_int(self):
        """Test creating cubic lattice with integer."""
        lat = Lattice(5)
        
        self.assertAlmostEqual(lat.a, 5.0)
        self.assertAlmostEqual(lat.b, 5.0)
        self.assertAlmostEqual(lat.c, 5.0)
        self.assertAlmostEqual(lat.alpha, 90.0)
        self.assertAlmostEqual(lat.beta, 90.0)
        self.assertAlmostEqual(lat.gamma, 90.0)
    
    def test_cubic_with_float(self):
        """Test creating cubic lattice with float."""
        lat = Lattice(5.43)
        
        self.assertAlmostEqual(lat.a, 5.43)
        self.assertAlmostEqual(lat.b, 5.43)
        self.assertAlmostEqual(lat.c, 5.43)
    
    def test_cubic_lattice_vectors(self):
        """Test that cubic creates correct lattice vectors."""
        lat = Lattice(10)
        
        expected = np.array([
            [10, 0, 0],
            [0, 10, 0],
            [0, 0, 10]
        ])
        
        self.assertTrue(np.allclose(lat.lattice_vectors, expected))
    
    def test_cubic_equivalent_to_class_method(self):
        """Test that Lattice(a) is equivalent to Lattice.cubic(a)."""
        a = 7.5
        lat1 = Lattice(a)
        lat2 = Lattice.cubic(a)
        
        self.assertTrue(np.allclose(lat1.lattice_vectors, lat2.lattice_vectors))
    
    def test_cubic_with_small_value(self):
        """Test cubic with small but valid value."""
        lat = Lattice(0.5)
        self.assertAlmostEqual(lat.a, 0.5)
    
    def test_cubic_with_large_value(self):
        """Test cubic with large value."""
        lat = Lattice(1000.0)
        self.assertAlmostEqual(lat.a, 1000.0)


class TestLatticeOrthorhombicConstructor(unittest.TestCase):
    """Test Lattice([a,b,c]) -> orthorhombic lattice."""
    
    def test_orthorhombic_with_list(self):
        """Test creating orthorhombic lattice with list."""
        lat = Lattice([3, 4, 5])
        
        self.assertAlmostEqual(lat.a, 3.0)
        self.assertAlmostEqual(lat.b, 4.0)
        self.assertAlmostEqual(lat.c, 5.0)
        self.assertAlmostEqual(lat.alpha, 90.0)
        self.assertAlmostEqual(lat.beta, 90.0)
        self.assertAlmostEqual(lat.gamma, 90.0)
    
    def test_orthorhombic_with_floats(self):
        """Test orthorhombic with float values."""
        lat = Lattice([3.5, 4.2, 5.8])
        
        self.assertAlmostEqual(lat.a, 3.5)
        self.assertAlmostEqual(lat.b, 4.2)
        self.assertAlmostEqual(lat.c, 5.8)
    
    def test_orthorhombic_lattice_vectors(self):
        """Test that orthorhombic creates correct lattice vectors."""
        lat = Lattice([2, 3, 4])
        
        expected = np.array([
            [2, 0, 0],
            [0, 3, 0],
            [0, 0, 4]
        ])
        
        self.assertTrue(np.allclose(lat.lattice_vectors, expected))
    
    def test_orthorhombic_equivalent_to_class_method(self):
        """Test that Lattice([a,b,c]) is equivalent to Lattice.orthorhombic(a,b,c)."""
        a, b, c = 3, 4, 5
        lat1 = Lattice([a, b, c])
        lat2 = Lattice.orthorhombic(a, b, c)
        
        self.assertTrue(np.allclose(lat1.lattice_vectors, lat2.lattice_vectors))
    
    def test_orthorhombic_all_same_is_cubic(self):
        """Test that [a,a,a] creates cubic lattice."""
        lat = Lattice([5, 5, 5])
        
        self.assertAlmostEqual(lat.a, 5.0)
        self.assertAlmostEqual(lat.b, 5.0)
        self.assertAlmostEqual(lat.c, 5.0)


class TestLatticeTraditionalConstructor(unittest.TestCase):
    """Test that traditional Lattice([[...], [...], [...]]) still works."""
    
    def test_traditional_3x3_matrix(self):
        """Test traditional full lattice vectors."""
        vectors = [[5, 0, 0], [0, 5, 0], [0, 0, 5]]
        lat = Lattice(vectors)
        
        self.assertAlmostEqual(lat.a, 5.0)
        self.assertAlmostEqual(lat.b, 5.0)
        self.assertAlmostEqual(lat.c, 5.0)
    
    def test_traditional_non_orthogonal(self):
        """Test traditional with non-orthogonal vectors."""
        vectors = [[5, 0, 0], [0, 5, 0], [2, 0, 5]]
        lat = Lattice(vectors)
        
        self.assertTrue(np.allclose(lat.lattice_vectors, vectors))
    
    def test_backward_compatibility(self):
        """Test that old code still works."""
        # This is how lattice was created before the enhancement
        lat = Lattice([[10, 0, 0], [0, 10, 0], [0, 0, 10]])
        
        self.assertAlmostEqual(lat.a, 10.0)


class TestLatticeValidation(unittest.TestCase):
    """Test input validation for convenient constructors."""
    
    def test_negative_cubic_raises_error(self):
        """Test that negative value for cubic raises error."""
        with self.assertRaises(ValueError) as context:
            Lattice(-5)
        
        self.assertIn("positive", str(context.exception).lower())
    
    def test_zero_cubic_raises_error(self):
        """Test that zero value for cubic raises error."""
        with self.assertRaises(ValueError):
            Lattice(0)
    
    def test_negative_orthorhombic_raises_error(self):
        """Test that negative values in orthorhombic raise error."""
        with self.assertRaises(ValueError) as context:
            Lattice([3, -4, 5])
        
        self.assertIn("positive", str(context.exception).lower())
    
    def test_zero_in_orthorhombic_raises_error(self):
        """Test that zero in orthorhombic raises error."""
        with self.assertRaises(ValueError):
            Lattice([3, 0, 5])
    
    def test_wrong_length_list_raises_error(self):
        """Test that list with wrong length raises error."""
        with self.assertRaises(ValueError):
            Lattice([3, 4])  # Only 2 values
        
        with self.assertRaises(ValueError):
            Lattice([3, 4, 5, 6])  # 4 values
    
    def test_invalid_type_raises_error(self):
        """Test that invalid types raise error."""
        with self.assertRaises(TypeError):
            Lattice("invalid")
        
        with self.assertRaises(TypeError):
            Lattice({'a': 5})


class TestLatticeConvenienceEdgeCases(unittest.TestCase):
    """Test edge cases for convenient constructors."""
    
    def test_cubic_with_very_small_value(self):
        """Test cubic with small but reasonable value."""
        lat = Lattice(0.1)
        self.assertAlmostEqual(lat.a, 0.1)
    
    def test_orthorhombic_with_very_different_values(self):
        """Test orthorhombic with very different parameters."""
        lat = Lattice([1, 10, 100])
        
        self.assertAlmostEqual(lat.a, 1.0)
        self.assertAlmostEqual(lat.b, 10.0)
        self.assertAlmostEqual(lat.c, 100.0)
    
    def test_numpy_array_works(self):
        """Test that numpy arrays work for orthorhombic."""
        import numpy as np
        arr = np.array([3, 4, 5])
        lat = Lattice(arr.tolist())
        
        self.assertAlmostEqual(lat.a, 3.0)
        self.assertAlmostEqual(lat.b, 4.0)
        self.assertAlmostEqual(lat.c, 5.0)


class TestLatticeIntegration(unittest.TestCase):
    """Integration tests with other Lattice functionality."""
    
    def test_cubic_lattice_parameters(self):
        """Test that lattice parameters work with convenient constructor."""
        lat = Lattice(5)
        
        self.assertAlmostEqual(lat.a, 5.0)
        self.assertAlmostEqual(lat.b, 5.0)
        self.assertAlmostEqual(lat.c, 5.0)
    
    def test_orthorhombic_lattice_parameters(self):
        """Test lattice parameters for orthorhombic."""
        lat = Lattice([2, 3, 4])
        
        self.assertAlmostEqual(lat.a, 2.0)
        self.assertAlmostEqual(lat.b, 3.0)
        self.assertAlmostEqual(lat.c, 4.0)
    
    def test_cubic_as_dict(self):
        """Test that as_dict works with cubic constructor."""
        lat = Lattice(5)
        d = lat.as_dict()
        
        self.assertEqual(d['@class'], 'Lattice')
        self.assertEqual(len(d['lattice_vectors']), 3)
    
    def test_orthorhombic_as_dict(self):
        """Test that as_dict works with orthorhombic constructor."""
        lat = Lattice([3, 4, 5])
        d = lat.as_dict()
        
        # Should be able to reconstruct
        lat2 = Lattice.from_dict(d)
        self.assertTrue(np.allclose(lat.lattice_vectors, lat2.lattice_vectors))
    
    def test_cubic_with_crystal(self):
        """Test using convenient cubic constructor with Crystal."""
        from matsimpy.core import Crystal
        
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        
        self.assertEqual(len(crystal), 1)
        self.assertAlmostEqual(crystal.lattice.a, 10.0)
    
    def test_orthorhombic_with_crystal(self):
        """Test using convenient orthorhombic constructor with Crystal."""
        from matsimpy.core import Crystal
        
        lat = Lattice([5, 6, 7])
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        
        self.assertAlmostEqual(crystal.lattice.a, 5.0)
        self.assertAlmostEqual(crystal.lattice.b, 6.0)
        self.assertAlmostEqual(crystal.lattice.c, 7.0)


class TestLatticeDocumentation(unittest.TestCase):
    """Test that documentation is clear and examples work."""
    
    def test_docstring_examples_cubic(self):
        """Test that docstring examples work - cubic."""
        # From docstring: lat = Lattice(5)
        lat = Lattice(5)
        self.assertAlmostEqual(lat.a, 5.0)
    
    def test_docstring_examples_orthorhombic(self):
        """Test that docstring examples work - orthorhombic."""
        # From docstring: lat = Lattice([3, 4, 5])
        lat = Lattice([3, 4, 5])
        self.assertAlmostEqual(lat.a, 3.0)
        self.assertAlmostEqual(lat.b, 4.0)
        self.assertAlmostEqual(lat.c, 5.0)
    
    def test_docstring_examples_traditional(self):
        """Test that docstring examples work - traditional."""
        # From docstring: lat = Lattice([[5, 0, 0], [0, 5, 0], [0, 0, 5]])
        lat = Lattice([[5, 0, 0], [0, 5, 0], [0, 0, 5]])
        self.assertAlmostEqual(lat.a, 5.0)


if __name__ == '__main__':
    unittest.main()

