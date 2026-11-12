"""High-symmetry k-paths of two-dimensional (layer) crystals.

0.9.0 ignored ``pbc``: a monolayer got the 3D path of its slab cell, with
k-points along the vacuum axis (graphene: A, L, H).  The 2D paths are checked
against the Brillouin-zone geometry itself, and against ASE 3.29.0 (optional
oracle) for the lattice classification and |k| of each special point.
ASE is not used as the oracle for the fractional coordinates: for an obtuse
oblique input cell its H and H1 are not on the zone boundary.
"""

import itertools

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice

spglib = pytest.importorskip("spglib")

from matsimpy.symmetry import HighSymmKpath  # noqa: E402

LAYER = [True, True, False]
G = "\\Gamma"

LATTICES = {
    "square": ([[3, 0, 0], [0, 3, 0], [0, 0, 20]], "tp"),
    "square_sheared": ([[3, 3, 0], [0, 3, 0], [0, 0, 20]], "tp"),
    "rectangular": ([[3, 0, 0], [0, 4, 0], [0, 0, 20]], "op"),
    "rectangular_sheared": ([[3, 0, 0], [6, 4, 0], [0, 0, 20]], "op"),
    "centered_70": (Lattice.from_parameters(3, 3, 20, 90, 90, 70).matrix, "oc"),
    "centered_110": (Lattice.from_parameters(3, 3, 20, 90, 90, 110).matrix, "oc"),
    "centered_skew": ([[3, 0, 0], [4.5, 1.2, 0], [0, 0, 20]], "oc"),
    "hexagonal_120": (Lattice.hexagonal(3, 20).matrix, "hp"),
    "hexagonal_60": (Lattice.from_parameters(3, 3, 20, 90, 90, 60).matrix, "hp"),
    "oblique_70": (Lattice.from_parameters(3, 4, 20, 90, 90, 70).matrix, "mp"),
    "oblique_110": (Lattice.from_parameters(3, 4, 20, 90, 90, 110).matrix, "mp"),
    "oblique_skew": ([[3, 0, 0], [5.2, 2.1, 0], [0, 0, 20]], "mp"),
    "oblique_long": (Lattice.from_parameters(3, 7.5, 20, 90, 90, 80).matrix, "mp"),
}
PATHS = {
    "tp": ["M", G, "X", "M"],
    "op": [G, "X", "S", "Y", G, "S"],
    "oc": [G, "X", "A_1", "Y", G],
    "hp": [G, "M", "K", G],
    "mp": [G, "Y", "H", "C", "H_1", "X", G],
}
# labels at Brillouin-zone corners; every other non-Gamma label is an edge midpoint
CORNERS = {"tp": {"M"}, "op": {"S"}, "oc": {"X", "A_1"}, "hp": {"K"}, "mp": {"H", "H_1"}}


def _one_atom_layer(matrix):
    return Crystal(["C"], [[0, 0, 0]], Lattice(np.asarray(matrix, float)), pbc=LAYER)


def _zone_lines(kpath, label):
    """Number of zone-edge lines (perpendicular bisectors of reciprocal lattice
    vectors) through the point; 0 means strictly inside the first zone."""
    reciprocal = kpath._reciprocal[:2, :2]
    k = np.asarray(kpath.kpath["kpoints"][label])[:2] @ reciprocal
    on_line = 0
    for i, j in itertools.product(range(-4, 5), repeat=2):
        if (i, j) == (0, 0):
            continue
        g = i * reciprocal[0] + j * reciprocal[1]
        ratio = k @ g / (g @ g)
        assert ratio <= 0.5 + 1e-9, f"{label} lies outside the first Brillouin zone"
        on_line += abs(ratio - 0.5) < 1e-9
    return on_line


@pytest.mark.parametrize("name", LATTICES)
def test_lattice_classification_and_path(name):
    matrix, bravais = LATTICES[name]
    kpath = HighSymmKpath(_one_atom_layer(matrix))
    assert kpath.bravais == kpath.kpath["bravais"] == bravais
    assert kpath.kpath["path"] == [PATHS[bravais]]


@pytest.mark.parametrize("name", LATTICES)
def test_special_points_are_zone_corners_and_edge_midpoints(name):
    matrix, bravais = LATTICES[name]
    kpath = HighSymmKpath(_one_atom_layer(matrix))
    for label in kpath.kpath["kpoints"]:
        lines = _zone_lines(kpath, label)
        if label == G:
            assert lines == 0
        elif label in CORNERS[bravais]:
            assert lines >= 2, label
        else:
            assert lines == 1, label


@pytest.mark.parametrize("name", LATTICES)
def test_points_have_no_component_along_the_vacuum_axis(name):
    kpath = HighSymmKpath(_one_atom_layer(LATTICES[name][0]))
    assert all(point[2] == 0 for point in kpath.kpath["kpoints"].values())
    points, labels = kpath.get_kpoints(line_density=10)
    assert len(points) == len(labels)
    assert np.all(np.asarray(points)[:, 2] == 0)


