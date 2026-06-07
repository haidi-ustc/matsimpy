"""
Tests for Lennard-Jones calculator.
"""

import unittest
import numpy as np
from matsimpy import Crystal, Molecule, Lattice
from matsimpy.calculator.lj import LennardJones
from tests.conftest import has_ase

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

    def _ase_lj_results(self, species, positions, cutoff, cell=None, pbc=False):
        if not has_ase():
            self.skipTest("ASE is required for LJ reference results")

        from ase import Atoms
        from ase.calculators.lj import LennardJones as ASELennardJones

        atoms = Atoms(species, positions=positions, cell=cell, pbc=pbc)
        atoms.calc = ASELennardJones(
            sigma=self.sigma,
            epsilon=self.epsilon,
            rc=cutoff,
            smooth=False,
        )
        energy = atoms.get_potential_energy()
        forces = atoms.get_forces()
        stress = atoms.get_stress(voigt=False) if np.any(pbc) else None
        return energy, forces, stress

    def _ase_shifted_energy(self, r, cutoff):
        pair_energy = 4.0 * self.epsilon * (
            (self.sigma / r) ** 12 - (self.sigma / r) ** 6
        )
        cutoff_energy = 4.0 * self.epsilon * (
            (self.sigma / cutoff) ** 12 - (self.sigma / cutoff) ** 6
        )
        return pair_energy - cutoff_energy
    
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
        # ASE uses a finite-cutoff shifted LJ potential when smooth=False.
        mol = Molecule(['Ar', 'Ar'], [[0, 0, 0], [self.sigma, 0, 0]])
        self.calc.calculate(mol)
        energy = self.calc.get_potential_energy()
        expected = self._ase_shifted_energy(self.sigma, self.calc.parameters["cutoff"])
        self.assertAlmostEqual(energy, expected, places=8)
    
    def test_energy_at_minimum(self):
        """Test energy at minimum (r = 2^(1/6) * sigma)."""
        r_min = self.sigma * (2 ** (1.0/6.0))
        mol = Molecule(['Ar', 'Ar'], [[0, 0, 0], [r_min, 0, 0]])
        self.calc.calculate(mol)
        energy = self.calc.get_potential_energy()
        expected = self._ase_shifted_energy(r_min, self.calc.parameters["cutoff"])
        self.assertAlmostEqual(energy, expected, places=8)
    
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
        
        self.assertNotAlmostEqual(energy_long, energy_short)
    
    def test_crystal_stress(self):
        """Test stress calculation for crystal."""
        self.calc.calculate(self.crystal)
        stress = self.calc.get_stress()
        self.assertEqual(stress.shape, (3, 3))
        # Stress should be symmetric
        np.testing.assert_array_almost_equal(stress, stress.T, decimal=5)

    def test_stress_voigt(self):
        """Stress supports full tensor and ASE-order Voigt forms."""
        self.calc.calculate(self.crystal)
        full = self.calc.get_stress(voigt=False)
        voigt = self.calc.get_stress(voigt=True)
        self.assertEqual(full.shape, (3, 3))
        self.assertEqual(voigt.shape, (6,))
        np.testing.assert_allclose(
            voigt,
            [full[0, 0], full[1, 1], full[2, 2], full[1, 2], full[0, 2], full[0, 1]],
        )
    
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
        self.assertEqual(crystal.get_stress(voigt=True).shape, (6,))
    
    def test_integration_with_molecule(self):
        """Test integration with Molecule class."""
        molecule = Molecule(['Ar', 'Ar'], [[0, 0, 0], [3.4, 0, 0]])
        molecule.calc = self.calc
        
        energy = molecule.get_potential_energy()
        forces = molecule.get_forces()
        
        self.assertIsInstance(energy, float)
        self.assertEqual(forces.shape, (2, 3))

    def test_molecule_matches_ase_reference(self):
        """Molecule energy and forces follow ASE LennardJones conventions."""
        cutoff = 8.0
        positions = np.array([[0, 0, 0], [4.0, 0, 0]], dtype=float)
        mol = Molecule(['Ar', 'Ar'], positions)
        calc = LennardJones(sigma=self.sigma, epsilon=self.epsilon, cutoff=cutoff)
        calc.calculate(mol)

        ase_energy, ase_forces, _ = self._ase_lj_results(
            ['Ar', 'Ar'], positions, cutoff
        )
        self.assertAlmostEqual(calc.get_potential_energy(), ase_energy, places=10)
        np.testing.assert_allclose(calc.get_forces(), ase_forces, atol=1e-12)

    def test_periodic_crystal_matches_ase_reference(self):
        """Periodic crystal uses Cartesian coordinates and matches ASE."""
        cutoff = 8.0
        positions = np.array([[0, 0, 0], [4.0, 0, 0]], dtype=float)
        cell = np.eye(3) * 10.0
        crystal = Crystal(
            ['Ar', 'Ar'],
            positions,
            Lattice(cell),
            coords_are_cartesian=True,
            pbc=(True, True, True),
        )
        calc = LennardJones(sigma=self.sigma, epsilon=self.epsilon, cutoff=cutoff)
        calc.calculate(crystal)

        ase_energy, ase_forces, ase_stress = self._ase_lj_results(
            ['Ar', 'Ar'], positions, cutoff, cell=cell, pbc=True
        )
        self.assertAlmostEqual(calc.get_potential_energy(), ase_energy, places=10)
        np.testing.assert_allclose(calc.get_forces(), ase_forces, atol=1e-12)
        np.testing.assert_allclose(calc.get_stress(), ase_stress, atol=1e-12)

    def test_periodic_self_images_match_ase_reference(self):
        """Single-atom periodic image interactions match ASE."""
        crystal = Crystal(['Ar'], [[0, 0, 0]], Lattice.cubic(5.0))
        calc = LennardJones(sigma=self.sigma, epsilon=self.epsilon)
        calc.calculate(crystal)

        ase_energy, ase_forces, ase_stress = self._ase_lj_results(
            ['Ar'],
            np.array([[0, 0, 0]], dtype=float),
            calc.parameters["cutoff"],
            cell=np.eye(3) * 5.0,
            pbc=True,
        )
        self.assertAlmostEqual(calc.get_potential_energy(), ase_energy, places=10)
        np.testing.assert_allclose(calc.get_forces(), ase_forces, atol=1e-12)
        np.testing.assert_allclose(calc.get_stress(), ase_stress, atol=1e-12)


