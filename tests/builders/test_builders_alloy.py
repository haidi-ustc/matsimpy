"""Tests for alloy builders."""
import unittest
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.alloy import (
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


class TestOrderedAlloy(unittest.TestCase):
    """Tests for ordered alloy generation."""
    
    def setUp(self):
        """Set up test base structure."""
        self.base = Crystal(
            ['A', 'A', 'A', 'A'],
            [[0,0,0], [0.5,0.5,0], [0.5,0,0.5], [0,0.5,0.5]],
            Lattice.cubic(4.0)
        )
    
    
    
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


if __name__ == '__main__':
    unittest.main()
