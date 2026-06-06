"""Tests for surface builders."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice, Molecule
from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.surface import generate_slab, generate_symmetric_slab
from matsimpy.transformation.atomic import add_adsorbate


def _sorted_rows(values, decimals=8):
    rounded = np.round(np.asarray(values, dtype=float), decimals)
    return rounded[np.lexsort(rounded.T[::-1])]


def _centered_cartesian_signature(positions):
    centered = np.asarray(positions, dtype=float) - np.mean(positions, axis=0)
    return _sorted_rows(centered)


class TestSlabGeneration(unittest.TestCase):
    """Tests for slab generation."""
    
    def setUp(self):
        """Set up test bulk structures."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.si_bulk = from_prototype('diamond', 'Si', 5.43)
        self.fcc_cu = from_prototype('fcc', 'Cu', 3.61)
    
    def test_generate_slab_basic(self):
        """Test basic slab generation."""
        slab = generate_slab(self.si_bulk, (1, 0, 0), min_slab_size=10, min_vacuum_size=15)
        
        # Should have atoms
        self.assertGreater(len(slab.species), 0)
        # Should be Crystal
        self.assertIsInstance(slab, Crystal)
        # Should have vacuum (larger c)
        self.assertGreater(slab.lattice.c, self.si_bulk.lattice.c)
        self.assertEqual(slab.pbc, (True, True, False))
    
    def test_generate_slab_111(self):
        """Test (111) slab generation."""
        slab = generate_slab(self.si_bulk, (1, 1, 1), min_slab_size=10, min_vacuum_size=15)
        
        self.assertGreater(len(slab.species), 0)
        self.assertEqual(slab.pbc, (True, True, False))

    def test_generate_slab_rejects_zero_miller_index(self):
        """The zero Miller index is invalid."""
        with self.assertRaises(ValueError):
            generate_slab(self.si_bulk, (0, 0, 0), 10, 15)

    def test_generate_slab_validates_sizes(self):
        """Slab and vacuum sizes must be physically meaningful."""
        with self.assertRaises(ValueError):
            generate_slab(self.si_bulk, (1, 0, 0), 0, 15)
        with self.assertRaises(ValueError):
            generate_slab(self.si_bulk, (1, 0, 0), 10, -1)
        with self.assertRaises(ValueError):
            generate_slab(self.si_bulk, (1, 0, 0), 10, 15, layers=0)
    
    def test_generate_slab_with_layers(self):
        """Test slab generation with specific number of layers."""
        slab = generate_slab(
            self.si_bulk, (1, 0, 0), 
            min_slab_size=10, min_vacuum_size=15,
            layers=5
        )
        
        self.assertGreater(len(slab.species), 0)
        self.assertEqual(len(slab.species), len(self.si_bulk.species) * 5)
        self.assertEqual(slab.pbc, (True, True, False))
    
    def test_generate_slab_centered(self):
        """Test centered slab generation."""
        slab = generate_slab(
            self.si_bulk, (1, 0, 0),
            min_slab_size=10, min_vacuum_size=15,
            center_slab=True
        )
        
        self.assertIsNotNone(slab)
    
    def test_generate_slab_not_centered(self):
        """Test non-centered slab generation."""
        slab = generate_slab(
            self.si_bulk, (1, 0, 0),
            min_slab_size=10, min_vacuum_size=15,
            center_slab=False
        )
        
        self.assertIsNotNone(slab)
    
    def test_generate_symmetric_slab(self):
        """Test symmetric slab generation."""
        slab = generate_symmetric_slab(self.si_bulk, (1, 1, 0), 15, 10)
        
        self.assertGreater(len(slab.species), 0)
        self.assertIsInstance(slab, Crystal)
    
    def test_slab_volume_increase(self):
        """Test that slab has larger volume than bulk (due to vacuum)."""
        slab = generate_slab(self.si_bulk, (0, 0, 1), min_slab_size=10, min_vacuum_size=15)
        
        self.assertGreater(slab.volume, self.si_bulk.volume)

    def test_slab_vacuum_satisfies_minimum_along_normal(self):
        bulk = from_prototype('fcc', 'Cu', 3.61)
        slab = generate_slab(bulk, (1, 1, 1), min_slab_size=8, min_vacuum_size=12)

        c_vec = slab.lattice.lattice_vectors[2]
        normal = c_vec / np.linalg.norm(c_vec)
        cart = slab.cart_positions
        projections = np.dot(cart, normal)
        thickness = float(np.max(projections) - np.min(projections))
        vacuum = np.linalg.norm(c_vec) - thickness
        self.assertGreaterEqual(vacuum, 12.0 - 1e-6)

    def test_slab_miller_orientation_matches_reference_invariants(self):
        """Miller-index slab basis follows crystallographic reference invariants."""
        from pymatgen.core import Structure
        from pymatgen.core.surface import SlabGenerator

        bulk = from_prototype('sc', 'Cu', 3.0)
        original_positions = bulk.positions.copy()
        hkl = np.array([1, 1, 1])
        slab = generate_slab(bulk, tuple(hkl), min_slab_size=6, min_vacuum_size=8)

        reference_structure = Structure(
            bulk.lattice.lattice_vectors,
            list(bulk.species),
            bulk.frac_positions,
        )
        reference_slab = SlabGenerator(
            reference_structure,
            tuple(hkl),
            6,
            8,
            center_slab=True,
            primitive=False,
        ).get_slab()

        self.assertGreater(len(slab), 0)
        self.assertGreater(len(reference_slab), 0)
        self.assertEqual(slab.pbc, (True, True, False))
        self.assertGreaterEqual(np.linalg.norm(slab.lattice.lattice_vectors[2]), 14.0)
        np.testing.assert_array_almost_equal(bulk.positions, original_positions)

        reciprocal_normal = np.linalg.solve(
            bulk.lattice.lattice_vectors,
            hkl.astype(float),
        )
        reciprocal_normal /= np.linalg.norm(reciprocal_normal)
        for vector in slab.lattice.lattice_vectors[:2]:
            self.assertAlmostEqual(np.dot(vector, reciprocal_normal), 0.0, places=6)
        self.assertAlmostEqual(
            abs(np.dot(
                slab.lattice.lattice_vectors[2] / np.linalg.norm(slab.lattice.lattice_vectors[2]),
                reciprocal_normal,
            )),
            1.0,
            places=6,
        )
        np.testing.assert_allclose(
            np.diff(sorted(np.unique(np.round(slab.cart_positions @ reciprocal_normal, 8)))),
            np.diff(sorted(np.unique(np.round(reference_slab.cart_coords @ reciprocal_normal, 8)))),
            rtol=1e-6,
            atol=1e-6,
        )

    def test_slab_001_coordinates_match_pymatgen_reference(self):
        """Simple cubic (001) slab coordinates should match reference geometry."""
        from pymatgen.core import Structure
        from pymatgen.core.surface import SlabGenerator

        bulk = from_prototype('sc', 'Cu', 3.0)
        hkl = (0, 0, 1)
        slab = generate_slab(bulk, hkl, min_slab_size=6, min_vacuum_size=8)
        reference_slab = SlabGenerator(
            Structure(
                bulk.lattice.lattice_vectors,
                list(bulk.species),
                bulk.frac_positions,
            ),
            hkl,
            6,
            8,
            center_slab=True,
            primitive=False,
        ).get_slab()

        self.assertEqual(len(slab), len(reference_slab))
        np.testing.assert_allclose(
            _centered_cartesian_signature(slab.cart_positions),
            _centered_cartesian_signature(reference_slab.cart_coords),
            rtol=1e-6,
            atol=1e-6,
        )

