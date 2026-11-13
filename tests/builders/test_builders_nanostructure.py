"""
Tests for nanostructure builders.
"""

import numpy as np
import pytest

from matsimpy.builders.nanostructure import (
    build_carbon_nanotube,
    build_magic_angle_twisted,
    build_nanotube,
    build_twisted_bilayer,
    build_twisted_multilayer,
    commensurate_twist_angles,
    nanotube_translation,
)
from matsimpy.core import Crystal, Lattice


def _graphene(a=2.46, basis=120):
    if basis == 120:
        return Crystal(["C", "C"], [[0, 0, 0.5], [1 / 3, 2 / 3, 0.5]], Lattice.hexagonal(a, 15.0))
    lattice = Lattice([[a, 0, 0], [a / 2, a * np.sqrt(3) / 2, 0], [0, 0, 15.0]])
    return Crystal(["C", "C"], [[0, 0, 0.5], [1 / 3, 1 / 3, 0.5]], lattice)


def _mos2():
    dz = 1.56 / 20
    return Crystal(["Mo", "S", "S"], [[1 / 3, 2 / 3, 0.5], [2 / 3, 1 / 3, 0.5 + dz], [2 / 3, 1 / 3, 0.5 - dz]],
                   Lattice.hexagonal(3.16, 20.0))


def _periodic_neighbor_distances(crystal, mask=None, k=3):
    """Distances to the k nearest neighbours of each atom, with periodic images along periodic axes."""
    from scipy.spatial import cKDTree

    frac = crystal.frac_positions if mask is None else crystal.frac_positions[mask]
    shifts = [range(-1, 2) if periodic else [0] for periodic in crystal.pbc]
    images = np.array([[i, j, l] for i in shifts[0] for j in shifts[1] for l in shifts[2]])
    cart = frac @ crystal.lattice.matrix
    everything = ((frac[None] + images[:, None]) @ crystal.lattice.matrix).reshape(-1, 3)
    distances, _ = cKDTree(everything).query(cart, k=k + 1)
    return distances[:, 1:]


def _radii(tube):
    center = np.array([tube.lattice.a / 2, tube.lattice.b / 2])
    return np.linalg.norm(tube.cart_positions[:, :2] - center, axis=1)


def _same_on_cylinder(ours, reference, period, mirror=False):
    """Whether two tubes coincide after a rotation about and a shift along the axis."""
    def cylindrical(cart, center):
        xy = cart[:, :2] - center
        return np.arctan2(xy[:, 1], xy[:, 0]), cart[:, 2], np.linalg.norm(xy, axis=1)

    th1, z1, r1 = cylindrical(ours.cart_positions, np.array([ours.lattice.a / 2] * 2))
    th2, z2, r2 = cylindrical(reference.positions, np.zeros(2))
    if mirror:
        z1 = -z1
    target = np.column_stack([np.cos(th2), np.sin(th2), np.mod(z2, period), r2])
    for j in range(len(reference)):
        dth, dz = th2[j] - th1[0], z2[j] - z1[0]
        moved = np.column_stack([np.cos(th1 + dth), np.sin(th1 + dth), np.mod(z1 + dz, period), r1])
        d = np.abs(moved[:, None] - target[None])
        d[..., 2] = np.minimum(d[..., 2], period - d[..., 2])
        if np.all(d.max(-1).min(1) < 1e-5):
            return True
    return False


