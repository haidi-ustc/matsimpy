"""
Base class for DFT (Density Functional Theory) calculators.

Provides common functionality for file-based DFT calculators including
input file generation, calculation execution, and output parsing.
"""

from abc import abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
from ..base import Calculator
from ...core import Crystal, Molecule


class BaseDFT(Calculator):
    """
    Base class for DFT calculators (file-based).
    
    DFT calculators work by:
    1. Writing input files for external DFT codes
    2. Executing the DFT calculation
    3. Reading and parsing output files
    
    Subclasses should implement:
    - _write_input(): Write input files for specific DFT code
    - _run_calculation(): Execute the DFT calculation
    - _read_output(): Parse output files and extract results
    
    Attributes:
        directory: Working directory for calculation files
        input_files: Dictionary mapping file types to paths
        output_files: Dictionary mapping file types to paths
        command: Command to execute DFT calculation
        
    Example:
        >>> from matsimpy.calculator.dft import BaseDFT
        >>> 
        >>> class VASP(BaseDFT):
        ...     def _write_input(self, structure):
        ...         # Write POSCAR, INCAR, KPOINTS
        ...         pass
        ...     def _run_calculation(self):
        ...         # Execute vasp command
        ...         pass
        ...     def _read_output(self):
        ...         # Parse OUTCAR
        ...         pass
    """
    
    def __init__(self,
                 directory: str = './',
                 command: Optional[str] = None,
                 **parameters):
        """
        Initialize DFT calculator.
        
        Args:
            directory: Working directory for calculation files
            command: Command to execute DFT calculation (e.g., 'vasp', 'pw.x')
            **parameters: DFT code-specific parameters
        """
        super().__init__(directory=directory, command=command, **parameters)
        
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        
        self.command = command
        self.input_files: Dict[str, Path] = {}
        self.output_files: Dict[str, Path] = {}
        
    def _compute(self) -> None:
        """
        Perform DFT calculation.
        
        Orchestrates the DFT workflow:
        1. Write input files
        2. Execute calculation
        3. Read and parse output
        """
        if self.structure is None:
            raise ValueError("Structure not set. Call calculate(structure) first.")
            
        # Write input files
        self._write_input(self.structure)
        
        # Execute calculation
        self._run_calculation()
        
        # Read output and extract results
        results = self._read_output()
        
        # Store results
        self.results.update(results)
        
    @abstractmethod
    def _write_input(self, structure: Crystal) -> None:
        """
        Write input files for DFT calculation.
        
        This method should create all necessary input files (e.g., POSCAR,
        INCAR, KPOINTS for VASP) in self.directory.
        
        Args:
            structure: Crystal structure to calculate
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _write_input()")
        
    @abstractmethod
    def _run_calculation(self) -> None:
        """
        Execute DFT calculation.
        
        This method should run the external DFT program using self.command.
        It should handle execution, waiting for completion, and error checking.
        
        Raises:
            NotImplementedError: If not implemented by subclass
            RuntimeError: If calculation fails
        """
        raise NotImplementedError("Subclasses must implement _run_calculation()")
        
    @abstractmethod
    def _read_output(self) -> Dict[str, Any]:
        """
        Read and parse output files.
        
        This method should read output files created by the DFT calculation
        and extract energy, forces, stress, etc.
        
        Returns:
            dict: Dictionary with calculation results:
                - 'energy': Total energy in eV
                - 'forces': Forces array (N, 3) in eV/Å
                - 'stress': Stress tensor (3, 3) in eV/Å³
                - Any other relevant results
                
        Raises:
            NotImplementedError: If not implemented by subclass
            FileNotFoundError: If output files not found
        """
        raise NotImplementedError("Subclasses must implement _read_output()")
        
    def get_input_files(self) -> Dict[str, Path]:
        """
        Get dictionary of input file paths.
        
        Returns:
            dict: Mapping of file types to paths
        """
        return self.input_files.copy()
        
    def get_output_files(self) -> Dict[str, Path]:
        """
        Get dictionary of output file paths.
        
        Returns:
            dict: Mapping of file types to paths
        """
        return self.output_files.copy()


__all__ = ['BaseDFT']

