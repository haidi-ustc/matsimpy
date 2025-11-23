"""
Configuration module for MatSimPy.

Provides global configuration management for user settings, paths, and defaults.

Usage:
    >>> from matsimpy.config import get_config, ConfigManager
    >>>
    >>> # Get config value
    >>> device = get_config('calculator.ml.default_device')
    >>>
    >>> # Get full config manager
    >>> config = ConfigManager()
    >>> config.set('calculator.ml.default_device', 'cuda', save=True)
"""

from .manager import ConfigManager, get_config_manager, get_config
from .defaults import get_default_config

__all__ = [
    "ConfigManager",
    "get_config_manager",
    "get_config",
    "get_default_config",
]
