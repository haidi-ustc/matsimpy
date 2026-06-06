"""
MatSimPy exception hierarchy.

Provides domain-specific exception classes for consistent error handling
across all layers. All MatSimPy-specific exceptions inherit from
MatSimPyError.
"""


class MatSimPyError(Exception):
    """Base exception for all MatSimPy-specific errors."""
    pass


class FormatError(MatSimPyError):
    """Raised when a file format is malformed or cannot be parsed."""
    pass


class StructureTypeError(MatSimPyError, TypeError):
    """Raised when a structure type is incompatible with an operation."""
    pass


class RegistryError(MatSimPyError):
    """Raised on duplicate registration or unknown spec/handler name."""
    pass


class ValidationError(MatSimPyError, ValueError):
    """Raised when structure validation fails (species, positions, lattice)."""
    pass


class StorageError(MatSimPyError):
    """Raised on storage backend failures."""
    pass


__all__ = [
    "MatSimPyError",
    "FormatError",
    "StructureTypeError",
    "RegistryError",
    "ValidationError",
    "StorageError",
]
