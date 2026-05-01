"""
Base calculator class for MatSimPy.

All calculators inherit from this base class and implement the abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
import numpy as np
from monty.json import MSONable
from ..core import Crystal, Molecule


class Calculator(ABC, MSONable):
    """
    Base class for all calculators.

    Calculators are objects that can compute properties (energy, forces, stress, etc.)
    for Crystal or Molecule structures. They follow an ASE-inspired interface but
    are adapted for MatSimPy's architecture.

    Attributes:
        parameters (dict): Calculator-specific parameters
        results (dict): Storage for calculation results
        structure (Crystal or Molecule): The structure being calculated

    Example:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.calculator import LennardJones
        >>>
        >>> crystal = Crystal(['Ar'], [[0,0,0]], Lattice.cubic(5.0))
        >>> calc = LennardJones(sigma=3.4, epsilon=0.0104)
        >>> crystal.calc = calc
        >>> calc.calculate(crystal)
        >>> energy = calc.get_potential_energy()
    """

    def __init__(self, **parameters):
        """
        Initialize calculator with parameters.

        Args:
            **parameters: Calculator-specific parameters
        """
        self.parameters = parameters.copy()
        self.results: Dict[str, Any] = {}
        self.structure: Optional[Union[Crystal, Molecule]] = None
        self._calculation_performed = False
        # Hash of the structure last passed to calculate().  Used by Structure
        # to detect when the calculator's cached results are stale (i.e. the
        # attached structure has changed since the last calculate() call).
        self._last_structure_hash: Optional[int] = None

    def set_parameters(self, **kwargs) -> None:
        """
        Set calculator parameters.

        Args:
            **kwargs: Parameters to set
        """
        self.parameters.update(kwargs)
        # Clear results if parameters change
        self.results.clear()
        self._calculation_performed = False
        self._last_structure_hash = None

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get current calculator parameters.

        Returns:
            dict: Copy of current parameters
        """
        return self.parameters.copy()

    def update_parameters(self, **kwargs) -> None:
        """
        Update specific parameters without clearing others.

        Args:
            **kwargs: Parameters to update
        """
        self.set_parameters(**kwargs)

    def calculate(self, structure: Union[Crystal, Molecule]) -> None:
        """
        Perform calculation on the given structure.

        This is the main entry point for calculations. It stores the structure,
        performs the calculation, and stores results in self.results.

        Args:
            structure: Crystal or Molecule structure to calculate

        Raises:
            ValueError: If structure is not a valid Crystal or Molecule
        """
        if not isinstance(structure, (Crystal, Molecule)):
            raise ValueError(
                f"Calculator requires Crystal or Molecule, got {type(structure)}"
            )

        self.structure = structure
        self._calculation_performed = False
        # Record the structure identity before running so that callers can
        # cheaply detect whether results are stale for a different structure.
        self._last_structure_hash = hash(structure)

        # Perform the actual calculation (implemented by subclasses)
        self._compute()

        self._calculation_performed = True

    @abstractmethod
    def _compute(self) -> None:
        """
        Perform the actual calculation.

        This method should:
        1. Compute energy and store in self.results['energy']
        2. Compute forces and store in self.results['forces'] (if applicable)
        3. Compute stress and store in self.results['stress'] (if applicable)
        4. Store any other relevant results

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _compute()")

    def get_potential_energy(self) -> float:
        """
        Get potential energy from calculation results.

        Returns:
            float: Potential energy in eV

        Raises:
            ValueError: If calculation has not been performed or energy not available
        """
        if not self._calculation_performed:
            raise ValueError("Calculation not performed. Call calculate() first.")
        if "energy" not in self.results:
            raise ValueError("Energy not available in results.")
        return self.results["energy"]

    def get_forces(self) -> np.ndarray:
        """
        Get forces from calculation results.

        Returns:
            np.ndarray: Forces array of shape (N, 3) in eV/Å

        Raises:
            ValueError: If calculation has not been performed or forces not available
        """
        if not self._calculation_performed:
            raise ValueError("Calculation not performed. Call calculate() first.")
        if "forces" not in self.results:
            raise ValueError("Forces not available in results.")
        return np.array(self.results["forces"])

    def get_stress(self) -> np.ndarray:
        """
        Get stress tensor from calculation results.

        Returns:
            np.ndarray: Stress tensor of shape (3, 3) or (6,) in eV/Å³

        Raises:
            ValueError: If calculation has not been performed or stress not available
        """
        if not self._calculation_performed:
            raise ValueError("Calculation not performed. Call calculate() first.")
        if "stress" not in self.results:
            raise ValueError("Stress not available in results.")
        return np.array(self.results["stress"])

    def get_result(self, key: str) -> Any:
        """
        Get a specific result by key.

        Args:
            key: Result key (e.g., 'energy', 'forces', 'stress')

        Returns:
            Result value

        Raises:
            ValueError: If key not found in results
        """
        if key not in self.results:
            raise ValueError(
                f"Result '{key}' not available. Available: {list(self.results.keys())}"
            )
        return self.results[key]

    def as_dict(self) -> Dict[str, Any]:
        """
        Serialize calculator to dictionary (MSONable).

        Returns:
            Dictionary representation of the calculator
        """
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "parameters": self.parameters.copy(),
        }
        # Only include results if calculation has been performed
        if self._calculation_performed and self.results:
            # Convert numpy arrays to lists for JSON serialization
            results_dict = {}
            for key, value in self.results.items():
                if isinstance(value, np.ndarray):
                    results_dict[key] = value.tolist()
                else:
                    results_dict[key] = value
            d["results"] = results_dict
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Calculator":
        """
        Deserialize calculator from dictionary (MSONable).

        Args:
            d: Dictionary representation of the calculator

        Returns:
            Calculator instance
        """
        # Extract parameters
        parameters = d.get("parameters", {})

        # Create instance
        calc = cls(**parameters)

        # Restore results if present
        if "results" in d:
            # Convert lists back to numpy arrays
            results = {}
            for key, value in d["results"].items():
                if isinstance(value, list):
                    results[key] = np.array(value)
                else:
                    results[key] = value
            calc.results = results
            calc._calculation_performed = True

        return calc

    def __repr__(self) -> str:
        """String representation of calculator."""
        params_str = ", ".join(f"{k}={v}" for k, v in self.parameters.items())
        return f"{self.__class__.__name__}({params_str})"


__all__ = ["Calculator"]
