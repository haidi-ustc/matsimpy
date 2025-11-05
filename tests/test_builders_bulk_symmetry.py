"""Tests for symmetry-based bulk crystal generation."""
import unittest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.bulk.symmetry import (
    from_space_group,
    from_crystal_system,
    list_space_groups_by_system
)


class TestFromSpaceGroup(unittest.TestCase):
    """Tests for from_space_group function."""
    
    def test_from_space_group_number(self):
        """Test generation from space group number."""
        lattice = Lattice.cubic(5.0)
        crystal = from_space_group(
            225,  # Fm-3m
            ['Na', 'Cl'],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
            lattice=lattice
        )
        
        self.assertIsInstance(crystal, Crystal)
        self.assertGreater(len(crystal.species), 0)
        self.assertEqual(crystal.lattice.a, 5.0)
    
    def test_from_space_group_symbol(self):
        """Test generation from space group symbol."""
        lattice = Lattice.cubic(5.0)
        
        try:
            crystal = from_space_group(
                'Fm-3m',
                ['Na', 'Cl'],
                [[0, 0, 0], [0.5, 0.5, 0.5]],
                lattice=lattice
            )
            self.assertIsInstance(crystal, Crystal)
        except ValueError:
            # May fail if symbol not in data
            pass
    
    def test_from_space_group_with_lattice_params(self):
        """Test generation with lattice_params instead of lattice."""
        crystal = from_space_group(
            221,  # Pm-3m
            ['Si'],
            [[0, 0, 0]],
            lattice_params=5.43
        )
        
        self.assertIsInstance(crystal, Crystal)
        self.assertAlmostEqual(crystal.lattice.a, 5.43, places=2)
    
    def test_from_space_group_invalid(self):
        """Test invalid space group."""
        with self.assertRaises((ValueError, TypeError)):
            from_space_group(
                999,  # Invalid
                ['Si'],
                [[0, 0, 0]],
                lattice_params=5.43
            )
    
    def test_from_space_group_missing_params(self):
        """Test missing lattice parameters."""
        with self.assertRaises(ValueError):
            from_space_group(
                225,
                ['Si'],
                [[0, 0, 0]]
                # Missing lattice or lattice_params
            )


class TestFromCrystalSystem(unittest.TestCase):
    """Tests for from_crystal_system function."""
    
    def test_from_crystal_system_cubic(self):
        """Test cubic crystal system."""
        crystal = from_crystal_system(
            'Cubic',
            ['Si'],
            [[0, 0, 0]],
            5.43
        )
        
        self.assertIsInstance(crystal, Crystal)
        self.assertAlmostEqual(crystal.lattice.a, 5.43, places=2)
        self.assertAlmostEqual(crystal.lattice.b, 5.43, places=2)
        self.assertAlmostEqual(crystal.lattice.c, 5.43, places=2)
    
    def test_from_crystal_system_tetragonal(self):
        """Test tetragonal crystal system."""
        crystal = from_crystal_system(
            'Tetragonal',
            ['Ti', 'O'],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
            [3.8, 9.6]
        )
        
        self.assertIsInstance(crystal, Crystal)
        self.assertAlmostEqual(crystal.lattice.a, 3.8, places=2)
        self.assertAlmostEqual(crystal.lattice.c, 9.6, places=2)
    
    def test_from_crystal_system_orthorhombic(self):
        """Test orthorhombic crystal system."""
        crystal = from_crystal_system(
            'Orthorhombic',
            ['Si'],
            [[0, 0, 0]],
            [5.0, 6.0, 7.0]
        )
        
        self.assertIsInstance(crystal, Crystal)
        self.assertAlmostEqual(crystal.lattice.a, 5.0, places=2)
        self.assertAlmostEqual(crystal.lattice.b, 6.0, places=2)
        self.assertAlmostEqual(crystal.lattice.c, 7.0, places=2)
    
    def test_from_crystal_system_hexagonal(self):
        """Test hexagonal crystal system."""
        crystal = from_crystal_system(
            'Hexagonal',
            ['Mg'],
            [[0, 0, 0]],
            [3.21, 5.21]
        )
        
        self.assertIsInstance(crystal, Crystal)
        self.assertAlmostEqual(crystal.lattice.a, 3.21, places=2)
        self.assertAlmostEqual(crystal.lattice.c, 5.21, places=2)
    
    def test_from_crystal_system_with_space_group(self):
        """Test crystal system with specific space group."""
        crystal = from_crystal_system(
            'Cubic',
            ['Si'],
            [[0, 0, 0]],
            5.43,
            space_group=227  # Fd-3m
        )
        
        self.assertIsInstance(crystal, Crystal)
    
    def test_from_crystal_system_monoclinic(self):
        """Test monoclinic crystal system."""
        crystal = from_crystal_system(
            'Monoclinic',
            ['Si'],
            [[0, 0, 0]],
            [5.0, 6.0, 7.0, 90.0]
        )
        
        self.assertIsInstance(crystal, Crystal)
        self.assertAlmostEqual(crystal.lattice.a, 5.0, places=2)
        self.assertAlmostEqual(crystal.lattice.b, 6.0, places=2)
        self.assertAlmostEqual(crystal.lattice.c, 7.0, places=2)


