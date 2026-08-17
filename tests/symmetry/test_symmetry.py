"""Tests for symmetry analysis module."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.symmetry import SymmetryAnalyzer, analyze_symmetry

class TestSymmetryAnalyzer(unittest.TestCase):
    """Tests for SymmetryAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = SymmetryAnalyzer()
        
        # Create test crystal (simple cubic)
        self.test_crystal = Crystal(
            ['Si', 'Si'],
            [[0, 0, 0], [0.25, 0.25, 0.25]],
            Lattice.cubic(5.43)
        )
        
        # Create test molecule (water)
        self.test_molecule = Molecule(
            ['O', 'H', 'H'],
            [[0, 0, 0], [0.96, 0, 0], [-0.96, 0, 0]]
        )
    
    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = SymmetryAnalyzer(symprec=1e-4, angle_tolerance=5.0)
        self.assertEqual(analyzer.symprec, 1e-4)
        self.assertEqual(analyzer.angle_tolerance, 5.0)
    
    def test_symmetry_data_loading(self):
        """Test that symmetry data is loaded."""
        # Data should be loaded during initialization
        self.assertIsNotNone(self.analyzer._symmetry_data)
    
    def test_get_space_group_info(self):
        """Test getting space group information."""
        info = self.analyzer.get_space_group_info('Pm-3m')
        self.assertIsNotNone(info)
        self.assertIn('int_number', info)
        self.assertIn('point_group', info)
        self.assertEqual(info['int_number'], 221)
    
    def test_get_point_group_encoding(self):
        """Test getting point group encoding."""
        encoding = self.analyzer.get_point_group_encoding('m-3m')
        self.assertIsNotNone(encoding)
        self.assertIsInstance(encoding, str)
    
    def test_get_generator_matrix(self):
        """Test getting generator matrices."""
        # Test identity generator
        gen_a = self.analyzer.get_generator_matrix('a')
        self.assertIsNotNone(gen_a)
        self.assertTrue(np.allclose(gen_a, np.eye(3)))
        
        # Test inversion generator
        gen_h = self.analyzer.get_generator_matrix('h')
        self.assertIsNotNone(gen_h)
        self.assertTrue(np.allclose(gen_h, -np.eye(3)))
    
    def test_get_generator_matrix_invalid(self):
        """Test getting invalid generator matrix."""
        gen = self.analyzer.get_generator_matrix('invalid')
        self.assertIsNone(gen)
    
    def test_get_point_group_order(self):
        """Test getting point group order."""
        order = self.analyzer._get_point_group_order('Oh')
        self.assertEqual(order, 48)
        
        order = self.analyzer._get_point_group_order('C1')
        self.assertEqual(order, 1)
        
        order = self.analyzer._get_point_group_order('Td')
        self.assertEqual(order, 24)
    
    def test_element_to_number(self):
        """Test element to number conversion."""
        self.assertEqual(self.analyzer._element_to_number('Si'), 14)
        self.assertEqual(self.analyzer._element_to_number('O'), 8)
        self.assertEqual(self.analyzer._element_to_number('H'), 1)
        self.assertEqual(self.analyzer._element_to_number(14), 14)  # Already a number
    
    def test_get_crystal_system(self):
        """Test crystal system determination."""
        self.assertEqual(self.analyzer._get_crystal_system(1), "Triclinic")
        self.assertEqual(self.analyzer._get_crystal_system(15), "Monoclinic")
        self.assertEqual(self.analyzer._get_crystal_system(74), "Orthorhombic")
        self.assertEqual(self.analyzer._get_crystal_system(142), "Tetragonal")
        self.assertEqual(self.analyzer._get_crystal_system(167), "Trigonal")
        self.assertEqual(self.analyzer._get_crystal_system(194), "Hexagonal")
        self.assertEqual(self.analyzer._get_crystal_system(230), "Cubic")
        self.assertEqual(self.analyzer._get_crystal_system(999), "Unknown")

    def test_bound_crystal_spglib_services(self):
        """Test bound-crystal convenience methods backed by spglib."""
        analyzer = SymmetryAnalyzer(self.test_crystal, symprec=1e-5)

        mesh = analyzer.get_ir_reciprocal_mesh((2, 2, 2))
        self.assertEqual(sum(weight for _, weight in mesh), 8)
        self.assertTrue(all(len(kpoint) == 3 for kpoint, _ in mesh))

        primitive = analyzer.get_primitive_standard_structure()
        conventional = analyzer.get_conventional_standard_structure()
        self.assertIsInstance(primitive, Crystal)
        self.assertIsInstance(conventional, Crystal)
        self.assertEqual(primitive.pbc, self.test_crystal.pbc)

    def test_spglib_services_require_crystal_argument(self):
        """Test unbound analyzer raises a precise error for service methods."""
        with self.assertRaisesRegex(ValueError, "crystal must be supplied"):
            self.analyzer.get_ir_reciprocal_mesh((2, 2, 2))

    def test_spglib_services_raise_precise_optional_dependency_error(self):
        """Test service methods use the MatSimPy analysis extra message."""
        import matsimpy.symmetry.analyzer as analyzer_module

        original_has_spglib = analyzer_module.HAS_SPGLIB
        analyzer_module.HAS_SPGLIB = False
        try:
            analyzer = SymmetryAnalyzer(self.test_crystal)
            with self.assertRaisesRegex(
                ImportError,
                r"spglib is required; install MatSimPy\[analysis\]",
            ):
                analyzer.get_ir_reciprocal_mesh((2, 2, 2))
        finally:
            analyzer_module.HAS_SPGLIB = original_has_spglib

