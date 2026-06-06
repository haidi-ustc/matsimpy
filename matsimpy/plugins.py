"""
Plugin discovery via Python entry points.

Discovers and loads plugins registered under MatSimPy's entry point groups:
- ``matsimpy.transformations``
- ``matsimpy.builders``
- ``matsimpy.io_formats``
- ``matsimpy.storage_backends``

Usage::

    >>> from matsimpy.plugins import discover_all
    >>> counts = discover_all()
    >>> print(counts)
    {'transformations': 0, 'builders': 0, 'io_formats': 0, 'storage_backends': 0}
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


def discover_transformations() -> int:
    """Load transformation plugins from entry points. Returns count loaded."""
    from matsimpy.transformation.registry import registry
    from matsimpy.transformation.spec import TransformationSpec

    count = 0
    try:
        group = entry_points(group="matsimpy.transformations")
    except TypeError:
        group = entry_points().get("matsimpy.transformations", [])

    for ep in group:
        try:
            spec_or_list = ep.load()()
            specs = spec_or_list if isinstance(spec_or_list, list) else [spec_or_list]
            for spec in specs:
                if isinstance(spec, TransformationSpec):
                    registry.register(spec)
                    count += 1
        except Exception:
            logger.exception("Failed to load transformation plugin: %s", ep.name)
    return count


def discover_builders() -> int:
    """Load builder plugins from entry points. Returns count loaded."""
    from matsimpy.builders.registry import registry
    from matsimpy.builders.registry import BuilderSpec

    count = 0
    try:
        group = entry_points(group="matsimpy.builders")
    except TypeError:
        group = entry_points().get("matsimpy.builders", [])

    for ep in group:
        try:
            specs = ep.load()()
            for spec in specs:
                registry.register(spec)
                count += 1
        except Exception:
            logger.exception("Failed to load builder plugin: %s", ep.name)
    return count


def discover_io_formats() -> int:
    """Load IO format plugins from entry points. Returns count loaded."""
    from matsimpy.io.registry import registry

    count = 0
    try:
        group = entry_points(group="matsimpy.io_formats")
    except TypeError:
        group = entry_points().get("matsimpy.io_formats", [])

    for ep in group:
        try:
            handlers = ep.load()()
            for handler in handlers:
                registry.register(handler)
                count += 1
        except Exception:
            logger.exception("Failed to load IO format plugin: %s", ep.name)
    return count


def discover_storage_backends() -> int:
    """Load storage backend plugins. Returns count loaded."""
    count = 0
    try:
        group = entry_points(group="matsimpy.storage_backends")
    except TypeError:
        group = entry_points().get("matsimpy.storage_backends", [])

    for ep in group:
        logger.info("Discovered storage backend: %s", ep.name)
        count += 1
    return count


def discover_all() -> dict[str, int]:
    """Discover and load all plugins. Returns counts by group."""
    results = {
        "transformations": 0,
        "builders": 0,
        "io_formats": 0,
        "storage_backends": 0,
    }
    results["transformations"] = discover_transformations()
    results["builders"] = discover_builders()
    results["io_formats"] = discover_io_formats()
    results["storage_backends"] = discover_storage_backends()
    return results


__all__ = [
    "discover_all",
    "discover_transformations",
    "discover_builders",
    "discover_io_formats",
    "discover_storage_backends",
]
