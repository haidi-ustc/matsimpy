"""Tests for alloy builders."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype
from matsimpy.transformation.chemical import (
    generate_random_alloy,
    generate_ordered_alloy,
    generate_intermetallic
)
from matsimpy.transformation.structural import make_supercell

class TestRandomAlloy(unittest.TestCase):
    """Tests for random alloy generation."""
    
    def setUp(self):
        """Set up test base structure."""
        fcc = from_prototype('fcc', 'Al', 4.05)
        self.base = make_supercell(fcc, [2, 2, 2])
    
    def test_generate_random_alloy_binary(self):
        """Test binary alloy generation."""
        alloy = generate_random_alloy(self.base, ['Cu'], 'Al', [0.5], seed=42)
        
        # Count Cu atoms
        cu_count = sum(1 for s in alloy.species if s == 'Cu')
        total = len(alloy.species)
        
        # Should be approximately 50%
        self.assertGreater(cu_count, total * 0.4)
        self.assertLess(cu_count, total * 0.6)
    
    def test_generate_random_alloy_ternary(self):
        """Test ternary alloy generation."""
        alloy = generate_random_alloy(
            self.base, ['Cu', 'Mg'], 'Al', [0.4, 0.1], seed=42
        )
        
        cu_count = sum(1 for s in alloy.species if s == 'Cu')
        mg_count = sum(1 for s in alloy.species if s == 'Mg')
        al_count = sum(1 for s in alloy.species if s == 'Al')
        
        total = len(alloy.species)
        self.assertGreater(cu_count, 0)
        self.assertGreater(mg_count, 0)
        self.assertGreater(al_count, 0)
        self.assertEqual(cu_count + mg_count + al_count, total)
    
    def test_generate_random_alloy_reproducible(self):
        """Test that same seed gives same result."""
        alloy1 = generate_random_alloy(self.base, ['Cu'], 'Al', [0.5], seed=42)
        alloy2 = generate_random_alloy(self.base, ['Cu'], 'Al', [0.5], seed=42)
        
        # Should have same composition
        self.assertEqual(alloy1.species, alloy2.species)
    
    def test_generate_random_alloy_different_seeds(self):
        """Test that different seeds give different results."""
        alloy1 = generate_random_alloy(self.base, ['Cu'], 'Al', [0.5], seed=42)
        alloy2 = generate_random_alloy(self.base, ['Cu'], 'Al', [0.5], seed=100)
        
        # Should have different arrangements
        self.assertNotEqual(alloy1.species, alloy2.species)
    
    def test_generate_random_alloy_invalid_concentration(self):
        """Test with invalid concentration sum."""
        with self.assertRaises(ValueError):
            # Concentration > 1.0 should fail
            generate_random_alloy(self.base, ['Cu'], 'Al', [1.2])
        with self.assertRaises(ValueError):
            generate_random_alloy(self.base, ['Cu'], 'Al', [-0.1])
        with self.assertRaises(ValueError):
            generate_random_alloy(self.base, [], 'Al')
    
    def test_generate_random_alloy_no_sites(self):
        """Test with species not in structure."""
        with self.assertRaises(ValueError):
            generate_random_alloy(self.base, ['Cu'], 'Fe', [0.5])

    def test_generate_random_alloy_seed_does_not_reset_global_rng(self):
        """Local alloy seeding should not mutate NumPy's global RNG state."""
        np.random.seed(123)
        expected = np.random.random(3)

        np.random.seed(123)
        generate_random_alloy(self.base, ['Cu'], 'Al', [0.5], seed=42)
        actual = np.random.random(3)

        np.testing.assert_allclose(actual, expected)

