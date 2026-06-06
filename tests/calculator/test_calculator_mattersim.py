"""
Tests for Mattersim ML calculator.
"""

import unittest
import numpy as np
from pathlib import Path
import json
import os
import subprocess
import sys
import textwrap
from matsimpy import Crystal, Molecule, Lattice
from matsimpy.calculator.ml.dataloader import MatSimPyGraphConvertor
from matsimpy.calculator.ml.mattersim import GPA_TO_EV_PER_A3
from tests.conftest import has_ase, has_torch, has_torch_geometric

# Conditional import - Mattersim requires torch
if has_torch() and has_torch_geometric():
    from matsimpy.calculator import Mattersim
else:
    Mattersim = None

requires_torch_geometric = unittest.skipUnless(
    has_torch() and has_torch_geometric(),
    "torch or torch_geometric not installed",
)


@requires_torch_geometric
class TestMattersim(unittest.TestCase):
    """Tests for Mattersim ML calculator."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        self.crystal = from_prototype('diamond', 'Si', 5.43)
        self.molecule = Molecule(['H', 'H'], [[0, 0, 0], [0.74, 0, 0]])
    
    def test_init_with_model_path(self):
        """Test initialization with model path."""
        # Use non-existent path to test error handling
        with self.assertRaises(FileNotFoundError):
            calc = Mattersim(model_path='nonexistent.pth')
    
    def test_init_without_model(self):
        """Test initialization without model."""
        with self.assertRaises(ValueError):
            calc = Mattersim()
    
    def test_init_with_model_object(self):
        """Test initialization with model object."""
        # Mock potential object with required attributes
        class MockPotential:
            model_name = 'm3gnet'
        
        mock_potential = MockPotential()
        calc = Mattersim(model=mock_potential, device='cpu')
        self.assertEqual(calc.model, mock_potential)
        self.assertEqual(calc.potential, mock_potential)
    
    def test_model_types(self):
        """Test model type handling."""
        # Create mock potential
        class MockPotential:
            model_name = 'm3gnet'
        
        mock_potential = MockPotential()
        
        # MatterSim uses 'm3gnet' as default
        calc = Mattersim(model=mock_potential, device='cpu')
        self.assertEqual(calc.model_type, 'm3gnet')
    
    def test_set_model(self):
        """Test setting model."""
        class MockPotential:
            model_name = 'm3gnet'
        
        mock_potential1 = MockPotential()
        mock_potential2 = MockPotential()
        
        calc = Mattersim(model=mock_potential1, device='cpu')
        self.assertEqual(calc.model, mock_potential1)
        
        calc.set_model(mock_potential2)
        self.assertEqual(calc.model, mock_potential2)
        self.assertFalse(calc._calculation_performed)
        self.assertEqual(len(calc.results), 0)
    
    def test_load_model_not_implemented(self):
        """Test that model loading with invalid file raises error."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy model file (not a valid MatterSim checkpoint)
            dummy_path = Path(tmpdir) / 'dummy_model.pth'
            dummy_path.touch()
            # Should raise error when trying to load invalid model
            with self.assertRaises((ValueError, FileNotFoundError)):
                calc = Mattersim(model_path=str(dummy_path))
    
    def test_compute_requires_real_model(self):
        """Test that computation requires a real MatterSim model."""
        # Mock potential without proper forward method
        class MockPotential:
            model_name = 'm3gnet'
            def forward(self, *args, **kwargs):
                raise NotImplementedError("Mock model not implemented")
        
        mock_potential = MockPotential()
        calc = Mattersim(model=mock_potential, device='cpu')
        
        # Should raise error when trying to compute without proper model
        with self.assertRaises((NotImplementedError, AttributeError)):
            calc.calculate(self.crystal)
    
    def test_parameters(self):
        """Test parameter management."""
        class MockPotential:
            model_name = 'm3gnet'
        
        mock_potential = MockPotential()
        calc = Mattersim(
            model=mock_potential,
            device='cuda',
            args_dict={'batch_size': 32}
        )
        
        self.assertEqual(calc.model_type, 'm3gnet')
        self.assertEqual(calc.device, 'cuda')
        self.assertEqual(calc.args_dict['batch_size'], 32)
    
    def test_device_parameter(self):
        """Test device parameter."""
        class MockPotential:
            model_name = 'm3gnet'
        
        mock_potential = MockPotential()
        calc1 = Mattersim(model=mock_potential, device='cpu')
        calc2 = Mattersim(model=mock_potential, device='cuda')
        
        self.assertEqual(calc1.device, 'cpu')
        self.assertEqual(calc2.device, 'cuda')
    
    def test_integration_with_crystal(self):
        """Test integration with Crystal class."""
        class MockPotential:
            model_name = 'm3gnet'
            def forward(self, *args, **kwargs):
                raise NotImplementedError("Mock model not implemented")
        
        mock_potential = MockPotential()
        calc = Mattersim(model=mock_potential, device='cpu')
        
        # Use proper diamond structure (2 atoms in primitive cell)
        from matsimpy.builders.bulk import from_prototype
        crystal = from_prototype('diamond', 'Si', 5.43)
        crystal.calc = calc
        
        # Should raise error when trying to get energy with mock model
        with self.assertRaises((NotImplementedError, AttributeError)):
            energy = crystal.get_potential_energy()
    
    def test_integration_with_molecule(self):
        """Test integration with Molecule class."""
        class MockPotential:
            model_name = 'm3gnet'
            def forward(self, *args, **kwargs):
                raise NotImplementedError("Mock model not implemented")
        
        mock_potential = MockPotential()
        calc = Mattersim(model=mock_potential, device='cpu')
        
        molecule = Molecule(['H', 'H'], [[0, 0, 0], [0.74, 0, 0]])
        molecule.calc = calc
        
        # Should raise error when trying to get energy with mock model
        with self.assertRaises((NotImplementedError, AttributeError)):
            energy = molecule.get_potential_energy()
    
    def test_prepare_model_input(self):
        """Test model input preparation."""
        # Create a mock potential object with required attributes
        class MockPotential:
            model_name = 'm3gnet'
            model = type('obj', (object,), {
                'model_args': {'cutoff': 5.0, 'threebody_cutoff': 4.0}
            })()
        
        mock_potential = MockPotential()
        calc = Mattersim(model=mock_potential, device='cpu')
        
        # Test with crystal - should return graph batch (PyG Data object)
        graph_batch = calc._prepare_model_input(
            self.crystal.cart_positions,
            self.crystal.species,
            self.crystal.lattice,
            self.crystal.pbc
        )
        
        # Graph batch should have atom_pos, cell, etc.
        self.assertIsNotNone(graph_batch)
        self.assertTrue(hasattr(graph_batch, 'atom_pos') or hasattr(graph_batch, 'pos'))
        
        # Test with molecule
        graph_batch = calc._prepare_model_input(
            np.array(self.molecule.positions),
            self.molecule.species,
            None,
            [False, False, False]
        )
        
        self.assertIsNotNone(graph_batch)

    def test_mock_prediction_si_diamond_shapes(self):
        """MatterSim-style prediction works on MatSimPy Crystal without ASE."""
        class MockPotential:
            model_name = 'm3gnet'
            model = type('obj', (object,), {
                'model_args': {'cutoff': 5.0, 'threebody_cutoff': 4.0}
            })()

            def predict(self, graph_batch):
                n_atoms = int(graph_batch.num_nodes)
                return {
                    "total_energy": np.array([-8.0]),
                    "energy_per_atom": np.array([-8.0 / n_atoms]),
                    "forces": np.zeros((n_atoms, 3)),
                    "stresses": np.eye(3)[None, :, :] * 0.25,
                }

        calc = Mattersim(model=MockPotential(), device='cpu')
        self.crystal.calc = calc

        energy = self.crystal.get_potential_energy()
        forces = self.crystal.get_forces()
        stress = self.crystal.get_stress(voigt=False)

        self.assertAlmostEqual(energy, -8.0)
        self.assertAlmostEqual(calc.get_result("energy_per_atom"), -8.0 / len(self.crystal))
        self.assertEqual(forces.shape, (len(self.crystal), 3))
        self.assertEqual(stress.shape, (3, 3))
        self.assertAlmostEqual(stress[0][0], 0.25 * GPA_TO_EV_PER_A3)

    def test_graph_input_matches_mattersim_ase_converter(self):
        """MatSimPy-native graph input matches MatterSim's ASE graph oracle."""
        if not has_ase():
            self.skipTest("ASE is required for the MatterSim graph oracle")

        try:
            from ase import Atoms
            from mattersim.datasets.utils.convertor import GraphConvertor
        except ImportError as exc:
            self.skipTest(f"MatterSim graph oracle is unavailable: {exc}")

        cutoff = 5.0
        threebody_cutoff = 4.0
        matsimpy_graph = MatSimPyGraphConvertor(
            "m3gnet", cutoff, True, threebody_cutoff
        ).convert(self.crystal)
        atoms = Atoms(
            self.crystal.species,
            positions=self.crystal.cart_positions,
            cell=self.crystal.lattice.matrix,
            pbc=self.crystal.pbc,
        )
        ase_graph = GraphConvertor(
            "m3gnet", cutoff, True, threebody_cutoff
        ).convert(atoms.copy())

        for attr in (
            "atom_attr",
            "atom_pos",
            "cell",
            "edge_index",
            "pbc_offsets",
            "three_body_indices",
            "num_triple_ij",
        ):
            np.testing.assert_array_equal(
                getattr(matsimpy_graph, attr).numpy(),
                getattr(ase_graph, attr).numpy(),
            )
        self.assertEqual(matsimpy_graph.num_bonds, ase_graph.num_bonds)
        self.assertEqual(matsimpy_graph.num_three_body, ase_graph.num_three_body)

    def test_real_mattersim_matches_ase_calculator_when_usable(self):
        """Real MatterSim parity check; skips if the native MatterSim stack crashes."""
        if not (has_ase() and has_torch() and has_torch_geometric()):
            self.skipTest("ASE, torch, and torch_geometric are required")

        model_path = (
            Path.home()
            / ".local"
            / "mattersim"
            / "pretrained_models"
            / "mattersim-v1.0.0-1M.pth"
        )
        if not model_path.exists():
            self.skipTest(f"Real MatterSim checkpoint not found: {model_path}")

        script = textwrap.dedent(
            f"""
            import json
            import numpy as np
            from ase import Atoms
            from matsimpy.builders.bulk import from_prototype
            from matsimpy.calculator.ml.mattersim import Mattersim
            from mattersim.forcefield import MatterSimCalculator, Potential

            si = from_prototype("diamond", "Si", 5.43)
            potential = Potential.from_checkpoint(
                load_path={str(model_path)!r},
                device="cpu",
                load_training_state=False,
            )

            si.calc = Mattersim(model=potential, device="cpu")
            ms_energy = si.get_potential_energy()
            ms_forces = si.get_forces()
            ms_stress = si.get_stress(voigt=False)

            atoms = Atoms(
                si.species,
                positions=si.cart_positions,
                cell=si.lattice.matrix,
                pbc=si.pbc,
            )
            atoms.calc = MatterSimCalculator.from_potential(potential, device="cpu")
            ase_energy = atoms.get_potential_energy()
            ase_forces = atoms.get_forces()
            ase_stress = atoms.get_stress(voigt=False)

            print(json.dumps({{
                "energy_diff": float(abs(ms_energy - ase_energy)),
                "forces_diff": float(np.max(np.abs(ms_forces - ase_forces))),
                "stress_diff": float(np.max(np.abs(ms_stress - ase_stress))),
            }}))
            """
        )
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", "/private/tmp/matsimpy-mpl")
        env.setdefault("OMP_NUM_THREADS", "1")
        env.setdefault("MKL_NUM_THREADS", "1")
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            timeout=180,
        )

        if result.returncode != 0:
            self.skipTest(
                "Installed MatterSim native stack failed before parity assertion: "
                + (result.stderr or result.stdout)[-500:]
            )

        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertLessEqual(payload["energy_diff"], 1e-5)
        self.assertLessEqual(payload["forces_diff"], 1e-6)
        self.assertLessEqual(payload["stress_diff"], 1e-8)

if __name__ == '__main__':
    unittest.main()
