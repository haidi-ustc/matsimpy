"""Tests for surface builders."""
import numpy as np
import pytest

from matsimpy.builders.surface import add_adsorbate, generate_slab, generate_symmetric_slab
from matsimpy.core import Crystal, Lattice, Molecule

FCC = [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]


def _cu():
    return Crystal(['Cu'] * 4, FCC, Lattice.cubic(3.61))


def _si():
    positions = FCC + [[x + 0.25, y + 0.25, z + 0.25] for x, y, z in FCC]
    return Crystal(['Si'] * 8, positions, Lattice.cubic(5.43))


def _si_primitive():
    a = 5.43 / 2
    return Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice([[0, a, a], [a, 0, a], [a, a, 0]]))


def _nearest(crystal):
    cart = crystal.cart_positions
    shifts = [range(-1, 2) if p else [0] for p in crystal.pbc]
    images = np.array([[i, j, k] for i in shifts[0] for j in shifts[1] for k in shifts[2]]) @ crystal.lattice.matrix
    d = np.linalg.norm(cart[:, None, None] - cart[None, :, None] - images[None, None], axis=-1).min(axis=-1)
    np.fill_diagonal(d, np.inf)
    return d


def _pymatgen_slab(bulk, hkl, layers):
    pytest.importorskip("pymatgen")
    from pymatgen.core import Lattice as PL, Structure
    from pymatgen.core.surface import SlabGenerator

    structure = Structure(PL(bulk.lattice.matrix), list(bulk.species), bulk.frac_positions)
    return SlabGenerator(structure, hkl, layers, 10, in_unit_planes=True, primitive=True).get_slabs()[0]


