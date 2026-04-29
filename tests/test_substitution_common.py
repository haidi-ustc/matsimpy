"""Tests for common substitution methods in Crystal and Molecule classes."""
import unittest

from matsimpy.core import Crystal, Molecule, Lattice
from tests.conftest import make_simple_crystal, make_simple_molecule

class TestMoleculeSubstitution(unittest.TestCase):
    """Tests for substitution methods in Molecule class."""
    
    def setUp(self):
        """Set up test molecules."""
        self.molecule = make_simple_molecule()
    
    def test_substitute_single(self):
        """Test substituting a single atom."""
        original_species = list(self.molecule.species)
        self.molecule.substitute(0, 'N')
        
        self.assertEqual(self.molecule.species[0], 'N')
        self.assertEqual(self.molecule.species[1], original_species[1])
        # Sites should be updated
        self.assertEqual(len(self.molecule.sites), 2)
        self.assertEqual(self.molecule.sites[0].specie, 'N')
    
    def test_substitute_multiple(self):
        """Test substituting multiple atoms."""
        self.molecule.substitute([0, 1], ['N', 'S'])
        
        self.assertEqual(self.molecule.species[0], 'N')
        self.assertEqual(self.molecule.species[1], 'S')
        self.assertEqual(self.molecule.sites[0].specie, 'N')
        self.assertEqual(self.molecule.sites[1].specie, 'S')
    
    def test_substitute_all(self):
        """Test substituting all atoms of a species."""
        molecule = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        molecule.substitute_all('C', 'N')
        
        self.assertEqual(molecule.species[0], 'N')
        self.assertEqual(molecule.species[1], 'N')
        self.assertEqual(molecule.species[2], 'O')
    
    def test_substitute_invalid_index(self):
        """Test substitution with invalid index."""
        with self.assertRaises(IndexError):
            self.molecule.substitute(10, 'N')
    
    def test_substitute_mismatched_lengths(self):
        """Test substitution with mismatched indices and species."""
        with self.assertRaises(ValueError):
            self.molecule.substitute([0, 1], ['N'])
    
    def test_substitute_cache_invalidation(self):
        """Test that substitution invalidates formula cache."""
        molecule = Molecule(['C', 'C'], [[0, 0, 0], [1.2, 0, 0]])  # C2
        original_formula = molecule.formula
        self.assertEqual(original_formula, 'C2')
        
        # Verify species actually changed
        molecule.substitute(0, 'N')
        self.assertEqual(molecule.species[0], 'N')
        self.assertEqual(molecule.species[1], 'C')
        
        # Formula should be recalculated (force recalculation)
        new_formula = molecule.formula
        self.assertNotEqual(original_formula, new_formula)
        # Formula should contain both C and N (order may vary)
        self.assertIn('C', new_formula)
        self.assertIn('N', new_formula)

class TestCrystalSubstitution(unittest.TestCase):
    """Tests for substitution methods in Crystal class."""
    
    def setUp(self):
        """Set up test crystals."""
        self.crystal = make_simple_crystal()
    
    def test_substitute_single(self):
        """Test substituting a single atom."""
        original_species = list(self.crystal.species)
        self.crystal.substitute(0, 'Ge')
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[1], original_species[1])
        # Sites should be updated
        self.assertEqual(len(self.crystal.sites), 2)
        self.assertEqual(self.crystal.sites[0].specie, 'Ge')
    
    def test_substitute_multiple(self):
        """Test substituting multiple atoms."""
        crystal = Crystal(['Si', 'Si', 'O'], 
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], 
                         Lattice.cubic(10))
        crystal.substitute([0, 1], ['Ge', 'Ge'])
        
        self.assertEqual(crystal.species[0], 'Ge')
        self.assertEqual(crystal.species[1], 'Ge')
        self.assertEqual(crystal.species[2], 'O')
    
    def test_substitute_all(self):
        """Test substituting all atoms of a species."""
        crystal = Crystal(['Si', 'Si', 'O'], 
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], 
                         Lattice.cubic(10))
        crystal.substitute_all('Si', 'Ge')
        
        self.assertEqual(crystal.species[0], 'Ge')
        self.assertEqual(crystal.species[1], 'Ge')
        self.assertEqual(crystal.species[2], 'O')
    
    def test_substitute_neighbor_tree_invalidation(self):
        """Test that substitution invalidates neighbor tree."""
        # Build neighbor tree
        self.crystal.get_neighbor_list(5.0)
        self.assertIsNotNone(self.crystal._neighbor_tree)
        
        # Substitute atom
        self.crystal.substitute(0, 'Ge')
        
        # Neighbor tree should be invalidated
        self.assertIsNone(self.crystal._neighbor_tree)
    
    def test_substitute_cache_invalidation(self):
        """Test that substitution invalidates formula cache."""
        crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))  # Si2
        original_formula = crystal.formula
        self.assertEqual(original_formula, 'Si2')
        
        # Verify species actually changed
        crystal.substitute(0, 'Ge')
        self.assertEqual(crystal.species[0], 'Ge')
        self.assertEqual(crystal.species[1], 'Si')
        
        # Formula should be recalculated (force recalculation)
        new_formula = crystal.formula
        self.assertNotEqual(original_formula, new_formula)
        # Formula should contain both Si and Ge (order may vary)
        self.assertIn('Si', new_formula)
        self.assertIn('Ge', new_formula)

class TestSubstitutionConsistency(unittest.TestCase):
    """Tests for consistency between class methods and transformation module."""
    
    def test_substitute_consistency(self):
        """Test that class method and transformation module produce same result."""
        from matsimpy.transformation import substitute
        
        # Test with class method
        mol1 = make_simple_molecule()
        mol1.substitute(0, 'N')
        
        # Test with transformation module (inplace)
        mol2 = make_simple_molecule()
        # Transformation functions always return new objects
        mol2 = substitute(mol2, 0, 'N')
        
        # Results should be the same
        self.assertEqual(mol1.species, mol2.species)
        self.assertEqual(mol1.positions.tolist(), mol2.positions.tolist())
    
    def test_substitute_all_consistency(self):
        """Test that substitute_all is consistent."""
        from matsimpy.transformation import substitute_all
        
        # Test with class method
        mol1 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        mol1.substitute_all('C', 'N')
        
        # Test with transformation module (inplace)
        mol2 = Molecule(['C', 'C', 'O'], [[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        # Transformation functions always return new objects
        mol2 = substitute_all(mol2, 'C', 'N')
        
        # Results should be the same
        self.assertEqual(mol1.species, mol2.species)

if __name__ == '__main__':
    unittest.main()
