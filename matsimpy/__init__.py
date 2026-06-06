"""
MatSimPy - Materials Simulation in Python

A comprehensive package for materials simulation and analysis.
"""

# Core modules
from .core import (
    Structure,
    Crystal,
    Molecule,
    Lattice,
    Composition,
    Site,
    CrystalSite,
    Element,
)

# Constants
from .constants import POSITION_TOL, LATTICE_TOL

# Version
__version__ = "0.5.0"


# Plugin discovery (lazy — call discover_plugins() to load extensions)
def discover_plugins():
    """Discover and load all registered plugins via entry points.

    Scans Python entry point groups:
    - ``matsimpy.transformations``
    - ``matsimpy.builders``
    - ``matsimpy.io_formats``
    - ``matsimpy.storage_backends``

    Returns a dict with counts by group::

        >>> import matsimpy
        >>> matsimpy.discover_plugins()
        {'transformations': 0, 'builders': 0, 'io_formats': 0, 'storage_backends': 0}
    """
    from .plugins import discover_all
    return discover_all()


__all__ = [
    # Core classes
    "Structure",
    "Crystal",
    "Molecule",
    "Lattice",
    "Composition",
    "Site",
    "CrystalSite",
    "Element",
    # Constants
    "POSITION_TOL",
    "LATTICE_TOL",
    # Version
    "__version__",
    # Plugin discovery
    "discover_plugins",
]
