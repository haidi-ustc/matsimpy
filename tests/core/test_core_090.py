"""0.9.0 core data-model contracts: one coordinate store, one add_atom, one __str__."""

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice, Molecule


def _skew_crystal():
    lat = Lattice([[4.123456789, 0.1, 0.0], [0.0, 4.0, 0.0], [0.0, 0.3, 5.7]])
    cart = [[0.1, 0.2, 0.3], [2.3, 0.31, 3.37], [1.0, 2.0, 1.0]]
    return Crystal(["O", "Fe", "H"], cart, lat, coords_are_cartesian=True)


@pytest.mark.parametrize("op", [lambda c: c.remove_atom([1]), lambda c: c.sort_atoms("element")])
def test_subset_and_reorder_keep_exact_cartesian_rows(op):
    c = _skew_crystal()
    out = op(c)
    rows = [c.species.index(sp) for sp in out.species]
    assert np.array_equal(out.cart_positions, c.cart_positions[rows])  # bit-exact, not frac @ matrix


def test_add_atom_cartesian_input_is_kept_exactly():
    c = _skew_crystal()
    new = [3.3, 3.1, 0.123456789]
    out = c.add_atom("C", new, coords_are_cartesian=True)
    assert out.cart_positions[-1].tolist() == new
    assert np.array_equal(out.cart_positions[:3], c.cart_positions)


def test_add_atom_uses_minimum_image_only_along_periodic_axes():
    c = Crystal(["Si"], [[0.01, 0.5, 0.5]], Lattice.cubic(5.0))
    with pytest.raises(ValueError, match="too close"):
        c.add_atom("Si", [0.99, 0.5, 0.5])  # 0.1 A apart through the boundary
    slab = c.set_pbc([False, True, True])
    assert len(slab.add_atom("Si", [0.99, 0.5, 0.5])) == 2  # 4.9 A apart: a is not periodic


@pytest.mark.parametrize(
    "s",
    [Molecule(["O"], [[0, 0, 0]]), Crystal(["O"], [[0, 0, 0]], Lattice.cubic(5.0))],
)
def test_add_atom_behaves_the_same_for_molecule_and_crystal(s):
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


def test_str_is_one_implementation():
    from matsimpy.core.structure import Structure
    assert "__str__" not in vars(Crystal) and "__str__" not in vars(Molecule)
    c = Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64),
                site_properties=[{"m": 1}, {}])
    text = str(c)
    assert text.startswith("Crystal: NaCl\n  Sites: 2 atoms\n  PBC: [T T T]")
    assert "Fractional Coordinates" in text and "m=1" in text
    assert Structure.__str__ is type(c).__str__


def test_crystal_site_snapshot_matches_backing_rows_exactly():
    c = _skew_crystal()
    for i, site in enumerate(c.sites):
        assert np.array_equal(site.cart_position, c.cart_positions[i])
        assert np.array_equal(site.frac_position, c.frac_positions[i])
        assert site.lattice is c.lattice
    assert c[1] == c.sites[1]