class TestLJMultispecies(unittest.TestCase):
    """Tests for multi-species Lennard-Jones with Lorentz-Berthelot mixing."""

    def test_multispecies_energy_different_from_single(self):
        """Ar+Kr system should have different energy than pure Ar."""
        from matsimpy.calculator.lj import LennardJones

        crystal = Crystal(
            ["Ar", "Kr", "Ar", "Kr"],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0]],
            Lattice.cubic(5.0),
        )
        calc = LennardJones(
            sigma=3.4, epsilon=0.0104,
            species_sigma={"Kr": 3.6}, species_epsilon={"Kr": 0.014},
        )
        calc.calculate(crystal)
        energy_mixed = calc.get_potential_energy()

        crystal_ar = Crystal(
            ["Ar", "Ar", "Ar", "Ar"],
            [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0.5, 0.5, 0]],
            Lattice.cubic(5.0),
        )
        calc_ar = LennardJones(sigma=3.4, epsilon=0.0104)
        calc_ar.calculate(crystal_ar)
        energy_pure = calc_ar.get_potential_energy()

        self.assertNotEqual(energy_mixed, energy_pure)

    def test_lorentz_berthelot_mixing_rules(self):
        """sigma_12 = (s1+s2)/2, eps_12 = sqrt(eps1*eps2)."""
        from matsimpy.calculator.lj import LennardJones

        calc = LennardJones(
            sigma=3.0, epsilon=0.01,
            species_sigma={"B": 4.0}, species_epsilon={"B": 0.02},
        )
        sig, eps = calc.get_pair_params("A", "B")
        self.assertAlmostEqual(sig, 3.5)
        self.assertAlmostEqual(eps, 0.0141421356237)

    def test_backward_compatible_single_species(self):
        """Existing single-species usage unchanged."""
        from matsimpy.calculator.lj import LennardJones

        crystal = Crystal(["Ar"], [[0, 0, 0]], Lattice.cubic(5.26))
        calc = LennardJones(sigma=3.4, epsilon=0.0104)
        calc.calculate(crystal)
        energy = calc.get_potential_energy()
        self.assertIsInstance(energy, float)
        self.assertTrue(np.isfinite(energy))

    def test_pair_params_default_for_unknown(self):
        """get_pair_params returns defaults for species not in dicts."""
        from matsimpy.calculator.lj import LennardJones

        calc = LennardJones(
            sigma=3.4, epsilon=0.0104,
            species_sigma={"Kr": 3.6}, species_epsilon={"Kr": 0.014},
        )
        sig, eps = calc.get_pair_params("Ar", "Ar")
        self.assertAlmostEqual(sig, 3.4)
        self.assertAlmostEqual(eps, 0.0104)


if __name__ == '__main__':
    unittest.main()
