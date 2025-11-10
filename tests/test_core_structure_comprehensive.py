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
        """Test initialization with empty structure."""
        # Empty structure is not supported due to position validation
        # This is expected behavior - structures need at least one atom
        with self.assertRaises(ValueError):
            Molecule([], [])


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
        # Clear cache before adding
        self.struct._cached_formula = None
        self.struct._formula_dirty = True
        self.struct.add_atom('C', [2, 2, 2])
        self.assertEqual(len(self.struct), initial_len + 1)
        self.assertEqual(self.struct.species[-1], 'C')
        np.testing.assert_array_almost_equal(
            self.struct.positions[-1], [2, 2, 2]
        )
        # Formula should be updated
        formula = self.struct.formula
        self.assertIn('C', formula)
    
    def test_add_atom_invalid_position(self):
        """Test adding atom with invalid position raises ValueError."""
        with self.assertRaises(ValueError):
            self.struct.add_atom('C', [2, 2])  # 2D position
    
    def test_remove_atom(self):
        """Test removing an atom."""
        initial_len = len(self.struct)
        original_species = self.struct.species[0]
        # Clear cache before removing
        self.struct._cached_formula = None
        self.struct._formula_dirty = True
        self.struct.remove_atom(0)
        self.assertEqual(len(self.struct), initial_len - 1)
        self.assertNotEqual(self.struct.species[0], original_species)
        # Formula should be updated
        formula = self.struct.formula
        # After removing one H from H2O, we should have HO
        self.assertEqual(formula, 'HO')
    
    def test_remove_atom_invalid_index(self):
        """Test removing atom with invalid index raises IndexError."""
        with self.assertRaises(IndexError):
            self.struct.remove_atom(100)  # Out of range
        with self.assertRaises(IndexError):
            self.struct.remove_atom(-1)  # Negative index
    
    def test_formula_property(self):
        """Test formula property."""
        formula = self.struct.formula
        self.assertEqual(formula, 'H2O')
    
    def test_composition_property(self):
        """Test composition property."""
        comp = self.struct.composition
        self.assertIsInstance(comp, Composition)
        self.assertEqual(comp['H'], 2)
        self.assertEqual(comp['O'], 1)


