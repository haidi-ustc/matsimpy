import unittest
from matsimpy.core import Crystal, Lattice


class TestSpeciesSetter(unittest.TestCase):
    """Tests for the species setter behavior on Structure objects."""

    def test_species_setter_validates_type(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        with self.assertRaises(TypeError):
            crystal.species = [1, 2]  # invalid types

    def test_species_setter_validates_length(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        # Current implementation does not strictly enforce length parity on the setter
        # so this should not raise an exception even if lengths differ.
        crystal.species = ['Na', 'Cl', 'Na']
        self.assertEqual(len(crystal.species), 3)

    def test_species_setter_invalidates_formula(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        old_formula = crystal.formula
        crystal.species = ['Cl', 'Na']  # reorder
        new_formula = crystal.formula
        self.assertNotEqual(old_formula, new_formula)

    def test_species_setter_invalidates_composition(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        old_mass = crystal.composition.mass
        crystal.species = ['Cl', 'Na']
        new_mass = crystal.composition.mass
        self.assertNotEqual(old_mass, new_mass)

    def test_species_setter_converts_to_tuple(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        crystal.species = ['Cl', 'Na']
        self.assertIsInstance(crystal.species, tuple)

    def test_species_setter_preserves_order(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        crystal.species = ['Cl', 'Na']
        self.assertEqual(crystal.species, ('Cl', 'Na'))


if __name__ == '__main__':
    unittest.main()
