
import unittest
from matsimpy.core import Crystal
from matsimpy.core import Lattice

class TestCrystal(unittest.TestCase):
    def setUp(self):
#        self.maxDiff = None
        species = ['H', 'O', 'O']
        positions = [[0, 0, 0], [0, 0, 1.2], [0, 1.2, 0]]
        lattice = Lattice.from_parameters(a=3.0, b=3.0, c=3.0, alpha=90, beta=90, gamma=90)
        self.structure = Crystal(species=species, positions=positions, lattice=lattice)

    def test_composition(self):
        expected_composition = {'H': 1, 'O': 2}
        self.assertEqual(self.structure.get_composition(), expected_composition)

    def test_formula(self):
        expected_formula = 'H2O'
        self.assertEqual(self.structure.get_formula(), expected_formula)

    def test_as_dict(self):
        expected_dict = {
            "@module": "matsimpy.core.crystal",
            "@class": "Crystal",
            "species": ["H", "O", "O"],
            "positions": [[0.0, 0.0, 0.0], [0.0, 0.0, 1.2], [0.0, 1.2, 0.0]],
            "lattice": {
                "@module": "matsimpy.core.lattice",
                "@class": "Lattice",
                "lattice_vectors": [[3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 3.0]]
            }
        }
        self.assertDictEqual(self.structure.as_dict(), expected_dict)

    def test_from_dict(self):
        d = {
            "@module": "matsimpy.core.crystal",
            "@class": "Crystal",
            "species": ["H", "O", "O"],
            "positions": [[0.0, 0.0, 0.0], [0.0, 0.0, 1.2], [0.0, 1.2, 0.0]],
            "lattice": {
                "@module": "matsimpy.core.lattice",
                "@class": "Lattice",
                "lattice_vectors": [[3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 3.0]]
            }
        }
        expected_structure = self.structure
        self.assertEqual(Crystal.from_dict(d), expected_structure)

    def test_add_atom(self):
        self.structure.add_atom(species='H', position=[1.0, 1.0, 1.0])
        self.assertEqual(len(self.structure), 4)
        self.assertEqual(self.structure.species, ['H', 'O', 'O', 'H'])

    def test_remove_atom(self):
        self.structure.remove_atom(index=1)
        self.assertEqual(len(self.structure), 2)
        self.assertEqual(self.structure.species, ['H', 'O'])

if __name__ == '__main__':
    unittest.main()