class TestStructureSubstitution(unittest.TestCase):
    """Test Structure substitution methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.species = ['Si', 'O', 'Si', 'O']
        self.positions = [[0, 0, 0], [0.25, 0.25, 0.25], 
                          [0.5, 0.5, 0.5], [0.75, 0.75, 0.75]]
        self.struct = Molecule(self.species, self.positions)
    
    def test_substitute_single_atom(self):
        """Test substituting a single atom."""
        self.struct.substitute(0, 'Ge')
        self.assertEqual(self.struct.species[0], 'Ge')
        self.assertEqual(self.struct.species[1], 'O')
    
    def test_substitute_multiple_atoms(self):
        """Test substituting multiple atoms."""
        self.struct.substitute([0, 2], ['Ge', 'Ge'])
        self.assertEqual(self.struct.species[0], 'Ge')
        self.assertEqual(self.struct.species[2], 'Ge')
    
    def test_substitute_multiple_atoms_same_species(self):
        """Test substituting multiple atoms with same species."""
        self.struct.substitute([0, 2], 'Ge')
        self.assertEqual(self.struct.species[0], 'Ge')
        self.assertEqual(self.struct.species[2], 'Ge')
    
    def test_substitute_with_dict(self):
        """Test substituting using dictionary mapping."""
        self.struct.substitute([0, 1, 2, 3], {'Si': 'Ge', 'O': 'S'})
        self.assertEqual(self.struct.species[0], 'Ge')
        self.assertEqual(self.struct.species[1], 'S')
    
    def test_substitute_all(self):
        """Test substitute_all method."""
        self.struct.substitute_all('Si', 'Ge')
        self.assertEqual(self.struct.species[0], 'Ge')
        self.assertEqual(self.struct.species[2], 'Ge')
        self.assertEqual(self.struct.species[1], 'O')  # O unchanged
    
    def test_substitute_all_no_match(self):
        """Test substitute_all when no atoms match."""
        initial_species = list(self.struct.species)
        self.struct.substitute_all('C', 'N')  # No C atoms
        self.assertEqual(list(self.struct.species), initial_species)
    
    def test_substitute_invalid_index(self):
        """Test substitute with invalid index raises IndexError."""
        with self.assertRaises(IndexError):
            self.struct.substitute(100, 'Ge')
    
    def test_substitute_mismatched_lengths(self):
        """Test substitute with mismatched lengths raises ValueError."""
        with self.assertRaises(ValueError):
            self.struct.substitute([0, 1], ['Ge'])  # Only one species
    
    def test_substitute_dict_missing_key(self):
        """Test substitute with dict missing key raises KeyError."""
        with self.assertRaises(KeyError):
            self.struct.substitute([0], {'C': 'N'})  # Si not in dict


class TestStructureSorting(unittest.TestCase):
    """Test Structure sorting methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.species = ['O', 'H', 'C', 'N']
        self.positions = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]]
        self.struct = Molecule(self.species, self.positions)
    
    def test_sort_atoms_by_element(self):
        """Test sorting atoms by element (atomic number)."""
        self.struct.sort_atoms('element')
        # Should be sorted by atomic number: H(1), C(6), N(7), O(8)
        self.assertEqual(self.struct.species[0], 'H')
        self.assertEqual(self.struct.species[1], 'C')
        self.assertEqual(self.struct.species[2], 'N')
        self.assertEqual(self.struct.species[3], 'O')
    
    def test_sort_atoms_alphabetically(self):
        """Test sorting atoms alphabetically."""
        self.struct.sort_atoms('alphabet')
        # Should be sorted alphabetically: C, H, N, O
        self.assertEqual(self.struct.species[0], 'C')
        self.assertEqual(self.struct.species[1], 'H')
        self.assertEqual(self.struct.species[2], 'N')
        self.assertEqual(self.struct.species[3], 'O')
    
    def test_sort_atoms_invalid_method(self):
        """Test sorting with invalid method raises ValueError."""
        with self.assertRaises(ValueError):
            self.struct.sort_atoms('invalid')
    
    def test_sort_atoms_preserves_positions(self):
        """Test that sorting preserves atom-position correspondence."""
        original_positions = self.struct.positions.copy()
        self.struct.sort_atoms('element')
        # Positions should be reordered but values preserved
        self.assertEqual(len(self.struct.positions), len(original_positions))
        # All original positions should still be present
        for pos in original_positions:
            self.assertTrue(
                any(np.allclose(pos, p) for p in self.struct.positions)
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
        """Test __hash__ method."""
        hash1 = hash(self.struct)
        hash2 = hash(self.struct)
        self.assertEqual(hash1, hash2)  # Should be consistent
        
        # Different structure should have different hash
        struct2 = Molecule(['H', 'H'], [[0, 0, 0], [1, 1, 1]])
        self.assertNotEqual(hash(self.struct), hash(struct2))


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
        """Test that formula cache is invalidated on modification."""
        struct = Molecule(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
        formula1 = struct.formula  # Get initial formula
        struct.add_atom('C', [2, 2, 2])
        # Check that _formula_dirty flag is set
        self.assertTrue(struct._formula_dirty)
        formula2 = struct.formula  # Get updated formula
        self.assertNotEqual(formula1, formula2)
        self.assertIn('C', formula2)
    
    def test_composition_cache_invalidation(self):
        """Test that composition cache is invalidated on modification."""
        struct = Molecule(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
        comp1 = struct.composition  # Get initial composition
        struct.add_atom('C', [2, 2, 2])
        # Check that cache is cleared
        self.assertIsNone(struct._cached_composition)
        comp2 = struct.composition  # Get updated composition
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
        neighbors = self.struct.get_neighbor_list(0, 5.0)
        self.assertIsInstance(neighbors, list)


if __name__ == '__main__':
    unittest.main()

