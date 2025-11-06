"""
Examples for building molecular structures.

This example demonstrates:
- Building molecules from geometry
- SMILES parsing (if RDKit available)
- Different molecular geometries
"""

from matsimpy.builders.molecule import (
    build_linear,
    build_bent,
    build_tetrahedral,
    build_trigonal_planar,
    build_from_smiles
)

print("=" * 70)
print("MatSimPy Builders - Molecular Structures Examples")
print("=" * 70)

# ============================================================================
# Example 1: Linear Molecules
# ============================================================================
print("\n1. Linear Molecules")
print("-" * 70)

# CO2 molecule
co2 = build_linear(['O', 'C', 'O'], [1.16, 1.16])
print(f"CO2: {co2.formula}")
print(f"  Atoms: {len(co2)}")
print(f"  Bond lengths: O-C = 1.16 Å, C-O = 1.16 Å")

# HCN molecule
hcn = build_linear(['H', 'C', 'N'], [1.06, 1.15])
print(f"\nHCN: {hcn.formula}")
print(f"  Atoms: {len(hcn)}")
print(f"  Bond lengths: H-C = 1.06 Å, C-N = 1.15 Å")

# ============================================================================
# Example 2: Bent Molecules
# ============================================================================
print("\n\n2. Bent Molecules")
print("-" * 70)

# Water molecule
h2o = build_bent(['O', 'H', 'H'], [0.96, 0.96], [104.5])
print(f"H2O: {h2o.formula}")
print(f"  Atoms: {len(h2o)}")
print(f"  Bond lengths: O-H = 0.96 Å")
print(f"  Bond angle: 104.5°")

# H2S molecule
h2s = build_bent(['S', 'H', 'H'], [1.34, 1.34], [92.1])
print(f"\nH2S: {h2s.formula}")
print(f"  Atoms: {len(h2s)}")
print(f"  Bond lengths: S-H = 1.34 Å")
print(f"  Bond angle: 92.1°")

# ============================================================================
# Example 3: Trigonal Planar Molecules
# ============================================================================
print("\n\n3. Trigonal Planar Molecules")
print("-" * 70)

# BF3 molecule
bf3 = build_trigonal_planar('B', ['F', 'F', 'F'], 1.30)
print(f"BF3: {bf3.formula}")
print(f"  Atoms: {len(bf3)}")
print(f"  Bond length: B-F = 1.30 Å")
print(f"  Geometry: Trigonal planar (120°)")

# ============================================================================
# Example 4: Tetrahedral Molecules
# ============================================================================
print("\n\n4. Tetrahedral Molecules")
print("-" * 70)

# Methane (CH4)
ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)
print(f"CH4: {ch4.formula}")
print(f"  Atoms: {len(ch4)}")
print(f"  Bond length: C-H = 1.09 Å")
print(f"  Geometry: Tetrahedral (109.5°)")

# Silicon tetrachloride (SiCl4)
sicl4 = build_tetrahedral('Si', ['Cl', 'Cl', 'Cl', 'Cl'], 2.02)
print(f"\nSiCl4: {sicl4.formula}")
print(f"  Atoms: {len(sicl4)}")
print(f"  Bond length: Si-Cl = 2.02 Å")
print(f"  Geometry: Tetrahedral")

# ============================================================================
# Example 5: SMILES Parsing (requires RDKit)
# ============================================================================
print("\n\n5. SMILES Parsing")
print("-" * 70)

try:
    # Parse molecules from SMILES strings
    smiles_molecules = {
        'C': 'Methane',
        'CCO': 'Ethanol',
        'c1ccccc1': 'Benzene',
        'CC(=O)O': 'Acetic acid',
    }
    
    for smiles, name in smiles_molecules.items():
        try:
            mol = build_from_smiles(smiles)
            print(f"{name} ({smiles}):")
            print(f"  Formula: {mol.formula}")
            print(f"  Atoms: {len(mol)}")
        except Exception as e:
            print(f"{name} ({smiles}): Error - {e}")
            
except ImportError:
    print("RDKit not installed. Skipping SMILES examples.")
    print("Install with: pip install rdkit")
except Exception as e:
    print(f"SMILES parsing error: {e}")

# ============================================================================
# Example 6: Comparing Geometries
# ============================================================================
print("\n\n6. Comparing Different Geometries")
print("-" * 70)

molecules = {
    'Linear (CO2)': build_linear(['O', 'C', 'O'], [1.16, 1.16]),
    'Bent (H2O)': build_bent(['O', 'H', 'H'], [0.96, 0.96], [104.5]),
    'Trigonal (BF3)': build_trigonal_planar('B', ['F', 'F', 'F'], 1.30),
    'Tetrahedral (CH4)': build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09),
}

print(f"{'Geometry':<20} {'Formula':<10} {'Atoms':<8}")
print("-" * 40)
for name, mol in molecules.items():
    print(f"{name:<20} {mol.formula:<10} {len(mol):<8}")

print("\n" + "=" * 70)
print("Molecular structure examples completed!")
print("=" * 70)

