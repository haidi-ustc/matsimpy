"""
Examples for creating defect structures.

This example demonstrates:
- Vacancy creation
- Interstitial creation
- Substitution defects
- Complex defects (Frenkel, Schottky, antisite)
"""

from matsimpy.builders.bulk import from_prototype
from matsimpy.builders.defects import (
    create_vacancy,
    create_interstitial,
    create_substitution,
    create_frenkel,
    create_schottky,
    create_antisite
)
from matsimpy.transformation.structural import make_supercell

print("=" * 70)
print("MatSimPy Builders - Defect Structures Examples")
print("=" * 70)

# ============================================================================
# Example 1: Vacancy Defects
# ============================================================================
print("\n1. Vacancy Defects")
print("-" * 70)

# Start with FCC Cu
fcc_cu = from_prototype('fcc', 'Cu', 3.61)
supercell = make_supercell(fcc_cu, [3, 3, 3])
print(f"Base structure: {supercell.formula}, {len(supercell)} atoms")

# Create single vacancy
with_vacancy = create_vacancy(supercell, 0)
print(f"\nSingle vacancy:")
print(f"  Formula: {with_vacancy.formula}")
print(f"  Atoms: {len(with_vacancy)} (removed 1)")

# Create multiple vacancies
with_vacancies = create_vacancy(supercell, [0, 1, 2])
print(f"\nMultiple vacancies (3 atoms):")
print(f"  Formula: {with_vacancies.formula}")
print(f"  Atoms: {len(with_vacancies)} (removed 3)")

# ============================================================================
# Example 2: Interstitial Defects
# ============================================================================
print("\n\n2. Interstitial Defects")
print("-" * 70)

# Create interstitial atom
with_interstitial = create_interstitial(supercell, 'H', position=[0.5, 0.5, 0.5])
print(f"Interstitial H:")
print(f"  Formula: {with_interstitial.formula}")
print(f"  Atoms: {len(with_interstitial)} (added 1)")
print(f"  H atoms: {sum(1 for s in with_interstitial.species if s == 'H')}")

# Create multiple interstitials
with_interstitials = create_interstitial(supercell, 'C', position=[0.5, 0.5, 0.5])
with_interstitials = create_interstitial(with_interstitials, 'C', position=[0.25, 0.25, 0.25])
print(f"\nMultiple interstitials (2 C atoms):")
print(f"  Formula: {with_interstitials.formula}")
print(f"  Atoms: {len(with_interstitials)} (added 2)")
print(f"  C atoms: {sum(1 for s in with_interstitials.species if s == 'C')}")

# ============================================================================
# Example 3: Substitution Defects
# ============================================================================
print("\n\n3. Substitution Defects")
print("-" * 70)

# Single substitution
with_sub = create_substitution(supercell, 0, 'Ni')
print(f"Single substitution (Cu → Ni):")
print(f"  Formula: {with_sub.formula}")
print(f"  Cu atoms: {sum(1 for s in with_sub.species if s == 'Cu')}")
print(f"  Ni atoms: {sum(1 for s in with_sub.species if s == 'Ni')}")

# Multiple substitutions
with_subs = create_substitution(supercell, [0, 1, 2], ['Ni', 'Ni', 'Ni'])
print(f"\nMultiple substitutions (3 Cu → Ni):")
print(f"  Formula: {with_subs.formula}")
print(f"  Cu atoms: {sum(1 for s in with_subs.species if s == 'Cu')}")
print(f"  Ni atoms: {sum(1 for s in with_subs.species if s == 'Ni')}")

# ============================================================================
# Example 4: Frenkel Defects
# ============================================================================
print("\n\n4. Frenkel Defects")
print("-" * 70)

# Frenkel defect: atom moves from lattice site to interstitial
frenkel = create_frenkel(supercell, 0, interstitial_pos=[0.5, 0.5, 0.5])
print(f"Frenkel defect:")
print(f"  Formula: {frenkel.formula}")
print(f"  Atoms: {len(frenkel)} (same number, one displaced)")

# ============================================================================
# Example 5: Schottky Defects
# ============================================================================
print("\n\n5. Schottky Defects")
print("-" * 70)

# For binary compound, create Schottky pair (vacancy pair)
rocksalt = from_prototype('rocksalt', ['Na', 'Cl'], 5.64)
rocksalt_super = make_supercell(rocksalt, [2, 2, 2])

try:
    schottky = create_schottky(rocksalt_super, ['Na', 'Cl'])
    print(f"Schottky defect (NaCl):")
    print(f"  Formula: {schottky.formula}")
    print(f"  Atoms: {len(schottky)} (removed 2)")
except Exception as e:
    print(f"Schottky defect creation: {e}")

# ============================================================================
# Example 6: Antisite Defects
# ============================================================================
print("\n\n6. Antisite Defects")
print("-" * 70)

# Antisite: swap two atoms of different species
try:
    antisite = create_antisite(rocksalt_super, 0, 4)  # Swap Na and Cl
    print(f"Antisite defect (Na ↔ Cl):")
    print(f"  Formula: {antisite.formula}")
    print(f"  Atoms: {len(antisite)} (swapped 2)")
except Exception as e:
    print(f"Antisite defect creation: {e}")

# ============================================================================
# Example 7: Combining Defects
# ============================================================================
print("\n\n7. Combining Multiple Defects")
print("-" * 70)

# Start fresh
base = make_supercell(fcc_cu, [3, 3, 3])

# Create structure with multiple defect types
defected = create_vacancy(base, 0)  # Remove one atom
defected = create_substitution(defected, 1, 'Ni')  # Substitute one
defected = create_interstitial(defected, 'H', position=[0.5, 0.5, 0.5])  # Add interstitial

print(f"Combined defects:")
print(f"  Formula: {defected.formula}")
print(f"  Atoms: {len(defected)}")
print(f"  Cu: {sum(1 for s in defected.species if s == 'Cu')}")
print(f"  Ni: {sum(1 for s in defected.species if s == 'Ni')}")
print(f"  H: {sum(1 for s in defected.species if s == 'H')}")

print("\n" + "=" * 70)
print("Defect structure examples completed!")
print("=" * 70)

