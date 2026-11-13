"""
Tests for ParameterSweep class.
"""

import unittest
from matsimpy.transformation.composite import ParameterSweep
from matsimpy.transformation import apply_strain, make_supercell, translate
from matsimpy.builders.bulk import from_prototype
from matsimpy.core import Molecule
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.transformation import move_atoms


def identity_with_kwargs(structure, **kwargs):
    return structure.copy()


class TestParameterSweep(unittest.TestCase):
    """Test cases for ParameterSweep."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
    
    
    
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
                            [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]],
                        ]
                    }
                }
            },
            mode='zip'
        )

        self.assertEqual(len(sweep), 3)

        structures = list(sweep)
        self.assertEqual(len(structures), 3)

    def test_zip_mode_rejects_unequal_lengths(self):
        """zip mode used to pad the shorter list with its last value."""
        with self.assertRaisesRegex(ValueError, "equal length"):
            ParameterSweep(
                base_structure=self.crystal,
                transformations={
                    'supercell': {'func': make_supercell,
                                  'params': {'scaling_matrix': [[1, 1, 1], [2, 2, 2]]}},
                    'strain': {'func': apply_strain,
                               'params': {'strain_matrix': [[[0.0, 0, 0], [0, 0, 0], [0, 0, 0]]]}},
                },
                mode='zip',
            )
    
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
    
    def test_custom_mode_requires_combinations(self):
        """Test that custom mode requires explicit combinations."""
        with self.assertRaises(ValueError):
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

    def test_custom_mode_uses_explicit_combinations(self):
        """Test custom mode with caller-provided parameter combinations."""
        sweep = ParameterSweep(
            base_structure=self.crystal,
            transformations={
                'supercell': {
                    'func': make_supercell,
                    'params': {'scaling_matrix': [[2, 2, 2], [3, 3, 3]]}
                }
            },
            mode='custom',
            custom_combinations=[
                {'supercell': {'scaling_matrix': [2, 1, 1]}},
                {'supercell': {'scaling_matrix': [1, 2, 1]}},
            ],
        )

        structures = list(sweep)

        self.assertEqual(len(structures), 2)
        self.assertEqual(len(structures[0][0]), len(self.crystal) * 2)
        self.assertEqual(len(structures[1][0]), len(self.crystal) * 2)

    def test_cartesian_sweep_does_not_materialize_all_combinations(self):
        """Large Cartesian sweeps should construct and yield lazily."""
        values = list(range(100))
        sweep = ParameterSweep(
            base_structure=self.molecule,
            transformations={
                'identity': {
                    'func': identity_with_kwargs,
                    'params': {
                        'p0': values,
                        'p1': values,
                        'p2': values,
                        'p3': values,
                        'p4': values,
                        'p5': values,
                    }
                }
            },
            mode='cartesian',
        )

        self.assertEqual(len(sweep), 100 ** 6)
        _structure, params = next(iter(sweep))
        self.assertEqual(params['identity']['p0'], 0)
        self.assertEqual(params['identity']['p5'], 0)

    def test_generator_custom_sweep_has_unknown_length(self):
        """Custom generator sweeps can be iterated without being materialized."""
        def combinations(_transformations):
            yield {'identity': {'label': 'first'}}

        sweep = ParameterSweep(
            base_structure=self.molecule,
            transformations={
                'identity': {
                    'func': identity_with_kwargs,
                    'params': {'label': ['fallback']}
                }
            },
            mode='custom',
            custom_combinations=combinations,
        )

        with self.assertRaises(TypeError):
            len(sweep)
        _structure, params = next(iter(sweep))
        self.assertEqual(params['identity']['label'], 'first')


def test_custom_mode_applies_steps_in_declared_order():
    sweep = ParameterSweep(
        Crystal(["Cu"], [[0, 0, 0]], Lattice.cubic(3.0)),
        {
            "supercell": {"func": make_supercell, "params": {"scaling_matrix": [[2, 1, 1]]}},
            "move": {"func": move_atoms, "params": {"indices": [1], "displacement": [[0.1, 0, 0]]}},
        },
        mode="custom",
        # listed in the other order: atom 1 only exists after the supercell step
        custom_combinations=[{"move": {"indices": 1, "displacement": [0.1, 0, 0]},
                              "supercell": {"scaling_matrix": [2, 1, 1]}}],
    )
    ((structure, _),) = list(sweep)
    np.testing.assert_allclose(structure.cart_positions[1], [3.1, 0, 0], atol=1e-12)


if __name__ == '__main__':
    unittest.main()
