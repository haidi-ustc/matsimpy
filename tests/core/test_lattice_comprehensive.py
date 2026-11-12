"""Comprehensive tests for Lattice class - constructors, properties, serialization."""
import unittest

from matsimpy.core import Lattice


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

    def test_class_method_hexagonal(self):
        lat = Lattice.hexagonal(a=3.0, c=5.0)
        self.assertAlmostEqual(lat.a, 3.0, places=5)
        self.assertAlmostEqual(lat.b, 3.0, places=5)
        self.assertAlmostEqual(lat.c, 5.0, places=5)
        self.assertAlmostEqual(lat.alpha, 90.0, places=5)
        self.assertAlmostEqual(lat.beta, 90.0, places=5)
        self.assertAlmostEqual(lat.gamma, 120.0, places=5)

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


class TestLatticeValidation(unittest.TestCase):
    def test_negative_scalar_raises(self):
        with self.assertRaises(ValueError) as ctx:
            Lattice(-5)
        self.assertIn("positive", str(ctx.exception).lower())

    def test_negative_orthorhombic_raises(self):
        with self.assertRaises(ValueError) as ctx:
            Lattice([3, -4, 5])
        self.assertIn("positive", str(ctx.exception).lower())

    def test_invalid_type_raises(self):
        for bad in ("invalid", {'a': 5}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    Lattice(bad)

    def test_non_3d_vectors_raises(self):
        with self.assertRaises(ValueError):
            Lattice([[1, 0], [0, 1]])


class TestLatticeRepr(unittest.TestCase):

    def test_repr(self):
        lat = Lattice.cubic(10.0)
        r = repr(lat)
        self.assertIn('Lattice', r)


if __name__ == '__main__':
    unittest.main()
