"""Tests for bulk crystal builders."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk import from_prototype, list_prototypes, CRYSTAL_PROTOTYPES

class TestPrototypeBuilder(unittest.TestCase):
    """Tests for prototype-based bulk crystal generation."""
    
    def test_from_prototype_fcc(self):
        """Test FCC structure generation (primitive cell)."""
        fcc_cu = from_prototype('fcc', 'Cu', 3.61)
        
        self.assertEqual(len(fcc_cu.species), 1)  # FCC primitive has 1 atom
        # Primitive cell: a = a_cubic / sqrt(2)
        expected_a = 3.61 / np.sqrt(2)
        self.assertAlmostEqual(fcc_cu.lattice.a, expected_a, places=5)
        self.assertAlmostEqual(fcc_cu.lattice.alpha, 60.0, places=2)  # Rhombohedral angle
        self.assertEqual(fcc_cu.species[0], 'Cu')
    
    def test_from_prototype_bcc(self):
        """Test BCC structure generation (primitive cell)."""
        bcc_fe = from_prototype('bcc', 'Fe', 2.87)
        
        self.assertEqual(len(bcc_fe.species), 2)  # BCC primitive has 2 atoms
        # Primitive cell: a = a_cubic * sqrt(3) / 2
        expected_a = 2.87 * np.sqrt(3) / 2
        self.assertAlmostEqual(bcc_fe.lattice.a, expected_a, places=5)
        # BCC primitive is rhombohedral with alpha ≈ 109.47°
        import math
        expected_alpha = math.acos(-1/3) * 180 / math.pi
        self.assertAlmostEqual(bcc_fe.lattice.alpha, expected_alpha, places=2)
    
    def test_from_prototype_diamond(self):
        """Test diamond structure generation (primitive cell)."""
        diamond_si = from_prototype('diamond', 'Si', 5.43)
        
        self.assertEqual(len(diamond_si.species), 2)  # Diamond primitive has 2 atoms
        self.assertEqual(diamond_si.species[0], 'Si')
        self.assertEqual(diamond_si.species[1], 'Si')
        # Primitive cell: a = a_cubic / sqrt(2), alpha = 60°
        expected_a = 5.43 / np.sqrt(2)
        self.assertAlmostEqual(diamond_si.lattice.a, expected_a, places=5)
        self.assertAlmostEqual(diamond_si.lattice.alpha, 60.0, places=2)
    
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
        """Test FCC volume calculation (primitive cell)."""
        fcc = from_prototype('fcc', 'Cu', 3.61)
        # Primitive cell volume = a^3 * sqrt(1 - 3*cos^2(alpha) + 2*cos^3(alpha))
        # For FCC primitive: alpha = 60°, a = a_cubic / sqrt(2)
        # Volume = a^3 * sqrt(1 - 3*(1/2)^2 + 2*(1/2)^3) = a^3 * sqrt(1/2)
        a_prim = 3.61 / np.sqrt(2)
        alpha_rad = np.radians(60.0)
        expected_volume = a_prim ** 3 * np.sqrt(1 - 3 * np.cos(alpha_rad)**2 + 2 * np.cos(alpha_rad)**3)
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
    
    def test_binary_compound_formula(self):
        """Test binary compound formula parsing (e.g., 'SiC')."""
        # Test diamond with SiC
        sic = from_prototype('diamond', 'SiC', 5.2)
        self.assertEqual(len(sic.species), 2)
        self.assertIn('Si', sic.species)
        self.assertIn('C', sic.species)
        
        # Test zincblende with GaN
        gan = from_prototype('zincblende', 'GaN', 4.5)
        self.assertEqual(len(gan.species), 2)
        self.assertIn('Ga', gan.species)
        self.assertIn('N', gan.species)
        
        # Test rocksalt with NaCl
        nacl = from_prototype('rocksalt', 'NaCl', 5.64)
        self.assertEqual(len(nacl.species), 2)
        self.assertIn('Na', nacl.species)
        self.assertIn('Cl', nacl.species)

if __name__ == '__main__':
    unittest.main()

