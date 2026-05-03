"""Tests for surface builders."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.surface import generate_slab, generate_symmetric_slab, add_adsorbate

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

if __name__ == '__main__':
    unittest.main()
