"""
MatSimPy Calculator Module - Basic Examples

Demonstrates usage of calculators for computing energies and forces.
"""

import numpy as np
from matsimpy import Crystal, Molecule, Lattice
from matsimpy.calculator import LennardJones
from matsimpy.calculator.ml import Mattersim

print("=" * 70)
print("MatSimPy Calculator Module - Basic Examples")
print("=" * 70)

# ======================================================================
# 1. Lennard-Jones Calculator
# ======================================================================
print("\n1. Lennard-Jones Calculator")
print("-" * 70)

# Create Ar crystal
crystal = Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(5.0))
print(f"Structure: {crystal.formula} in {crystal.lattice.a:.2f} Å cubic cell")

# Create and attach LJ calculator
calc = LennardJones(sigma=3.4, epsilon=0.0104)  # Ar parameters
crystal.calc = calc

# Calculate energy and forces
energy = crystal.get_potential_energy()
forces = crystal.get_forces()

print(f"Potential energy: {energy:.6f} eV")
print(f"Forces on atom: {forces[0]}")
print(f"Force magnitude: {np.linalg.norm(forces[0]):.6f} eV/Å")

# ======================================================================
# 2. LJ Calculator for Molecule
# ======================================================================
print("\n2. Lennard-Jones Calculator for Molecule")
print("-" * 70)

# Create Ar dimer
molecule = Molecule(['Ar', 'Ar'], [[0, 0, 0], [3.4, 0, 0]])
calc_mol = LennardJones(sigma=3.4, epsilon=0.0104)
molecule.calc = calc_mol

energy_mol = molecule.get_potential_energy()
forces_mol = molecule.get_forces()

print(f"Molecule: Ar dimer at r = 3.4 Å (sigma)")
print(f"Potential energy: {energy_mol:.6f} eV")
print(f"Forces: {forces_mol}")

# ======================================================================
# 3. LJ Calculator with Different Parameters
# ======================================================================
print("\n3. LJ Calculator with Custom Parameters")
print("-" * 70)

# Test with different cutoff
calc_custom = LennardJones(sigma=3.4, epsilon=0.01, cutoff=15.0)
crystal.calc = calc_custom
energy_custom = crystal.get_potential_energy()

print(f"Cutoff: 15.0 Å")
print(f"Potential energy: {energy_custom:.6f} eV")

# ======================================================================
# 4. ML Calculator (Mattersim) - MatterSim Framework
# ======================================================================
print("\n4. ML Calculator (Mattersim) - MatterSim Framework")
print("-" * 70)

# MatterSim uses M3GNet-based models
try:
    from pathlib import Path
    
    # Try to load MatterSim model (if available)
    model_path = Path.home() / '.matsimpy' / 'models' / 'mattersim-v1.0.0-5M.pth.tar'
    
    if model_path.exists():
        print(f"Loading MatterSim model from: {model_path}")
        ml_calc = Mattersim(model_path=str(model_path), device='cpu')
        
        # Test with Si crystal
        si_crystal = Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5.43))
        si_crystal.calc = ml_calc
        
        energy = si_crystal.get_potential_energy()
        forces = si_crystal.get_forces()
        
        print(f"✓ MatterSim calculator loaded successfully")
        print(f"Model type: {ml_calc.model_type}")
        print(f"Device: {ml_calc.device}")
        print(f"Si crystal energy: {energy:.6f} eV")
        print(f"Forces shape: {forces.shape}")
    else:
        print("MatterSim model not found at default location")
        print(f"Expected: {model_path}")
        print("\nTo use MatterSim calculator:")
        print("1. Install mattersim: pip install mattersim")
        print("2. Place model file at ~/.matsimpy/models/mattersim-v1.0.0-5M.pth.tar")
        print("3. Or specify model_path when creating calculator")
    
except ImportError:
    print("MatterSim library not available")
    print("Install with: pip install mattersim")
except Exception as e:
    print(f"MatterSim calculator error: {type(e).__name__}: {e}")

# ======================================================================
# 5. Calculator Integration with Structures
# ======================================================================
print("\n5. Calculator Integration with Structures")
print("-" * 70)

# Multiple structures with same calculator
calc_shared = LennardJones(sigma=3.4, epsilon=0.0104)

crystals = [
    Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(5.0)),
    Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(6.0)),
    Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(7.0)),
]

print("Energy as function of lattice parameter:")
for crystal in crystals:
    crystal.calc = calc_shared
    energy = crystal.get_potential_energy()
    print(f"  a = {crystal.lattice.a:.2f} Å: E = {energy:.6f} eV")

print("\n" + "=" * 70)
print("Calculator examples completed!")
print("=" * 70)