class TestGenerateSlab:
    @pytest.mark.parametrize("bulk,hkl", [
        (_cu, (1, 0, 0)), (_cu, (1, 1, 0)), (_cu, (1, 1, 1)), (_cu, (2, 1, 0)),
        (_si, (1, 0, 0)), (_si, (1, 1, 1)), (_si, (2, 2, 1)),
    ])
    def test_surface_cell_matches_pymatgen(self, bulk, hkl):
        """The old builder's cells were up to 26 times too large and sometimes left-handed."""
        bulk = bulk()
        slab = generate_slab(bulk, hkl, layers=4, min_vacuum_size=10)
        reference = _pymatgen_slab(bulk, hkl, 4)
        matrix = slab.lattice.matrix
        area = np.linalg.norm(np.cross(matrix[0], matrix[1]))
        assert np.isclose(area, reference.surface_area)
        # each layer is one primitive cell, of volume area * d_hkl
        primitive_atoms = len(bulk) * area * slab.metadata["d_spacing"] / bulk.volume
        assert len(slab) == pytest.approx(4 * primitive_atoms)
        assert np.linalg.det(matrix) > 0
        assert np.allclose(matrix[2, :2], 0) and np.allclose(matrix[:2, 2], 0)
        assert slab.pbc == (True, True, False)

    @pytest.mark.parametrize("hkl", [(1, 0, 0), (1, 1, 0), (1, 1, 1), (3, 1, 1)])
    def test_bulk_bonds_are_kept(self, hkl):
        slab = generate_slab(_si(), hkl, min_slab_size=8)
        assert np.isclose(_nearest(slab).min(), 5.43 * np.sqrt(3) / 4)

    def test_layers_and_spacing(self):
        slab = generate_slab(_cu(), (1, 1, 1), layers=5)
        assert len(slab) == 5
        assert np.isclose(slab.metadata["d_spacing"], 3.61 / np.sqrt(3))
        z = np.sort(slab.cart_positions[:, 2])
        assert np.allclose(np.diff(z), 3.61 / np.sqrt(3))

    def test_miller_index_is_reduced(self):
        """(2, 2, 2) used to give a different, wrong slab from (1, 1, 1)."""
        a = generate_slab(_cu(), (1, 1, 1), layers=4)
        b = generate_slab(_cu(), (2, 2, 2), layers=4)
        assert len(a) == len(b)
        assert np.allclose(a.lattice.matrix, b.lattice.matrix)

    def test_conventional_and_primitive_bulk_give_the_same_surface(self):
        conventional = generate_slab(_si(), (1, 1, 1), layers=3)
        # (111) of the conventional cell is (111) of this primitive cell too
        primitive = generate_slab(_si_primitive(), (1, 1, 1), layers=3)
        assert len(conventional) == len(primitive) == 6
        assert np.isclose(conventional.lattice.a, primitive.lattice.a)

    def test_si111_is_cut_between_bilayers(self):
        slab = generate_slab(_si(), (1, 1, 1), layers=2)
        z = np.sort(slab.cart_positions[:, 2])
        gaps = np.round(np.diff(z), 4)
        # bilayers of 0.78 A, separated by 2.35 A bonds; the surface bonds are the short ones
        assert gaps[0] == gaps[-1] == round(5.43 * np.sqrt(3) / 12, 4)

    def test_slab_size_and_vacuum(self):
        slab = generate_slab(_cu(), (1, 0, 0), min_slab_size=10, min_vacuum_size=12)
        z = slab.cart_positions[:, 2]
        assert slab.metadata["layers"] * slab.metadata["d_spacing"] >= 10
        assert slab.lattice.c - np.ptp(z) >= 12
        assert np.isclose(z.min(), slab.lattice.c - z.max())  # centred

    def test_site_properties_are_kept(self):
        bulk = Crystal(['Fe', 'Fe'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(2.87),
                       site_properties=[{"magmom": 2.2}, {"magmom": -2.2}])
        slab = generate_slab(bulk, (0, 0, 1), layers=4)
        # the antiferromagnetic order makes the lattice simple cubic: d = a, 2 atoms per layer
        assert np.isclose(slab.metadata["d_spacing"], 2.87)
        assert len(slab) == 8
        assert sorted(p["magmom"] for p in slab.site_properties) == [-2.2] * 4 + [2.2] * 4

    def test_invalid_inputs(self):
        with pytest.raises(ValueError, match="0, 0, 0"):
            generate_slab(_cu(), (0, 0, 0), 10)
        with pytest.raises(ValueError, match="exactly one"):
            generate_slab(_cu(), (1, 0, 0))
        with pytest.raises(ValueError, match="exactly one"):
            generate_slab(_cu(), (1, 0, 0), 10, layers=3)
        with pytest.raises(ValueError, match="min_slab_size"):
            generate_slab(_cu(), (1, 0, 0), 0)
        with pytest.raises(ValueError, match="min_vacuum_size"):
            generate_slab(_cu(), (1, 0, 0), 10, -1)
        with pytest.raises(ValueError, match="layers"):
            generate_slab(_cu(), (1, 0, 0), layers=0)
        with pytest.raises(ValueError, match="three integers"):
            generate_slab(_cu(), (1.5, 0, 0), 10)
        with pytest.raises(TypeError):
            generate_slab(_cu(), (1, 0, 0), 10, shift=0.2)


class TestSymmetricSlab:
    @pytest.mark.parametrize("bulk,hkl", [(_si, (1, 1, 1)), (_si, (1, 0, 0)), (_cu, (1, 1, 0))])
    def test_top_and_bottom_are_equivalent(self, bulk, hkl):
        """The old function returned an ordinary slab and called it symmetric."""
        slab = generate_symmetric_slab(bulk(), hkl, layers=3)
        z = slab.cart_positions[:, 2]
        flipped = np.sort(z.max() + z.min() - z)
        assert np.allclose(np.sort(z), flipped, atol=1e-6)

    def test_polar_surface_raises(self):
        gaas = Crystal(['Ga'] * 4 + ['As'] * 4,
                       FCC + [[x + 0.25, y + 0.25, z + 0.25] for x, y, z in FCC], Lattice.cubic(5.65))
        with pytest.raises(ValueError, match="symmetric"):
            generate_symmetric_slab(gaas, (1, 1, 1), layers=3)


class TestAdsorbate:
    def setup_method(self):
        self.slab = generate_slab(_cu(), (1, 1, 1), layers=4, min_vacuum_size=15)

    def test_add_atom(self):
        top = self.slab.cart_positions[:, 2].max()
        with_ads = add_adsorbate(self.slab, 'O', (1 / 3, 1 / 3), height=1.2)
        assert len(with_ads) == len(self.slab) + 1
        assert np.isclose(with_ads.cart_positions[-1, 2], top + 1.2)
        np.testing.assert_allclose(self.slab.cart_positions, with_ads.cart_positions[:-1])

    def test_add_molecule(self):
        co = Molecule(['C', 'O'], [[5, 5, 0], [5, 5, 1.13]])
        top = self.slab.cart_positions[:, 2].max()
        with_ads = add_adsorbate(self.slab, co, (0.5, 0.5), height=1.85)
        cart = with_ads.cart_positions[-2:]
        assert with_ads.species[-2:] == ('C', 'O')
        assert np.isclose(cart[:, 2].min(), top + 1.85)
        site = 0.5 * self.slab.lattice.matrix[0] + 0.5 * self.slab.lattice.matrix[1]
        assert np.allclose(cart[:, :2].mean(axis=0), site[:2])

    def test_tilted_c_vector_uses_the_true_normal(self):
        """The old code measured heights along c and centred molecules in xy."""
        tilted = Crystal(self.slab.species, self.slab.cart_positions.tolist(),
                         Lattice([self.slab.lattice.matrix[0], self.slab.lattice.matrix[1], [2.0, 1.0, 20.0]]),
                         coords_are_cartesian=True, pbc=(True, True, False))
        top = tilted.cart_positions[:, 2].max()
        with_ads = add_adsorbate(tilted, 'H', (0.5, 0.5), height=1.5)
        assert np.isclose(with_ads.cart_positions[-1, 2], top + 1.5)

    def test_invalid_height(self):
        for height in (-1.0, float('nan'), float('inf')):
            with pytest.raises(ValueError):
                add_adsorbate(self.slab, 'O', (0.5, 0.5), height=height)
