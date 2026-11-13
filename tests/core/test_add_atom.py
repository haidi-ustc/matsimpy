"""Tests for add_atom: single and batch input, site properties, distance checks."""

import warnings

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule


@pytest.mark.parametrize(("species", "positions", "message"), [
    (["H", "N"], [[2.0, 0, 0]], "must match"),
    (["H", "N", "O"], [[2.0, 0, 0], [3.0, 0, 0]], "must match"),
    ("H", [0, 0], "3D coordinate"),
    (["H", "O"], [[0, 0, 0], [1, 2]], "3D coordinate"),
])
def test_rejects_invalid_batch_input(species, positions, message):
    molecule = Molecule(["C", "O"], [[0, 0, 0], [1.2, 0, 0]])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with pytest.raises(ValueError, match=message):
            molecule.add_atom(species, positions)


@pytest.mark.parametrize("s", [Molecule(["O"], [[0, 0, 0]]), Crystal(["O"], [[0, 0, 0]], Lattice.cubic(5.0))],
                         ids=["molecule", "crystal"])
def test_behaves_the_same_for_molecules_and_crystals(s):
    with pytest.raises(ValueError, match="Duplicate"):
        s.add_atom(["H", "H"], [[0.2, 0.2, 0.2], [0.2, 0.2, 0.2]])
    with pytest.raises(ValueError, match="already exists"):
        s.add_atom("H", [0, 0, 0])
    with pytest.raises(ValueError, match="must match"):
        s.add_atom(["H", "H"], [[0.3, 0.3, 0.3]])
    with pytest.warns(UserWarning, match="has none"):
        out = s.add_atom("H", [0.3, 0.3, 0.3], {"tag": "h"})
    assert out.site_properties == ({}, {"tag": "h"})
    assert s.add_atom([], []) == s


def test_atoms_closer_than_half_an_angstrom_raise():
    with pytest.raises(ValueError, match="too close.*0.5|0.5.*too close"):
        Molecule(["C"], [[0, 0, 0]]).add_atom("O", [0.05, 0, 0])


def test_batch_of_atoms_from_a_numpy_array():
    out = Molecule(["C"], [[0, 0, 0]]).add_atom(["H", "O"], np.array([[1, 0, 0], [2, 0, 0]]))
    assert out.species == ("C", "H", "O")
    np.testing.assert_allclose(out.positions[1:], [[1, 0, 0], [2, 0, 0]])


def test_one_site_property_dict_applies_to_every_new_atom():
    c = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(10.0))
    out = c.add_atom(["H", "H"], [[0.1, 0, 0], [0.2, 0, 0]], {"type": "hydrogen"})
    assert out.site_properties[1:] == ({"type": "hydrogen"}, {"type": "hydrogen"})


def test_existing_site_properties_are_kept():
    c = Crystal(["Si", "O"], [[0, 0, 0], [0.5, 0, 0]], Lattice.cubic(10.0),
                site_properties=[{"oxidation": 4}, {"oxidation": -2}])
    out = c.add_atom(["H", "H"], [[0.1, 0, 0], [0.2, 0, 0]], [{"charge": 1}, {"charge": 1}])
    assert out.site_properties == ({"oxidation": 4}, {"oxidation": -2}, {"charge": 1}, {"charge": 1})
