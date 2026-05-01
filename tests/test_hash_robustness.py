"""Tests for robust hash implementation with floating-point rounding."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice

class TestHashRounding(unittest.TestCase):
    """Test that hash properly rounds positions for consistency."""
    
    def test_hash_identical_structures(self):
        """Test that identical structures have the same hash."""
        mol1 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        mol2 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_hash_with_floating_point_noise(self):
        """Test that structures with tiny floating-point differences hash the same."""
        # Create structures with positions that differ by less than 1e-8
        mol1 = Molecule(['C', 'O'], [[0.0, 0.0, 0.0], [1.2, 0.0, 0.0]])
        mol2 = Molecule(['C', 'O'], [[0.0, 0.0, 1e-10], [1.2, 1e-10, 0.0]])
        
        # Should hash to the same value (rounded to 8 decimals)
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_hash_with_larger_differences(self):
        """Test that structures with differences > 1e-8 hash differently."""
        mol1 = Molecule(['C', 'O'], [[0.0, 0.0, 0.0], [1.2, 0.0, 0.0]])
        mol2 = Molecule(['C', 'O'], [[0.0, 0.0, 0.0], [1.2, 1e-7, 0.0]])
        
        # Should hash to different values (difference is significant)
        self.assertNotEqual(hash(mol1), hash(mol2))
    
    def test_hash_rounding_consistency(self):
        """Test that positions round consistently."""
        # These should round to the same value at 8 decimals
        mol1 = Molecule(['C'], [[1.123456785, 0, 0]])
        mol2 = Molecule(['C'], [[1.123456784, 0, 0]])
        
        # Both round to 1.12345678, should have same hash
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_hash_boundary_case_rounding_down(self):
        """Test rounding at boundary (4 in 9th decimal place)."""
        # 1.200000004 rounds to 1.20000000
        mol1 = Molecule(['C'], [[1.200000004, 0, 0]])
        mol2 = Molecule(['C'], [[1.20000000, 0, 0]])
        
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_hash_different_species_different_hash(self):
        """Test that different species result in different hash."""
        mol1 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        mol2 = Molecule(['N', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        self.assertNotEqual(hash(mol1), hash(mol2))
    
    def test_hash_different_positions_different_hash(self):
        """Test that different positions result in different hash."""
        mol1 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        mol2 = Molecule(['C', 'O'], [[0, 0, 0], [1.3, 0, 0]])
        
        self.assertNotEqual(hash(mol1), hash(mol2))

class TestHashCrystal(unittest.TestCase):
    """Test hash for Crystal structures with lattice."""
    
    def test_hash_identical_crystals(self):
        """Test that identical crystals have the same hash."""
        lattice = Lattice.cubic(10.0)
        crystal1 = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)
        crystal2 = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], lattice)
        
        self.assertEqual(hash(crystal1), hash(crystal2))
    
    def test_hash_with_floating_point_noise_crystal(self):
        """Test that crystals with tiny position differences hash the same."""
        lattice = Lattice.cubic(10.0)
        crystal1 = Crystal(['Si', 'O'], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]], lattice)
        crystal2 = Crystal(['Si', 'O'], [[1e-10, 0.0, 0.0], [0.5, 0.5, 0.5 + 1e-10]], lattice)
        
        self.assertEqual(hash(crystal1), hash(crystal2))
    
    def test_hash_different_lattice_different_hash(self):
        """Test that different lattices result in different hash."""
        lattice1 = Lattice.cubic(10.0)
        lattice2 = Lattice.cubic(10.5)
        crystal1 = Crystal(['Si'], [[0, 0, 0]], lattice1)
        crystal2 = Crystal(['Si'], [[0, 0, 0]], lattice2)
        
        self.assertNotEqual(hash(crystal1), hash(crystal2))
    
    def test_hash_same_lattice_params_same_hash(self):
        """Test that crystals with identical lattice parameters hash the same."""
        lattice1 = Lattice.cubic(10.0)
        lattice2 = Lattice.cubic(10.0)
        crystal1 = Crystal(['Si'], [[0, 0, 0]], lattice1)
        crystal2 = Crystal(['Si'], [[0, 0, 0]], lattice2)
        
        self.assertEqual(hash(crystal1), hash(crystal2))

class TestHashUseCases(unittest.TestCase):
    """Test hash in practical use cases."""
    
    def test_hash_in_set(self):
        """Test that structures can be used in sets."""
        mol1 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        mol2 = Molecule(['C', 'O'], [[0, 0, 1e-10], [1.2, 1e-10, 0]])
        mol3 = Molecule(['C', 'N'], [[0, 0, 0], [1.2, 0, 0]])
        
        # mol1 and mol2 should be treated as same (hash equal)
        # mol3 is different
        structure_set = {mol1, mol2, mol3}
        
        # Set should contain 2 unique structures (mol1==mol2, mol3 different)
        self.assertEqual(len(structure_set), 2)
    
    def test_hash_in_dict(self):
        """Test that structures can be used as dict keys."""
        mol1 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        mol2 = Molecule(['C', 'O'], [[0, 0, 1e-10], [1.2, 1e-10, 0]])
        
        structure_dict = {mol1: "structure1"}
        
        # Should be able to access with mol2 (same hash)
        structure_dict[mol2] = "structure2"
        
        # Should have overwritten the value
        self.assertEqual(len(structure_dict), 1)
        self.assertEqual(structure_dict[mol1], "structure2")
    
    def test_hash_after_modification(self):
        """Test that hash changes after modifying structure."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        hash1 = hash(mol)

        # Modify structure (returns new object)
        mol2 = mol.add_atom('H', [2.0, 0, 0])
        hash2 = hash(mol2)

        # Hash should be different
        self.assertNotEqual(hash1, hash2)

    def test_hash_after_substitution(self):
        """Test that hash changes after substitution."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        hash1 = hash(mol)

        # Substitute atom (returns new object)
        mol2 = mol.substitute(0, 'N')
        hash2 = hash(mol2)

        # Hash should be different
        self.assertNotEqual(hash1, hash2)
    
    def test_hash_consistency_after_copy(self):
        """Test that copied structure has same hash."""
        mol1 = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        mol2 = mol1.copy()
        
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_hash_with_numpy_operations(self):
        """Test hash after numpy operations that may introduce noise."""
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(['Si'], [[0.5, 0.5, 0.5]], lattice)
        
        # Create another crystal with positions computed via numpy operations
        # that might introduce tiny floating-point errors
        positions = np.array([[0.5, 0.5, 0.5]])
        positions = positions * 2.0 / 2.0  # Should be identity but may have noise
        crystal2 = Crystal(['Si'], positions.tolist(), lattice)
        
        # Should have same hash despite potential floating-point noise
        self.assertEqual(hash(crystal), hash(crystal2))

class TestHashPrecision(unittest.TestCase):
    """Test the precision level of hash rounding."""
    
    def test_precision_at_8_decimals(self):
        """Test that 8 decimal places are preserved."""
        # These differ at 8th decimal
        mol1 = Molecule(['C'], [[1.12345678, 0, 0]])
        mol2 = Molecule(['C'], [[1.12345679, 0, 0]])
        
        # Should have different hashes
        self.assertNotEqual(hash(mol1), hash(mol2))
    
    def test_precision_beyond_8_decimals_ignored(self):
        """Test that differences beyond 8 decimals are ignored."""
        # These differ at 9th decimal
        mol1 = Molecule(['C'], [[1.123456789, 0, 0]])
        mol2 = Molecule(['C'], [[1.123456788, 0, 0]])
        
        # Should have same hash (rounded to 8 decimals)
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_negative_positions(self):
        """Test that negative positions are handled correctly."""
        mol1 = Molecule(['C'], [[-1.2, -0.5, -0.3]])
        mol2 = Molecule(['C'], [[-1.2, -0.5, -0.3 + 1e-10]])
        
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_zero_positions(self):
        """Test that zero positions are handled correctly."""
        mol1 = Molecule(['C'], [[0.0, 0.0, 0.0]])
        mol2 = Molecule(['C'], [[1e-10, 1e-10, 1e-10]])
        
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_large_positions(self):
        """Test that large position values are handled correctly."""
        mol1 = Molecule(['C'], [[1000.12345678, 2000.0, 3000.0]])
        mol2 = Molecule(['C'], [[1000.12345678 + 1e-10, 2000.0, 3000.0]])
        
        self.assertEqual(hash(mol1), hash(mol2))

class TestHashEdgeCases(unittest.TestCase):
    """Test edge cases for hash implementation."""
    
    def test_hash_single_atom(self):
        """Test hash for single atom structure."""
        mol1 = Molecule(['C'], [[0, 0, 0]])
        mol2 = Molecule(['C'], [[1e-10, 0, 0]])
        
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_hash_many_atoms(self):
        """Test hash for structure with many atoms."""
        n = 100
        positions1 = [[i * 0.1, 0, 0] for i in range(n)]
        positions2 = [[i * 0.1 + 1e-10, 1e-10, 0] for i in range(n)]
        
        mol1 = Molecule(['C'] * n, positions1)
        mol2 = Molecule(['C'] * n, positions2)
        
        self.assertEqual(hash(mol1), hash(mol2))
    
    def test_hash_deterministic(self):
        """Test that hash is deterministic (same structure always gives same hash)."""
        mol = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        hash1 = hash(mol)
        hash2 = hash(mol)
        hash3 = hash(mol)
        
        self.assertEqual(hash1, hash2)
        self.assertEqual(hash2, hash3)

if __name__ == '__main__':
    unittest.main()

