"""Comprehensive tests for Crystal class."""
import unittest
import numpy as np
from pathlib import Path

from matsimpy.core import Crystal, Lattice
from matsimpy.io import read

class TestCrystalComprehensive(unittest.TestCase):
    """Comprehensive tests for Crystal class."""
    
    
    

    

    
    
    
    
    
    
    

    
    def test_crystal_from_file_poscar(self):
        """Test reading POSCAR file using from_file."""
        poscar_file = Path(__file__).parent / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = read(str(poscar_file))
            self.assertIsInstance(crystal, Crystal)
            self.assertGreater(len(crystal), 0)
    
    
    
    
    
    
    
    
    
    def test_crystal_wrap_positive(self):
        """Test wrapping positive fractional coordinates > 1."""
        species = ['Fe', 'O']
        positions = [[1.5, 2.3, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        result = crystal.wrap()
        np.testing.assert_array_almost_equal(
            result.frac_positions[0], [0.5, 0.3, 0.5], decimal=6
        )
        np.testing.assert_array_almost_equal(
            result.frac_positions[1], [0.2, 0.2, 0.2], decimal=6
        )
        # Verify sites are updated
        np.testing.assert_array_almost_equal(
            result.sites[0].frac_position, [0.5, 0.3, 0.5], decimal=6
        )
    
    
    
    
    
    
    def test_crystal_wrap_original_unchanged(self):
        species = ['Fe', 'O']
        positions = [[1.5, -0.3, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        original_frac = crystal.frac_positions.copy()
        result = crystal.wrap()
        self.assertIsNot(result, crystal)
        self.assertTrue(np.allclose(crystal.frac_positions, original_frac))
    

if __name__ == '__main__':
    unittest.main()
