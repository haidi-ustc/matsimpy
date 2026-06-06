"""
Comprehensive tests for Structure class in core module.

This test suite covers:
- Initialization with various input types
- All methods and properties
- Edge cases and error handling
- Integration with other core classes
"""
import unittest
import numpy as np
from matsimpy.core import Structure, Crystal, Molecule, Lattice, Composition, Element

class TestStructureInitialization(unittest.TestCase):
    """Test Structure initialization with various input types."""
    
    def test_init_with_string_species(self):
        """Test initialization with string species."""
        species = ['H', 'O', 'H']
        positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        struct = Molecule(species, positions)
        self.assertEqual(len(struct.species), 3)
        self.assertEqual(struct.species, ('H', 'O', 'H'))
        np.testing.assert_array_equal(struct.positions, positions)
    
    def test_init_with_integer_species(self):
        """Test initialization with atomic numbers."""
        species = [1, 8, 1]  # H, O, H
        positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        struct = Molecule(species, positions)
        self.assertEqual(struct.species, ('H', 'O', 'H'))
    
    def test_init_with_element_objects(self):
        """Test initialization with Element objects."""
        species = [Element('H'), Element('O'), Element('H')]
        positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        struct = Molecule(species, positions)
        self.assertEqual(struct.species, ('H', 'O', 'H'))
    
    def test_init_with_lattice(self):
        """Test initialization with lattice."""
        lattice = Lattice([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        species = ['H', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        struct = Crystal(species, positions, lattice)
        self.assertEqual(struct.lattice, lattice)
    
    def test_init_mismatched_lengths(self):
        """Test that mismatched species and positions raise ValueError."""
        species = ['H', 'O']
        positions = [[0, 0, 0]]  # Only one position
        with self.assertRaises(ValueError):
            Molecule(species, positions)
    
    def test_init_non_3d_positions(self):
        """Test that non-3D positions raise ValueError."""
        species = ['H', 'O']
        positions = [[0, 0], [1, 1]]  # 2D positions
        with self.assertRaises(ValueError):
            Molecule(species, positions)
    
    def test_init_invalid_species_type(self):
        """Test that mixed species types raise TypeError."""
        species = ['H', 8, 'O']  # Mixed types
        positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        with self.assertRaises(TypeError):
            Molecule(species, positions)
    
    def test_init_empty_structure(self):
        """Test initialization with empty structure (0 atoms allowed)."""
        empty = Molecule([], [])
        self.assertEqual(len(empty), 0)
        self.assertEqual(empty.species, ())

class TestStructureProperties(unittest.TestCase):
    """Test Structure properties and caching."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.species = ['H', 'O', 'H']
        self.positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        self.struct = Molecule(self.species, self.positions)
    
    def test_formula_property(self):
        """Test formula property."""
        formula = self.struct.formula
        self.assertEqual(formula, 'H2O')
        # Test caching - should be same object
        self.assertIs(formula, self.struct.formula)
    
    def test_composition_property(self):
        """Test composition property."""
        comp = self.struct.composition
        self.assertIsInstance(comp, Composition)
        self.assertEqual(comp['H'], 2)
        self.assertEqual(comp['O'], 1)
        # Test caching
        self.assertIs(comp, self.struct.composition)
    
    def test_species_immutability(self):
        """Test that species tuple is immutable."""
        with self.assertRaises(AttributeError):
            self.struct.species.append('C')
    
    def test_len_method(self):
        """Test __len__ method."""
        self.assertEqual(len(self.struct), 3)
    
    def test_symbol_set_property(self):
        """Test symbol_set property returns tuple with unique elements."""
        symbol_set = self.struct.symbol_set
        self.assertIsInstance(symbol_set, tuple)
        self.assertEqual(symbol_set, ('H', 'O'))
        self.assertEqual(len(symbol_set), 2)  # Unique elements only
    
    def test_symbol_set_preserves_order(self):
        """Test that symbol_set preserves order of first appearance."""
        # H2O - H appears first, then O
        struct = Molecule(['H', 'O', 'H'], [[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        self.assertEqual(struct.symbol_set, ('H', 'O'))
        
        # OH2 - O appears first, then H
        struct2 = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        self.assertEqual(struct2.symbol_set, ('O', 'H'))
    
    def test_symbol_set_crystal(self):
        """Test symbol_set for Crystal structures."""
        from matsimpy.core import Lattice
        crystal = Crystal(['Na', 'Cl', 'Na'], 
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]], 
                         Lattice.cubic(5.64))
        symbol_set = crystal.symbol_set
        self.assertIsInstance(symbol_set, tuple)
        self.assertEqual(symbol_set, ('Na', 'Cl'))
    
    def test_symbol_set_complex(self):
        """Test symbol_set with multiple elements."""
        from matsimpy.core import Lattice
        crystal = Crystal(['Fe', 'O', 'Fe', 'O', 'Al'], 
                         [[0,0,0], [0.5,0.5,0.5], [0.25,0.25,0.25], [0.75,0.75,0.75], [0.1,0.1,0.1]], 
                         Lattice.cubic(5.0))
        symbol_set = crystal.symbol_set
        self.assertEqual(symbol_set, ('Fe', 'O', 'Al'))
        self.assertEqual(len(symbol_set), 3)
    
    def test_symbol_set_single_element(self):
        """Test symbol_set with single element."""
        from matsimpy.core import Lattice
        crystal = Crystal(['Si', 'Si'], 
                         [[0, 0, 0], [0.25, 0.25, 0.25]], 
                         Lattice.cubic(5.43))
        symbol_set = crystal.symbol_set
        self.assertEqual(symbol_set, ('Si',))
        self.assertEqual(len(symbol_set), 1)
    
    def test_symbol_set_affected_by_sort_atoms(self):
        from matsimpy.core import Lattice

        crystal = Crystal(['Cl', 'Na', 'Cl'],
                         [[0, 0, 0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25]],
                         Lattice.cubic(5.64))

        self.assertEqual(crystal.symbol_set, ('Cl', 'Na'))

        result = crystal.sort_atoms('element')
        self.assertEqual(result.species, ('Na', 'Cl', 'Cl'))
        self.assertEqual(result.symbol_set, ('Na', 'Cl'))

        result2 = result.sort_atoms('alphabet')
        self.assertEqual(result2.species, ('Cl', 'Cl', 'Na'))
        self.assertEqual(result2.symbol_set, ('Cl', 'Na'))

class TestStructureMethods(unittest.TestCase):
    """Test Structure methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.species = ['H', 'O', 'H']
        self.positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        self.struct = Molecule(self.species, self.positions)
    
    def test_add_atom(self):
        """Test adding an atom."""
        initial_len = len(self.struct)
        result = self.struct.add_atom('C', [2, 2, 2])
        self.assertEqual(len(result), initial_len + 1)
        self.assertEqual(result.species[-1], 'C')
        np.testing.assert_array_almost_equal(
            result.positions[-1], [2, 2, 2]
        )
        # Formula should be updated
        formula = result.formula
        self.assertIn('C', formula)

    def test_add_atom_invalid_position(self):
        """Test adding atom with invalid position raises ValueError."""
        with self.assertRaises(ValueError):
            self.struct.add_atom('C', [2, 2])  # 2D position

    def test_remove_atom(self):
        """Test removing an atom."""
        initial_len = len(self.struct)
        result = self.struct.remove_atom(0)
        self.assertEqual(len(result), initial_len - 1)
        self.assertEqual(result.species[0], 'O')
        # Formula should be updated
        formula = result.formula
        # After removing first H from H2O (species=['H', 'O', 'H']),
        # species becomes ['O', 'H'], so formula is 'OH' (preserves order)
        self.assertEqual(formula, 'OH')

    def test_remove_atom_invalid_index(self):
        """Test removing atom with invalid index raises IndexError."""
        with self.assertRaises(IndexError):
            self.struct.remove_atom(100)  # Out of range
        with self.assertRaises(IndexError):
            self.struct.remove_atom(-1)  # Negative index
    
class TestStructureSorting(unittest.TestCase):
    """Test Structure sorting methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.species = ['O', 'H', 'C', 'N']
        self.positions = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]]
        self.struct = Molecule(self.species, self.positions)

    def test_sort_atoms_by_element(self):
        """Test sorting atoms by element (atomic number)."""
        result = self.struct.sort_atoms('element')
        # Should be sorted by atomic number: H(1), C(6), N(7), O(8)
        self.assertEqual(result.species[0], 'H')
        self.assertEqual(result.species[1], 'C')
        self.assertEqual(result.species[2], 'N')
        self.assertEqual(result.species[3], 'O')

    def test_sort_atoms_alphabetically(self):
        """Test sorting atoms alphabetically."""
        result = self.struct.sort_atoms('alphabet')
        # Should be sorted alphabetically: C, H, N, O
        self.assertEqual(result.species[0], 'C')
        self.assertEqual(result.species[1], 'H')
        self.assertEqual(result.species[2], 'N')
        self.assertEqual(result.species[3], 'O')
    
    def test_sort_atoms_invalid_method(self):
        """Test sorting with invalid method raises ValueError."""
        with self.assertRaises(ValueError):
            self.struct.sort_atoms('invalid')
    
    def test_sort_atoms_preserves_positions(self):
        """Test that sorting preserves atom-position correspondence."""
        original_positions = self.struct.positions.copy()
        result = self.struct.sort_atoms('element')
        # Positions should be reordered but values preserved
        self.assertEqual(len(result.positions), len(original_positions))
        # All original positions should still be present
        for pos in original_positions:
            self.assertTrue(
                any(np.allclose(pos, p) for p in result.positions)
            )

class TestStructureSerialization(unittest.TestCase):
    """Test Structure serialization (as_dict, from_dict)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.lattice = Lattice([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.species = ['H', 'O']
        self.positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        self.struct = Crystal(self.species, self.positions, self.lattice)
    
    def test_as_dict(self):
        """Test as_dict method."""
        d = self.struct.as_dict()
        self.assertIn('@module', d)
        self.assertIn('@class', d)
        self.assertIn('species', d)
        self.assertIn('positions', d)
        self.assertIn('lattice', d)
        self.assertEqual(list(d['species']), ['H', 'O'])
        np.testing.assert_array_almost_equal(
            d['positions'], self.struct.positions.tolist()
        )
    
    def test_from_dict(self):
        """Test from_dict class method."""
        d = self.struct.as_dict()
        new_struct = Crystal.from_dict(d)
        self.assertEqual(new_struct.species, self.struct.species)
        np.testing.assert_array_almost_equal(
            new_struct.positions, self.struct.positions
        )
        self.assertIsNotNone(new_struct.lattice)
    
    def test_from_dict_no_lattice(self):
        """Test from_dict with no lattice."""
        struct = Molecule(self.species, self.positions)
        d = struct.as_dict()
        new_struct = Molecule.from_dict(d)
        self.assertIsNone(new_struct.lattice)
    
    def test_hash(self):
        """Test that structures are unhashable (__hash__ = None)."""
        with self.assertRaises(TypeError):
            hash(self.struct)

        struct2 = Molecule(['H', 'H'], [[0, 0, 0], [1, 1, 1]])
        with self.assertRaises(TypeError):
            hash(struct2)

class TestStructureEdgeCases(unittest.TestCase):
    """Test Structure edge cases and error handling."""
    
    def test_single_atom_structure(self):
        """Test structure with single atom."""
        struct = Molecule(['H'], [[0, 0, 0]])
        self.assertEqual(len(struct), 1)
        self.assertEqual(struct.formula, 'H')
    
    def test_large_structure(self):
        """Test structure with many atoms."""
        n_atoms = 1000
        species = ['H'] * n_atoms
        positions = [[i, i, i] for i in range(n_atoms)]
        struct = Molecule(species, positions)
        self.assertEqual(len(struct), n_atoms)
    
    def test_structure_with_duplicate_positions(self):
        """Test structure with duplicate positions (should be allowed)."""
        species = ['H', 'H']
        positions = [[0, 0, 0], [0, 0, 0]]
        struct = Molecule(species, positions)
        self.assertEqual(len(struct), 2)
    
    def test_formula_cache_invalidation(self):
        """Test that formula is different after modification."""
        struct = Molecule(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
        formula1 = struct.formula  # Get initial formula
        result = struct.add_atom('C', [2, 2, 2])
        formula2 = result.formula  # Get updated formula
        self.assertNotEqual(formula1, formula2)
        self.assertIn('C', formula2)

    def test_composition_cache_invalidation(self):
        """Test that composition is different after modification."""
        struct = Molecule(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
        comp1 = struct.composition  # Get initial composition
        result = struct.add_atom('C', [2, 2, 2])
        comp2 = result.composition  # Get updated composition
        self.assertNotEqual(comp1.formula, comp2.formula)
        self.assertIn('C', comp2.composition)

class TestStructureNeighborList(unittest.TestCase):
    """Test Structure neighbor list method."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.struct = Molecule(['H', 'H'], [[0, 0, 0], [1, 0, 0]])
    
    def test_get_neighbor_list_implemented(self):
        """Test that get_neighbor_list is implemented in Molecule."""
        # Molecule implements get_neighbor_list with different signature
        neighbors = self.struct.get_neighbor_list(cutoff=5.0, atom_index=0)
        self.assertIsInstance(neighbors, dict)
        # Check that it contains the requested atom index
        self.assertIn(0, neighbors)
        # Check that values are lists of tuples
        self.assertIsInstance(neighbors[0], list)

if __name__ == '__main__':
    unittest.main()

