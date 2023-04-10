import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import CrystalSite,Lattice
from matsimpy.core.periodic_table import Element


class TestCrystalSite(unittest.TestCase):
    def setUp(self):
        self.lattice_vectors = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
        self.lattice = Lattice(self.lattice_vectors)
        self.position = [0.5, 0.5, 0.5]
        self.specie = Element('C')
        self.site = CrystalSite(position=self.position, specie=self.specie, lattice=self.lattice_vectors)

    def test_position(self):
        self.assertEqual(self.site.position.tolist(), self.site.cart_position.tolist())
        self.site.position = [1, 1, 1]
        self.assertEqual(self.site.position.tolist(), self.site.cart_position.tolist())

    def test_frac_position(self):
        frac_position = self.site.frac_position
        self.assertAlmostEqual(frac_position[0], 0.25)
        self.assertAlmostEqual(frac_position[1], 0.25)
        self.assertAlmostEqual(frac_position[2], 0.25)

    def test_specie(self):
        self.assertEqual(self.site.specie, self.specie.symbol)

    def test_lattice(self):
        self.assertEqual(self.site.lattice.lattice_vectors.tolist(), self.lattice_vectors)

    def test_as_dict(self):
        d = self.site.as_dict()
        self.assertEqual(d["@class"], "CrystalSite")
        self.assertEqual(d["position"], self.position)
        self.assertEqual(d["specie"], self.specie.symbol)
        self.assertEqual(d["lattice"]["@class"], "Lattice")
        self.assertEqual(d["lattice"]["lattice_vectors"], self.lattice_vectors)

    def test_from_dict(self):
        d = self.site.as_dict()
        site = CrystalSite.from_dict(d)
        self.assertEqual(site.position.tolist(), self.position)
        self.assertEqual(site.specie, self.specie.symbol)
        self.assertEqual(site.lattice.lattice_vectors.tolist(), self.lattice_vectors)

if __name__ == '__main__':
    unittest.main()

