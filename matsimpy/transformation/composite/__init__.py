"""
Composite transformation tools for high-throughput structure generation.

This module provides advanced tools for:
- Reusable transformation pipelines
- Parameter sweeps
- Batch processing
- Combinatorial generation
"""

from typing import List, Callable, Union, Any
from ...core import Crystal, Molecule
from ..base import _copy_structure, _validate_structure


# Import basic chain functions
def chain(
    structure: Union[Crystal, Molecule],
    transformations: List[Callable],
    inplace: bool = False,
) -> Union[Crystal, Molecule]:
    """
    Apply multiple transformations in sequence.

    Args:
        structure: Crystal or Molecule to transform
        transformations: List of transformation functions to apply in order
        inplace: If True, apply transformations in-place (default: False)

    Returns:
        Transformed structure

    Examples:
        >>> from matsimpy.transformation import translate, rotate, chain
        >>> mol = chain(molecule, [
        ...     lambda s: translate(s, [1, 1, 1]),
        ...     lambda s: rotate(s, 90, [0, 0, 1])
        ... ])
    """
    _validate_structure(structure)

    if not inplace:
        structure = _copy_structure(structure)

    result = structure
    for transform in transformations:
        result = transform(result)

    return result


def apply_transformations(
    structure: Union[Crystal, Molecule],
    *transformations: Callable,
    inplace: bool = False
) -> Union[Crystal, Molecule]:
    """
    Apply multiple transformations as separate arguments.

    More convenient syntax than chain() for a few transformations.

    Args:
        structure: Crystal or Molecule to transform
        *transformations: Transformation functions to apply in order
        inplace: If True, apply transformations in-place (default: False)

    Returns:
        Transformed structure

    Examples:
        >>> from matsimpy.transformation import translate, rotate, apply_transformations
        >>> mol = apply_transformations(
        ...     molecule,
        ...     lambda s: translate(s, [1, 1, 1]),
        ...     lambda s: rotate(s, 90, [0, 0, 1])
        ... )
    """
    return chain(structure, list(transformations), inplace=inplace)


# Import new pipeline class
from .pipeline import TransformationPipeline
from .sweep import ParameterSweep
from .batch import BatchProcessor, BatchResult

__all__ = [
    "chain",
    "apply_transformations",
    "TransformationPipeline",
    "ParameterSweep",
    "BatchProcessor",
    "BatchResult",
]