class TestAdsorbate(unittest.TestCase):
    """Tests for adsorbate placement."""
    
    def setUp(self):
        """Set up test slab."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        bulk = from_prototype('diamond', 'Si', 5.43)
        self.slab = generate_slab(bulk, (1, 0, 0), min_slab_size=10, min_vacuum_size=15)
    
    def test_add_adsorbate_single_atom(self):
        """Test adding single atom adsorbate."""
        with_ads = add_adsorbate(self.slab, 'O', (0.5, 0.5), height=2.0)
        
        # Should have one more atom
        self.assertEqual(len(with_ads.species), len(self.slab.species) + 1)
        # Last atom should be O
        self.assertEqual(with_ads.species[-1], 'O')
    
    def test_add_adsorbate_different_positions(self):
        """Test adding adsorbates at different positions."""
        ads1 = add_adsorbate(self.slab, 'O', (0.25, 0.25), height=2.0)
        ads2 = add_adsorbate(self.slab, 'O', (0.75, 0.75), height=2.0)
        
        # Both should have same number of atoms
        self.assertEqual(len(ads1.species), len(ads2.species))
        # But different positions
        self.assertFalse(np.allclose(ads1.positions, ads2.positions))
    
    def test_add_adsorbate_different_heights(self):
        """Test adding adsorbates at different heights."""
        ads1 = add_adsorbate(self.slab, 'O', (0.5, 0.5), height=1.5)
        ads2 = add_adsorbate(self.slab, 'O', (0.5, 0.5), height=3.0)
        
        # Heights should be different
        self.assertFalse(np.allclose(ads1.positions[-1], ads2.positions[-1]))
    
    def test_add_adsorbate_preserves_slab(self):
        """Test that adding adsorbate doesn't modify original slab."""
        original_count = len(self.slab.species)
        with_ads = add_adsorbate(self.slab, 'H', (0.5, 0.5), height=1.0)
        
        # Original slab unchanged
        self.assertEqual(len(self.slab.species), original_count)
        # New slab has more atoms
        self.assertEqual(len(with_ads.species), original_count + 1)

    def test_add_adsorbate_molecule(self):
        """Test adding a molecular adsorbate."""
        adsorbate = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        original_positions = self.slab.positions.copy()
        slab_cart = self.slab.cart_positions.copy()
        normal = self.slab.lattice.lattice_vectors[2] / np.linalg.norm(self.slab.lattice.lattice_vectors[2])
        projections = np.dot(slab_cart, normal)
        surface_proj = float(np.max(projections))

        with_ads = add_adsorbate(self.slab, adsorbate, (0.5, 0.5), height=2.0)

        self.assertIsInstance(with_ads, Crystal)
        self.assertEqual(len(with_ads.species), len(self.slab.species) + 2)
        self.assertEqual(with_ads.species[-2:], ('C', 'O'))
        ads_cart = with_ads.cart_positions[-2:, :]
        ads_proj = np.dot(ads_cart, normal)
        ads_cart = with_ads.cart_positions[-2:, :]
        ads_proj = np.dot(ads_cart, normal)
        self.assertAlmostEqual(
            np.min(ads_proj),
            surface_proj + 2.0,
            places=3,
        )
        np.testing.assert_array_almost_equal(self.slab.positions, original_positions)

    def test_add_adsorbate_invalid_height(self):
        with self.assertRaises(ValueError):
            add_adsorbate(self.slab, 'O', (0.5, 0.5), height=-1.0)
        with self.assertRaises(ValueError):
            add_adsorbate(self.slab, 'O', (0.5, 0.5), height=float('nan'))
        with self.assertRaises(ValueError):
            add_adsorbate(self.slab, 'O', (0.5, 0.5), height=float('inf'))

    def test_add_adsorbate_non_001_slab(self):
        bulk = from_prototype('diamond', 'Si', 5.43)
        slab = generate_slab(bulk, (1, 1, 1), min_slab_size=8, min_vacuum_size=10)
        slab_cart = slab.cart_positions.copy()
        normal = slab.lattice.lattice_vectors[2] / np.linalg.norm(slab.lattice.lattice_vectors[2])
        projections = np.dot(slab_cart, normal)
        surface_proj = float(np.max(projections))

        with_ads = add_adsorbate(slab, 'H', (0.5, 0.5), height=2.5)
        ads_cart = with_ads.cart_positions
        ads_proj = np.dot(ads_cart[-1], normal)
        self.assertAlmostEqual(ads_proj - surface_proj, 2.5, places=6)

if __name__ == '__main__':
    unittest.main()
