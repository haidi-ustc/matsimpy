"""Tests that hash raises TypeError for unhashable core classes."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.core.site import Site, CrystalSite


class TestHashRaisesTypeError(unittest.TestCase):
    """Test that hash() raises TypeError for unhashable core classes."""

    def test_hash_molecule_raises_typeerror(self):
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        with self.assertRaises(TypeError):
            hash(mol)

    def test_hash_crystal_raises_typeerror(self):
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)
        with self.assertRaises(TypeError):
            hash(crystal)

    def test_hash_lattice_raises_typeerror(self):
        lat = Lattice.cubic(5.0)
        with self.assertRaises(TypeError):
            hash(lat)

    def test_hash_site_raises_typeerror(self):
        site = Site([0, 0, 0], 'Fe')
        with self.assertRaises(TypeError):
            hash(site)

    def test_hash_crystalsite_raises_typeerror(self):
        lattice = Lattice.cubic(10.0)
        site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        with self.assertRaises(TypeError):
            hash(site)

    def test_structure_in_set_raises_typeerror(self):
        mol = Molecule(['C'], [[0, 0, 0]])
        with self.assertRaises(TypeError):
            {mol}

    def test_structure_as_dict_key_raises_typeerror(self):
        mol = Molecule(['C'], [[0, 0, 0]])
        with self.assertRaises(TypeError):
            {mol: 'value'}

    def test_lattice_in_set_raises_typeerror(self):
        lat = Lattice.cubic(5.0)
        with self.assertRaises(TypeError):
            {lat}

    def test_site_in_set_raises_typeerror(self):
        site = Site([0, 0, 0], 'Fe')
        with self.assertRaises(TypeError):
            {site}


if __name__ == '__main__':
    unittest.main()