class TestNanotube:
    @pytest.mark.parametrize("n,m", [(5, 5), (10, 0), (7, 3), (6, 2)])
    def test_carbon_nanotube_matches_ase(self, n, m):
        ase_build = pytest.importorskip("ase.build")
        reference = ase_build.nanotube(n, m, bond=1.42)
        tube = build_carbon_nanotube(n, m)
        period = reference.cell.lengths()[2]
        assert len(tube) == len(reference)
        assert np.isclose(tube.lattice.c, period)
        # ASE rolls chiral tubes with the opposite handedness: (n, m) and (m, n) are mirror images
        assert _same_on_cylinder(tube, reference, period, mirror=(n != m and m != 0))
        assert tube.pbc == (False, False, True)

    def test_tube_axis_is_centred_and_atoms_on_one_radius(self):
        tube = build_carbon_nanotube(10, 0)
        radii = _radii(tube)
        assert np.allclose(radii, tube.metadata["radius"])
        assert np.allclose(tube.cart_positions[:, :2].mean(axis=0), tube.lattice.a / 2, atol=1e-6)

    @pytest.mark.parametrize("chirality", [(5, 5), (7, 3), (6, 0)])
    def test_120_degree_basis_gives_periodic_tube(self, chirality):
        """The old builder found a T not perpendicular to C in a 120-degree basis."""
        tube = build_nanotube(_graphene(basis=120), chirality)
        t1, t2 = tube.metadata["translation"]
        lattice = Lattice.hexagonal(2.46, 15.0).matrix[:2, :2].T
        chiral, translation = lattice @ np.array(chirality), lattice @ np.array([t1, t2])
        assert abs(chiral @ translation) < 1e-9
        distances = _periodic_neighbor_distances(tube)
        assert distances.min() > 1.35
        assert np.allclose(distances[:, 0], distances[:, 0].mean(), atol=0.05)

    def test_120_and_60_degree_bases_give_the_same_tube(self):
        # (n, m) in the 60-degree basis is (n + m, m) in the 120-degree one
        sixty = build_nanotube(_graphene(basis=60), (4, 2))
        hundred_twenty = build_nanotube(_graphene(basis=120), (6, 2))
        assert len(sixty) == len(hundred_twenty)
        assert np.isclose(sixty.lattice.c, hundred_twenty.lattice.c)
        assert np.isclose(sixty.metadata["radius"], hundred_twenty.metadata["radius"])

    def test_thick_sheet_keeps_all_atoms_on_coaxial_shells(self):
        """The old builder dropped one S layer (Mo20S20) and put every atom on one radius."""
        tube = build_nanotube(_mos2(), (10, 10))
        assert tube.formula == "Mo20S40"
        radii = _radii(tube)
        radius = tube.metadata["radius"]
        species = np.array(tube.species)
        assert np.allclose(radii[species == "Mo"], radius)
        sulfur = np.sort(radii[species == "S"])
        assert np.allclose(sulfur[:20], radius - 1.56) and np.allclose(sulfur[20:], radius + 1.56)

    @pytest.mark.parametrize("chirality,translation,count", [
        ((10, 0), [0, 1], 10), ((0, 7), [-1, 0], 7), ((4, 3), [-3, 4], 25), ((5, -2), [2, 5], 29),
    ])
    def test_square_lattice(self, chirality, translation, count):
        sheet = Crystal(["Cu"], [[0, 0, 0.5]], Lattice.tetragonal(2.55, 15.0))
        tube = build_nanotube(sheet, chirality)
        assert tube.metadata["translation"] == translation
        assert len(tube) == count
        assert np.isclose(tube.lattice.c, 2.55 * np.linalg.norm(translation))
        assert _periodic_neighbor_distances(tube, k=1).min() > 2.3

    @pytest.mark.parametrize("chirality,count,period", [((0, 8), 32, 3.30), ((12, 0), 48, 4.60)])
    def test_rectangular_puckered_lattice(self, chirality, count, period):
        sheet = Crystal(["P"] * 4, [[0, 0, 0.45], [0.5, 0.18, 0.45], [0, 0.5, 0.55], [0.5, 0.68, 0.55]],
                        Lattice.orthorhombic(3.30, 4.60, 20.0))
        tube = build_nanotube(sheet, chirality)
        assert len(tube) == count
        assert np.isclose(tube.lattice.c, period)
        radii = np.unique(np.round(_radii(tube), 6))
        assert np.allclose(np.diff(radii), 2.0)  # the two sub-layers, 0.1 * 20 A apart

    def test_incommensurate_direction_raises(self):
        sheet = Crystal(["P"], [[0, 0, 0.5]], Lattice.orthorhombic(3.30, 4.60, 20.0))
        with pytest.raises(ValueError, match="no lattice vector perpendicular"):
            build_nanotube(sheet, (3, 2))

    def test_translation_orientation(self):
        lattice = np.array([[1.0, 0.0], [0.0, 1.0]])
        for chirality in [(1, 0), (0, 1), (2, 3), (-2, 3), (3, -1)]:
            t = nanotube_translation(lattice, *chirality)
            assert chirality[0] * t[1] - chirality[1] * t[0] > 0
            assert np.dot(chirality, t) == 0

    def test_length_rounds_up_to_whole_periods(self):
        tube = build_carbon_nanotube(5, 5, length=10.0)
        assert np.isclose(tube.lattice.c, 5 * 2.4595121467478056)
        assert len(tube) == 100

    def test_finite_tube_has_vacuum_at_both_ends(self):
        tube = build_carbon_nanotube(5, 5, periodic=False, vacuum=8.0)
        assert tube.pbc == (False, False, False)
        z = tube.cart_positions[:, 2]
        assert np.isclose(z.min(), 4.0) and np.isclose(tube.lattice.c - z.max(), 4.0 + 2.4595121467478056 / 4,
                                                       atol=0.7)

    def test_site_properties_are_carried(self):
        layer = Crystal(["B", "N"], [[1 / 3, 2 / 3, 0.5], [2 / 3, 1 / 3, 0.5]], Lattice.hexagonal(2.5, 15.0),
                        site_properties=[{"charge": 1}, {"charge": -1}])
        tube = build_nanotube(layer, (6, 0))
        charges = [p["charge"] for p in tube.site_properties]
        assert [c for c, s in zip(charges, tube.species) if s == "B"] == [1] * 12

    def test_invalid_inputs(self):
        with pytest.raises(ValueError, match="Chirality indices cannot both be zero"):
            build_carbon_nanotube(0, 0)
        with pytest.raises(ValueError, match="integers"):
            build_nanotube(_graphene(), (2.5, 1))
        with pytest.raises(ValueError, match="max_atoms"):
            build_nanotube(_graphene(), (40, 39), max_atoms=1000)
        with pytest.raises(ValueError, match="xy-plane"):
            build_nanotube(Crystal(["C"], [[0, 0, 0]], Lattice([[0, 0, 3.0], [3.0, 0, 0], [0, 3.0, 0]])), (1, 0))
        with pytest.raises(ValueError, match="bond_length"):
            build_carbon_nanotube(5, 5, bond_length=-1.0)
        with pytest.raises(ValueError, match="too narrow"):
            build_nanotube(_mos2(), (1, 0))


