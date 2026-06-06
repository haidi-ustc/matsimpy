"""Comprehensive tests for Structure class."""
import unittest
import numpy as np

from matsimpy.core import Structure, Crystal, Molecule, Lattice, Element

class TestStructureComprehensive(unittest.TestCase):
    """Comprehensive tests for Structure class."""
    
    def test_structure_init_with_strings(self):
        """Test structure initialization with string species."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        self.assertEqual(len(struct), 2)
        self.assertEqual(struct.species, ('Si', 'O'))
    
    def test_structure_init_with_integers(self):
        """Test structure initialization with integer species (atomic numbers)."""
        species = [14, 8]  # Si, O
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        self.assertEqual(struct.species, ('Si', 'O'))
    
    def test_structure_init_with_elements(self):
        """Test structure initialization with Element objects."""
        species = [Element('Si'), Element('O')]
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        self.assertEqual(struct.species, ('Si', 'O'))
    
    def test_structure_init_mixed_types_error(self):
        """Test that mixed types raise error."""
        species = ['Si', 8]  # Mixed types
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        
        with self.assertRaises(TypeError):
            Crystal(species, positions, lattice)
    
    def test_structure_positions(self):
        """Test positions property."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        np.testing.assert_array_equal(struct.positions, np.array([[0, 0, 0]]))
    
    def test_structure_get_formula(self):
        """Test formula calculation."""
        species = ['Si', 'O', 'O']
        positions = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        formula = struct.formula
        self.assertIn('Si', formula)
        self.assertIn('O', formula)
    
    def test_structure_formula_caching(self):
        """Test that formula is cached."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)

        formula1 = struct.formula
        formula2 = struct.formula
        self.assertEqual(formula1, formula2)
    
    def test_structure_composition(self):
        """Test composition calculation."""
        species = ['Si', 'O', 'O']
        positions = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        comp = struct.composition
        self.assertEqual(comp['Si'], 1)
        self.assertEqual(comp['O'], 2)
    
    def test_structure_composition_caching(self):
        """Test that composition is cached."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        comp1 = struct.composition
        comp2 = struct.composition
        self.assertIs(comp1, comp2)  # Should be same object
    
    def test_structure_add_atom(self):
        """Test adding atom."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)

        # Use fractional coords that don't conflict
        result = struct.add_atom('O', [0.3, 0.3, 0.3])
        self.assertEqual(len(result), 2)
        self.assertEqual(result.species, ('Si', 'O'))
        # Original unchanged
        self.assertEqual(len(struct), 1)

    def test_structure_add_atom_cache_invalidation(self):
        """Test that formula changes after adding atom."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)

        formula1 = struct.formula
        result = struct.add_atom('O', [0.3, 0.3, 0.3])
        formula2 = result.formula
        self.assertNotEqual(formula1, formula2)

    def test_structure_remove_atom(self):
        """Test removing atom."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)

        result = struct.remove_atom(0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.species, ('O',))
        # Original unchanged
        self.assertEqual(len(struct), 2)
    
    def test_structure_remove_atom_invalid_index(self):
        """Test removing atom with invalid index."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        with self.assertRaises(IndexError):
            struct.remove_atom(10)
    
    def test_structure_remove_atom_cache_invalidation(self):
        """Test that formula changes after removing atom."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)

        formula1 = struct.formula
        result = struct.remove_atom(0)
        formula2 = result.formula
        self.assertNotEqual(formula1, formula2)
    
    def test_structure_len(self):
        """Test length."""
        species = ['Si', 'O', 'O']
        positions = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        self.assertEqual(len(struct), 3)
    
    def test_structure_hash(self):
        """Test that structures are unhashable (__hash__ = None)."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)

        with self.assertRaises(TypeError):
            hash(struct)
    
    def test_structure_as_dict(self):
        """Test dictionary representation."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [1, 1, 1]]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        d = struct.as_dict()
        self.assertIn('species', d)
        self.assertIn('positions', d)
        self.assertIn('lattice', d)
    
    def test_structure_as_dict_no_lattice(self):
        """Test dictionary representation without lattice."""
        species = ['H', 'H']
        positions = [[0, 0, 0], [1, 1, 1]]
        struct = Molecule(species, positions)
        
        d = struct.as_dict()
        self.assertNotIn('lattice', d)
    
    def test_structure_from_dict(self):
        """Test creation from dictionary."""
        d = {
            'species': ['Si', 'O'],
            'positions': [[0, 0, 0], [1, 1, 1]],
            'lattice': {
                'lattice_vectors': [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
            }
        }
        struct = Crystal.from_dict(d)
        self.assertEqual(len(struct), 2)
    
    def test_structure_from_dict_no_lattice(self):
        """Test creation from dictionary without lattice."""
        d = {
            'species': ['H', 'H'],
            'positions': [[0, 0, 0], [1, 1, 1]]
        }
        struct = Molecule.from_dict(d)
        self.assertIsNone(struct.lattice)
    
    def test_structure_formula_single_element(self):
        """Test formula for single element."""
        species = ['Si'] * 10
        positions = [[i, i, i] for i in range(10)]
        lattice = Lattice.cubic(10.0)
        struct = Crystal(species, positions, lattice)
        
        formula = struct.formula
        self.assertIn('Si', formula)
        self.assertIn('10', formula)

if __name__ == '__main__':
    unittest.main()

