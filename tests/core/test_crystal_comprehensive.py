"""Comprehensive tests for Crystal class."""
import unittest
import numpy as np
from pathlib import Path

from matsimpy.core import Crystal, Lattice, Element

class TestCrystalComprehensive(unittest.TestCase):
    """Comprehensive tests for Crystal class."""
    
    def test_crystal_init_fractional(self):
        """Test crystal initialization with fractional coordinates."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertEqual(len(crystal), 2)
        np.testing.assert_array_almost_equal(crystal.frac_positions, positions)
    
    def test_crystal_init_cartesian(self):
        """Test crystal initialization with cartesian coordinates."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [5, 5, 5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice, coords_are_cartesian=True)
        
        np.testing.assert_array_almost_equal(crystal.cart_positions, positions)
    
    def test_crystal_coordinate_conversion(self):
        """Test coordinate conversion."""
        species = ['Si']
        positions = [[0.5, 0.5, 0.5]]  # Fractional
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        # Convert to cartesian and back
        cart = crystal.cart_positions
        frac_back = crystal._convert_to_fractional()
        
        np.testing.assert_array_almost_equal(positions, frac_back, decimal=6)

    def test_crystal_cartesian_coordinate_conversion_roundtrip(self):
        """Test fractional/cartesian conversion helpers with matching structures."""
        species = ['H', 'He']
        positions = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        lattice = Lattice.cubic(1.0)

        crystal_frac = Crystal(species, positions, lattice)
        crystal_cart = Crystal(species, positions, lattice, coords_are_cartesian=True)

        np.testing.assert_array_almost_equal(crystal_frac._convert_to_fractional(), positions)
        np.testing.assert_array_almost_equal(
            crystal_frac._convert_to_cartesian(),
            crystal_cart.cart_positions,
        )
        np.testing.assert_array_almost_equal(crystal_cart._convert_to_cartesian(), positions)
        np.testing.assert_array_almost_equal(
            crystal_cart._convert_to_fractional(),
            crystal_frac.frac_positions,
        )
    
    def test_crystal_volume(self):
        """Test volume calculation."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertEqual(crystal.volume, 1000.0)

    def test_crystal_volume_orthorhombic_lattice(self):
        """Test volume calculation for non-cubic orthogonal lattice."""
        crystal = Crystal(
            ['H', 'He'],
            [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            Lattice.from_parameters(a=2.0, b=3.0, c=4.0, alpha=90, beta=90, gamma=90),
        )

        self.assertAlmostEqual(crystal.volume, 24.0, places=6)
    
    def test_crystal_density(self):
        """Test density calculation."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        density = crystal.density
        self.assertGreater(density, 0)
    
    def test_crystal_pbc(self):
        """Test periodic boundary conditions."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice, pbc=[True, False, True])
        
        self.assertEqual(crystal.pbc, (True, False, True))
    
    def test_crystal_pbc_default(self):
        """Test default PBC."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertEqual(crystal.pbc, (True, True, True))
    
    def test_crystal_site_properties(self):
        """Test site properties."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        site_properties = [{'magmom': 2.0}, {'charge': -2}]
        crystal = Crystal(species, positions, lattice, site_properties=site_properties)
        
        self.assertEqual(len(crystal.site_properties), 2)
        self.assertEqual(crystal.sites[0].properties['magmom'], 2.0)
    
    def test_crystal_sites(self):
        """Test sites property."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        self.assertEqual(len(crystal.sites), 2)
        self.assertEqual(crystal.sites[0].specie, 'Si')
    
    def test_crystal_getitem(self):
        """Test indexing."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        site = crystal[0]
        self.assertEqual(site.specie, 'Si')
    
    def test_crystal_add_atom(self):
        """Test adding atom."""
        species = ['Si']
        positions = [[0, 0, 0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        result = crystal.add_atom('O', [0.5, 0.5, 0.5])
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result.sites), 2)

    def test_crystal_remove_atom(self):
        """Test removing atom."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        result = crystal.remove_atom(0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.species[0], 'O')
    
    def test_crystal_from_file_poscar(self):
        """Test reading POSCAR file using from_file."""
        poscar_file = Path(__file__).parent / "POSCAR-frac.vasp"
        if poscar_file.exists():
            crystal = Crystal.from_file(str(poscar_file))
            self.assertIsInstance(crystal, Crystal)
            self.assertGreater(len(crystal), 0)
    
    def test_crystal_to_file_poscar(self):
        """Test writing POSCAR file using io.write."""
        import tempfile
        from matsimpy.io import read, write
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vasp') as f:
            temp_file = f.name

        try:
            write(crystal, temp_file)
            # Verify file was created
            self.assertTrue(Path(temp_file).exists())
            # Read back to verify
            crystal2 = read(temp_file)
            self.assertEqual(len(crystal2), len(crystal))
        finally:
            Path(temp_file).unlink()
    
    
    def test_crystal_to_code_quantum_espresso(self):
        """Test writing DFT code input using to_code interface."""
        import tempfile
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            temp_file = f.name
        
        try:
            crystal.to_code('quantum_espresso', temp_file)
            self.assertTrue(Path(temp_file).exists())
            
            # Verify file content
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertIn('&system', content)
                self.assertIn('ATOMIC_POSITIONS', content)
                self.assertIn('CELL_PARAMETERS', content)
        finally:
            Path(temp_file).unlink()
    
    def test_crystal_to_code_qe_alias(self):
        """Test writing using 'qe' alias."""
        import tempfile
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f:
            temp_file = f.name
        
        try:
            crystal.to_code('qe', temp_file)
            self.assertTrue(Path(temp_file).exists())
        finally:
            Path(temp_file).unlink()
    
    def test_crystal_to_code_invalid_code(self):
        """Test to_code with invalid code name."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        with self.assertRaises(ValueError):
            crystal.to_code('invalid_code', 'test.in')
    
    def test_crystal_from_code_not_implemented(self):
        """Test from_code raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            Crystal.from_code('quantum_espresso', 'test.out')
    
    def test_crystal_str(self):
        """Test string representation."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        str_repr = str(crystal)
        self.assertIn('Crystal', str_repr)
        self.assertIn('atoms', str_repr)
    
    def test_crystal_repr(self):
        """Test representation."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        repr_str = repr(crystal)
        self.assertIn('Crystal', repr_str)
    
    def test_crystal_as_dict(self):
        """Test dictionary representation."""
        species = ['Si', 'O']
        positions = [[0, 0, 0], [0.5, 0.5, 0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        d = crystal.as_dict()
        self.assertIn('species', d)
        self.assertIn('positions', d)
        self.assertIn('lattice', d)
        self.assertIn('pbc', d)
    
    def test_crystal_from_dict(self):
        """Test creation from dictionary."""
        d = {
            'species': ['Si', 'O'],
            'positions': [[0, 0, 0], [0.5, 0.5, 0.5]],
            'lattice': {
                'lattice_vectors': [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
            },
            'pbc': [True, True, True],
            'site_properties': []
        }
        crystal = Crystal.from_dict(d)
        self.assertEqual(len(crystal), 2)
    
    def test_crystal_neighbor_list_small_cutoff(self):
        """Test neighbor list with small cutoff."""
        species = ['Si'] * 4
        positions = [[0, 0, 0], [0.1, 0, 0], [0, 0.1, 0], [0, 0, 0.1]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        neighbors = crystal.get_neighbor_list(1.0)
        self.assertIsInstance(neighbors, dict)
        self.assertEqual(len(neighbors), 4)
    
    def test_crystal_periodic_images(self):
        """Test periodic images generation."""
        species = ['Si'] * 2
        positions = [[0, 0, 0], [0.9, 0, 0]]  # Close to boundary
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        
        images = crystal._get_periodic_images(5.0)
        self.assertGreater(len(images), len(crystal.cart_positions))
    
    def test_crystal_wrap_positive(self):
        """Test wrapping positive fractional coordinates > 1."""
        species = ['Fe', 'O']
        positions = [[1.5, 2.3, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        result = crystal.wrap()
        np.testing.assert_array_almost_equal(
            result.frac_positions[0], [0.5, 0.3, 0.5], decimal=6
        )
        np.testing.assert_array_almost_equal(
            result.frac_positions[1], [0.2, 0.2, 0.2], decimal=6
        )
        # Verify sites are updated
        np.testing.assert_array_almost_equal(
            result.sites[0].frac_position, [0.5, 0.3, 0.5], decimal=6
        )
    
    def test_crystal_wrap_negative(self):
        """Test wrapping negative fractional coordinates."""
        species = ['Fe', 'O']
        positions = [[-0.3, -1.2, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        result = crystal.wrap()
        np.testing.assert_array_almost_equal(
            result.frac_positions[0], [0.7, 0.8, 0.5], decimal=6
        )
        # Verify Cartesian coordinates are updated
        expected_cart = np.dot([0.7, 0.8, 0.5], lattice.matrix)
        np.testing.assert_array_almost_equal(
            result.cart_positions[0], expected_cart, decimal=6
        )
    
    def test_crystal_wrap_mixed(self):
        """Test wrapping mixed positive and negative coordinates."""
        species = ['Fe', 'O', 'Si']
        positions = [[1.5, -0.3, 2.7], [0.2, 0.2, 0.2], [-0.1, 1.1, -0.5]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        result = crystal.wrap()
        np.testing.assert_array_almost_equal(
            result.frac_positions[0], [0.5, 0.7, 0.7], decimal=6
        )
        np.testing.assert_array_almost_equal(
            result.frac_positions[1], [0.2, 0.2, 0.2], decimal=6
        )
        np.testing.assert_array_almost_equal(
            result.frac_positions[2], [0.9, 0.1, 0.5], decimal=6
        )
    
    def test_crystal_wrap_already_in_range(self):
        """Test wrapping coordinates already in [0, 1) range."""
        species = ['Fe', 'O']
        positions = [[0.3, 0.5, 0.7], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        original_frac = crystal.frac_positions.copy()
        original_cart = crystal.cart_positions.copy()

        result = crystal.wrap()
        # Should remain unchanged
        np.testing.assert_array_almost_equal(
            result.frac_positions, original_frac, decimal=6
        )
        np.testing.assert_array_almost_equal(
            result.cart_positions, original_cart, decimal=6
        )
    
    def test_crystal_wrap_method_chaining(self):
        """Test wrap returns new crystal."""
        species = ['Fe', 'O']
        positions = [[1.5, -0.3, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        original_frac = crystal.frac_positions.copy()
        result = crystal.wrap()
        # Should return new object for chaining
        self.assertIsNot(result, crystal)
        # Original should be unchanged
        np.testing.assert_array_almost_equal(
            crystal.frac_positions, original_frac, decimal=6
        )
        # Result should be wrapped
        np.testing.assert_array_almost_equal(
            result.frac_positions[0], [0.5, 0.7, 0.5], decimal=6
        )
    
    def test_crystal_wrap_updates_sites(self):
        """Test that wrap updates all sites correctly."""
        species = ['Fe', 'O']
        positions = [[1.5, -0.3, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        result = crystal.wrap()
        # Verify sites match wrapped positions
        np.testing.assert_array_almost_equal(
            result.sites[0].frac_position, result.frac_positions[0], decimal=6
        )
        np.testing.assert_array_almost_equal(
            result.sites[1].frac_position, result.frac_positions[1], decimal=6
        )
        # Verify sites' Cartesian coordinates match
        np.testing.assert_array_almost_equal(
            result.sites[0].cart_position, result.cart_positions[0], decimal=6
        )
        np.testing.assert_array_almost_equal(
            result.sites[1].cart_position, result.cart_positions[1], decimal=6
        )
    
    def test_crystal_wrap_original_unchanged(self):
        species = ['Fe', 'O']
        positions = [[1.5, -0.3, 0.5], [0.2, 0.2, 0.2]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)
        original_frac = crystal.frac_positions.copy()
        result = crystal.wrap()
        self.assertIsNot(result, crystal)
        self.assertTrue(np.allclose(crystal.frac_positions, original_frac))
    
    def test_crystal_wrap_boundary_values(self):
        """Test wrapping boundary values (0.0, 1.0, etc.)."""
        species = ['Fe', 'O']
        # Test exactly 1.0 (should wrap to 0.0)
        positions = [[1.0, 1.0, 1.0], [0.0, 0.0, 0.0]]
        lattice = Lattice.cubic(10.0)
        crystal = Crystal(species, positions, lattice)

        result = crystal.wrap()
        np.testing.assert_array_almost_equal(
            result.frac_positions[0], [0.0, 0.0, 0.0], decimal=6
        )
        np.testing.assert_array_almost_equal(
            result.frac_positions[1], [0.0, 0.0, 0.0], decimal=6
        )

        # Test values just below 1.0 (should remain unchanged)
        positions2 = [[0.999, 0.999, 0.999], [0.001, 0.001, 0.001]]
        crystal2 = Crystal(species, positions2, lattice)
        result2 = crystal2.wrap()
        np.testing.assert_array_almost_equal(
            result2.frac_positions[0], [0.999, 0.999, 0.999], decimal=6
        )

if __name__ == '__main__':
    unittest.main()
