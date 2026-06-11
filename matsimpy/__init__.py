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
def _get_version() -> str:
    from pathlib import Path
    import re

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if pyproject.exists():
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.MULTILINE)
        if match:
            return match.group(1)

    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("MatSimPy")
    except PackageNotFoundError:  # pragma: no cover - source tree without install metadata
        return "0.8.0"


__version__ = _get_version()


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
