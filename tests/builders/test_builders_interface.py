"""Tests for interface builders."""

import numpy as np

from matsimpy.builders.bulk import from_prototype
from matsimpy.transformation.structural import create_simple_interface
from matsimpy.core import Crystal


def test_create_simple_interface_stacks_crystals_without_mutating_inputs():
    substrate = from_prototype("diamond", "Si", 5.43)
    film = from_prototype("fcc", "Cu", 3.61)
    substrate_positions = substrate.positions.copy()
    film_positions = film.positions.copy()

    interface = create_simple_interface(substrate, film, vacuum=8.0, gap=2.0)

    assert isinstance(interface, Crystal)
    assert len(interface) == len(substrate) + len(film)
    assert interface.pbc == (True, True, False)
    assert interface.lattice.c > substrate.lattice.c
    np.testing.assert_allclose(substrate.positions, substrate_positions)
    np.testing.assert_allclose(film.positions, film_positions)


def test_create_simple_interface_validates_inputs():
    substrate = from_prototype("diamond", "Si", 5.43)

    try:
        create_simple_interface(substrate, "not a crystal")
    except TypeError as e:
        assert "Crystal" in str(e)
    else:
        raise AssertionError("expected TypeError")

    try:
        create_simple_interface(substrate, substrate, vacuum=-1.0)
    except ValueError as e:
        assert "vacuum" in str(e)
    else:
        raise AssertionError("expected ValueError")

    try:
        create_simple_interface(substrate, substrate, gap=-1.0)
    except ValueError as e:
        assert "gap" in str(e)
    else:
        raise AssertionError("expected ValueError")
