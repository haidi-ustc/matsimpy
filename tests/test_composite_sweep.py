"""
Tests for ParameterSweep class.
"""

import unittest
from matsimpy.transformation.composite import ParameterSweep
from matsimpy.transformation import apply_strain, make_supercell, translate
from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Molecule


class TestParameterSweep(unittest.TestCase):
    """Test cases for ParameterSweep."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    def test_single_transformation_cartesian(self):
        """Test sweep with single transformation in cartesian mode."""
        sweep = ParameterSweep(
            base_structure=self.crystal,
            transformations={
                'supercell': {
                    'func': make_supercell,
                    'params': {
                        'scaling_matrix': [[2, 2, 2], [3, 3, 3]]
                    }
                }
            },
            mode='cartesian'
        )
        
        self.assertEqual(len(sweep), 2)
        
        structures = list(sweep)
        self.assertEqual(len(structures), 2)
        
        # Check first structure (2x2x2 supercell)
        struct1, params1 = structures[0]
        self.assertEqual(len(struct1), len(self.crystal) * 8)  # 2^3 = 8
        self.assertIn('supercell', params1)
        
        # Check second structure (3x3x3 supercell)
        struct2, params2 = structures[1]
        self.assertEqual(len(struct2), len(self.crystal) * 27)  # 3^3 = 27
    
    def test_multiple_transformations_cartesian(self):
        """Test sweep with multiple transformations in cartesian mode."""
        sweep = ParameterSweep(
            base_structure=self.crystal,
            transformations={
                'supercell': {
                    'func': make_supercell,
                    'params': {
                        'scaling_matrix': [[2, 2, 2], [3, 3, 3]]
                    }
                },
                'strain': {
                    'func': apply_strain,
                    'params': {
                        'strain_matrix': [
                            [[0.00, 0, 0], [0, 0, 0], [0, 0, 0]],
                            [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
                        ]
                    }
                }
            },
            mode='cartesian'
        )
        
        # Should have 2 × 2 = 4 combinations
        self.assertEqual(len(sweep), 4)
        
        structures = list(sweep)
        self.assertEqual(len(structures), 4)
        
        # Check that all combinations are present
        seen_combos = set()
        for struct, params in structures:
            # Convert lists to tuples for hashing
            supercell_key = tuple(params['supercell']['scaling_matrix'])
            strain_key = params['strain']['strain_matrix'][0][0]  # First element of strain
            combo_key = (supercell_key, strain_key)
            seen_combos.add(combo_key)
        
        self.assertEqual(len(seen_combos), 4)  # All unique
    
    def test_zip_mode(self):
        """Test sweep in zip mode (parallel iteration)."""
        sweep = ParameterSweep(
            base_structure=self.crystal,
            transformations={
                'supercell': {
                    'func': make_supercell,
                    'params': {
                        'scaling_matrix': [[2, 2, 2], [3, 3, 3], [4, 4, 4]]
                    }
                },
                'strain': {
                    'func': apply_strain,
                    'params': {
                        'strain_matrix': [
                            [[0.00, 0, 0], [0, 0, 0], [0, 0, 0]],
                            [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
                        ]
                    }
                }
            },
            mode='zip'
        )
        
        # Should have max(3, 2) = 3 combinations
        self.assertEqual(len(sweep), 3)
        
        structures = list(sweep)
        self.assertEqual(len(structures), 3)
    
    def test_multiple_parameters_per_transformation(self):
        """Test transformation with multiple parameters."""
        sweep = ParameterSweep(
            base_structure=self.molecule,
            transformations={
                'translate': {
                    'func': translate,
                    'params': {
                        'vector': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
                    }
                }
            },
            mode='cartesian'
        )
        
        self.assertEqual(len(sweep), 3)
        
        structures = list(sweep)
        self.assertEqual(len(structures), 3)
    
    def test_generate_method(self):
        """Test generate() method returns list."""
        sweep = ParameterSweep(
            base_structure=self.crystal,
            transformations={
                'supercell': {
                    'func': make_supercell,
                    'params': {
                        'scaling_matrix': [[2, 2, 2]]
                    }
                }
            }
        )
        
        structures = sweep.generate()
        self.assertIsInstance(structures, list)
        self.assertEqual(len(structures), 1)
    
    def test_invalid_mode(self):
        """Test that invalid mode raises error."""
        with self.assertRaises(ValueError):
            ParameterSweep(
                base_structure=self.crystal,
                transformations={
                    'supercell': {
                        'func': make_supercell,
                        'params': {'scaling_matrix': [[2, 2, 2]]}
                    }
                },
                mode='invalid_mode'
            )
    
    def test_missing_func(self):
        """Test that missing func raises error."""
        with self.assertRaises(ValueError):
            ParameterSweep(
                base_structure=self.crystal,
                transformations={
                    'supercell': {
                        'params': {'scaling_matrix': [[2, 2, 2]]}
                    }
                }
            )
    
    def test_missing_params(self):
        """Test that missing params raises error."""
        with self.assertRaises(ValueError):
            ParameterSweep(
                base_structure=self.crystal,
                transformations={
                    'supercell': {
                        'func': make_supercell
                    }
                }
            )
    
    def test_empty_params_list(self):
        """Test that empty params list raises error."""
        with self.assertRaises(ValueError):
            ParameterSweep(
                base_structure=self.crystal,
                transformations={
                    'supercell': {
                        'func': make_supercell,
                        'params': {'scaling_matrix': []}
                    }
                }
            )
    
    def test_no_transformations(self):
        """Test that no transformations raises error."""
        with self.assertRaises(ValueError):
            ParameterSweep(
                base_structure=self.crystal,
                transformations={}
            )
    
    def test_repr(self):
        """Test string representation."""
        sweep = ParameterSweep(
            base_structure=self.crystal,
            transformations={
                'supercell': {
                    'func': make_supercell,
                    'params': {'scaling_matrix': [[2, 2, 2], [3, 3, 3]]}
                }
            }
        )
        
        repr_str = repr(sweep)
        self.assertIn("ParameterSweep", repr_str)
        self.assertIn("cartesian", repr_str)
        self.assertIn("2", repr_str)  # Number of combinations
    
    def test_custom_mode_not_implemented(self):
        """Test that custom mode raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            ParameterSweep(
                base_structure=self.crystal,
                transformations={
                    'supercell': {
                        'func': make_supercell,
                        'params': {'scaling_matrix': [[2, 2, 2]]}
                    }
                },
                mode='custom'
            )


if __name__ == '__main__':
    unittest.main()