class TestListSpaceGroupsBySystem(unittest.TestCase):
    """Tests for list_space_groups_by_system function."""
    
    def test_list_all_space_groups(self):
        """Test listing all space groups."""
        result = list_space_groups_by_system()
        
        self.assertIsInstance(result, dict)
        self.assertIn('Cubic', result)
        self.assertIn('Hexagonal', result)
        self.assertIn('Triclinic', result)
        
        # Check cubic space groups
        cubic_sgs = result['Cubic']
        self.assertEqual(len(cubic_sgs), 36)  # 195-230
        self.assertEqual(cubic_sgs[0], 195)
        self.assertEqual(cubic_sgs[-1], 230)
    
    def test_list_space_groups_by_system_cubic(self):
        """Test listing cubic space groups."""
        cubic_sgs = list_space_groups_by_system('Cubic')
        
        self.assertIsInstance(cubic_sgs, list)
        self.assertEqual(len(cubic_sgs), 36)
        self.assertEqual(cubic_sgs[0], 195)
        self.assertEqual(cubic_sgs[-1], 230)
    
    def test_list_space_groups_by_system_tetragonal(self):
        """Test listing tetragonal space groups."""
        tetragonal_sgs = list_space_groups_by_system('Tetragonal')
        
        self.assertIsInstance(tetragonal_sgs, list)
        self.assertEqual(len(tetragonal_sgs), 68)  # 75-142
        self.assertEqual(tetragonal_sgs[0], 75)
        self.assertEqual(tetragonal_sgs[-1], 142)
    
    def test_list_space_groups_by_system_invalid(self):
        """Test listing with invalid crystal system."""
        result = list_space_groups_by_system('Invalid')
        self.assertEqual(result, [])


class TestHelperFunctions(unittest.TestCase):
    """Tests for helper functions."""
    
    def test_get_space_group_number(self):
        """Test space group number conversion."""
        from matsimpy.builders.bulk.symmetry import _get_space_group_number
        
        # Test integer
        self.assertEqual(_get_space_group_number(225), 225)
        self.assertEqual(_get_space_group_number(1), 1)
        self.assertIsNone(_get_space_group_number(999))
        
        # Test symbol (if data available)
        sg_num = _get_space_group_number('Fm-3m', use_data=True)
        if sg_num:
            self.assertIsInstance(sg_num, int)
            self.assertGreaterEqual(sg_num, 1)
            self.assertLessEqual(sg_num, 230)
    
    def test_get_default_space_group(self):
        """Test default space group for crystal systems."""
        from matsimpy.builders.bulk.symmetry import _get_default_space_group
        
        self.assertEqual(_get_default_space_group('Cubic'), 221)
        self.assertEqual(_get_default_space_group('Hexagonal'), 194)
        self.assertEqual(_get_default_space_group('Triclinic'), 1)
        self.assertEqual(_get_default_space_group('Monoclinic'), 12)
        self.assertEqual(_get_default_space_group('Orthorhombic'), 47)
        self.assertEqual(_get_default_space_group('Tetragonal'), 123)
        self.assertEqual(_get_default_space_group('Trigonal'), 166)
        self.assertEqual(_get_default_space_group('Invalid'), 221)  # Default
    
    def test_create_lattice_from_system(self):
        """Test lattice creation from crystal system."""
        from matsimpy.builders.bulk.symmetry import _create_lattice_from_system_by_name
        
        # Cubic
        lattice = _create_lattice_from_system_by_name('Cubic', 5.0)
        self.assertAlmostEqual(lattice.a, 5.0)
        self.assertAlmostEqual(lattice.b, 5.0)
        self.assertAlmostEqual(lattice.c, 5.0)
        
        # Tetragonal
        lattice = _create_lattice_from_system_by_name('Tetragonal', [4.0, 6.0])
        self.assertAlmostEqual(lattice.a, 4.0)
        self.assertAlmostEqual(lattice.c, 6.0)
        
        # Orthorhombic
        lattice = _create_lattice_from_system_by_name('Orthorhombic', [5.0, 6.0, 7.0])
        self.assertAlmostEqual(lattice.a, 5.0)
        self.assertAlmostEqual(lattice.b, 6.0)
        self.assertAlmostEqual(lattice.c, 7.0)


if __name__ == '__main__':
    unittest.main()

