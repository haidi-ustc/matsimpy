"""
Utility functions for configuration management.
"""

import os
from typing import Any, Dict

from ..utils.path_utils import expand_path
from ..utils.dict_utils import get_nested_value, set_nested_value

# Re-export for backward compatibility
__all__ = [
    "expand_path",
    "get_nested_value",
    "set_nested_value",
    "merge_configs",
    "load_env_overrides",
]


def merge_configs(
    user_config: Dict[str, Any], default_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge user configuration with default configuration.

    User config values override defaults, but nested dicts are merged recursively.

    Args:
        user_config: User configuration (may be partial)
        default_config: Default configuration (complete)

    Returns:
        dict: Merged configuration
    """
    result = default_config.copy()
    for key, value in user_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(value, result[key])
        else:
            result[key] = value
    return result


def load_env_overrides(prefix: str = "MATSIMPY") -> Dict[str, Any]:
    """Load configuration overrides from environment variables.

    Environment variables should be in format:
    MATSIMPY_<SECTION>__<SUBSECTION>__<KEY>=value

    Double underscores (__) are converted to dots (.) in the key path.

    Args:
        prefix: Environment variable prefix (default: 'MATSIMPY')

    Returns:
        dict: Configuration overrides
    """
    overrides = {}
    prefix_with_underscore = f"{prefix}_"

    for env_key, env_value in os.environ.items():
        if env_key.startswith(prefix_with_underscore):
            key_path = env_key[len(prefix_with_underscore):].replace("__", ".")
            key_path = key_path.lower()
            value = _parse_env_value(env_value)
            set_nested_value(overrides, key_path, value)
    return overrides


def _parse_env_value(value: str) -> Any:
    """Parse environment variable value to appropriate Python type."""
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    if value.lower() in ("none", "null"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
