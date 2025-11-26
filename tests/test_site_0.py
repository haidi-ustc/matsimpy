import unittest
import numpy as np

from matsimpy.core import Site
from matsimpy.core.periodic_table import Element

class TestSite(unittest.TestCase):

    def test_init(self):
        # Test default values
        s = Site([0, 0, 0])
        self.assertEqual(s.position.tolist(), [0, 0, 0])
        self.assertEqual(s.specie,'X')
        self.assertEqual(s.properties, {})

        # Test setting values
        s = Site([0.5, 0.5, 0.5], specie="Fe", properties={"magmom": 2.5})
        self.assertEqual(s.position.tolist(), [0.5, 0.5, 0.5])
        self.assertEqual(s.specie, "Fe")
        self.assertEqual(s.properties, {"magmom": 2.5})

        # Test setting Element object as specie
        s = Site([0.5, 0.5, 0.5], specie=Element("Fe"), properties={"magmom": 2.5})
        self.assertEqual(s.specie, "Fe")

        # Test setting invalid specie (invalid atomic number)
        with self.assertRaises(ValueError):
            s = Site([0, 0, 0], specie=123)

        # Test setting invalid properties
        with self.assertRaises(TypeError):
            s = Site([0, 0, 0], properties="not_a_dict")

    def test_properties(self):
        s = Site([0, 0, 0])
        self.assertEqual(s.properties, {})

        # Test setting properties
        s.properties = {"charge": 2}
        self.assertEqual(s.properties, {"charge": 2})

        # Test setting invalid properties
        with self.assertRaises(TypeError):
            s.properties = "not_a_dict"

    def test_specie(self):
        s = Site([0, 0, 0])
        self.assertEqual(s.specie,'X')

        # Test setting specie
        s.specie = "Fe"
        self.assertEqual(s.specie, "Fe")

        # Test setting Element object as specie
        s.specie = Element("Fe")
        self.assertEqual(s.specie, "Fe")

        # Test setting invalid specie (invalid atomic number)
        with self.assertRaises(ValueError):
            s.specie = 123

    def test_position(self):
        s = Site([0, 0, 0])
        self.assertEqual(s.position.tolist(), [0, 0, 0])

        # Test setting position
        s.position = [0.5, 0.5, 0.5]
        self.assertEqual(s.position.tolist(), [0.5, 0.5, 0.5])

        # Test setting invalid position
        with self.assertRaises(TypeError):
            s.position = "not_a_list"
            s.position = [0, 0]
            s.position = [0, 0, "not_a_float"]

if __name__ == '__main__':
    unittest.main()

