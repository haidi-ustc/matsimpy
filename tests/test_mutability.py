import unittest
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.core.structure import FrozenStructureError


class TestMutabilityMutability(unittest.TestCase):
    """Tests for the freeze/unfreeze mutability guards on Crystal and Molecule.

    This test suite verifies that, when structures are frozen, mutation
    operations raise a FrozenStructureError (a RuntimeError subclass). It also
    checks basic read access while frozen and that unfreezing re-enables mutation.
    """

    def setUp(self):
        self.crystal = Crystal(["Na", "Cl"], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        self mol = Molecule(["O", "H", "H"], [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]])

    def test_freeze_blocks_add_atom(self):
        crystal = self.crystal
        crystal.freeze()
        with self.assertRaises(FrozenStructureError):
            crystal.add_atom('H', [0.1, 0.0, 0.0])
        self.mol.freeze()
        with self.assertRaises(FrozenStructureError):
            self.mol.add_atom('H', [0.1, 0.0, 0.0])

    def test_freeze_blocks_remove_atom(self):
        crystal = self.crystal
        crystal.freeze()
        with self.assertRaises(FrozenStructureError):
            crystal.remove_atom(0)
        self.mol.freeze()
        with self.assertRaises(FrozenStructureError):
            self.mol.remove_atom(0)

    def test_freeze_blocks_substitute(self):
        crystal = self.crystal
        crystal.freeze()
        with self.assertRaises(FrozenStructureError):
            crystal.substitute(0, 'K')
        self.mol.freeze()
        with self.assertRaises(FrozenStructureError):
            self.mol.substitute(0, 'O')

    def test_freeze_blocks_substitute_all(self):
        crystal = self.crystal
        crystal.freeze()
        with self.assertRaises(FrozenStructureError):
            crystal.substitute_all('Na', 'K')
        self.mol.freeze()
        with self.assertRaises(FrozenStructureError):
            self.mol.substitute_all('O', 'S')

    def test_freeze_blocks_sort_atoms(self):
        crystal = self.crystal
        crystal.freeze()
        with self.assertRaises(FrozenStructureError):
            crystal.sort_atoms('element')
        self.mol.freeze()
        with self.assertRaises(FrozenStructureError):
            self.mol.sort_atoms('alphabet')

    def test_freeze_blocks_positions_setter(self):
        crystal = self.crystal
        crystal.freeze()
        with self.assertRaises(FrozenStructureError):
            crystal.positions = [[0.0, 0.0, 0.0]] * 2
        self.mol.freeze()
        with self.assertRaises(FrozenStructureError):
            self.mol.positions = [[1.0, 0.0, 0.0]] * 3

    def test_freeze_blocks_species_setter(self):
        crystal = self.crystal
        crystal.freeze()
        with self.assertRaises(FrozenStructureError):
            crystal.species = ['K', 'Na']
        self.mol.freeze()
        with self.assertRaises(FrozenStructureError):
            self.mol.species = ['O', 'H']

    def test_unfreeze_allows_mutation(self):
        crystal = self.crystal
        crystal.freeze()
        crystal.unfreeze()
        # Should be allowed after unfreeze
        crystal.add_atom('H', [0.1, 0.0, 0.0])
        self.assertIn('H', crystal.species)

    def test_is_frozen_reflects_state(self):
        crystal = self.crystal
        self.assertFalse(crystal.is_frozen)
        crystal.freeze()
        self.assertTrue(crystal.is_frozen)
        crystal.unfreeze()
        self.assertFalse(crystal.is_frozen)

    def test_frozen_structure_error_type(self):
        # FrozenStructureError must be a subclass of RuntimeError
        self.assertTrue(issubclass(FrozenStructureError, RuntimeError))

    def test_freeze_idempotent(self):
        crystal = self.crystal
        crystal.freeze()
        # Calling freeze again should not raise
        crystal.freeze()

    def test_read_always_allowed_when_frozen(self):
        crystal = self.crystal
        crystal.freeze()
        # Accessors should work even when frozen
        _ = crystal.formula
        _ = crystal.positions
        _ = len(crystal)
        _ = [site for site in crystal]

    def test_copy_preserves_frozen_state(self):
        crystal = self.crystal
        crystal.freeze()
        crystal_copy = crystal.copy()
        self.assertFalse(crystal_copy.is_frozen)


if __name__ == '__main__':
    unittest.main()
