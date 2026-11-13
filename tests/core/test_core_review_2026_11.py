"""Regression tests for the November 2026 review of ``matsimpy.core``.

Each test failed on the code before the fix.
"""

import copy
import json
import pickle

import numpy as np
import pytest
from monty.json import MontyEncoder

from matsimpy.core import Composition, Crystal, Lattice, Molecule, Site, Trajectory
from matsimpy.core.periodic_table import Element
from matsimpy.core.symmop import SymmOp


# --------------------------------------------------------------------------
# SymmOp.from_origin_axis_angle
# --------------------------------------------------------------------------


def test_symmop_axis_angle_is_right_handed_degrees():
    op = SymmOp.from_origin_axis_angle([0, 0, 0], [0, 0, 1], 90)
    np.testing.assert_allclose(op.operate([1, 0, 0]), [0, 1, 0], atol=1e-12)
    op_rad = SymmOp.from_origin_axis_angle([0, 0, 0], [0, 0, 1], np.pi / 2, angle_in_radians=True)
    np.testing.assert_allclose(op_rad.affine_matrix, op.affine_matrix, atol=1e-12)


def test_symmop_axis_angle_matches_pymatgen():
    pmg = pytest.importorskip("pymatgen.core.operations")
    for origin, axis, angle in [
        ([0, 0, 0], [1, 1, 1], 120),
        ([1.0, -2.0, 0.5], [0.3, -0.2, 0.9], 37.0),
    ]:
        ours = SymmOp.from_origin_axis_angle(origin, axis, angle)
        ref = pmg.SymmOp.from_origin_axis_angle(origin, axis, angle)
        np.testing.assert_allclose(ours.affine_matrix, ref.affine_matrix, atol=1e-10)


def test_symmop_axis_angle_rejects_bad_vectors():
    with pytest.raises(ValueError):
        SymmOp.from_origin_axis_angle([0, 0], [0, 0, 1], 90)
    with pytest.raises(ValueError):
        SymmOp.from_origin_axis_angle([0, 0, 0], [0, 0, 1], float("nan"))


# --------------------------------------------------------------------------
# Neighbour list, wrap and minimum image
# --------------------------------------------------------------------------


def test_neighbor_list_finds_neighbours_of_unwrapped_atoms():
    # Cl stored three cells away is 1.5 Å from Na through the boundary.
    c = Crystal(["Na", "Cl"], [[0, 0, 0], [3.375, -2, 1]], Lattice.cubic(4.0))
    nl = c.get_neighbor_list(2.5)
    assert [j for j, _ in nl[0]] == [1]
    assert nl[0][0][1] == pytest.approx(1.5)
    assert nl == c.wrap().get_neighbor_list(2.5)


def test_single_atom_neighbor_list_includes_cutoff_boundary():
    c = Crystal(["Cu", "Cu"], [[0, 0, 0], [0.5, 0, 0]], Lattice.cubic(3.0), pbc=[False, False, False])
    # 1.5 Å apart: exactly at the cutoff, included like the all-atom query does
    assert c.get_neighbor_list(1.5, atom_index=0, use_pbc=False) == {0: [(1, 1.5)]}
    assert c.get_neighbor_list(1.5, use_pbc=False)[0] == [(1, 1.5)]


def test_wrap_leaves_non_periodic_axes_alone():
    c = Crystal(["C"], [[0.5, 0.5, 1.3]], Lattice.cubic(5.0), pbc=[True, True, False])
    np.testing.assert_allclose(c.wrap().frac_positions, [[0.5, 0.5, 1.3]])
    c2 = Crystal(["C"], [[1.5, -0.25, 1.3]], Lattice.cubic(5.0), pbc=[True, True, False])
    np.testing.assert_allclose(c2.wrap().frac_positions, [[0.5, 0.75, 1.3]])


def test_add_atom_uses_true_minimum_image_in_skewed_cell():
    m = [[1, 0, 0], [0.9, 0.3, 0], [0, 0, 10]]
    c = Crystal(["H"], [[0, 0, 0]], Lattice(m))
    # The true minimum-image distance is ~0.19 Å; rounding alone gives 1.3 Å.
    with pytest.raises(ValueError, match="too close"):
        c.add_atom("H", [0.6, 0.6, 0.0])


# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------


def test_composition_reduced_formula_respects_sort_by():
    assert Composition("O6Fe4", sort_by="alphabet").reduced_formula == "Fe2O3"


def test_composition_fractional_html_and_latex():
    c = Composition.from_mapping({"Fe": 0.5, "O": 1.5})
    assert c.to_html() == "Fe<sub>0.5</sub>O<sub>1.5</sub>"
    assert Composition.from_mapping({"Fe": 0.5, "O": 1}).to_latex() == "Fe$_{0.5}$O"


def test_composition_add_fractional():
    total = Composition.from_mapping({"Fe": 0.5, "O": 1.0}) + Composition.from_mapping({"O": 1.5})
    assert total.formula == "Fe0.5O2.5"


def test_composition_rejects_empty_group_and_bool_amounts():
    with pytest.raises(ValueError, match="Empty group"):
        Composition("Fe()")
    with pytest.raises(TypeError):
        Composition.from_mapping({"Fe": True})
    with pytest.raises(TypeError):
        Composition.from_mapping({"Fe": "2"})


def test_composition_formula_is_read_only_and_getitem_rejects_typos():
    c = Composition("H2O")
    with pytest.raises(AttributeError):
        c.formula = "CO2"
    assert c["C"] == 0
    with pytest.raises(KeyError):
        c["h"]


# --------------------------------------------------------------------------
# Element
# --------------------------------------------------------------------------


def test_element_value_equality_and_immutability():
    assert Element("Fe") == Element("Fe")
    assert len({Element("Fe"), Element("Fe"), Element("O")}) == 2
    assert Element("Fe") != Element("O")
    cached = Element.get_element("Cu")
    with pytest.raises(AttributeError):
        cached.symbol = "Zn"
    assert Element.get_element("Cu").symbol == "Cu"
    assert pickle.loads(pickle.dumps(cached)) == cached
    assert copy.deepcopy(cached).symbol == "Cu"


# --------------------------------------------------------------------------
# Serialization
# --------------------------------------------------------------------------


def test_crystal_site_properties_with_arrays_survive_json():
    c = Crystal(
        ["Fe", "Fe"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(2.87),
        site_properties=[{"magmom": np.array([0, 0, 1.0])}, {"magmom": np.array([0, 0, -1.0])}],
    )
    back = Crystal.from_dict(json.loads(json.dumps(c.as_dict(), cls=MontyEncoder)))
    assert isinstance(back.site_properties[0]["magmom"], np.ndarray)
    np.testing.assert_array_equal(back.site_properties[1]["magmom"], [0, 0, -1.0])


def test_molecule_site_properties_with_arrays_survive_json():
    m = Molecule(["O", "H"], [[0, 0, 0], [1, 0, 0]], site_properties=[{"q": np.array([1.0])}, {"q": np.array([2.0])}])
    back = Molecule.from_dict(json.loads(json.dumps(m.as_dict(), cls=MontyEncoder)))
    assert isinstance(back.site_properties[0]["q"], np.ndarray)


def test_crystal_from_dict_rejects_inconsistent_cart_positions():
    c = Crystal(["Fe"], [[0.1, 0.2, 0.3]], Lattice.cubic(2.87), coords_are_cartesian=True)
    d = c.as_dict()
    np.testing.assert_allclose(Crystal.from_dict(d).cart_positions, [[0.1, 0.2, 0.3]])
    d["cart_positions"] = [[1.0, 1.0, 1.0]]
    with pytest.raises(ValueError, match="inconsistent"):
        Crystal.from_dict(d)


# --------------------------------------------------------------------------
# Molecule
# --------------------------------------------------------------------------


def test_molecule_to_crystal_keeps_site_properties_and_validates_vacuum():
    m = Molecule(["O", "H"], [[0, 0, 0], [1, 0, 0]], site_properties=[{"q": -1}, {"q": 1}])
    assert m.to_crystal(5.0).site_properties == ({"q": -1}, {"q": 1})
    for bad in (-1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            m.to_crystal(bad)
    with pytest.raises(TypeError):
        m.to_crystal(True)


def test_molecule_all_neighbor_lists_validate_cutoff_and_include_boundary():
    m = Molecule(["H", "H"], [[0, 0, 0], [1, 0, 0]])
    assert m.get_all_neighbor_lists(1.0) == [[1], [0]]
    with pytest.raises(ValueError):
        m.get_all_neighbor_lists(float("nan"))
    with pytest.raises(TypeError):
        m.get_all_neighbor_lists(True)


def test_molecule_translate_requires_3_vector():
    m = Molecule(["H"], [[0, 0, 0]])
    with pytest.raises(ValueError):
        m.translate([1, 2])
    with pytest.raises(ValueError):
        m.translate([1])  # used to broadcast to [1, 1, 1]
    with pytest.raises(ValueError):
        m.translate([[1, 2, 3], [1, 2, 3]])
    np.testing.assert_allclose(m.translate([1, 2, 3]).positions, [[1, 2, 3]])


# --------------------------------------------------------------------------
# Index and coordinate validation
# --------------------------------------------------------------------------


@pytest.fixture
def nacl():
    return Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.0))


