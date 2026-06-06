"""Comprehensive tests for Lattice class - constructors, properties, serialization."""
import unittest
import numpy as np

from matsimpy.core import Lattice, Crystal


class TestLatticeConstructors(unittest.TestCase):
    def test_scalar_cubic_constructor(self):
        for val, expected_a in [(5, 5.0), (5.43, 5.43), (0.5, 0.5), (1000.0, 1000.0)]:
            with self.subTest(val=val):
                lat = Lattice(val)
                self.assertAlmostEqual(lat.a, expected_a)
                self.assertAlmostEqual(lat.b, expected_a)
                self.assertAlmostEqual(lat.c, expected_a)
                self.assertAlmostEqual(lat.alpha, 90.0)
                self.assertAlmostEqual(lat.beta, 90.0)
                self.assertAlmostEqual(lat.gamma, 90.0)

    def test_scalar_equivalent_to_cubic(self):
        a = 7.5
        lat1 = Lattice(a)
        lat2 = Lattice.cubic(a)
        self.assertTrue(np.allclose(lat1.lattice_vectors, lat2.lattice_vectors))

    def test_list_orthorhombic_constructor(self):
        for vec, (ea, eb, ec) in [
            ([3, 4, 5], (3.0, 4.0, 5.0)),
            ([3.5, 4.2, 5.8], (3.5, 4.2, 5.8)),
            ([5, 5, 5], (5.0, 5.0, 5.0)),
            ([1, 10, 100], (1.0, 10.0, 100.0)),
        ]:
            with self.subTest(vec=vec):
                lat = Lattice(vec)
                self.assertAlmostEqual(lat.a, ea)
                self.assertAlmostEqual(lat.b, eb)
                self.assertAlmostEqual(lat.c, ec)
                self.assertAlmostEqual(lat.alpha, 90.0)
                self.assertAlmostEqual(lat.beta, 90.0)
                self.assertAlmostEqual(lat.gamma, 90.0)

    def test_list_equivalent_to_orthorhombic(self):
        a, b, c = 3, 4, 5
        lat1 = Lattice([a, b, c])
        lat2 = Lattice.orthorhombic(a, b, c)
        self.assertTrue(np.allclose(lat1.lattice_vectors, lat2.lattice_vectors))

    def test_3x3_matrix_orthogonal(self):
        lat = Lattice([[5, 0, 0], [0, 5, 0], [0, 0, 5]])
        self.assertAlmostEqual(lat.a, 5.0)
        self.assertAlmostEqual(lat.b, 5.0)
        self.assertAlmostEqual(lat.c, 5.0)

    def test_3x3_matrix_non_orthogonal(self):
        vectors = [[5, 0, 0], [0, 5, 0], [2, 0, 5]]
        lat = Lattice(vectors)
        self.assertTrue(np.allclose(lat.lattice_vectors, vectors))

    def test_class_method_cubic(self):
        lat = Lattice.cubic(10.0)
        self.assertAlmostEqual(lat.a, 10.0)
        self.assertAlmostEqual(lat.alpha, 90.0)

    def test_class_method_tetragonal(self):
        lat = Lattice.tetragonal(a=5.0, c=10.0)
        self.assertEqual(lat.a, 5.0)
        self.assertEqual(lat.c, 10.0)

    def test_class_method_orthorhombic(self):
        lat = Lattice.orthorhombic(a=5.0, b=6.0, c=7.0)
        self.assertEqual(lat.a, 5.0)
        self.assertEqual(lat.b, 6.0)
        self.assertEqual(lat.c, 7.0)

    def test_class_method_hexagonal(self):
        lat = Lattice.hexagonal(a=3.0, c=5.0)
        self.assertAlmostEqual(lat.a, 3.0, places=5)
        self.assertAlmostEqual(lat.b, 3.0, places=5)
        self.assertAlmostEqual(lat.c, 5.0, places=5)
        self.assertAlmostEqual(lat.alpha, 90.0, places=5)
        self.assertAlmostEqual(lat.beta, 90.0, places=5)
        self.assertAlmostEqual(lat.gamma, 120.0, places=5)

    def test_class_method_rhombohedral(self):
        lat = Lattice.rhombohedral(a=5.0, alpha=60.0)
        self.assertAlmostEqual(lat.a, 5.0, places=5)
        self.assertAlmostEqual(lat.b, 5.0, places=5)
        self.assertAlmostEqual(lat.c, 5.0, places=5)
        self.assertAlmostEqual(lat.alpha, 60.0, places=5)
        self.assertAlmostEqual(lat.beta, 60.0, places=5)
        self.assertAlmostEqual(lat.gamma, 60.0, places=5)

    def test_class_method_monoclinic(self):
        lat = Lattice.monoclinic(a=5.0, b=6.0, c=7.0, beta=90.0)
        self.assertAlmostEqual(lat.a, 5.0, places=5)
        self.assertAlmostEqual(lat.alpha, 90.0, places=5)
        self.assertAlmostEqual(lat.gamma, 90.0, places=5)

        lat2 = Lattice.monoclinic(a=5.0, b=6.0, c=7.0, beta=120.0)
        self.assertAlmostEqual(lat2.beta, 120.0, places=5)

    def test_class_method_triclinic(self):
        lat = Lattice.triclinic(a=5.0, b=6.0, c=7.0, alpha=80.0, beta=90.0, gamma=100.0)
        self.assertAlmostEqual(lat.a, 5.0, places=5)
        self.assertAlmostEqual(lat.alpha, 80.0, places=5)
        self.assertAlmostEqual(lat.gamma, 100.0, places=5)

    def test_from_parameters_orthogonal(self):
        lat = Lattice.from_parameters(a=5.0, b=6.0, c=7.0, alpha=90, beta=90, gamma=90)
        self.assertAlmostEqual(lat.a, 5.0, places=5)
        self.assertAlmostEqual(lat.b, 6.0, places=5)
        self.assertAlmostEqual(lat.c, 7.0, places=5)

    def test_from_parameters_non_orthogonal(self):
        lat = Lattice.from_parameters(a=5.0, b=5.0, c=5.0, alpha=60, beta=60, gamma=60)
        self.assertAlmostEqual(lat.a, 5.0, places=5)


