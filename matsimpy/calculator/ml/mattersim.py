"""
Mattersim machine learning potential calculator.

Provides interface to MatterSim ML potentials for materials simulation.
Uses MatterSim's M3GNet-based models for energy, force, and stress prediction.
"""

import numpy as np
from typing import Optional, Dict, Any, Union
from pathlib import Path
import os
from .base_ml import BaseML
from ...core import Crystal, Molecule
from ...io.converters import to_ase


class Mattersim(BaseML):
    """
    Machine learning potential calculator using MatterSim framework.
    
    This calculator interfaces with MatterSim models (M3GNet-based) to predict
    energies, forces, and stress for atomic structures.
    
    Attributes:
        potential: Loaded MatterSim Potential object
        model_path: Path to model file
        device: Computation device ('cpu' or 'cuda')
        args_dict: Additional arguments for dataloader
        
    Example:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.calculator.ml import Mattersim
        >>> 
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> calc = Mattersim(model_path='~/.matsimpy/models/mattersim-v1.0.0-5M.pth.tar')
        >>> crystal.calc = calc
        >>> energy = crystal.get_potential_energy()
        >>> forces = crystal.get_forces()
    """
    
    def __init__(self,
                 model_path: Optional[Union[str, Path]] = None,
                 model: Optional[Any] = None,
                 device: Optional[str] = None,
                 load_training_state: bool = False,
                 compute_stress: bool = True,
                 **kwargs):
        """
        Initialize MatterSim ML calculator.
        
        Args:
            model_path: Path to saved model file (.pth.tar or .pth)
                       Can also be shortcut like 'mattersim-v1.0.0-5M' or 'mattersim-v1.0.0-1M'
            model: Pre-loaded Potential object (alternative to model_path)
            device: Computation device ('cpu' or 'cuda'). If None, uses config default.
            load_training_state: Whether to load optimizer/scheduler state
            compute_stress: Whether to compute stress tensor
            **kwargs: Additional parameters (e.g., args_dict for dataloader)
            
        Raises:
            ImportError: If mattersim is not installed
            ValueError: If neither model_path nor model is provided
            FileNotFoundError: If model file doesn't exist
        """
        # Check if mattersim is available
        try:
            from mattersim.forcefield.m3gnet.m3gnet import M3Gnet
            from mattersim.forcefield.potential import Potential
            from mattersim.datasets.utils.build import build_dataloader
        except ImportError:
            raise ImportError(
                "MatterSim library is required. Install with: pip install mattersim"
            )
        
        # Store MatterSim classes
        self._Potential = Potential
        self._build_dataloader = build_dataloader
        
        # Set model_type for compatibility (MatterSim uses M3GNet)
        self.model_type = 'm3gnet'
        
        # Get device from config if not provided
        if device is None:
            try:
                from ...config import get_config
                device = get_config('calculator.ml.default_device', 'cpu')
            except ImportError:
                device = 'cpu'
        
        # Store additional parameters before super() call
        self.compute_stress = compute_stress
        self.load_training_state = load_training_state
        self.args_dict = kwargs.get('args_dict', {})
        self.args_dict.setdefault('batch_size', 1)
        self.args_dict.setdefault('only_inference', 1)
        
        # Initialize base ML calculator
        # Pass model_path but we'll handle the actual loading ourselves
        super().__init__(model=model, model_path=model_path, device=device, **kwargs)
        
        # Override model_path to Path object if provided
        if model_path:
            self.model_path = Path(model_path)
        
        # Load model if path provided and model not already provided
        # Skip the base class's automatic loading by checking if model is still None
        if self.model_path and self.model is None:
            self._load_model()
        elif model is not None:
            # If model provided directly, use it
            self.potential = model
            self.model = model
            
    def _load_model(self) -> None:
        """
        Load MatterSim model from checkpoint file.
        
        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If model loading fails
        """
        if self.model_path is None:
            raise ValueError("Model path not provided")
        
        # Convert to Path object
        model_path = Path(self.model_path)
        
        # Handle relative paths and shortcuts
        if not model_path.is_absolute():
            # Try expanding user path
            model_path = Path(os.path.expanduser(str(model_path)))
            
            # Handle shortcuts like 'mattersim-v1.0.0-5M' or 'mattersim-v1.0.0-5M.pth'
            model_name = model_path.name
            if (not model_path.exists() and 
                ('mattersim-v1.0.0-5m' in model_name.lower() or 
                 'mattersim-v1.0.0-5m.pth' in model_name.lower())):
                # Check default location
                default_path = Path.home() / '.matsimpy' / 'models' / 'mattersim-v1.0.0-5M.pth.tar'
                if default_path.exists():
                    model_path = default_path
                else:
                    # Try with .pth extension
                    default_path = Path.home() / '.matsimpy' / 'models' / 'mattersim-v1.0.0-5M.pth'
                    if default_path.exists():
                        model_path = default_path
            elif (not model_path.exists() and 
                  ('mattersim-v1.0.0-1m' in model_name.lower() or 
                   'mattersim-v1.0.0-1m.pth' in model_name.lower())):
                # Check default location
                default_path = Path.home() / '.matsimpy' / 'models' / 'mattersim-v1.0.0-1M.pth.tar'
                if default_path.exists():
                    model_path = default_path
                else:
                    default_path = Path.home() / '.matsimpy' / 'models' / 'mattersim-v1.0.0-1M.pth'
                    if default_path.exists():
                        model_path = default_path
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                f"Please ensure the model file exists or use a shortcut like "
                f"'mattersim-v1.0.0-5M'"
            )
        
        # Load model using MatterSim's from_checkpoint
        try:
            self.potential = self._Potential.from_checkpoint(
                load_path=str(model_path),
                device=self.device,
                load_training_state=self.load_training_state
            )
            self.model = self.potential  # Store in model for compatibility
        except Exception as e:
            raise ValueError(f"Failed to load MatterSim model: {str(e)}") from e
        
    def _prepare_model_input(self,
                            positions: np.ndarray,
                            species: list,
                            lattice: Optional[Any],
                            pbc: list) -> Any:
        """
        Prepare input for MatterSim model.
        
        Converts structure to ASE Atoms and prepares graph batch.
        
        Args:
            positions: Atomic positions (N, 3)
            species: Atomic species list (N,)
            lattice: Lattice object (for crystals)
            pbc: Periodic boundary conditions
            
        Returns:
            Graph batch object for MatterSim
        """
        # Convert to ASE Atoms
        from ase import Atoms
        
        if lattice is not None:
            # Crystal structure
            cell = lattice.lattice_vectors
            ase_atoms = Atoms(
                symbols=species,
                positions=positions,
                cell=cell,
                pbc=pbc
            )
        else:
            # Molecule
            ase_atoms = Atoms(
                symbols=species,
                positions=positions
            )
        
        # Get cutoff parameters from model
        if hasattr(self.potential, 'model') and hasattr(self.potential.model, 'model_args'):
            cutoff = self.potential.model.model_args.get('cutoff', 5.0)
            threebody_cutoff = self.potential.model.model_args.get('threebody_cutoff', 4.0)
        else:
            cutoff = 5.0
            threebody_cutoff = 4.0
        
        # Build dataloader
        dataloader = self._build_dataloader(
            [ase_atoms],
            model_type=self.potential.model_name,
            cutoff=cutoff,
            threebody_cutoff=threebody_cutoff,
            **self.args_dict
        )
        
        # Get graph batch
        for graph_batch in dataloader:
            graph_batch = graph_batch.to(self.device)
            return graph_batch
        
        raise ValueError("Failed to create graph batch from structure")
        
    def _run_model(self, model_input: Any) -> Dict[str, np.ndarray]:
        """
        Run MatterSim model prediction.
        
        Args:
            model_input: Graph batch object from _prepare_model_input
            
        Returns:
            dict: Dictionary with 'energy', 'forces', 'stress' keys
        """
        # Convert graph batch to input dictionary
        # batch_to_dict is defined in mattersim.forcefield.potential module
        try:
            from mattersim.forcefield.potential import batch_to_dict
        except ImportError:
            # Fallback: try importing from potential module directly
            import mattersim.forcefield.potential as potential_module
            batch_to_dict = potential_module.batch_to_dict
        
        input_dict = batch_to_dict(model_input, model_type=self.potential.model_name, device=self.device)
        
        # Run forward pass
        with self.potential.ema.average_parameters():
            result = self.potential.forward(
                input_dict,
                include_forces=True,
                include_stresses=self.compute_stress
            )
        
        # Extract results
        energy = result["total_energy"].detach().cpu().numpy()[0]
        forces = result["forces"].detach().cpu().numpy()
        
        # Convert stress if needed
        stress = None
        if self.compute_stress and "stresses" in result:
            # MatterSim returns stress in eV/Å³, convert to 3x3 tensor
            stress_3x3 = result["stresses"].detach().cpu().numpy()[0]
            stress = stress_3x3
        
        return {
            'energy': float(energy),
            'forces': forces,
            'stress': stress if stress is not None else np.zeros((3, 3))
        }


__all__ = ['Mattersim']

