"""Tests for class-method substitution on Crystal and Molecule."""
import unittest

from matsimpy.core import Crystal, Molecule, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule


class TestMoleculeSubstitution(unittest.TestCase):

    def setUp(self):
        self.molecule = make_simple_molecule()

    def test_substitute_single(self):
        original_species = list(self.molecule.species)
        result = self.molecule.substitute(0, 'N')

        self.assertEqual(list(self.molecule.species), original_species)
        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], original_species[1])
        self.assertEqual(len(result.sites), 2)
        self.assertEqual(result.sites[0].specie, 'N')

    def test_substitute_multiple(self):
        result = self.molecule.substitute([0, 1], ['N', 'S'])

        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], 'S')
        self.assertEqual(result.sites[0].specie, 'N')
        self.assertEqual(result.sites[1].specie, 'S')

    def test_substitute_all(self):
        molecule = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        result = molecule.substitute_all('C', 'N')

        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], 'N')
        self.assertEqual(result.species[2], 'O')

    def test_substitute_invalid_index(self):
        with self.assertRaises(IndexError):
            self.molecule.substitute(10, 'N')

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

    def test_substitute_cache_invalidation(self):
        molecule = Molecule(['C', 'C'], [[0, 0, 0], [1.2, 0, 0]])
        original_formula = molecule.formula
        self.assertEqual(original_formula, 'C2')

        result = molecule.substitute(0, 'N')
        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], 'C')

        new_formula = result.formula
        self.assertNotEqual(original_formula, new_formula)
        self.assertIn('C', new_formula)
        self.assertIn('N', new_formula)

    def test_substitute_all_no_match(self):
        molecule = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        result = molecule.substitute_all('X', 'N')
        self.assertEqual(list(result.species), list(molecule.species))

    def test_substitute_dict_missing_key(self):
        with self.assertRaises(KeyError):
            self.molecule.substitute([0], {'X': 'N'})


class TestCrystalSubstitution(unittest.TestCase):

    def setUp(self):
        self.crystal = make_simple_crystal()

    def test_substitute_single(self):
        original_species = list(self.crystal.species)
        result = self.crystal.substitute(0, 'Ge')

        self.assertEqual(list(self.crystal.species), original_species)
        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], original_species[1])
        self.assertEqual(len(result.sites), 2)
        self.assertEqual(result.sites[0].specie, 'Ge')

    def test_substitute_multiple(self):
        crystal = Crystal(['Si', 'Si', 'O'],
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
                         Lattice.cubic(10))
        result = crystal.substitute([0, 1], ['Ge', 'Ge'])

        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], 'Ge')
        self.assertEqual(result.species[2], 'O')

    def test_substitute_all(self):
        crystal = Crystal(['Si', 'Si', 'O'],
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
                         Lattice.cubic(10))
        result = crystal.substitute_all('Si', 'Ge')

        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], 'Ge')
        self.assertEqual(result.species[2], 'O')

    def test_substitute_neighbor_tree_invalidation(self):
        self.crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(self.crystal._neighbor_cache)

        result = self.crystal.substitute(0, 'Ge')

        self.assertIsNotNone(self.crystal._neighbor_cache)
        self.assertIsNone(result._neighbor_cache)

    def test_substitute_cache_invalidation(self):
        crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
        original_formula = crystal.formula
        self.assertEqual(original_formula, 'Si2')

        result = crystal.substitute(0, 'Ge')
        self.assertEqual(result.species[0], 'Ge')
        self.assertEqual(result.species[1], 'Si')

        new_formula = result.formula
        self.assertNotEqual(original_formula, new_formula)
        self.assertIn('Si', new_formula)
        self.assertIn('Ge', new_formula)

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

    def test_substitute_consistency(self):
        from matsimpy.transformation import substitute

        mol1 = make_simple_molecule()
        mol1_result = mol1.substitute(0, 'N')

        mol2 = make_simple_molecule()
        mol2_result = substitute(mol2, 0, 'N')

        self.assertEqual(mol1_result.species, mol2_result.species)
        self.assertEqual(mol1_result.positions.tolist(), mol2_result.positions.tolist())

    def test_substitute_all_consistency(self):
        from matsimpy.transformation import substitute_all

        mol1 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mol1_result = mol1.substitute_all('C', 'N')

        mol2 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mol2_result = substitute_all(mol2, 'C', 'N')

        self.assertEqual(mol1_result.species, mol2_result.species)


if __name__ == '__main__':
    unittest.main()