@pytest.mark.parametrize("name", LATTICES)
def test_optional_ase_reference(name):
    """Classification and |k| per label equal ASE's for its canonical cell."""
    pytest.importorskip("ase")
    from ase.cell import Cell

    matrix = np.asarray(LATTICES[name][0], float)
    kpath = HighSymmKpath(_one_atom_layer(matrix))
    lattice = Cell(matrix).get_bravais_lattice(pbc=LAYER)
    assert lattice.pearson_symbol == kpath.bravais
    canonical = np.asarray(lattice.tocell())
    canonical[2, 2] = 20.0
    reciprocal = 2 * np.pi * np.linalg.inv(canonical).T
    expected = {
        label: np.linalg.norm(np.asarray(point) @ reciprocal)
        for label, point in lattice.get_special_points().items()
    }
    for label, point in kpath.kpath["kpoints"].items():
        ase_label = label.replace(G, "G").replace("_", "")
        assert np.linalg.norm(np.asarray(point) @ kpath._reciprocal) == pytest.approx(expected[ase_label])


SQUARE = Lattice([[3, 0, 0], [0, 3, 0], [0, 0, 20]])
HEXAGONAL = Lattice.hexagonal(3, 20)


@pytest.mark.parametrize(
    ("species", "positions", "lattice", "bravais", "path"),
    [
        # square cell, mirrors only along the cell axes: rectangular zone
        (["C", "N"], [[0, 0, .5], [.3, 0, .5]], SQUARE, "op", PATHS["op"]),
        # square cell, mirrors only along the diagonals: centered rectangular
        # at alpha = 90, where A_1 coincides with Y and is merged
        (["C", "N"], [[0, 0, .5], [.3, .3, .5]], SQUARE, "oc", [G, "X", "Y", G]),
        # 4-fold axis without mirrors: only half the zone is equivalent to the
        # rest; the oblique path collapses to a quadrant (H = C = H_1)
        (["C"] + ["N"] * 4, [[0, 0, .5], [.1, .3, .5], [-.3, .1, .5], [-.1, -.3, .5], [.3, -.1, .5]],
         SQUARE, "mp", [G, "Y", "C", "X", G]),
        # 3-fold axis without mirrors: K and K' are inequivalent, both are on the path
        (["C"] + ["N"] * 3, [[0, 0, .5], [.1, .25, .5], [-.25, -.15, .5], [.15, -.1, .5]],
         HEXAGONAL, "mp", PATHS["mp"]),
        # hexagonal cell with a mirror but no 3-fold axis
        (["C", "N"], [[0, 0, .5], [.3, 0, .5]], HEXAGONAL, "oc", PATHS["oc"]),
    ],
    ids=["square-axis-mirrors", "square-diagonal-mirrors", "square-C4-only", "hexagonal-C3-only",
         "hexagonal-mirror-only"],
)
def test_classification_follows_the_layer_symmetry_not_the_cell_shape(species, positions, lattice, bravais, path):
    kpath = HighSymmKpath(Crystal(species, positions, lattice, pbc=LAYER))
    assert kpath.bravais == bravais
    assert kpath.kpath["path"] == [path]
    for label in kpath.kpath["kpoints"]:
        assert _zone_lines(kpath, label) >= (label != G)


def test_graphene_has_no_out_of_plane_points():
    graphene = Crystal(["C", "C"], [[1/3, 2/3, .5], [2/3, 1/3, .5]], Lattice.hexagonal(2.46, 20), pbc=LAYER)
    kpath = HighSymmKpath(graphene)
    assert kpath.bravais == "hp"
    assert kpath.kpath["path"] == [[G, "M", "K", G]]
    assert kpath.kpath["kpoints"]["K"] == pytest.approx((1/3, 1/3, 0))
    # the same cell as a 3D crystal keeps its 3D path with k_z points
    bulk = HighSymmKpath(Crystal(graphene.species, graphene.frac_positions, graphene.lattice))
    assert {"A", "L", "H"} <= set(bulk.kpath["kpoints"])


def test_mos2_monolayer_is_hexagonal():
    lattice = Lattice.hexagonal(3.16, 20)
    dz = 1.56 / 20
    mos2 = Crystal(["Mo", "S", "S"], [[1/3, 2/3, .5], [2/3, 1/3, .5 + dz], [2/3, 1/3, .5 - dz]], lattice, pbc=LAYER)
    kpath = HighSymmKpath(mos2)
    assert kpath.bravais == "hp"
    assert _zone_lines(kpath, "K") == 2


def test_vacuum_along_another_axis():
    crystal = Crystal(["C"], [[0, 0, 0]], Lattice([[4, 0, 0], [0, 20, 0], [0, 0, 3]]), pbc=[True, False, True])
    kpath = HighSymmKpath(crystal)
    assert kpath.bravais == "op"
    assert all(point[1] == 0 for point in kpath.kpath["kpoints"].values())
    # X is along the shorter periodic axis (c = 3 A), Y along a = 4 A
    assert kpath.kpath["kpoints"]["X"] == pytest.approx((0, 0, .5))
    assert kpath.kpath["kpoints"]["Y"] == pytest.approx((.5, 0, 0))


@pytest.mark.parametrize("pbc", [[True, False, False], [False, False, False]])
def test_fewer_than_two_periodic_axes_raise(pbc):
    crystal = Crystal(["C"], [[0, 0, 0]], Lattice.cubic(10), pbc=pbc)
    with pytest.raises(ValueError, match="two or three periodic axes"):
        HighSymmKpath(crystal)


def test_line_mode_kpoints_for_a_layer():
    from matsimpy.calculator.vasp.inputs import Kpoints

    kpath = HighSymmKpath(_one_atom_layer(LATTICES["rectangular"][0]))
    kpoints = Kpoints.automatic_linemode(10, kpath)
    assert kpoints.style.name == "Line_mode"
    assert kpoints.labels[:2] == [G, "X"]
    assert all(point[2] == 0 for point in kpoints.kpts)
