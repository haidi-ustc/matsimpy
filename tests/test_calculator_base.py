"""
Tests for base Calculator class.
"""

import unittest
import numpy as np
from matsimpy import Crystal, Molecule, Lattice
from matsimpy.calculator.base import Calculator


class MockCalculator(Calculator):
    """Mock calculator for testing base class."""
    
    def _compute(self):
        """Mock computation that sets fake results."""
        self.results['energy'] = 1.0
        self.results['forces'] = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        self.results['stress'] = np.eye(3)


class TestCalculatorBase(unittest.TestCase):
    """Tests for base Calculator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = MockCalculator(sigma=3.4, epsilon=0.01)
        self.crystal = Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5.43))
        self.molecule = Molecule(['H', 'H'], [[0, 0, 0], [0.74, 0, 0]])
    
    def test_init(self):
        """Test calculator initialization."""
        self.assertEqual(self.calc.parameters['sigma'], 3.4)
        self.assertEqual(self.calc.parameters['epsilon'], 0.01)
        self.assertEqual(self.calc.structure, None)
        self.assertEqual(len(self.calc.results), 0)
        self.assertFalse(self.calc._calculation_performed)
    
    def test_set_parameters(self):
        """Test setting parameters."""
        self.calc.set_parameters(sigma=4.0, new_param=5.0)
        self.assertEqual(self.calc.parameters['sigma'], 4.0)
        self.assertEqual(self.calc.parameters['new_param'], 5.0)
        self.assertEqual(self.calc.parameters['epsilon'], 0.01)  # Unchanged
    
    def test_get_parameters(self):
        """Test getting parameters."""
        params = self.calc.get_parameters()
        self.assertEqual(params['sigma'], 3.4)
        self.assertIsNot(params, self.calc.parameters)  # Should be copy
    
    def test_update_parameters(self):
        """Test updating parameters."""
        self.calc.update_parameters(sigma=5.0)
        self.assertEqual(self.calc.parameters['sigma'], 5.0)
        self.assertEqual(self.calc.parameters['epsilon'], 0.01)  # Unchanged
    
    def test_calculate(self):
        """Test calculation on structure."""
        self.calc.calculate(self.crystal)
        self.assertEqual(self.calc.structure, self.crystal)
        self.assertTrue(self.calc._calculation_performed)
        self.assertIn('energy', self.calc.results)
        self.assertIn('forces', self.calc.results)
    
    def test_calculate_molecule(self):
        """Test calculation on molecule."""
        self.calc.calculate(self.molecule)
        self.assertEqual(self.calc.structure, self.molecule)
        self.assertTrue(self.calc._calculation_performed)
    
    def test_calculate_invalid_structure(self):
        """Test calculation with invalid structure."""
        with self.assertRaises(ValueError):
            self.calc.calculate("not a structure")
    
    def test_get_potential_energy(self):
        """Test getting potential energy."""
        self.calc.calculate(self.crystal)
        energy = self.calc.get_potential_energy()
        self.assertEqual(energy, 1.0)
    
    def test_get_potential_energy_not_calculated(self):
        """Test getting energy before calculation."""
        with self.assertRaises(ValueError):
            self.calc.get_potential_energy()
    
    def test_get_forces(self):
        """Test getting forces."""
        self.calc.calculate(self.crystal)
        forces = self.calc.get_forces()
        self.assertEqual(forces.shape, (2, 3))
        np.testing.assert_array_equal(forces, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    
    def test_get_forces_not_calculated(self):
        """Test getting forces before calculation."""
        with self.assertRaises(ValueError):
            self.calc.get_forces()
    
    def test_get_stress(self):
        """Test getting stress."""
        self.calc.calculate(self.crystal)
        stress = self.calc.get_stress()
        self.assertEqual(stress.shape, (3, 3))
        np.testing.assert_array_equal(stress, np.eye(3))
    
    def test_get_stress_not_calculated(self):
        """Test getting stress before calculation."""
        with self.assertRaises(ValueError):
            self.calc.get_stress()
    
    def test_get_result(self):
        """Test getting custom result."""
        self.calc.calculate(self.crystal)
        energy = self.calc.get_result('energy')
        self.assertEqual(energy, 1.0)
    
    def test_get_result_not_found(self):
        """Test getting non-existent result."""
        self.calc.calculate(self.crystal)
        with self.assertRaises(ValueError):
            self.calc.get_result('nonexistent')
    
    def test_parameters_clear_results(self):
        """Test that changing parameters clears results."""
        self.calc.calculate(self.crystal)
        self.assertTrue(self.calc._calculation_performed)
        
        self.calc.set_parameters(sigma=5.0)
        self.assertFalse(self.calc._calculation_performed)
        self.assertEqual(len(self.calc.results), 0)
    
    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.calc)
        self.assertIn('MockCalculator', repr_str)
        self.assertIn('sigma=3.4', repr_str)
        self.assertIn('epsilon=0.01', repr_str)


if __name__ == '__main__':
    unittest.main()

