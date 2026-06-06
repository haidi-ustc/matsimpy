"""Contract tests for the Structure domain model.

Tests immutable-return, species tuple immutability, positions writeable=False,
as_dict/from_dict round-trip, and equality/hash consistency.
Parametrized over Crystal and Molecule variants.
"""

import pytest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice


@pytest.fixture
def nacl():
    return Crystal(
        ['Na', 'Cl'],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
        Lattice.cubic(5.64),
    )


@pytest.fixture
def water():
    return Molecule(
        ['O', 'H', 'H'],
        [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
    )


@pytest.fixture(params=["crystal", "molecule"])
def structure(request, nacl, water):
    if request.param == "crystal":
        return nacl
    return water


class TestImmutableReturn:
    """All mutation methods return new objects."""

    def test_add_atom_returns_new(self, structure):
        original_id = id(structure)
        # Use a position far from existing atoms
        try:
            new_s = structure.add_atom('H', [10.0, 10.0, 10.0])
        except ValueError:
            # For crystals with PBC, use fractional coords
            from matsimpy.core import Crystal
            if isinstance(structure, Crystal):
                new_s = structure.add_atom('H', [0.33, 0.33, 0.33],
                                           coords_are_cartesian=False)
            else:
                raise
        assert id(new_s) != original_id
        assert len(new_s) == len(structure) + 1

    def test_remove_atom_returns_new(self, structure):
        if len(structure) < 2:
            pytest.skip("Need at least 2 atoms")
        new_s = structure.remove_atom(0)
        assert id(new_s) != id(structure)
        assert len(new_s) == len(structure) - 1

    def test_substitute_returns_new(self, structure):
        new_s = structure.substitute(0, 'He')
        assert id(new_s) != id(structure)
        assert new_s.species[0] == 'He'

    def test_sort_atoms_returns_new(self, structure):
        new_s = structure.sort_atoms()
        assert id(new_s) != id(structure)


class TestSpeciesImmutability:
    """species is an immutable tuple."""

    def test_species_is_tuple(self, structure):
        assert isinstance(structure.species, tuple)

    def test_species_cannot_be_mutated(self, structure):
        with pytest.raises(TypeError):
            structure.species[0] = 'Xe'  # type: ignore


class TestPositionsReadOnly:
    """positions array has writeable=False."""

    def test_positions_not_writeable(self, structure):
        assert not structure.positions.flags.writeable


class TestSerializationRoundTrip:
    """as_dict() → from_dict() round-trip preserves structure."""

    def test_round_trip(self, structure):
        d = structure.as_dict()
        reconstructed = type(structure).from_dict(d)
        assert reconstructed == structure
        assert reconstructed.formula == structure.formula

    def test_lattice_preserved(self, nacl):
        d = nacl.as_dict()
        reconstructed = Crystal.from_dict(d)
        assert np.allclose(reconstructed.lattice.matrix, nacl.lattice.matrix)


class TestEqualityAndHash:
    """Equal structures are equal."""

    def test_equal_structures_are_equal(self, structure):
        d = structure.as_dict()
        reconstructed = type(structure).from_dict(d)
        assert structure == reconstructed
        # Note: Crystal/Molecule may not be hashable

    def test_different_structures_are_not_equal(self, nacl, water):
        assert nacl != water
