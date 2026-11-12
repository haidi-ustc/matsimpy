"""Tests for class-method substitution on Crystal and Molecule."""
import unittest

from matsimpy.core import Crystal, Molecule, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule


class TestMoleculeSubstitution(unittest.TestCase):

    def setUp(self):
        self.molecule = make_simple_molecule()

    def test_substitute_rejects_negative_index(self):
        molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])

        with self.assertRaises(IndexError):
            molecule.substitute(-1, 'N')
        with self.assertRaises(IndexError):
            molecule.substitute([-1], ['N'])
        with self.assertRaises(IndexError):
            molecule.substitute([-1], {'O': 'N'})

    def test_substitute_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            self.molecule.substitute([0, 1], ['N'])

    def test_substitute_dict_missing_key(self):
        with self.assertRaises(KeyError):
            self.molecule.substitute([0], {'X': 'N'})


class TestCrystalSubstitution(unittest.TestCase):

    def setUp(self):
        self.crystal = make_simple_crystal()

    def test_substitute_rejects_negative_index(self):
        crystal = Crystal(
            ['Si', 'O'],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5),
        )

        with self.assertRaises(IndexError):
            crystal.substitute(-1, 'Ge')
        with self.assertRaises(IndexError):
            crystal.substitute([-1], ['Ge'])
        with self.assertRaises(IndexError):
            crystal.substitute([-1], {'O': 'S'})


class TestSubstitutionTransformationEquivalence(unittest.TestCase):


    def test_substitute_all_consistency(self):
        from matsimpy.transformation import substitute_all

        mol1 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mol1_result = mol1.substitute_all('C', 'N')

        mol2 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mol2_result = substitute_all(mol2, 'C', 'N')

        self.assertEqual(mol1_result.species, mol2_result.species)


if __name__ == '__main__':
    unittest.main()
