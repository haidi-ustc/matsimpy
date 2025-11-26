import os
import unittest

from matsimpy.core import Crystal
from matsimpy.core import Lattice
from matsimpy.core import Composition
from monty.serialization import dumpfn, loadfn

class TestComposition(unittest.TestCase):
    def setUp(self):
        # Create composition.json file for testing
        with open("composition.json", "w") as f:
            f.write('{"@module": "matsimpy.core.composition", "@class": "Composition", "formula": "H2O"}')

    def test_parse_formula(self):
        c = Composition('H2O')
        self.assertEqual(c.composition['H'], 2)
        self.assertEqual(c.composition['O'], 1)

        c = Composition('NaCl')
        self.assertEqual(c.composition['Na'], 1)
        self.assertEqual(c.composition['Cl'], 1)

    def test_get_item(self):
        c = Composition('H2O')
        self.assertEqual(c['H'], 2)
        self.assertEqual(c['O'], 1)

    def test_serialization(self):
        c = Composition('H2O')
        dumpfn(c.as_dict(), 'composition.json')
        c2 = loadfn('composition.json')
        self.assertEqual(c.composition, c2.composition)

    def tearDown(self):
        # Remove composition.json file
        os.remove("composition.json")

if __name__ == '__main__':
    unittest.main()

