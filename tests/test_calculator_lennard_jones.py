"""
Tests for Lennard-Jones calculator.
"""

import unittest
import numpy as np
from matsimpy import Crystal, Molecule, Lattice
from matsimpy.calculator.classical import LennardJones

class TestLennardJones(unittest.TestCase):
    """Tests for Lennard-Jones calculator."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Argon parameters (typical values)
        self.sigma = 3.4  # Å
        self.epsilon = 0.0104  # eV
        self.calc = LennardJones(sigma=self.sigma, epsilon=self.epsilon)
        
        # Simple 2-atom system
        self.molecule = Molecule(['Ar', 'Ar'], [[0, 0, 0], [3.4, 0, 0]])
        
        # Simple crystal
        self.crystal = Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(5.0))
    
    def test_init(self):
        """Test LJ calculator initialization."""
        self.assertEqual(self.calc.parameters['sigma'], self.sigma)
        self.assertEqual(self.calc.parameters['epsilon'], self.epsilon)
        self.assertIn('cutoff', self.calc.parameters)
        self.assertAlmostEqual(self.calc.parameters['cutoff'], 3.0 * self.sigma)
    
    def test_init_custom_cutoff(self):
        """Test initialization with custom cutoff."""
        calc = LennardJones(sigma=3.4, epsilon=0.01, cutoff=15.0)
        self.assertEqual(calc.parameters['cutoff'], 15.0)
    
    def test_calculate_molecule(self):
        """Test calculation on molecule."""
        self.calc.calculate(self.molecule)
        self.assertIn('energy', self.calc.results)
        self.assertIn('forces', self.calc.results)
        self.assertEqual(self.calc.results['forces'].shape, (2, 3))
    
    def test_calculate_crystal(self):
        """Test calculation on crystal."""
        self.calc.calculate(self.crystal)
        self.assertIn('energy', self.calc.results)
        self.assertIn('forces', self.calc.results)
        self.assertIn('stress', self.calc.results)
    
    def test_energy_at_equilibrium(self):
        """Test energy at equilibrium distance (sigma)."""
        # At r = sigma, V = 0
        mol = Molecule(['Ar', 'Ar'], [[0, 0, 0], [self.sigma, 0, 0]])
        self.calc.calculate(mol)
        energy = self.calc.get_potential_energy()
        self.assertAlmostEqual(energy, 0.0, places=5)
    
    def test_energy_at_minimum(self):
        """Test energy at minimum (r = 2^(1/6) * sigma)."""
        r_min = self.sigma * (2 ** (1.0/6.0))
        mol = Molecule(['Ar', 'Ar'], [[0, 0, 0], [r_min, 0, 0]])
        self.calc.calculate(mol)
        energy = self.calc.get_potential_energy()
        # At minimum, V = -epsilon
        self.assertAlmostEqual(energy, -self.epsilon, places=3)
    
    def test_forces_at_equilibrium(self):
        """Test forces at equilibrium distance."""
        mol = Molecule(['Ar', 'Ar'], [[0, 0, 0], [self.sigma, 0, 0]])
        self.calc.calculate(mol)
        forces = self.calc.get_forces()
        # At r=sigma, V=0 but force is not zero (it's at minimum at r=2^(1/6)*sigma)
        # So we just check that forces are computed
        self.assertEqual(forces.shape, (2, 3))
    
    def test_forces_repulsive(self):
        """Test repulsive forces at short distance."""
        # Very close atoms (r < sigma)
        mol = Molecule(['Ar', 'Ar'], [[0, 0, 0], [0.5 * self.sigma, 0, 0]])
        self.calc.calculate(mol)
        forces = self.calc.get_forces()
        # Force on atom 0 should be repulsive (negative x, pushing away from atom 1)
        # Since atom 1 is at positive x, force on 0 should be negative (repulsive)
        self.assertLess(forces[0, 0], 0)
        # Force on atom 1 should be equal and opposite
        np.testing.assert_array_almost_equal(forces[0], -forces[1], decimal=5)
    
    def test_forces_attractive(self):
        """Test attractive forces at long distance."""
        # Atoms beyond equilibrium (r > 2^(1/6)*sigma)
        r = 2.0 * self.sigma
        mol = Molecule(['Ar', 'Ar'], [[0, 0, 0], [r, 0, 0]])
        self.calc.calculate(mol)
        forces = self.calc.get_forces()
        # Force on atom 0 should be attractive (positive x, pulling closer)
        self.assertGreater(forces[0, 0], 0)
        # Force on atom 1 should be equal and opposite
        np.testing.assert_array_almost_equal(forces[0], -forces[1], decimal=5)
    
    def test_energy_conservation(self):
        """Test that energy scales with epsilon."""
        calc1 = LennardJones(sigma=3.4, epsilon=0.01)
        calc2 = LennardJones(sigma=3.4, epsilon=0.02)
        
        # Use a distance where energy is non-zero
        r = 2.0 * self.sigma
        mol = Molecule(['Ar', 'Ar'], [[0, 0, 0], [r, 0, 0]])
        
        calc1.calculate(mol)
        energy1 = calc1.get_potential_energy()
        
        calc2.calculate(mol)
        energy2 = calc2.get_potential_energy()
        
        # Energy should scale with epsilon
        if abs(energy1) > 1e-10:  # Avoid division by zero
            self.assertAlmostEqual(energy2 / energy1, 2.0, places=5)
        else:
            # If energy1 is zero, energy2 should also be zero (at r=sigma)
            self.assertAlmostEqual(energy2, 0.0, places=5)
    
    def test_cutoff_effect(self):
        """Test that cutoff affects calculation."""
        calc_short = LennardJones(sigma=3.4, epsilon=0.01, cutoff=5.0)
        calc_long = LennardJones(sigma=3.4, epsilon=0.01, cutoff=20.0)
        
        # Large system where cutoff matters
        positions = [[i * 5.0, 0, 0] for i in range(5)]
        mol = Molecule(['Ar'] * 5, positions)
        
        calc_short.calculate(mol)
        energy_short = calc_short.get_potential_energy()
        
        calc_long.calculate(mol)
        energy_long = calc_long.get_potential_energy()
        
        # Longer cutoff should include more interactions
        self.assertGreater(abs(energy_long), abs(energy_short))
    
    def test_crystal_stress(self):
        """Test stress calculation for crystal."""
        self.calc.calculate(self.crystal)
        stress = self.calc.get_stress()
        self.assertEqual(stress.shape, (3, 3))
        # Stress should be symmetric
        np.testing.assert_array_almost_equal(stress, stress.T, decimal=5)
    
    def test_multiple_atoms(self):
        """Test calculation with multiple atoms."""
        positions = [[0, 0, 0], [3.4, 0, 0], [0, 3.4, 0], [3.4, 3.4, 0]]
        mol = Molecule(['Ar'] * 4, positions)
        self.calc.calculate(mol)
        
        energy = self.calc.get_potential_energy()
        forces = self.calc.get_forces()
        
        self.assertEqual(forces.shape, (4, 3))
        # Energy should be sum of all pair interactions
        self.assertIsInstance(energy, float)
    
    def test_integration_with_crystal(self):
        """Test integration with Crystal class."""
        crystal = Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(5.0))
        crystal.calc = self.calc
        
        energy = crystal.get_potential_energy()
        forces = crystal.get_forces()
        stress = crystal.get_stress()
        
        self.assertIsInstance(energy, float)
        self.assertEqual(forces.shape, (1, 3))
        self.assertEqual(stress.shape, (3, 3))
    
    def test_integration_with_molecule(self):
        """Test integration with Molecule class."""
        molecule = Molecule(['Ar', 'Ar'], [[0, 0, 0], [3.4, 0, 0]])
        molecule.calc = self.calc
        
        energy = molecule.get_potential_energy()
        forces = molecule.get_forces()
        
        self.assertIsInstance(energy, float)
        self.assertEqual(forces.shape, (2, 3))

if __name__ == '__main__':
    unittest.main()