def test_indexing_accepts_numpy_ints_and_negative(nacl):
    assert nacl[-1].specie == "Cl"
    assert nacl[np.int64(0)].specie == "Na"
    assert nacl.remove_atom(np.int64(0)).species == ("Cl",)


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c[True],
        lambda c: c[1.0],
        lambda c: c.remove_atom(True),
        lambda c: c.remove_atom([1.0]),
        lambda c: c.substitute(True, "K"),
    ],
)
def test_bool_and_float_indices_are_rejected(nacl, call):
    with pytest.raises(TypeError):
        call(nacl)


def test_bool_coordinates_are_rejected():
    with pytest.raises(TypeError):
        Site([True, 0, 0], "H")
    with pytest.raises(TypeError):
        Site(np.array([True, False, False]), "H")
    with pytest.raises(TypeError):
        Molecule(["H"], [[True, 0, 0]])
    with pytest.raises(TypeError):
        Molecule(["H"], [[0, 0, 0]]).add_atom("H", [True, 0, 3])


def test_lattice_rejects_bools():
    with pytest.raises(TypeError):
        Lattice(True)
    with pytest.raises(TypeError):
        Lattice([True, True, True])
    with pytest.raises(TypeError):
        Lattice.from_parameters(3, 3, 3, 90, 90, True)
    assert Lattice.from_parameters(np.float32(3), 3, 3, 90, 90, 120).matrix.dtype == np.float64


def test_lattice_attributes_cannot_be_reassigned():
    lat = Lattice.cubic(3.0)
    with pytest.raises(AttributeError):
        lat._matrix = np.eye(3)
    assert copy.deepcopy(lat) == lat
    assert pickle.loads(pickle.dumps(lat)) == lat


def test_pbc_accepts_numpy_bool_array():
    c = Crystal(["H"], [[0, 0, 0]], Lattice.cubic(5.0), pbc=np.array([True, True, False]))
    assert c.pbc == (True, True, False)


# --------------------------------------------------------------------------
# Trajectory
# --------------------------------------------------------------------------


def test_trajectory_rejects_inconsistent_frames(nacl):
    with pytest.raises(ValueError, match="same atoms"):
        Trajectory([nacl, nacl.remove_atom(0)])
    with pytest.raises(ValueError, match="same atoms"):
        Trajectory([nacl, nacl.substitute(0, "K")])


def test_trajectory_validates_scalars_and_base_positions(nacl):
    with pytest.raises(ValueError):
        Trajectory([nacl], time_step=float("nan"))
    with pytest.raises(ValueError):
        Trajectory([nacl], time_step=-1.0)
    with pytest.raises(ValueError):
        Trajectory([nacl], coords_are_displacement=True)
    with pytest.raises(ValueError):
        Trajectory([nacl], base_positions=[[0, 0, 0]])
    with pytest.raises(ValueError):
        Trajectory([nacl], base_positions=[[0, 0, 0], [np.nan, 0, 0]])
