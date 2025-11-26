import unittest
import numpy as np

from matsimpy.core import Crystal
from matsimpy.core import Lattice
from matsimpy.core import Composition
from monty.serialization import dumpfn, loadfn

class TestCrystal(unittest.TestCase):

    def setUp(self):
        self.species = ['Na', 'Cl']
        self.cart_positions = [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]]
        self.lattice = Lattice.from_parameters(a=5.0, b=5.0, c=5.0, alpha=90, beta=90, gamma=90)
        self.crystal = Crystal(self.species, self.cart_positions, self.lattice)

    def test_volume(self):
        volume = self.crystal.volume
        expected_volume = 125.0
        self.assertAlmostEqual(volume, expected_volume)

    def test_as_dict(self):
        d = self.crystal.as_dict()
        expected_dict = {
                '@module': 'matsimpy.core.crystal',
                '@class': 'Crystal',
                'pbc': [True, True, True],
                'lattice': {'@module': 'matsimpy.core.lattice',
                 '@class': 'Lattice',
                 'lattice_vectors': [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]]
            },
            "species": ["Na", "Cl"],
            "positions": [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]]
        }
        self.assertEqual(d["@module"], expected_dict["@module"])
        self.assertEqual(d["@class"], expected_dict["@class"])
        self.assertEqual(d["pbc"], expected_dict["pbc"])
        #np.testing.assert_allclose(d['lattice'], expected_dict['lattice'])
        # Species is now a tuple, but as_dict converts to list
        self.assertEqual(list(d['species']), expected_dict['species'])
        self.assertEqual(len(d['positions']), len(expected_dict['positions']))
        for p1, p2 in zip(d['positions'], expected_dict['positions']):
            for x, y in zip(p1, p2):
              self.assertAlmostEqual(x, y, places=6)

if __name__ == '__main__':
    unittest.main()

