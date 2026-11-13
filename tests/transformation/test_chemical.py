"""Tests for matsimpy.transformation.chemical: substitute, substitute_all."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.transformation.chemical import substitute, substitute_all


@pytest.fixture
def hoh():
    return Molecule(["H", "O", "H"], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])


def test_substitute_replaces_only_the_given_sites():
    c = Crystal(["Si", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10.0))
    out = substitute(c, 0, "Ge")
    assert out.species == ("Ge", "O")
    assert c.species == ("Si", "O")


def test_substitute_accepts_numpy_indices_and_one_species_per_index(hoh):
    assert substitute(hoh, np.int64(1), "S").species == ("H", "S", "H")
    assert substitute(hoh, np.array([0, 2]), ["F", "Cl"]).species == ("F", "O", "Cl")


@pytest.mark.parametrize("indices, species, error", [
    (0, ["F", "Cl"], ValueError),  # used to take the first species silently
    (True, "F", TypeError),
])
def test_substitute_rejects_bad_input(hoh, indices, species, error):
    with pytest.raises(error):
        substitute(hoh, indices, species)


def test_substitute_all(hoh):
    assert substitute_all(hoh, "H", "F").species == ("F", "O", "F")


def test_substitute_all_raises_when_the_species_is_absent(hoh):
    with pytest.raises(ValueError, match="not found"):
        substitute_all(hoh, "C", "Si")
