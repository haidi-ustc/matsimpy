"""Tests for defect structure builders."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.defects import (
    create_vacancy,
    create_interstitial,
    create_substitution,
    create_frenkel,
    create_schottky,
    create_antisite
)
from matsimpy.builders.bulk import from_prototype

class TestVacancy(unittest.TestCase):
    """Tests for create_vacancy function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use diamond structure instead of FCC since FCC primitive has only 1 atom
        self.fcc = from_prototype('diamond', 'Si', 5.43)
    
    def test_create_single_vacancy(self):
        """Test creating a single vacancy."""
        with_vacancy = create_vacancy(self.fcc, 0)
        
        self.assertIsInstance(with_vacancy, Crystal)
        self.assertEqual(len(with_vacancy.species), len(self.fcc.species) - 1)
        self.assertEqual(len(with_vacancy.positions), len(self.fcc.positions) - 1)
    
    def test_create_multiple_vacancies(self):
        """Test creating multiple vacancies."""
        with_vacancies = create_vacancy(self.fcc, [0, 1])
        
        self.assertIsInstance(with_vacancies, Crystal)
        self.assertEqual(len(with_vacancies.species), len(self.fcc.species) - 2)
    
    def test_create_vacancy_returns_new_object(self):
        """Test that create_vacancy returns a new object."""
        original_count = len(self.fcc.species)
        result = create_vacancy(self.fcc, 0)

        # Original unchanged
        self.assertEqual(len(self.fcc.species), original_count)
        # Result has one fewer atom
        self.assertEqual(len(result.species), original_count - 1)
    
    def test_create_vacancy_invalid_index(self):
        """Test creating vacancy with invalid index."""
        with self.assertRaises(IndexError):
            create_vacancy(self.fcc, 1000)
    
    def test_create_vacancy_duplicate_indices(self):
        """Test creating vacancy with duplicate indices."""
        with_vacancy = create_vacancy(self.fcc, [0, 0, 1])
        
        # Should only remove 2 unique atoms
        self.assertEqual(len(with_vacancy.species), len(self.fcc.species) - 2)

class TestInterstitial(unittest.TestCase):
    """Tests for create_interstitial function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use diamond structure instead of FCC since FCC primitive has only 1 atom
        self.fcc = from_prototype('diamond', 'Si', 5.43)
    
    def test_create_single_interstitial(self):
        """Test creating a single interstitial."""
        with_interstitial = create_interstitial(self.fcc, 'H', [0.5, 0.5, 0.5])
        
        self.assertIsInstance(with_interstitial, Crystal)
        self.assertEqual(len(with_interstitial.species), len(self.fcc.species) + 1)
        self.assertIn('H', with_interstitial.species)
    
    def test_create_multiple_interstitials(self):
        """Test creating multiple interstitials."""
        # Use positions that don't conflict with existing atoms (diamond has atoms at [0,0,0] and [0.25,0.25,0.25])
        with_interstitials = create_interstitial(
            self.fcc, ['H', 'H'], [[0.5, 0.5, 0.5], [0.1, 0.1, 0.1]]
        )
        
        self.assertIsInstance(with_interstitials, Crystal)
        self.assertEqual(len(with_interstitials.species), len(self.fcc.species) + 2)
        self.assertEqual(with_interstitials.species.count('H'), self.fcc.species.count('H') + 2)
    
    def test_create_interstitial_position_wrapping(self):
        """Test that positions are wrapped to [0, 1)."""
        with_interstitial = create_interstitial(self.fcc, 'H', [1.5, 1.5, 1.5])
        
        # Position should be wrapped to fractional [0.5, 0.5, 0.5]
        pos = with_interstitial.frac_positions[-1]
        self.assertAlmostEqual(pos[0], 0.5, places=5)
    
    def test_create_interstitial_mismatch(self):
        """Test creating interstitial with mismatched species/positions."""
        with self.assertRaises(ValueError):
            create_interstitial(self.fcc, ['H', 'H'], [[0.5, 0.5, 0.5]])

class TestSubstitution(unittest.TestCase):
    """Tests for create_substitution function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use diamond structure instead of FCC since FCC primitive has only 1 atom
        self.fcc = from_prototype('diamond', 'Si', 5.43)
    
    def test_create_single_substitution(self):
        """Test creating a single substitution."""
        doped = create_substitution(self.fcc, 0, 'Ni')
        
        self.assertIsInstance(doped, Crystal)
        self.assertEqual(len(doped.species), len(self.fcc.species))
        self.assertEqual(doped.species[0], 'Ni')
        self.assertEqual(doped.species.count('Ni'), 1)
        # Changed from 'Cu' to 'Si' since we're using diamond structure with Si
        self.assertEqual(doped.species.count('Si'), len(self.fcc.species) - 1)
    
    def test_create_multiple_substitutions(self):
        """Test creating multiple substitutions."""
        multi_doped = create_substitution(self.fcc, [0, 1], ['Ni', 'Zn'])
        
        self.assertIsInstance(multi_doped, Crystal)
        self.assertEqual(len(multi_doped.species), len(self.fcc.species))
        self.assertEqual(multi_doped.species[0], 'Ni')
        self.assertEqual(multi_doped.species[1], 'Zn')
    
    def test_create_substitution_mismatch(self):
        """Test creating substitution with mismatched indices/species."""
        with self.assertRaises(ValueError):
            create_substitution(self.fcc, [0, 1], ['Ni'])
    
    def test_create_substitution_invalid_index(self):
        """Test creating substitution with invalid index."""
        with self.assertRaises(IndexError):
            create_substitution(self.fcc, 1000, 'Ni')

