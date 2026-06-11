"""
Default configuration for MatSimPy.

Defines the default configuration structure and values.
"""

from pathlib import Path
from typing import Dict, Any


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration dictionary.

    Returns:
        dict: Default configuration with all settings
    """
    return {
        "calculator": {
            "classical": {
                "lennard_jones": {
                    "default_cutoff": None,  # Auto-calculate as 3*sigma
                    "default_rc_smooth": None,
                }
            },
            "ml": {
                "default_device": "cpu",
                "default_model_dir": "~/.matsimpy/models",
                "mattersim": {
                    "default_model_type": "mace",
                },
            },
            "dft": {
                "default_directory": "./calc",
                "default_restart": True,
                "vasp": {
                    "default_command": "vasp",
                    "default_npar": 1,
                    "default_ncore": 1,
                },
            },
        },
        "paths": {
            "models": "~/.matsimpy/models",
            "cache": "~/.matsimpy/cache",
            "output": "./output",
            "dft_workdir": "./calc",
        },
        "io": {
            "default_format": "vasp",  # For crystals
            "precision": 8,  # Decimal places
            "significant_figures": 6,
        },
        "units": {
            "energy": "eV",
            "length": "angstrom",
            "force": "eV/angstrom",
            "pressure": "GPa",
        },
        "logging": {
            "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": None,  # None = no file logging
        },
        "performance": {
            "cache_enabled": True,
            "cache_size_mb": 100,
            "num_threads": None,  # None = auto-detect
        },
        "visualization": {
            "backend": "matplotlib",
            "style": "default",
            "figure_size": [10, 8],
        },
        "storage": {
            "default_path": "~/.matsimpy/storage/data.json",
            "default_store_type": "json",  # 'json' or 'memory'
            "auto_save": True,
        },
    }


__all__ = ["get_default_config"]
