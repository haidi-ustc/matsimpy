"""Quick test to verify all fixes work."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import numpy as np
from matsimpy.core import Crystal, Lattice, Molecule


def test_crystal_operations():
    """Test basic crystal operations."""
    species = ['Si', 'O', 'O']
    positions = [[0, 0, 0], [1.5, 1.5, 1.5], [2.0, 2.0, 2.0]]
    lattice = Lattice.cubic(10.0)
    
    crystal = Crystal(species, positions, lattice)
    assert len(crystal) == 3
    assert crystal.volume > 0
    
    # Test neighbor finding
    neighbors = crystal.get_neighbor_list(5.0)
    assert isinstance(neighbors, dict)
    assert len(neighbors) == 3
    
    print("✓ Crystal operations work!")


def test_molecule_to_crystal():
    """Test molecule to crystal conversion."""
    species = ['C', 'O']
    positions = [[0, 0, 0], [1.4, 0, 0]]
    
    molecule = Molecule(species, positions)
    crystal = molecule.to_crystal()
    
    assert isinstance(crystal, Crystal)
    assert len(crystal) == 2
    assert crystal.lattice is not None
    
    print("✓ Molecule to crystal conversion works!")


def test_property_caching():
    """Test that caching works."""
    species = ['Si'] * 10
    positions = np.random.rand(10, 3)
    lattice = Lattice.cubic(10.0)
    crystal = Crystal(species, positions, lattice)
    
    # First call should compute
    formula1 = crystal.get_formula()
    
    # Second call should use cache
    import time
    start = time.time()
    formula2 = crystal.get_formula()
    elapsed = time.time() - start
    
    assert formula1 == formula2
    assert elapsed < 0.001  # Should be very fast
    
    print("✓ Property caching works!")


def test_species_immutability():
    """Test that species is immutable tuple."""
    species = ['Si', 'O']
    positions = [[0, 0, 0], [1.0, 1.0, 1.0]]
    lattice = Lattice.cubic(10.0)
    crystal = Crystal(species, positions, lattice)
    
    assert isinstance(crystal.species, tuple)
    print("✓ Species immutability works!")


def test_lattice_inverse_caching():
    """Test that lattice inverse matrix is cached."""
    lattice = Lattice.cubic(10.0)
    
    # First call computes
    inv1 = lattice.inv_matrix
    
    # Second call should use cache
    import time
    start = time.time()
    inv2 = lattice.inv_matrix
    elapsed = time.time() - start
    
    assert np.allclose(inv1, inv2)
    assert elapsed < 0.0001  # Should be very fast
    
    print("✓ Lattice inverse caching works!")


if __name__ == '__main__':
    print("Running quick fix tests...\n")
    test_crystal_operations()
    test_molecule_to_crystal()
    test_property_caching()
    test_species_immutability()
    test_lattice_inverse_caching()
    print("\n✅ All quick fixes verified!")