class TestFrenkel(unittest.TestCase):
    """Tests for create_frenkel function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
    
    def test_create_frenkel(self):
        """Test creating a Frenkel defect."""
        # Use a position that doesn't conflict with existing atoms (rocksalt has atoms at [0,0,0] and [0.5,0.5,0.5])
        with_frenkel = create_frenkel(self.nacl, 0, [0.25, 0.25, 0.25])
        
        self.assertIsInstance(with_frenkel, Crystal)
        # Should have same number of atoms (atom moved, not removed)
        self.assertEqual(len(with_frenkel.species), len(self.nacl.species))
        
        # Check that atom was moved
        original_pos = self.nacl.positions[0]
        new_pos = with_frenkel.positions[-1]  # Last position should be the interstitial
        self.assertFalse(np.allclose(original_pos, new_pos, atol=0.01))
    
    def test_create_frenkel_default_position(self):
        """Test creating Frenkel defect with default position."""
        with_frenkel = create_frenkel(self.nacl, 0)
        
        self.assertIsInstance(with_frenkel, Crystal)
        self.assertEqual(len(with_frenkel.species), len(self.nacl.species))
    
    def test_create_frenkel_invalid_index(self):
        """Test creating Frenkel defect with invalid index."""
        with self.assertRaises(IndexError):
            create_frenkel(self.nacl, 1000)

class TestSchottky(unittest.TestCase):
    """Tests for create_schottky function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
    
    def test_create_schottky_random(self):
        """Test creating Schottky defect with random selection."""
        with_schottky = create_schottky(self.nacl, num_vacancies=2)
        
        self.assertIsInstance(with_schottky, Crystal)
        self.assertEqual(len(with_schottky.species), len(self.nacl.species) - 2)
    
    def test_create_schottky_specific_indices(self):
        """Test creating Schottky defect with specific indices."""
        with_schottky = create_schottky(self.nacl, indices=[0, 1], num_vacancies=2)
        
        self.assertIsInstance(with_schottky, Crystal)
        self.assertEqual(len(with_schottky.species), len(self.nacl.species) - 2)
    
    def test_create_schottky_mismatch(self):
        """Test creating Schottky defect with mismatched indices."""
        with self.assertRaises(ValueError):
            create_schottky(self.nacl, indices=[0, 1], num_vacancies=3)
    
    def test_create_schottky_too_many(self):
        """Test creating Schottky defect with too many vacancies."""
        with self.assertRaises(ValueError):
            create_schottky(self.nacl, num_vacancies=10000)

class TestAntisite(unittest.TestCase):
    """Tests for create_antisite function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.gan = from_prototype('zincblende', ['Ga', 'N'], 4.5)
    
    def test_create_antisite(self):
        """Test creating an antisite defect."""
        with_antisite = create_antisite(self.gan, 0, 1)
        
        self.assertIsInstance(with_antisite, Crystal)
        self.assertEqual(len(with_antisite.species), len(self.gan.species))
        
        # Check that species were swapped
        self.assertEqual(with_antisite.species[0], self.gan.species[1])
        self.assertEqual(with_antisite.species[1], self.gan.species[0])
        # Antisite swaps occupancy on fixed sites; coordinates should not move.
        np.testing.assert_array_almost_equal(with_antisite.positions, self.gan.positions)
    
    def test_create_antisite_same_index(self):
        """Test creating antisite defect with same index."""
        with self.assertRaises(ValueError):
            create_antisite(self.gan, 0, 0)
    
    def test_create_antisite_invalid_index(self):
        """Test creating antisite defect with invalid index."""
        with self.assertRaises(IndexError):
            create_antisite(self.gan, 0, 1000)

if __name__ == '__main__':
    unittest.main()