class TestTwistedBilayer:
    def test_commensurate_bilayer_is_periodic(self):
        """The old builder rotated the top layer inside the unrotated cell."""
        bilayer = build_twisted_bilayer(_graphene(), 21.786789)
        assert len(bilayer) == 28
        assert bilayer.pbc == (True, True, False)
        assert np.isclose(bilayer.metadata["twist_angles"][1], 21.786789, atol=1e-5)
        for k in (0, 1):
            mask = np.array([p["layer"] == k for p in bilayer.site_properties])
            distances = _periodic_neighbor_distances(bilayer, mask)
            assert np.allclose(distances, 2.46 / np.sqrt(3), atol=1e-6)

    def test_layer_spacing_is_the_gap_between_layers(self):
        """The old default spacing was the c length of the input cell."""
        bilayer = build_twisted_bilayer(_mos2(), 21.786789, layer_spacing=3.0)
        z = np.unique(np.round(bilayer.cart_positions[:, 2], 6))
        assert np.allclose(np.diff(z), [1.56, 1.56, 3.0, 1.56, 1.56])

    def test_twist_rotates_the_top_lattice(self):
        bilayer = build_twisted_bilayer(_graphene(), 13.17355)
        bottom, top = (np.array(m) for m in bilayer.metadata["supercell_matrices"])
        sheet = Lattice.hexagonal(2.46, 15.0).matrix[:2, :2].T
        theta = np.radians(13.17355)
        rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
        assert np.allclose(sheet @ bottom, rotation @ sheet @ top, atol=1e-4)

    def test_incommensurate_angle_error_lists_nearby_angles(self):
        with pytest.raises(ValueError, match="Nearby commensurate angles: 1.0845"):
            build_twisted_bilayer(_graphene(), 1.1)

    def test_strain_and_angle_tolerance(self):
        bilayer = build_twisted_bilayer(_graphene(), 1.1, max_strain=2e-3)
        assert abs(bilayer.metadata["twist_angles"][1] - 1.1) <= 0.01
        assert bilayer.metadata["strain"][1] <= 2e-3

    def test_heterobilayer(self):
        hbn = Crystal(["B", "N"], [[1 / 3, 2 / 3, 0.5], [2 / 3, 1 / 3, 0.5]], Lattice.hexagonal(2.504, 15.0))
        bilayer = build_twisted_bilayer(_graphene(), 0.0, top_layer=hbn, max_atoms=14000)
        assert bilayer.formula == "C6498B3136N3136"
        assert bilayer.metadata["strain"][1] < 1e-4

    def test_invalid_inputs(self):
        with pytest.raises(ValueError, match="layer_spacing"):
            build_twisted_bilayer(_graphene(), 21.786789, layer_spacing=0.0)
        with pytest.raises(ValueError, match="finite"):
            build_twisted_bilayer(_graphene(), float("nan"))
        with pytest.raises(TypeError):
            build_twisted_bilayer(_graphene(), 21.786789, unknown=1)


