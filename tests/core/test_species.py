import unittest
from matsimpy.core import Crystal, Lattice


class TestSpeciesImmutability(unittest.TestCase):
    """Tests that species property is read-only on immutable Structure objects."""

    def test_species_is_tuple(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        self.assertIsInstance(crystal.species, tuple)

    def test_species_raises_attribute_error_on_set(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        with self.assertRaises(AttributeError):
            crystal.species = ['Cl', 'Na']

    def test_species_immutable_after_substitute(self):
        """Species on the original should remain unchanged after substitute."""
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        original_species = crystal.species
        result = crystal.substitute(0, 'K')
        self.assertEqual(crystal.species, original_species)
        self.assertEqual(result.species, ('K', 'Cl'))

    def test_species_order_preserved_through_copy(self):
        crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        c = crystal.copy()
        self.assertEqual(c.species, ('Na', 'Cl'))

    def test_species_type_validated_at_construction(self):
        with self.assertRaises(TypeError):
            Crystal(['Na', 1], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))


if __name__ == '__main__':
    unittest.main()
