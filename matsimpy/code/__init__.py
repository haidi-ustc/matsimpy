"""
DFT code interfaces.

This module provides interfaces for various DFT codes:
- Quantum Espresso
- VASP (future)
- PWDFT (future)
"""

from .quantum_espresso import (
    write_input as qe_write_input,
    read_output as qe_read_output,
)
from .vasp import write_input as vasp_write_input, read_output as vasp_read_output

# Code registry mapping code names to their write_input/read_output functions
_CODE_REGISTRY = {
    "quantum_espresso": {
        "write_input": qe_write_input,
        "read_output": qe_read_output,
    },
    "qe": {
        "write_input": qe_write_input,
        "read_output": qe_read_output,
    },
    "vasp": {
        "write_input": vasp_write_input,
        "read_output": vasp_read_output,
    },
}


def get_code_interface(code: str):
    """
    Get code interface functions for a given DFT code.

    Args:
        code: Code name (e.g., 'quantum_espresso', 'qe', 'vasp')

    Returns:
        dict: Dictionary with 'write_input' and 'read_output' functions

    Raises:
        ValueError: If code is not supported
    """
    code_lower = code.lower()
    if code_lower not in _CODE_REGISTRY:
        raise ValueError(
            f"Unsupported DFT code: {code}. "
            f"Supported codes: {list(_CODE_REGISTRY.keys())}"
        )
    return _CODE_REGISTRY[code_lower]


__all__ = ["get_code_interface", "_CODE_REGISTRY"]