class TestCrystalSymmetryAnalysis(unittest.TestCase):
    """Tests for crystal symmetry analysis."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = SymmetryAnalyzer()
        
        # Simple cubic structure (Fd-3m for diamond)
        self.diamond_crystal = Crystal(
            ['C', 'C'],
            [[0, 0, 0], [0.25, 0.25, 0.25]],
            Lattice.cubic(3.57)
        )
        
        # Simple cubic (Pm-3m)
        self.simple_cubic = Crystal(
            ['Si'],
            [[0, 0, 0]],
            Lattice.cubic(5.43)
        )
    
    @unittest.skipUnless(
        __import__('sys').modules.get('spglib') is not None,
        "spglib not available"
    )
    def test_analyze_crystal_basic(self):
        """Test basic crystal analysis."""
        result = self.analyzer.analyze_crystal(self.simple_cubic)
        
        self.assertIsInstance(result, dict)
        self.assertIn('space_group_number', result)
        self.assertIn('space_group_symbol', result)
        self.assertIn('point_group', result)
        self.assertIn('crystal_system', result)
    
    @unittest.skipUnless(
        __import__('sys').modules.get('spglib') is not None,
        "spglib not available"
    )
    def test_analyze_crystal_without_spglib(self):
        """Test that ImportError is raised without spglib."""
        # Create analyzer without spglib
        import matsimpy.symmetry.analyzer as analyzer_module
        original_has_spglib = analyzer_module.HAS_SPGLIB
        analyzer_module.HAS_SPGLIB = False
        
        try:
            analyzer = SymmetryAnalyzer()
            with self.assertRaises(ImportError):
                analyzer.analyze_crystal(self.simple_cubic)
        finally:
            analyzer_module.HAS_SPGLIB = original_has_spglib
    
    def test_format_symmetry_operations(self):
        """Test formatting symmetry operations."""
        # Mock dataset
        dataset = {
            'rotations': np.array([np.eye(3), -np.eye(3)]),
            'translations': np.array([[0, 0, 0], [0.5, 0.5, 0.5]])
        }
        
        ops = self.analyzer._format_symmetry_operations(dataset)
        
        self.assertEqual(len(ops), 2)
        self.assertIn('rotation', ops[0])
        self.assertIn('translation', ops[0])

class TestMoleculeSymmetryAnalysis(unittest.TestCase):
    """Tests for molecule symmetry analysis."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = SymmetryAnalyzer()
        
        # Linear molecule (CO2)
        self.co2 = Molecule(
            ['C', 'O', 'O'],
            [[0, 0, 0], [1.16, 0, 0], [-1.16, 0, 0]]
        )
        
        # Water molecule
        self.water = Molecule(
            ['O', 'H', 'H'],
            [[0, 0, 0], [0.96, 0, 0], [-0.96, 0, 0]]
        )
    
    def test_analyze_molecule_basic(self):
        """Test basic molecule analysis."""
        result = self.analyzer.analyze_molecule(self.water)
        
        self.assertIsInstance(result, dict)
        self.assertIn('point_group', result)
        self.assertIn('symmetry_operations', result)
        self.assertIn('rotation_axes', result)
        self.assertIn('mirror_planes', result)
        self.assertIn('inversion_center', result)
        self.assertIn('order', result)
    
    def test_analyze_molecule_no_data(self):
        """Test molecule analysis without symmetry data."""
        analyzer = SymmetryAnalyzer()
        # Temporarily disable data loading
        original_load = analyzer._load_symmetry_data
        analyzer._load_symmetry_data = lambda: None
        analyzer._symmetry_data = None
        
        try:
            with self.assertRaises(RuntimeError):
                analyzer.analyze_molecule(self.water)
        finally:
            analyzer._load_symmetry_data = original_load
    
    def test_is_linear(self):
        """Test linear molecule detection."""
        # CO2 should be linear
        positions = np.array([[0, 0, 0], [1.16, 0, 0], [-1.16, 0, 0]])
        self.assertTrue(self.analyzer._is_linear(positions, tolerance=0.1))
        
        # Water should not be linear (bent)
        positions = np.array([[0, 0, 0], [0.96, 0, 0.76], [-0.96, 0, 0.76]])
        self.assertFalse(self.analyzer._is_linear(positions, tolerance=0.1))
    
    def test_has_inversion_center(self):
        """Test inversion center detection."""
        # CO2 has inversion center (linear, symmetric)
        positions = np.array([[0, 0, 0], [1.16, 0, 0], [-1.16, 0, 0]])
        self.assertTrue(self.analyzer._has_inversion_center(positions, tolerance=0.1))
        
        # Water (bent) does not have inversion center
        # Actual water geometry: O at origin, H atoms at angles
        positions = np.array([[0, 0, 0], [0.96, 0, 0.76], [-0.96, 0, 0.76]])
        self.assertFalse(self.analyzer._has_inversion_center(positions, tolerance=0.1))
        
        # Asymmetric molecule
        positions = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        self.assertFalse(self.analyzer._has_inversion_center(positions, tolerance=0.1))
    
    def test_find_rotation_axes(self):
        """Test rotation axis finding."""
        # Linear molecule along z-axis
        positions = np.array([[0, 0, 0], [0, 0, 1], [0, 0, -1]])
        axes = self.analyzer._find_rotation_axes(positions, tolerance=0.1)
        
        # Should find at least the principal axis
        self.assertIsInstance(axes, list)
    
    def test_find_mirror_planes(self):
        """Test mirror plane finding."""
        # Symmetric molecule
        positions = np.array([[0, 0, 0], [1, 0, 0], [-1, 0, 0]])
        planes = self.analyzer._find_mirror_planes(positions, tolerance=0.1)
        
        self.assertIsInstance(planes, list)
    
    def test_rotation_matrix(self):
        """Test rotation matrix generation."""
        axis = np.array([0, 0, 1])
        angle = np.pi / 2
        
        rot_matrix = self.analyzer._rotation_matrix(axis, angle)
        
        self.assertEqual(rot_matrix.shape, (3, 3))
        # Should be orthogonal
        self.assertTrue(np.allclose(rot_matrix @ rot_matrix.T, np.eye(3)))
    
    def test_detect_point_group_linear(self):
        """Test point group detection for linear molecules."""
        # Linear with inversion
        positions = np.array([[0, 0, 0], [1, 0, 0], [-1, 0, 0]])
        pg = self.analyzer._detect_point_group(positions, ['O', 'C', 'O'], tolerance=0.1)
        self.assertIn(pg, ['D∞h', 'C∞v'])
        
        # Single atom
        positions = np.array([[0, 0, 0]])
        pg = self.analyzer._detect_point_group(positions, ['He'], tolerance=0.1)
        self.assertEqual(pg, 'Kh')

class TestConvenienceFunction(unittest.TestCase):
    """Tests for analyze_symmetry convenience function."""
    
    def test_analyze_symmetry_crystal(self):
        """Test analyze_symmetry with crystal."""
        crystal = Crystal(
            ['Si'],
            [[0, 0, 0]],
            Lattice.cubic(5.43)
        )
        
        result = analyze_symmetry(crystal, symprec=1e-5)
        
        self.assertIsInstance(result, dict)
        self.assertIn('space_group_number', result)
    
    def test_analyze_symmetry_molecule(self):
        """Test analyze_symmetry with molecule."""
        molecule = Molecule(
            ['O', 'H', 'H'],
            [[0, 0, 0], [0.96, 0, 0], [-0.96, 0, 0]]
        )
        
        result = analyze_symmetry(molecule, tolerance=0.1)
        
        self.assertIsInstance(result, dict)
        self.assertIn('point_group', result)
    
    def test_analyze_symmetry_invalid_type(self):
        """Test analyze_symmetry with invalid type."""
        with self.assertRaises(TypeError):
            analyze_symmetry("invalid")

if __name__ == '__main__':
    unittest.main()
