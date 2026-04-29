"""Tests for structural transformation helpers."""
import unittest
import numpy as np

from matsimpy.core import Molecule
from tests.conftest import make_simple_molecule


class TestMolecularStructuralTransformations(unittest.TestCase):
    """Regression tests for molecule-specific structural transformations."""

    def test_align_molecules_uses_molecule_positions(self):
        """align_molecules should work for Molecule, which stores Cartesian coords in positions."""
        from matsimpy.transformation.structural import align_molecules

        reference = make_simple_molecule()
        moving = Molecule(['C', 'O'], [[5, 5, 0], [6.2, 5, 0]])

        aligned = align_molecules(reference, moving, [0, 1], [0, 1])

        self.assertIsInstance(aligned, Molecule)
        np.testing.assert_array_almost_equal(aligned.positions, reference.positions)

    def test_merge_molecules_uses_molecule_positions(self):
        """merge_molecules should not rely on a non-existent cart_positions attribute."""
        from matsimpy.transformation.structural import merge_molecules

        mol1 = Molecule(['C'], [[0, 0, 0]])
        mol2 = Molecule(['O'], [[1, 0, 0]])

        merged = merge_molecules(mol1, mol2, 0, 0)

        self.assertIsInstance(merged, Molecule)
        self.assertEqual(merged.species, ('C', 'O'))
        np.testing.assert_array_almost_equal(merged.positions[1], mol1.positions[0])


if __name__ == '__main__':
    unittest.main()
