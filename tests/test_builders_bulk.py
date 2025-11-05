"""Tests for bulk crystal builders."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype, list_prototypes, CRYSTAL_PROTOTYPES


class TestPrototypeBuilder(unittest.TestCase):
    """Tests for prototype-based bulk crystal generation."""
    
    def test_from_prototype_fcc(self):
        """Test FCC structure generation."""
        fcc_cu = from_prototype('fcc', 'Cu', 3.61)
        
        self.assertEqual(len(fcc_cu.species), 4)  # FCC has 4 atoms
        self.assertAlmostEqual(fcc_cu.lattice.a, 3.61, places=5)
        self.assertEqual(fcc_cu.species[0], 'Cu')
    
    def test_from_prototype_bcc(self):
        """Test BCC structure generation."""
        bcc_fe = from_prototype('bcc', 'Fe', 2.87)
        
        self.assertEqual(len(bcc_fe.species), 2)  # BCC has 2 atoms
        self.assertAlmostEqual(bcc_fe.lattice.a, 2.87, places=5)
    
    def test_from_prototype_diamond(self):
        """Test diamond structure generation."""
        diamond_si = from_prototype('diamond', 'Si', 5.43)
        
        self.assertEqual(len(diamond_si.species), 2)
        self.assertEqual(diamond_si.species[0], 'Si')
        self.assertEqual(diamond_si.species[1], 'Si')
    
    def test_from_prototype_rocksalt(self):
        """Test rocksalt structure generation."""
        nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
        
        self.assertEqual(len(nacl.species), 2)
        self.assertIn('Na', nacl.species)
        self.assertIn('Cl', nacl.species)
    
    def test_from_prototype_zincblende(self):
        """Test zincblende structure generation."""
        gaas = from_prototype('zincblende', ['Ga', 'As'], 5.65)
        
        self.assertEqual(len(gaas.species), 2)
        self.assertIn('Ga', gaas.species)
        self.assertIn('As', gaas.species)
    
    def test_from_prototype_wurtzite(self):
        """Test wurtzite structure generation."""
        gan = from_prototype('wurtzite', ['Ga', 'N'], [3.19, 5.19])
        
        self.assertEqual(len(gan.species), 2)
        self.assertIn('Ga', gan.species)
        self.assertIn('N', gan.species)
        # Check hexagonal lattice
        self.assertAlmostEqual(gan.lattice.a, 3.19, places=2)
        self.assertAlmostEqual(gan.lattice.c, 5.19, places=2)
    
    def test_from_prototype_perovskite(self):
        """Test perovskite structure generation."""
        batio3 = from_prototype('perovskite', ['Ba', 'Ti', 'O'], 4.0)
        
        self.assertEqual(len(batio3.species), 5)  # ABO3 has 5 atoms
        self.assertEqual(batio3.species[0], 'Ba')
        self.assertEqual(batio3.species[1], 'Ti')
    
    def test_from_prototype_hcp(self):
        """Test HCP structure generation."""
        hcp_mg = from_prototype('hcp', 'Mg', [3.21, 5.21])
        
        self.assertEqual(len(hcp_mg.species), 2)
        self.assertEqual(hcp_mg.species[0], 'Mg')
    
    def test_from_prototype_invalid(self):
        """Test invalid prototype name."""
        with self.assertRaises(ValueError):
            from_prototype('invalid_prototype', 'Cu', 3.61)
    
    def test_from_prototype_wrong_species_count(self):
        """Test with wrong number of species."""
        with self.assertRaises(ValueError):
            # Rocksalt needs 2 species, providing 1
            from_prototype('rocksalt', 'Na', 5.64)
    
    def test_list_prototypes(self):
        """Test listing available prototypes."""
        prototypes = list_prototypes()
        
        self.assertIsInstance(prototypes, dict)
        self.assertIn('fcc', prototypes)
        self.assertIn('bcc', prototypes)
        self.assertIn('diamond', prototypes)
        self.assertGreater(len(prototypes), 5)
    
    def test_crystal_prototypes_constant(self):
        """Test CRYSTAL_PROTOTYPES constant."""
        self.assertIsInstance(CRYSTAL_PROTOTYPES, dict)
        self.assertIn('fcc', CRYSTAL_PROTOTYPES)
        self.assertIn('description', CRYSTAL_PROTOTYPES['fcc'])
        self.assertIn('positions', CRYSTAL_PROTOTYPES['fcc'])


class TestPrototypeProperties(unittest.TestCase):
    """Test properties of generated prototypes."""
    
    def test_fcc_volume(self):
        """Test FCC volume calculation."""
        fcc = from_prototype('fcc', 'Cu', 3.61)
        expected_volume = 3.61 ** 3
        self.assertAlmostEqual(fcc.volume, expected_volume, places=2)
    
    def test_bcc_formula(self):
        """Test BCC formula."""
        bcc = from_prototype('bcc', 'Fe', 2.87)
        self.assertEqual(bcc.formula, 'Fe2')
    
    def test_rocksalt_formula(self):
        """Test rocksalt formula."""
        nacl = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
        # Should have equal amounts of Na and Cl
        self.assertIn('Na', str(nacl.formula))
        self.assertIn('Cl', str(nacl.formula))
    
    def test_diamond_positions(self):
        """Test diamond structure has correct positions."""
        diamond = from_prototype('diamond', 'C', 3.57)
        
        # Check that positions are different
        self.assertFalse(np.allclose(diamond.positions[0], diamond.positions[1]))


if __name__ == '__main__':
    unittest.main()

