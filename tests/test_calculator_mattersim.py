"""
Tests for Mattersim ML calculator.
"""

import unittest
import numpy as np
from pathlib import Path
from matsimpy import Crystal, Molecule, Lattice
from matsimpy.calculator import Mattersim


class TestMattersim(unittest.TestCase):
    """Tests for Mattersim ML calculator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.crystal = Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5.43))
        self.molecule = Molecule(['H', 'H'], [[0, 0, 0], [0.74, 0, 0]])
    
    def test_init_with_model_path(self):
        """Test initialization with model path."""
        # Use non-existent path to test error handling
        with self.assertRaises(FileNotFoundError):
            calc = Mattersim(model_path='nonexistent.pth', model_type='mace')
    
    def test_init_without_model(self):
        """Test initialization without model."""
        with self.assertRaises(ValueError):
            calc = Mattersim(model_type='mace')
    
    def test_init_with_model_object(self):
        """Test initialization with model object."""
        # Mock model object
        mock_model = object()
        calc = Mattersim(model=mock_model, model_type='custom')
        self.assertEqual(calc.model, mock_model)
    
    def test_model_types(self):
        """Test different model types."""
        mock_model = object()
        
        # Test supported types (should not raise error for custom)
        calc1 = Mattersim(model=mock_model, model_type='custom')
        self.assertEqual(calc1.model_type, 'custom')
        
        calc2 = Mattersim(model=mock_model, model_type='MACE')  # Case insensitive
        self.assertEqual(calc2.model_type, 'mace')
    
    def test_set_model(self):
        """Test setting model."""
        mock_model1 = object()
        mock_model2 = object()
        
        calc = Mattersim(model=mock_model1, model_type='custom')
        self.assertEqual(calc.model, mock_model1)
        
        calc.set_model(mock_model2)
        self.assertEqual(calc.model, mock_model2)
        self.assertFalse(calc._calculation_performed)
        self.assertEqual(len(calc.results), 0)
    
    def test_load_model_not_implemented(self):
        """Test that model loading raises NotImplementedError."""
        # Create a dummy model file
        dummy_path = Path('dummy_model.pth')
        try:
            dummy_path.touch()
            with self.assertRaises(NotImplementedError):
                calc = Mattersim(model_path=str(dummy_path), model_type='mace')
        finally:
            if dummy_path.exists():
                dummy_path.unlink()
    
    def test_compute_not_implemented(self):
        """Test that computation raises NotImplementedError."""
        mock_model = object()
        calc = Mattersim(model=mock_model, model_type='custom')
        
        with self.assertRaises(NotImplementedError):
            calc.calculate(self.crystal)
    
    def test_parameters(self):
        """Test parameter management."""
        mock_model = object()
        calc = Mattersim(
            model=mock_model,
            model_type='mace',
            device='cuda',
            batch_size=32
        )
        
        self.assertEqual(calc.parameters['model_type'], 'mace')
        self.assertEqual(calc.parameters['device'], 'cuda')
        self.assertEqual(calc.parameters['batch_size'], 32)
    
    def test_device_parameter(self):
        """Test device parameter."""
        mock_model = object()
        calc1 = Mattersim(model=mock_model, model_type='mace', device='cpu')
        calc2 = Mattersim(model=mock_model, model_type='mace', device='cuda')
        
        self.assertEqual(calc1.device, 'cpu')
        self.assertEqual(calc2.device, 'cuda')
    
    def test_integration_with_crystal(self):
        """Test integration with Crystal class (should fail gracefully)."""
        mock_model = object()
        calc = Mattersim(model=mock_model, model_type='custom')
        
        crystal = Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5.43))
        crystal.calc = calc
        
        # Should raise NotImplementedError when trying to get energy
        with self.assertRaises(NotImplementedError):
            energy = crystal.get_potential_energy()
    
    def test_integration_with_molecule(self):
        """Test integration with Molecule class (should fail gracefully)."""
        mock_model = object()
        calc = Mattersim(model=mock_model, model_type='custom')
        
        molecule = Molecule(['H', 'H'], [[0, 0, 0], [0.74, 0, 0]])
        molecule.calc = calc
        
        # Should raise NotImplementedError when trying to get energy
        with self.assertRaises(NotImplementedError):
            energy = molecule.get_potential_energy()
    
    def test_prepare_model_input(self):
        """Test model input preparation."""
        mock_model = object()
        calc = Mattersim(model=mock_model, model_type='custom')
        
        # Test with crystal
        input_dict = calc._prepare_model_input(
            self.crystal.cart_positions,
            self.crystal.species,
            self.crystal.lattice,
            self.crystal.pbc
        )
        
        self.assertIn('positions', input_dict)
        self.assertIn('species', input_dict)
        self.assertIn('lattice', input_dict)
        self.assertIn('pbc', input_dict)
        
        # Test with molecule
        input_dict = calc._prepare_model_input(
            np.array(self.molecule.positions),
            self.molecule.species,
            None,
            [False, False, False]
        )
        
        self.assertIn('positions', input_dict)
        self.assertIn('species', input_dict)
        self.assertNotIn('lattice', input_dict)


if __name__ == '__main__':
    unittest.main()