class TestLatticeValidation(unittest.TestCase):
    def test_negative_scalar_raises(self):
        with self.assertRaises(ValueError) as ctx:
            Lattice(-5)
        self.assertIn("positive", str(ctx.exception).lower())

    def test_zero_scalar_raises(self):
        with self.assertRaises(ValueError):
            Lattice(0)

    def test_negative_orthorhombic_raises(self):
        with self.assertRaises(ValueError) as ctx:
            Lattice([3, -4, 5])
        self.assertIn("positive", str(ctx.exception).lower())

    def test_zero_orthorhombic_raises(self):
        with self.assertRaises(ValueError):
            Lattice([3, 0, 5])

    def test_wrong_length_list_raises(self):
        for bad in ([3, 4], [3, 4, 5, 6]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    Lattice(bad)

    def test_invalid_type_raises(self):
        for bad in ("invalid", {'a': 5}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    Lattice(bad)

    def test_non_3d_vectors_raises(self):
        with self.assertRaises(ValueError):
            Lattice([[1, 0], [0, 1]])

    def test_dependent_vectors_raises(self):
        with self.assertRaises(ValueError):
            Lattice([[1, 0, 0], [2, 0, 0], [0, 0, 1]])


class TestLatticeProperties(unittest.TestCase):
    def test_parameters_from_matrix(self):
        lat = Lattice([[5, 0, 0], [0, 6, 0], [0, 0, 7]])
        self.assertEqual(lat.a, 5.0)
        self.assertEqual(lat.b, 6.0)
        self.assertEqual(lat.c, 7.0)

    def test_angles_cubic(self):
        lat = Lattice.cubic(10.0)
        self.assertAlmostEqual(lat.alpha, 90.0, places=5)
        self.assertAlmostEqual(lat.beta, 90.0, places=5)
        self.assertAlmostEqual(lat.gamma, 90.0, places=5)

    def test_volume(self):
        lat = Lattice([2, 3, 4])
        self.assertAlmostEqual(lat.volume, 24.0, places=10)

    def test_matrix(self):
        lat = Lattice.cubic(10.0)
        matrix = lat.matrix
        self.assertEqual(matrix.shape, (3, 3))
        np.testing.assert_array_equal(matrix[0], [10, 0, 0])

    def test_inv_matrix(self):
        lat = Lattice.cubic(10.0)
        inv = lat.inv_matrix
        result = np.dot(lat.matrix, inv)
        np.testing.assert_array_almost_equal(result, np.eye(3))

    def test_inv_matrix_caching(self):
        lattice = Lattice.cubic(10.0)
        inv1 = lattice.inv_matrix
        inv2 = lattice.inv_matrix
        self.assertIs(lattice._inv_matrix, inv1)
        np.testing.assert_array_equal(inv1, inv2)


class TestLatticeSerialization(unittest.TestCase):
    def test_as_dict(self):
        lat = Lattice.cubic(10.0)
        d = lat.as_dict()
        self.assertIn('lattice_vectors', d)
        self.assertEqual(len(d['lattice_vectors']), 3)

    def test_from_dict(self):
        d = {'lattice_vectors': [[10, 0, 0], [0, 10, 0], [0, 0, 10]]}
        lat = Lattice.from_dict(d)
        self.assertEqual(lat.a, 10.0)

    def test_roundtrip_scalar(self):
        lat = Lattice(5)
        d = lat.as_dict()
        self.assertEqual(d['@class'], 'Lattice')
        lat2 = Lattice.from_dict(d)
        self.assertTrue(np.allclose(lat.lattice_vectors, lat2.lattice_vectors))

    def test_roundtrip_orthorhombic(self):
        lat = Lattice([3, 4, 5])
        d = lat.as_dict()
        lat2 = Lattice.from_dict(d)
        self.assertTrue(np.allclose(lat.lattice_vectors, lat2.lattice_vectors))


class TestLatticeRepr(unittest.TestCase):
    def test_str(self):
        lat = Lattice.cubic(10.0)
        s = str(lat)
        self.assertIn('Lattice', s)
        self.assertIn('10.0000', s)

    def test_repr(self):
        lat = Lattice.cubic(10.0)
        r = repr(lat)
        self.assertIn('Lattice', r)


class TestLatticeIntegration(unittest.TestCase):
    def test_scalar_lattice_with_crystal(self):
        lat = Lattice(10)
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        self.assertEqual(len(crystal), 1)
        self.assertAlmostEqual(crystal.lattice.a, 10.0)

    def test_orthorhombic_lattice_with_crystal(self):
        lat = Lattice([5, 6, 7])
        crystal = Crystal(['Si'], [[0, 0, 0]], lat)
        self.assertAlmostEqual(crystal.lattice.a, 5.0)
        self.assertAlmostEqual(crystal.lattice.b, 6.0)
        self.assertAlmostEqual(crystal.lattice.c, 7.0)


if __name__ == '__main__':
    unittest.main()
