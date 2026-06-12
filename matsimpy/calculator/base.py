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

    def __init__(self, run: bool = True, **parameters):
        """
        Initialize calculator with parameters.

        Args:
            run: If True (default), execute external code and parse output.
                 If False, only write input files. Call read_results() later
                 to parse output files manually.
            **parameters: Calculator-specific parameters
        """
        self.parameters = parameters.copy()
        self.results: Dict[str, Any] = {}
        self.structure: Optional[Union[Crystal, Molecule]] = None
        self._calculation_performed = False
        self.run = run
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

        For pure-Python calculators that override _compute() (e.g. LJ, MatterSim),
        the legacy _compute() path is used directly.

        For external-code calculators (VASP, Gaussian, LAMMPS), this writes input
        files, optionally executes the external program, and parses output.

        When run=True (default): write_input → _execute → _parse_output
        When run=False: write_input only. User calls read_results() later.

        Args:
            structure: Crystal or Molecule structure to calculate

        Raises:
            ValueError: If structure is not a valid Crystal or Molecule
        """
        if not isinstance(structure, (Crystal, Molecule)):
            raise ValueError(
                f"Calculator requires Crystal or Molecule, got {type(structure)}"
            )

        self.results.clear()
        self.structure = structure
        self._calculation_performed = False
        # Record the structure identity before running so that callers can
        # cheaply detect whether results are stale for a different structure.
        self._last_structure_hash = structure._structural_hash()

        # Detect which path to take:
        # - Legacy: subclass overrides _compute() (pure-Python calculators)
        # - Run-mode: subclass overrides write_input() (external-code calculators)
        if type(self)._compute is not Calculator._compute:
            # Legacy path: pure-Python calculators (LJ, MatterSim)
            self._compute()
        else:
            # Run-mode path: external-code calculators
            self.write_input(structure)
            if self.run:
                self._execute()
                self._parse_output()

        self._calculation_performed = True

    def _compute(self) -> None:
        """
        Perform the actual calculation (legacy path for pure-Python calculators).

        Pure-Python calculators (LJ, MatterSim) override this method to compute
        energy, forces, and stress directly without file I/O or subprocess calls.

        External-code calculators (VASP, Gaussian, LAMMPS) should NOT override
        this — they use write_input() / _execute() / _parse_output() instead.
        """
        # Default no-op: external-code calculators use the run-mode pipeline
        pass

    def write_input(self, structure: Union[Crystal, Molecule]) -> None:
        """
        Write input files for external code.

        Default implementation does nothing. Subclasses for external-code
        calculators (VASP, Gaussian, LAMMPS) should override this.

        Args:
            structure: Crystal or Molecule to write inputs for
        """
        pass

    def read_results(self) -> None:
        """
        Read and parse pre-existing output files.

        Called by user after run=False calculate() and manual execution.
        Calls _parse_output() internally; subclasses override _parse_output().
        """
        self._parse_output()
        self._calculation_performed = True

    def _execute(self) -> None:
        """
        Execute external code via subprocess.

        Default implementation does nothing. Subclasses for external-code
        calculators override this to run the relevant command.
        """
        pass

    def _parse_output(self) -> None:
        """
        Parse output files produced by external code.

        Default implementation does nothing. Subclasses override this
        to parse output files and populate self.results.
        """
        pass

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

    def get_stress(self, voigt: bool = False) -> np.ndarray:
        """
        Get stress tensor from calculation results.

        Args:
            voigt: If True, return Voigt notation [xx, yy, zz, yz, xz, xy].
                   If False, return the full 3x3 tensor.

        Returns:
            np.ndarray: Stress tensor of shape (3, 3) or (6,) in eV/Å³

        Raises:
            ValueError: If calculation has not been performed or stress not available
        """
        if not self._calculation_performed:
            raise ValueError("Calculation not performed. Call calculate() first.")
        if "stress" not in self.results:
            raise ValueError("Stress not available in results.")
        stress = np.array(self.results["stress"])
        if voigt:
            if stress.shape == (6,):
                return stress
            if stress.shape != (3, 3):
                raise ValueError(f"Stress must have shape (3, 3), got {stress.shape}")
            return np.array(
                [
                    stress[0, 0],
                    stress[1, 1],
                    stress[2, 2],
                    stress[1, 2],
                    stress[0, 2],
                    stress[0, 1],
                ]
            )
        if stress.shape == (6,):
            return np.array(
                [
                    [stress[0], stress[5], stress[4]],
                    [stress[5], stress[1], stress[3]],
                    [stress[4], stress[3], stress[2]],
                ]
            )
        return stress

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
