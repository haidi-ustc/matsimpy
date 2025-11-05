"""
Interface structure builders.

Tools for creating interfaces between materials:
- Heterostructures (film on substrate)
- Grain boundaries
- Multilayer structures

Note: This is a placeholder module. Full interface generation requires
more sophisticated algorithms for lattice matching, strain minimization,
and interface optimization.

Examples:
    >>> from matsimpy import Crystal, Lattice
    >>> from matsimpy.builders.interface import create_simple_interface
    >>> 
    >>> si = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
    >>> ge = Crystal(['Ge'], [[0,0,0]], Lattice.cubic(5.65))
    >>> 
    >>> # Simple stacking interface (placeholder)
    >>> # interface = create_simple_interface(si, ge, vacuum=5.0)
"""

# Placeholder - full implementation would go in separate files
# For now, just define the structure

__all__ = []

