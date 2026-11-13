"""Tests for defect structure builders."""
import unittest
import numpy as np
from matsimpy.core import Crystal
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
    

class TestInterstitial(unittest.TestCase):
    """Tests for create_interstitial function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use diamond structure instead of FCC since FCC primitive has only 1 atom
        self.fcc = from_prototype('diamond', 'Si', 5.43)
    
    
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

    def test_create_interstitial_wraps_only_periodic_axes(self):
        """Positions in the vacuum of a slab used to be wrapped back into the slab."""
        from matsimpy.core import Lattice

        slab = Crystal(['Cu'], [[0, 0, 0.5]], Lattice.tetragonal(2.55, 20.0), pbc=(True, True, False))
        above = create_interstitial(slab, 'H', [1.5, 0.5, 0.6])
        np.testing.assert_allclose(above.frac_positions[-1], [0.5, 0.5, 0.6])
        outside = create_interstitial(slab, 'H', [0.5, 0.5, 1.2])
        self.assertAlmostEqual(outside.frac_positions[-1][2], 1.2)

    def test_create_interstitial_rejects_overlap(self):
        with self.assertRaisesRegex(ValueError, "from an existing atom"):
            create_interstitial(self.fcc, 'H', [1.0, 0.0, 0.01])

class TestSubstitution(unittest.TestCase):
    """Tests for create_substitution function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use diamond structure instead of FCC since FCC primitive has only 1 atom
        self.fcc = from_prototype('diamond', 'Si', 5.43)
    
    
    
    def test_create_substitution_mismatch(self):
        """Test creating substitution with mismatched indices/species."""
        with self.assertRaises(ValueError):
            create_substitution(self.fcc, [0, 1], ['Ni'])
    
    def test_create_substitution_invalid_index(self):
        """Test creating substitution with invalid index."""
        with self.assertRaises(IndexError):
            create_substitution(self.fcc, 1000, 'Ni')

    def test_create_substitution_accepts_numpy_index(self):
        """A numpy integer index (e.g. from np.where) used to raise TypeError."""
        doped = create_substitution(self.fcc, np.int64(1), 'Ge')
        self.assertEqual(doped.species[1], 'Ge')

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
    
    
    def test_create_frenkel_invalid_index(self):
        """Test creating Frenkel defect with invalid index."""
        with self.assertRaises(IndexError):
            create_frenkel(self.nacl, 1000, [0.25, 0.25, 0.25])

    def test_create_frenkel_requires_a_free_site(self):
        """The old default moved the atom by a random, unseeded 0.1 fractional step."""
        with self.assertRaises(TypeError):
            create_frenkel(self.nacl, 0)
        with self.assertRaisesRegex(ValueError, "from an existing atom"):
            create_frenkel(self.nacl, 0, [0.5, 0.5, 0.52])

class TestSchottky(unittest.TestCase):
    """Tests for create_schottky function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
    
    
    
    def test_create_schottky_removes_a_formula_unit(self):
        """The old default removed two random atoms, often both Na or both Cl."""
        from matsimpy.transformation.structural import make_supercell

        cell = make_supercell(self.nacl, [2, 2, 2])
        for seed in range(5):
            defect = create_schottky(cell, seed=seed)
            self.assertEqual(defect.species.count('Na'), 7)
            self.assertEqual(defect.species.count('Cl'), 7)
        self.assertEqual(create_schottky(cell, seed=3).frac_positions.tolist(),
                         create_schottky(cell, seed=3).frac_positions.tolist())

    def test_create_schottky_rejects_non_stoichiometric_indices(self):
        na = [i for i, s in enumerate(self.nacl.species) if s == 'Na']
        with self.assertRaisesRegex(ValueError, "formula units"):
            create_schottky(self.nacl, indices=na[:1])
        with self.assertRaisesRegex(ValueError, "every atom"):
            create_schottky(self.nacl, indices=list(range(len(self.nacl))))

    def test_create_schottky_rejects_unknown_keyword(self):
        with self.assertRaises(TypeError):
            create_schottky(self.nacl, num_vacancies=2)

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
    
    def test_create_antisite_rejects_same_species(self):
        """Swapping two Ga atoms used to return an unchanged crystal as an 'antisite'."""
        from matsimpy.transformation.structural import make_supercell

        cell = make_supercell(self.gan, [2, 1, 1])
        ga = [i for i, s in enumerate(cell.species) if s == 'Ga']
        with self.assertRaisesRegex(ValueError, "different species"):
            create_antisite(cell, ga[0], ga[1])

    def test_create_antisite_invalid_index(self):
        """Test creating antisite defect with invalid index."""
        with self.assertRaises(IndexError):
            create_antisite(self.gan, 0, 1000)

if __name__ == '__main__':
    unittest.main()
