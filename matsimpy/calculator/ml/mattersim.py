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
from .dataloader import build_dataloader
from ...core import Crystal, Molecule

GPA_TO_EV_PER_A3 = 0.006241509125883258


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
        >>> from matsimpy.builders.bulk import from_prototype
        >>> from matsimpy.calculator.ml import Mattersim
        >>>
        >>> # Use proper diamond structure (2 atoms in primitive cell)
        >>> si_crystal = from_prototype('diamond', 'Si', 5.43)
        >>> calc = Mattersim(model_path='~/.matsimpy/models/mattersim-v1.0.0-5M.pth.tar')
        >>> si_crystal.calc = calc
        >>> energy = si_crystal.get_potential_energy()
        >>> forces = si_crystal.get_forces()
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        model: Optional[Any] = None,
        device: Optional[str] = None,
        load_training_state: bool = False,
        compute_stress: bool = True,
        **kwargs,
    ):
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
        self._Potential = None

        # Set model_type for compatibility (MatterSim uses M3GNet)
        self.model_type = "m3gnet"

        if device is None:
            device = "cpu"

        # Store additional parameters before super() call
        self.compute_stress = compute_stress
        self.load_training_state = load_training_state
        self.args_dict = kwargs.get("args_dict", {})
        self.args_dict.setdefault("batch_size", 1)
        self.args_dict.setdefault("only_inference", 1)

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
        if self._Potential is None:
            try:
                from mattersim.forcefield.potential import Potential
            except ImportError as exc:
                raise ImportError(
                    "MatterSim library is required for loading MatterSim models. "
                    "Install with: pip install mattersim"
                ) from exc
            self._Potential = Potential

        # Convert to Path object
        model_path = Path(self.model_path)

        # Handle relative paths and shortcuts
        if not model_path.is_absolute():
            # Try expanding user path
            model_path = Path(os.path.expanduser(str(model_path)))

            # Handle shortcuts like 'mattersim-v1.0.0-5M' or 'mattersim-v1.0.0-5M.pth'
            model_name = model_path.name
            if not model_path.exists() and (
                "mattersim-v1.0.0-5m" in model_name.lower()
                or "mattersim-v1.0.0-5m.pth" in model_name.lower()
            ):
                # Check default location
                default_path = (
                    Path.home() / ".matsimpy" / "models" / "mattersim-v1.0.0-5M.pth.tar"
                )
                if default_path.exists():
                    model_path = default_path
                else:
                    # Try with .pth extension
                    default_path = (
                        Path.home() / ".matsimpy" / "models" / "mattersim-v1.0.0-5M.pth"
                    )
                    if default_path.exists():
                        model_path = default_path
            elif not model_path.exists() and (
                "mattersim-v1.0.0-1m" in model_name.lower()
                or "mattersim-v1.0.0-1m.pth" in model_name.lower()
            ):
                # Check default location
                default_path = (
                    Path.home() / ".matsimpy" / "models" / "mattersim-v1.0.0-1M.pth.tar"
                )
                if default_path.exists():
                    model_path = default_path
                else:
                    default_path = (
                        Path.home() / ".matsimpy" / "models" / "mattersim-v1.0.0-1M.pth"
                    )
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
                load_training_state=self.load_training_state,
            )
            self.model = self.potential  # Store in model for compatibility
        except Exception as e:
            raise ValueError(f"Failed to load MatterSim model: {str(e)}") from e

    def _prepare_model_input(
        self, positions: np.ndarray, species: list, lattice: Optional[Any], pbc: list
    ) -> Any:
        """
        Prepare input for MatterSim model.

        Converts MatSimPy structure data directly to MatterSim's graph format
        using the adapted build_dataloader that works with Crystal/Molecule.

        Args:
            positions: Atomic positions (N, 3) - already in Cartesian coordinates
            species: Atomic species list (N,)
            lattice: Lattice object (for crystals) - contains lattice_vectors
            pbc: Periodic boundary conditions

        Returns:
            Graph batch object for MatterSim
        """
        # Reconstruct structure object from parameters
        if lattice is not None:
            temp_structure = Crystal(
                species, positions, lattice, coords_are_cartesian=True, pbc=pbc
            )
        else:
            temp_structure = Molecule(species, positions)

        # Get cutoff parameters from model
        if hasattr(self.potential, "model") and hasattr(
            self.potential.model, "model_args"
        ):
            cutoff = self.potential.model.model_args.get("cutoff", 5.0)
            threebody_cutoff = self.potential.model.model_args.get(
                "threebody_cutoff", 4.0
            )
        else:
            cutoff = 5.0
            threebody_cutoff = 4.0

        # Get model name (default to 'm3gnet' for MatterSim)
        model_name = getattr(self.potential, "model_name", "m3gnet")

        # Build dataloader directly from MatSimPy structure
        # Extract explicit parameters from args_dict to avoid conflicts
        dataloader_kwargs = self.args_dict.copy()
        batch_size = dataloader_kwargs.pop("batch_size", 1)
        only_inference = dataloader_kwargs.pop("only_inference", True)
        # Convert only_inference to bool if it's 1/0
        if isinstance(only_inference, int):
            only_inference = bool(only_inference)

        dataloader = build_dataloader(
            [temp_structure],
            cutoff=cutoff,
            threebody_cutoff=threebody_cutoff,
            model_type=model_name,
            only_inference=only_inference,
            batch_size=batch_size,
            **dataloader_kwargs,
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
        if hasattr(self.potential, "predict"):
            return self._normalize_prediction(self.potential.predict(model_input))

        if not hasattr(self.potential, "ema"):
            if not hasattr(self.potential, "forward"):
                raise AttributeError("MatterSim potential must provide forward() or predict()")
            result = self.potential.forward(
                model_input, include_forces=True, include_stresses=self.compute_stress
            )
            return self._normalize_prediction(result)

        # Convert graph batch to input dictionary
        # batch_to_dict is defined in mattersim.forcefield.potential module
        try:
            from mattersim.forcefield.potential import batch_to_dict
        except ImportError:
            # Fallback: try importing from potential module directly
            import mattersim.forcefield.potential as potential_module

            batch_to_dict = potential_module.batch_to_dict

        input_dict = batch_to_dict(
            model_input, model_type=self.potential.model_name, device=self.device
        )

        # Run forward pass
        with self.potential.ema.average_parameters():
            result = self.potential.forward(
                input_dict, include_forces=True, include_stresses=self.compute_stress
            )

        return self._normalize_prediction(result)

    def _normalize_prediction(self, result: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """Normalize MatterSim-style outputs to MatSimPy calculator results."""
        energy_value = result.get("energy", result.get("total_energy", 0.0))
        forces_value = result.get("forces", np.zeros((0, 3)))
        stress_value = result.get("stress", result.get("stresses", np.zeros((3, 3))))

        energy_array = self._to_numpy(energy_value)
        forces = self._to_numpy(forces_value)
        stress = self._to_numpy(stress_value)

        if energy_array.shape:
            energy = float(energy_array.reshape(-1)[0])
        else:
            energy = float(energy_array)

        if stress.ndim == 3 and stress.shape[0] == 1:
            stress = stress[0]
        if stress.size == 0:
            stress = np.zeros((3, 3))
        else:
            stress = stress * GPA_TO_EV_PER_A3

        normalized = {
            "energy": energy,
            "free_energy": energy,
            "forces": forces,
            "stress": stress,
        }
        if "energy_per_atom" in result:
            normalized["energy_per_atom"] = float(
                self._to_numpy(result["energy_per_atom"]).reshape(-1)[0]
            )
        elif forces.ndim == 2 and len(forces) > 0:
            normalized["energy_per_atom"] = energy / len(forces)
        return normalized

    @staticmethod
    def _to_numpy(value: Any) -> np.ndarray:
        if hasattr(value, "detach"):
            value = value.detach()
        if hasattr(value, "cpu"):
            value = value.cpu()
        if hasattr(value, "numpy"):
            return value.numpy()
        return np.asarray(value)

    def set_model(self, model: Any) -> None:
        super().set_model(model)
        self.potential = model

    def as_dict(self) -> Dict[str, Any]:
        """
        Serialize Mattersim calculator to dictionary (MSONable).

        Note: MatterSim Potential objects are not serialized. Only model_path
        and configuration are stored. The model will be reloaded when deserializing.

        Returns:
            Dictionary representation of the calculator
        """
        d = super().as_dict()

        # Add Mattersim-specific fields
        if hasattr(self, "model_type"):
            d["model_type"] = self.model_type
        if hasattr(self, "compute_stress"):
            d["compute_stress"] = self.compute_stress
        if hasattr(self, "load_training_state"):
            d["load_training_state"] = self.load_training_state
        if hasattr(self, "args_dict"):
            d["args_dict"] = self.args_dict.copy()

        # Remove potential/model from parameters if present
        if "potential" in d.get("parameters", {}):
            d["parameters"] = {
                k: v
                for k, v in d["parameters"].items()
                if k not in ["potential", "model"]
            }

        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Mattersim":
        """
        Deserialize Mattersim calculator from dictionary (MSONable).

        Note: The MatterSim Potential will be automatically reloaded from
        model_path if provided.

        Args:
            d: Dictionary representation of the calculator

        Returns:
            Mattersim instance
        """
        # Extract Mattersim-specific fields
        model_path = d.get("model_path")
        device = d.get("device", "cpu")
        model_type = d.get("model_type")
        compute_stress = d.get("compute_stress", True)
        load_training_state = d.get("load_training_state", False)
        args_dict = d.get("args_dict", {})

        # Extract parameters
        parameters = d.get("parameters", {}).copy()
        # Remove fields that are handled separately
        for key in ["model", "model_path", "device", "potential", "model_type"]:
            parameters.pop(key, None)

        # Create instance
        calc = cls(
            model_path=model_path,
            device=device,
            compute_stress=compute_stress,
            load_training_state=load_training_state,
            args_dict=args_dict,
            **parameters,
        )

        # Restore results if present
        if "results" in d:
            results = {}
            for key, value in d["results"].items():
                if isinstance(value, list):
                    results[key] = np.array(value)
                else:
                    results[key] = value
            calc.results = results
            calc._calculation_performed = True

        return calc


__all__ = ["Mattersim"]
