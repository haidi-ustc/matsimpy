"""
Tests for Mattersim ML calculator.
"""

import unittest
import numpy as np
from pathlib import Path
from matsimpy import Crystal, Molecule, Lattice
from tests.conftest import has_torch, has_torch_geometric

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

if __name__ == '__main__':
    unittest.main()
