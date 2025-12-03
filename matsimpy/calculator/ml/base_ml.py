"""
Base class for machine learning potential calculators.

Provides common functionality for all ML calculators including model loading,
input preparation, and framework abstraction.
"""

import numpy as np
from typing import Optional, Dict, Any, Union
from pathlib import Path
from abc import abstractmethod
from ..base import Calculator
from ...core import Crystal, Molecule


class BaseML(Calculator):
    """
    Base class for machine learning potential calculators.

    Provides common functionality for ML calculators:
    - Model loading and management
    - Input preparation for different frameworks
    - Device management (CPU/GPU)

    Subclasses should implement:
    - _load_model(): Framework-specific model loading
    - _prepare_input(): Framework-specific input preparation
    - _run_model(): Framework-specific model inference

    Attributes:
        model: Loaded ML model
        model_path: Path to model file
        device: Computation device ('cpu' or 'cuda')

    Example:
        >>> from matsimpy.calculator.ml import BaseML
        >>>
        >>> class MyMLCalculator(BaseML):
        ...     def _load_model(self):
        ...         # Load your model
        ...         pass
        ...     def _prepare_input(self, structure):
        ...         # Prepare input
        ...         pass
        ...     def _run_model(self, model_input):
        ...         # Run inference
        ...         pass
    """

    def __init__(
        self,
        model: Optional[Any] = None,
        model_path: Optional[Union[str, Path]] = None,
        device: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize ML calculator.

        Args:
            model: Pre-loaded model object
            model_path: Path to saved model file
            device: Computation device ('cpu' or 'cuda'). If None, uses config default.
            **kwargs: Additional parameters
        """
        # Get default device from config if not provided
        if device is None:
            try:
                from ...config import get_config

                device = get_config("calculator.ml.default_device", "cpu")
            except ImportError:
                device = "cpu"

        super().__init__(model=model, model_path=model_path, device=device, **kwargs)

        self.model = model
        self.model_path = Path(model_path) if model_path else None
        self.device = device

        # Load model if path provided
        if self.model_path and self.model is None:
            self._load_model()
        elif self.model is None and self.model_path is None:
            raise ValueError("Either model_path or model must be provided")

    @abstractmethod
    def _load_model(self) -> None:
        """
        Load ML model from file.

        This method should load the model from self.model_path and store it
        in self.model. Framework-specific implementations should override this.

        Raises:
            FileNotFoundError: If model file doesn't exist
            NotImplementedError: If model loading not implemented
        """
        raise NotImplementedError("Subclasses must implement _load_model()")

    def set_model(self, model: Any) -> None:
        """
        Set or update the ML model.

        Args:
            model: ML model object
        """
        self.model = model
        self.results.clear()
        self._calculation_performed = False

    def _compute(self) -> None:
        """
        Compute energy and forces using ML model.

        This method orchestrates the ML calculation workflow:
        1. Prepare input from structure
        2. Run model inference
        3. Extract and store results
        """
        if self.structure is None:
            raise ValueError("Structure not set. Call calculate(structure) first.")

        if self.model is None:
            raise ValueError("ML model not loaded. Provide model_path or model.")

        # Get structure data
        if isinstance(self.structure, Crystal):
            positions = self.structure.cart_positions
            lattice = self.structure.lattice
            species = self.structure.species
            pbc = self.structure.pbc
        else:
            # Molecule uses positions directly (Cartesian)
            positions = np.array(self.structure.positions)
            lattice = None
            species = self.structure.species
            pbc = [False, False, False]

        # Prepare model input
        model_input = self._prepare_model_input(positions, species, lattice, pbc)

        # Run prediction
        predictions = self._run_model(model_input)

        # Extract results
        energy = predictions.get("energy", 0.0)
        forces = predictions.get("forces", np.zeros((len(positions), 3)))
        stress = predictions.get("stress", np.zeros((3, 3)))

        # Store results
        self.results["energy"] = energy
        self.results["forces"] = forces
        if lattice is not None:
            self.results["stress"] = stress

    def _prepare_model_input(
        self, positions: np.ndarray, species: list, lattice: Optional[Any], pbc: list
    ) -> Dict[str, Any]:
        """
        Prepare input for ML model.

        Converts structure data to format expected by ML model.
        This is a generic implementation that subclasses can override
        for framework-specific formats.

        Args:
            positions: Atomic positions (N, 3)
            species: Atomic species list (N,)
            lattice: Lattice object (for crystals)
            pbc: Periodic boundary conditions

        Returns:
            dict: Model input dictionary
        """
        input_dict = {
            "positions": positions,
            "species": species,
            "pbc": pbc,
        }

        if lattice is not None:
            input_dict["lattice"] = lattice.lattice_vectors
            input_dict["cell"] = lattice.lattice_vectors

        return input_dict

    @abstractmethod
    def _run_model(self, model_input: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """
        Run ML model prediction.

        This method should take the prepared input and run inference using
        the loaded model. Framework-specific implementations should override this.

        Args:
            model_input: Dictionary of model inputs

        Returns:
            dict: Dictionary with 'energy', 'forces', 'stress' keys

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _run_model()")

    def as_dict(self) -> Dict[str, Any]:
        """
        Serialize ML calculator to dictionary (MSONable).

        Note: ML models are not serialized. Only model_path is stored.
        The model will need to be reloaded when deserializing.

        Returns:
            Dictionary representation of the calculator
        """
        d = super().as_dict()

        # Add ML-specific fields
        if self.model_path is not None:
            d["model_path"] = str(self.model_path)
        d["device"] = self.device

        # Remove model object from parameters if present (models can't be serialized)
        if "model" in d.get("parameters", {}):
            d["parameters"] = {k: v for k, v in d["parameters"].items() if k != "model"}

        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BaseML":
        """
        Deserialize ML calculator from dictionary (MSONable).

        Note: The model will be automatically reloaded from model_path if provided.

        Args:
            d: Dictionary representation of the calculator

        Returns:
            BaseML instance
        """
        # Extract ML-specific fields
        model_path = d.get("model_path")
        device = d.get("device", "cpu")

        # Extract parameters (excluding model)
        parameters = d.get("parameters", {}).copy()
        if "model" in parameters:
            del parameters["model"]
        if "model_path" in parameters:
            del parameters["model_path"]
        if "device" in parameters:
            del parameters["device"]

        # Create instance
        calc = cls(model_path=model_path, device=device, **parameters)

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


__all__ = ["BaseML"]
