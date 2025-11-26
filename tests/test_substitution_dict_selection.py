"""Tests for substitution with dict mapping and AtomSelection."""
import unittest

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.utils.selection import AtomSelection

class TestSubstitutionWithDict(unittest.TestCase):
    """Tests for dict-based substitution mapping."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0]],
            Lattice.cubic(10)
        )
        self.molecule = Molecule(['C', 'O', 'C', 'N'], [[0, 0, 0], [1.2, 0, 0], [2.4, 0, 0], [3.6, 0, 0]])
    
    def test_substitute_with_dict_simple(self):
        """Test substitution with simple dict mapping."""
        crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
        crystal.substitute([0, 1], {'Si': 'Ge', 'O': 'S'})
        
        self.assertEqual(crystal.species[0], 'Ge')
        self.assertEqual(crystal.species[1], 'S')
    
    def test_substitute_with_dict_multiple(self):
        """Test substitution with dict mapping for multiple atoms."""
        self.crystal.substitute([0, 1, 2, 3], {'Si': 'Ge', 'O': 'S'})
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[1], 'S')
        self.assertEqual(self.crystal.species[2], 'Ge')
        self.assertEqual(self.crystal.species[3], 'S')
    
    def test_substitute_with_dict_partial(self):
        """Test substitution with dict mapping for subset of atoms."""
        self.crystal.substitute([0, 2], {'Si': 'Ge'})
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[1], 'O')  # Unchanged
        self.assertEqual(self.crystal.species[2], 'Ge')
        self.assertEqual(self.crystal.species[3], 'O')  # Unchanged
    
    def test_substitute_with_dict_missing_key(self):
        """Test that missing key in dict raises KeyError."""
        with self.assertRaises(KeyError):
            self.crystal.substitute([0], {'Ge': 'Si'})  # 'Si' not in dict
    
    def test_substitute_with_dict_molecule(self):
        """Test dict substitution with molecule."""
        self.molecule.substitute([0, 1, 2, 3], {'C': 'N', 'O': 'S', 'N': 'P'})
        
        self.assertEqual(self.molecule.species[0], 'N')
        self.assertEqual(self.molecule.species[1], 'S')
        self.assertEqual(self.molecule.species[2], 'N')
        self.assertEqual(self.molecule.species[3], 'P')

class TestSubstitutionWithAtomSelectionAndDict(unittest.TestCase):
    """Tests for combining AtomSelection with dict mapping."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(
            ['Si', 'O', 'Si', 'O'],
            [[0, 0, 0], [5, 0, 0], [10, 0, 0], [15, 0, 0]],
            Lattice.cubic(20),
            coords_are_cartesian=True
        )
    
    def test_atom_selection_with_dict(self):
        """Test AtomSelection with dict mapping."""
        sel = AtomSelection(self.crystal).by_species('Si')
        self.crystal.substitute(sel, {'Si': 'Ge'})
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[1], 'O')
        self.assertEqual(self.crystal.species[2], 'Ge')
        self.assertEqual(self.crystal.species[3], 'O')
    
    def test_atom_selection_with_dict_multiple_species(self):
        """Test AtomSelection with dict mapping multiple species."""
        sel = AtomSelection(self.crystal)  # All atoms
        self.crystal.substitute(sel, {'Si': 'Ge', 'O': 'S'})
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[1], 'S')
        self.assertEqual(self.crystal.species[2], 'Ge')
        self.assertEqual(self.crystal.species[3], 'S')
    
    def test_atom_selection_chained_with_dict(self):
        """Test chained AtomSelection with dict mapping."""
        sel = AtomSelection(self.crystal).by_species('Si').near([0, 0, 0], 5.0)
        self.crystal.substitute(sel, {'Si': 'Ge'})
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[2], 'Si')  # Not substituted (too far)
    
    def test_combined_selections_with_dict(self):
        """Test combined selections with dict mapping."""
        sel1 = AtomSelection(self.crystal).by_species('Si')
        sel2 = AtomSelection(self.crystal).near([0, 0, 0], 5.0)
        combined = sel1 & sel2
        self.crystal.substitute(combined, {'Si': 'Ge'})
        
        self.assertEqual(self.crystal.species[0], 'Ge')
        self.assertEqual(self.crystal.species[2], 'Si')  # Not substituted

class TestSubstitutionTransformationModule(unittest.TestCase):
    """Tests for dict mapping in transformation module."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(['Si', 'O', 'Si'], [[0, 0, 0], [5, 0, 0], [10, 0, 0]], 
                              Lattice.cubic(20), coords_are_cartesian=True)
    
    def test_transformation_substitute_with_dict(self):
        """Test transformation.substitute with dict mapping."""
        from matsimpy.transformation import substitute
        
        new_crystal = substitute(self.crystal, [0, 1, 2], {'Si': 'Ge', 'O': 'S'})
        
        self.assertEqual(new_crystal.species[0], 'Ge')
        self.assertEqual(new_crystal.species[1], 'S')
        self.assertEqual(new_crystal.species[2], 'Ge')
        # Original unchanged
        self.assertEqual(self.crystal.species[0], 'Si')
    
    def test_transformation_substitute_with_atom_selection_and_dict(self):
        """Test transformation.substitute with AtomSelection and dict."""
        from matsimpy.transformation import substitute
        from matsimpy.utils.selection import AtomSelection
        
        sel = AtomSelection(self.crystal).by_species('Si')
        new_crystal = substitute(self.crystal, sel, {'Si': 'Ge'})
        
        self.assertEqual(new_crystal.species[0], 'Ge')
        self.assertEqual(new_crystal.species[2], 'Ge')
        self.assertEqual(new_crystal.species[1], 'O')

if __name__ == '__main__':
    unittest.main()

