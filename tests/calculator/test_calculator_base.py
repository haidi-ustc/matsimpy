"""
Tests for base Calculator class.
"""

import unittest
import numpy as np
# Import core classes first to avoid triggering calculator.__init__ imports
from matsimpy.core import Crystal, Molecule, Lattice
# Direct import from base module to avoid triggering ML imports
from matsimpy.calculator.base import Calculator

class MockCalculator(Calculator):
    """Mock calculator for testing base class."""

    def _compute(self):
        """Mock computation that sets fake results."""
        self.results['energy'] = 1.0
        self.results['forces'] = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        self.results['stress'] = np.eye(3)


class _DummyRunCalculator(Calculator):
    """Calculator that supports the run=True pipeline."""
    def __init__(self, run=True, **kwargs):
        super().__init__(run=run, **kwargs)
        self.written = False
        self.executed = False
        self.parsed = False
        self.read_called = False

    def write_input(self, structure):
        self.written = True
        self.input_structure = structure

    def _execute(self):
        self.executed = True

    def _parse_output(self):
        self.parsed = True
        self.results["energy"] = -1.0
        self.results["forces"] = np.zeros((1, 3))

    def read_results(self):
        self.read_called = True
        self._parse_output()


class _DummyNoRunCalculator(Calculator):
    """Calculator that supports run=False (offline) pipeline."""
    def __init__(self, run=False, **kwargs):
        super().__init__(run=run, **kwargs)

    def write_input(self, structure):
        self._input_written = True

    def _parse_output(self):
        self.results["energy"] = -5.0

class TestCalculatorBase(unittest.TestCase):
    """Tests for base Calculator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calc = MockCalculator(sigma=3.4, epsilon=0.01)
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.crystal = from_prototype('diamond', 'Si', 5.43)
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

class TestCalculatorRunMode(unittest.TestCase):
    """Tests for run-mode pipeline (run=True/False)."""

    def setUp(self):
        self.crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))

    def test_run_default_is_true(self):
        calc = Calculator()
        self.assertTrue(calc.run)

    def test_run_false_stored(self):
        calc = Calculator(run=False)
        self.assertFalse(calc.run)

    def test_run_true_calls_execute_and_parse(self):
        calc = _DummyRunCalculator(run=True)
        calc.calculate(self.crystal)
        self.assertTrue(calc.written)
        self.assertTrue(calc.executed)
        self.assertTrue(calc.parsed)
        self.assertFalse(calc.read_called)
        self.assertEqual(calc.get_potential_energy(), -1.0)

    def test_run_false_skips_execute_and_parse(self):
        calc = _DummyRunCalculator(run=False)
        calc.calculate(self.crystal)
        self.assertTrue(calc.written)
        self.assertFalse(calc.executed)
        self.assertFalse(calc.parsed)

    def test_read_results_after_offline_calculate(self):
        calc = _DummyRunCalculator(run=False)
        calc.calculate(self.crystal)
        calc.read_results()
        self.assertTrue(calc.read_called)
        self.assertEqual(calc.get_potential_energy(), -1.0)

    def test_read_results_without_calculate(self):
        calc = _DummyNoRunCalculator(run=False)
        calc.read_results()
        self.assertEqual(calc.get_potential_energy(), -5.0)

    def test_get_energy_before_calculate_raises(self):
        calc = _DummyRunCalculator(run=True)
        with self.assertRaises(ValueError):
            calc.get_potential_energy()

    def test_get_forces_before_calculate_raises(self):
        calc = _DummyRunCalculator(run=True)
        with self.assertRaises(ValueError):
            calc.get_forces()

    def test_legacy_compute_still_works(self):
        """Pure-Python calculators using _compute() should still work."""
        calc = MockCalculator(sigma=3.4)
        calc.calculate(self.crystal)
        self.assertEqual(calc.get_potential_energy(), 1.0)


if __name__ == '__main__':
    unittest.main()

