"""Tests for species validation and normalization, shared by all core classes."""

import pytest

from matsimpy.core import Composition, Crystal, Element, Lattice, Molecule, Site


def _nacl():
    return Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))


def test_species_is_a_tuple_kept_in_order():
    assert _nacl().species == ("Na", "Cl")
    assert _nacl().copy().species == ("Na", "Cl")


@pytest.mark.parametrize("make", [
    lambda: Molecule(["Zz"], [[0, 0, 0]]),
    lambda: Crystal(["Zz"], [[0, 0, 0]], Lattice.cubic(5)),
    lambda: Site([0, 0, 0], specie="Zz"),
    lambda: Composition("Zz"),
    lambda: Molecule(["H"], [[0, 0, 0]]).add_atom("Zz", [1, 0, 0]),
    lambda: Molecule(["H"], [[0, 0, 0]]).substitute(0, "Zz"),
])
def test_unknown_species_are_rejected_everywhere(make):
    with pytest.raises(ValueError):
        make()


def test_non_string_species_are_rejected():
    with pytest.raises(TypeError):
        Crystal(["Na", 1], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))


def test_dummy_species_are_accepted_everywhere():
    assert Molecule(["X"], [[0, 0, 0]]).species == ("X",)
    assert Crystal(["X"], [[0, 0, 0]], Lattice.cubic(5)).species == ("X",)
    assert Site([0, 0, 0], specie="X").specie == "X"
    assert Composition("X")["X"] == 1


def test_atomic_numbers_and_elements_are_normalized_to_symbols():
    assert Molecule([8], [[0, 0, 0]]).species == ("O",)
    assert Crystal([Element("Og")], [[0, 0, 0]], Lattice.cubic(5)).species == ("Og",)
