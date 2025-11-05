"""Performance benchmarks for structure operations."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import numpy as np
from matsimpy.core import Crystal, Lattice


def benchmark_structure_creation():
    """Benchmark structure creation."""
    print("Structure Creation Benchmarks:")
    print("-" * 50)
    sizes = [10, 100, 1000, 10000]
    
    for size in sizes:
        species = ['Si'] * size
        positions = np.random.rand(size, 3)
        lattice = Lattice.cubic(10.0)
        
        start = time.time()
        crystal = Crystal(species, positions, lattice)
        elapsed = time.time() - start
        
        print(f"Size {size:5d}: {elapsed*1000:8.2f} ms")
    print()


def benchmark_neighbor_finding():
    """Benchmark neighbor finding."""
    print("Neighbor Finding Benchmarks:")
    print("-" * 50)
    sizes = [10, 100, 1000]
    cutoff = 5.0
    
    for size in sizes:
        species = ['Si'] * size
        positions = np.random.rand(size, 3) * 10
        lattice = Lattice.cubic(20.0)
        crystal = Crystal(species, positions, lattice)
        
        start = time.time()
        neighbors = crystal.get_neighbor_list(cutoff)
        elapsed = time.time() - start
        
        n_neighbors = sum(len(v) for v in neighbors.values())
        print(f"Size {size:5d}: {elapsed*1000:8.2f} ms, "
              f"{n_neighbors:5d} neighbors")
    print()


def benchmark_formula_calculation():
    """Benchmark formula calculation with caching."""
    print("Formula Calculation Benchmarks (with caching):")
    print("-" * 50)
    sizes = [10, 100, 1000, 10000]
    
    for size in sizes:
        species = ['Si'] * size
        positions = np.random.rand(size, 3)
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        # First call (computes)
        start = time.time()
        formula1 = crystal.get_formula()
        elapsed1 = time.time() - start
        
        # Second call (uses cache)
        start = time.time()
        formula2 = crystal.get_formula()
        elapsed2 = time.time() - start
        
        print(f"Size {size:5d}: First call {elapsed1*1000:8.2f} ms, "
              f"Cached call {elapsed2*1000:8.2f} ms "
              f"(speedup: {elapsed1/elapsed2 if elapsed2 > 0 else 'inf':.1f}x)")
    print()


def benchmark_lattice_operations():
    """Benchmark lattice operations."""
    print("Lattice Operations Benchmarks:")
    print("-" * 50)
    
    lattice = Lattice.cubic(10.0)
    
    # Matrix access
    start = time.time()
    for _ in range(1000):
        _ = lattice.matrix
    elapsed = time.time() - start
    print(f"Matrix access (1000x): {elapsed*1000:.2f} ms")
    
    # Inverse matrix (first call computes, others use cache)
    start = time.time()
    for _ in range(1000):
        _ = lattice.inv_matrix
    elapsed = time.time() - start
    print(f"Inverse matrix (1000x, cached): {elapsed*1000:.2f} ms")
    print()


if __name__ == '__main__':
    print("=" * 50)
    print("MatSimPy Performance Benchmarks")
    print("=" * 50)
    print()
    
    benchmark_structure_creation()
    benchmark_neighbor_finding()
    benchmark_formula_calculation()
    benchmark_lattice_operations()
    
    print("=" * 50)
    print("Benchmarks completed!")