class TestOrderedAlloy(unittest.TestCase):
    """Tests for ordered alloy generation."""
    
    def setUp(self):
        """Set up test base structure."""
        self.base = Crystal(
            ['A', 'A', 'A', 'A'],
            [[0,0,0], [0.5,0.5,0], [0.5,0,0.5], [0,0.5,0.5]],
            Lattice.cubic(4.0)
        )
    
    def test_generate_ordered_alloy_simple(self):
        """Test simple ordered alloy."""
        pattern = {0: 'Au', 1: 'Au', 2: 'Cu', 3: 'Cu'}
        ordered = generate_ordered_alloy(self.base, pattern)
        
        self.assertEqual(ordered.species[0], 'Au')
        self.assertEqual(ordered.species[1], 'Au')
        self.assertEqual(ordered.species[2], 'Cu')
        self.assertEqual(ordered.species[3], 'Cu')
    
    def test_generate_ordered_alloy_partial(self):
        """Test partial substitution."""
        pattern = {0: 'Ni', 2: 'Al'}
        ordered = generate_ordered_alloy(self.base, pattern)
        
        self.assertEqual(ordered.species[0], 'Ni')
        self.assertEqual(ordered.species[1], 'A')  # Unchanged
        self.assertEqual(ordered.species[2], 'Al')
        self.assertEqual(ordered.species[3], 'A')  # Unchanged
    
    def test_generate_ordered_alloy_invalid_index(self):
        """Test with out of range index."""
        pattern = {100: 'Cu'}
        with self.assertRaises(ValueError):
            generate_ordered_alloy(self.base, pattern)

class TestIntermetallic(unittest.TestCase):
    """Tests for intermetallic generation."""
    
    def test_generate_intermetallic_l12(self):
        """Test L1_2 structure generation."""
        ni3al = generate_intermetallic(['Ni', 'Al'], 'A3B', 'L1_2', 3.56)
        
        self.assertEqual(len(ni3al.species), 4)
        # Should have 3 Ni and 1 Al
        ni_count = sum(1 for s in ni3al.species if s == 'Ni')
        al_count = sum(1 for s in ni3al.species if s == 'Al')
        
        self.assertEqual(ni_count, 3)
        self.assertEqual(al_count, 1)
    
    def test_generate_intermetallic_b2(self):
        """Test B2 structure generation."""
        feal = generate_intermetallic(['Fe', 'Al'], 'AB', 'B2', 2.9)
        
        self.assertEqual(len(feal.species), 2)
        self.assertIn('Fe', feal.species)
        self.assertIn('Al', feal.species)
    
    def test_generate_intermetallic_lattice_constant(self):
        """Test lattice constant is set correctly."""
        ni3al = generate_intermetallic(['Ni', 'Al'], 'A3B', 'L1_2', 3.56)
        
        self.assertAlmostEqual(ni3al.lattice.a, 3.56, places=5)

    def test_generate_intermetallic_unsupported_type_raises(self):
        with self.assertRaises(NotImplementedError):
            generate_intermetallic(['Fe', 'Pt'], 'AB', 'DO3', 3.85)

    def test_generate_intermetallic_l10(self):
        fept = generate_intermetallic(['Fe', 'Pt'], 'AB', 'L1_0', 3.85)
        self.assertEqual(len(fept.species), 2)
        self.assertIn('Fe', fept.species)
        self.assertIn('Pt', fept.species)
        self.assertAlmostEqual(fept.lattice.a, 3.85, places=5)

    def test_generate_intermetallic_wrong_element_count_raises(self):
        with self.assertRaises(ValueError):
            generate_intermetallic(['Fe'], 'AB', 'L1_2', 3.85)

    def test_generate_random_alloy_small_cell_deterministic(self):
        base = Crystal(
            ['Al', 'Al', 'Al'],
            [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5]],
            Lattice.cubic(4.0),
        )
        alloy = generate_random_alloy(base, ['Cu'], 'Al', [0.5], seed=1)
        cu_count = sum(1 for s in alloy.species if s == 'Cu')
        self.assertLessEqual(cu_count, 3)
        self.assertIn(cu_count, (1, 2))
        al_count = sum(1 for s in alloy.species if s == 'Al')
        self.assertGreaterEqual(al_count, 1)

    def test_generate_ordered_alloy_negative_index_raises(self):
        base = Crystal(
            ['A', 'A', 'A', 'A'],
            [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
            Lattice.cubic(4.0),
        )
        with self.assertRaises(ValueError):
            generate_ordered_alloy(base, {-1: 'Cu'})

if __name__ == '__main__':
    unittest.main()
