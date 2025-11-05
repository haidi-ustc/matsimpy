"""
Base class for DFT code interfaces.

All DFT code interfaces should inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..core import Crystal

class DFTCodeInterface(ABC):
    """Base class for DFT code interfaces."""
    
    @abstractmethod
    def write_input(self, crystal: Crystal, filename: str, **kwargs) -> None:
        """Write input file for DFT calculation."""
        pass
    
    @abstractmethod
    def read_output(self, filename: str) -> dict:
        """Read output file from DFT calculation."""
        pass
    
    @abstractmethod
    def get_energy(self, output_file: str) -> float:
        """Extract energy from output file."""
        pass

__all__ = ['DFTCodeInterface']

