"""Tests for substitution with dict mapping and AtomSelection."""
import unittest

from matsimpy.core import Crystal, Molecule, Lattice

class TestSubstitutionWithDict(unittest.TestCase):
    """Tests for dict-based substitution mapping."""

    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0]],
            Lattice.cubic(10)
        )
        self.molecule = Molecule(['C', 'O', 'C', 'N'], [[0, 0, 0], [1.2, 0, 0], [2.4, 0, 0], [3.6, 0, 0]])

    def test_substitute_with_dict_missing_key(self):
        """Test that missing key in dict raises KeyError."""
        with self.assertRaises(KeyError):
            self.crystal.substitute([0], {'Ge': 'Si'})  # 'Si' not in dict

    def test_substitute_with_dict_molecule(self):
        """Test dict substitution with molecule."""
        result = self.molecule.substitute([0, 1, 2, 3], {'C': 'N', 'O': 'S', 'N': 'P'})

        self.assertEqual(result.species[0], 'N')
        self.assertEqual(result.species[1], 'S')
        self.assertEqual(result.species[2], 'N')
        self.assertEqual(result.species[3], 'P')


class TestSubstitutionTransformationModule(unittest.TestCase):
    """Tests for dict mapping in transformation module."""

    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(['Si', 'O', 'Si'], [[0, 0, 0], [5, 0, 0], [10, 0, 0]],
                              Lattice.cubic(20), coords_are_cartesian=True)

    def test_transformation_substitute_with_atom_selection_and_dict(self):
        """Test transformation.substitute with AtomSelection and dict."""
        from matsimpy.transformation import substitute
        from matsimpy.analysis.selection import AtomSelection

        sel = AtomSelection(self.crystal).by_species('Si')
        new_crystal = substitute(self.crystal, sel, {'Si': 'Ge'})

        self.assertEqual(new_crystal.species[0], 'Ge')
        self.assertEqual(new_crystal.species[2], 'Ge')
        self.assertEqual(new_crystal.species[1], 'O')

if __name__ == '__main__':
    unittest.main()