class TestMagicAngleTwisted:
    @pytest.mark.parametrize("basis", [60, 120])
    @pytest.mark.parametrize("n,m,angle,atoms", [(1, 2, 21.786789, 28), (2, 3, 13.173551, 76),
                                                 (31, 32, 1.050121, 11908)])
    def test_hexagonal_commensurate_angles(self, basis, n, m, angle, atoms):
        """The old formula 360 / (n^2 + nm + m^2) gave 51.4 degrees for (1, 2)."""
        bilayer = build_magic_angle_twisted(_graphene(basis=basis), n, m)
        assert np.isclose(bilayer.metadata["twist_angles"][1], angle, atol=1e-5)
        assert len(bilayer) == atoms
        assert max(bilayer.metadata["strain"]) < 1e-9

    def test_square_lattice(self):
        sheet = Crystal(["Cu"], [[0, 0, 0.5]], Lattice.tetragonal(2.55, 15.0))
        bilayer = build_magic_angle_twisted(sheet, 1, 2)
        assert np.isclose(bilayer.metadata["twist_angles"][1], 36.869898, atol=1e-5)
        assert len(bilayer) == 10

    def test_invalid_indices(self):
        with pytest.raises(ValueError, match="Equal indices"):
            build_magic_angle_twisted(_graphene(), 1, 1)
        with pytest.raises(ValueError, match="n must be"):
            build_magic_angle_twisted(_graphene(), -1, 2)
        with pytest.raises(ValueError, match="m must be"):
            build_magic_angle_twisted(_graphene(), 2, 0)
        rectangular = Crystal(["P"], [[0, 0, 0.5]], Lattice.orthorhombic(3.3, 4.6, 15.0))
        with pytest.raises(ValueError, match="hexagonal or square"):
            build_magic_angle_twisted(rectangular, 1, 2)


class TestCommensurateAngles:
    def test_graphene(self):
        angles = commensurate_twist_angles(_graphene(), max_atoms=100)
        assert [(round(a["angle"], 2), a["atoms"]) for a in angles] == [
            (13.17, 76), (21.79, 28), (27.8, 52), (32.2, 52), (38.21, 28), (46.83, 76)]

    def test_magic_angle_is_listed(self):
        angles = commensurate_twist_angles(_graphene(), max_atoms=12000, max_angle=1.1)
        assert {"angle": 1.050121, "atoms": 11908} in angles


class TestTwistedMultilayer:
    def test_alternating_trilayer(self):
        trilayer = build_twisted_multilayer(_graphene(), 3, [21.786789, -21.786789])
        assert len(trilayer) == 42
        assert np.allclose(trilayer.metadata["twist_angles"], [0, 21.786789, 0], atol=1e-5)
        z = np.unique(np.round(trilayer.cart_positions[:, 2], 6))
        assert np.allclose(np.diff(z), 3.35)

    def test_same_angle_is_cumulative(self):
        trilayer = build_twisted_multilayer(_graphene(), 3, 21.786789, max_atoms=500)
        assert len(trilayer) == 294  # 7 x 7 graphene cells per layer
        assert np.allclose(trilayer.metadata["twist_angles"], [0, 21.786789, 43.573579], atol=1e-5)

    def test_invalid_inputs(self):
        with pytest.raises(ValueError, match="num_layers must be an integer"):
            build_twisted_multilayer(_graphene(), 1, 1.1)
        with pytest.raises(ValueError, match="Number of twist angles"):
            build_twisted_multilayer(_graphene(), 3, [1.1])
        for spacing in (0.0, -1.0, float("nan")):
            with pytest.raises(ValueError, match="layer_spacing"):
                build_twisted_multilayer(_graphene(), 3, 21.786789, layer_spacing=spacing)
