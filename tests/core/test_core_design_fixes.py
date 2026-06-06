"""Regression tests for core design-flaw fixes."""

import unittest

import numpy as np

from matsimpy.core import Composition, Crystal, Element, Lattice, Molecule, Site


class TestCrystalConstructionValidation(unittest.TestCase):
    """Test centralized Crystal lattice and PBC validation."""

    def test_crystal_rejects_none_lattice(self):
        with self.assertRaises(ValueError):
            Crystal(['Si'], [[0, 0, 0]], None)

    def test_crystal_rejects_invalid_pbc_length(self):
        with self.assertRaises(ValueError):
            Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5), pbc=[True, False])

    def test_crystal_rejects_non_bool_pbc(self):
        with self.assertRaises(ValueError):
            Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5), pbc=[True, 1, False])

    def test_crystal_normalizes_numpy_bool_pbc(self):
        crystal = Crystal(
            ['Si'],
            [[0, 0, 0]],
            Lattice.cubic(5),
            pbc=[np.bool_(True), np.bool_(False), np.bool_(True)],
        )

        self.assertEqual(crystal.pbc, (True, False, True))
        self.assertTrue(all(isinstance(flag, bool) for flag in crystal.pbc))

    def test_crystal_from_dict_validates_lattice_and_pbc(self):
        data = {
            "species": ['Si'],
            "positions": [[0, 0, 0]],
            "lattice": None,
            "pbc": [True, True, True],
        }
        with self.assertRaises(ValueError):
            Crystal.from_dict(data)

        data = {
            "species": ['Si'],
            "positions": [[0, 0, 0]],
            "lattice": Lattice.cubic(5).as_dict(),
            "pbc": [True, "yes", True],
        }
        with self.assertRaises(ValueError):
            Crystal.from_dict(data)

    def test_set_pbc_uses_same_validator(self):
        crystal = Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5))

        with self.assertRaises(ValueError):
            crystal.set_pbc([True, False])
        self.assertEqual(
            crystal.set_pbc([np.bool_(False), np.bool_(True), np.bool_(False)]).pbc,
            (False, True, False),
        )


class TestPBCNeighborModel(unittest.TestCase):
    """Test periodic neighbor behavior for skewed and same-index images."""

    def test_one_atom_crystal_reports_periodic_self_neighbor(self):
        crystal = Crystal(['H'], [[0, 0, 0]], Lattice.cubic(2.0))

        neighbors = crystal.get_neighbor_list(2.1, atom_index=0, use_pbc=True)

        self.assertEqual(len(neighbors[0]), 1)
        self.assertAlmostEqual(neighbors[0][0][1], 2.0, places=1)

    def test_skewed_cell_neighbor_search_uses_reciprocal_height_bound(self):
        lattice = Lattice([[10, 0, 0], [99.99, 0.01, 0], [0, 0, 10]])
        crystal = Crystal(
            ['H', 'H'],
            [[0, 0, 0], [0, 0.5, 0]],
            lattice,
            pbc=[True, True, True],
        )

        neighbors = crystal.get_neighbor_list(0.02, atom_index=0, use_pbc=True)

        distances_by_index = dict(neighbors[0])
        self.assertIn(1, distances_by_index)
        self.assertAlmostEqual(distances_by_index[1], np.sqrt(0.005**2 + 0.005**2))


class TestSharedSpeciesValidation(unittest.TestCase):
    """Test one species validation policy across core classes."""

    def test_invalid_species_are_rejected_in_core_constructors(self):
        with self.assertRaises(ValueError):
            Molecule(['Zz'], [[0, 0, 0]])
        with self.assertRaises(ValueError):
            Crystal(['Zz'], [[0, 0, 0]], Lattice.cubic(5))
        with self.assertRaises(ValueError):
            Site([0, 0, 0], specie='Zz')
        with self.assertRaises(ValueError):
            Composition("Zz")

    def test_dummy_species_are_accepted_consistently(self):
        self.assertEqual(Molecule(['X'], [[0, 0, 0]]).species, ('X',))
        self.assertEqual(Crystal(['X'], [[0, 0, 0]], Lattice.cubic(5)).species, ('X',))
        self.assertEqual(Site([0, 0, 0], specie='X').specie, 'X')
        self.assertEqual(Composition("X")["X"], 1)

    def test_template_placeholder_species_are_accepted_consistently(self):
        self.assertEqual(Molecule(['A'], [[0, 0, 0]]).species, ('A',))
        self.assertEqual(Crystal(['Z'], [[0, 0, 0]], Lattice.cubic(5)).species, ('Z',))
        self.assertEqual(Site([0, 0, 0], specie='A').specie, 'A')
        self.assertEqual(Composition("Z")["Z"], 1)

    def test_atomic_numbers_and_elements_normalize_consistently(self):
        self.assertEqual(Molecule([8], [[0, 0, 0]]).species, ('O',))
        self.assertEqual(Crystal([Element("Og")], [[0, 0, 0]], Lattice.cubic(5)).species, ('Og',))

    def test_mutation_paths_reject_invalid_species(self):
        molecule = Molecule(['H'], [[0, 0, 0]])

        with self.assertRaises(ValueError):
            molecule.add_atom('Zz', [1, 0, 0])
        with self.assertRaises(ValueError):
            molecule.substitute(0, 'Zz')


class TestUnicodeDisplayUnits(unittest.TestCase):
    """Test human-readable core displays use Unicode unit symbols."""

    def test_crystal_str_and_repr_use_unicode_units(self):
        crystal = Crystal(
            ['Na', 'Cl'],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
            Lattice.cubic(5.64),
        )

        printed = str(crystal)
        represented = repr(crystal)

        self.assertIn("90.0°/90.0°/90.0°", represented)
        self.assertIn("Volume: 179.4061 Å³", printed)
        self.assertIn("Density:", printed)
        self.assertIn("g/cm³", printed)
        self.assertNotIn(" deg", represented)
        self.assertNotIn("A^3", printed)
        self.assertNotIn("cm^3", printed)

    def test_crystal_lower_dimensional_str_uses_unicode_area_units(self):
        crystal = Crystal(
            ['C'],
            [[0, 0, 0]],
            Lattice.cubic(5.0),
            pbc=[True, True, False],
        )

        printed = str(crystal)

        self.assertIn("Area: 25.0000 Å²", printed)
        self.assertIn("g/cm²", printed)
        self.assertNotIn("A^2", printed)
        self.assertNotIn("cm^2", printed)

    def test_molecule_str_keeps_unicode_angstrom_units(self):
        molecule = Molecule(['H'], [[0, 0, 0]])

        printed = str(molecule)

        self.assertIn("Center of mass: (0.0000, 0.0000, 0.0000) Å", printed)
        self.assertNotIn(" A", printed)


if __name__ == "__main__":
    unittest.main()
