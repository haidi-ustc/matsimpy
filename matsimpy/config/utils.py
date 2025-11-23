"""
Utility functions for configuration management.
"""

import os
from typing import Any, Dict, Optional
from pathlib import Path


def expand_path(path: str) -> Path:
    """
    Expand user home directory and environment variables in path.

    Args:
        path: Path string that may contain ~ or $VAR

    Returns:
        Path: Expanded Path object
    """
    expanded = os.path.expanduser(path)
    expanded = os.path.expandvars(expanded)
    return Path(expanded)


def get_nested_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get value from nested dictionary using dot-notation.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated path (e.g., 'calculator.ml.default_device')
        default: Default value if key not found

    Returns:
        Value at key_path or default

    Examples:
        >>> config = {'a': {'b': {'c': 1}}}
        >>> get_nested_value(config, 'a.b.c')
        1
        >>> get_nested_value(config, 'a.b.d', default=0)
        0
    """
    keys = key_path.split(".")
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def set_nested_value(config: Dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set value in nested dictionary using dot-notation.

    Args:
        config: Configuration dictionary to modify
        key_path: Dot-separated path (e.g., 'calculator.ml.default_device')
        value: Value to set

    Examples:
        >>> config = {}
        >>> set_nested_value(config, 'a.b.c', 1)
        >>> config
        {'a': {'b': {'c': 1}}}
    """
    keys = key_path.split(".")
    current = config

    # Navigate/create nested structure
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the final value
    current[keys[-1]] = value


def merge_configs(
    user_config: Dict[str, Any], default_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge user configuration with default configuration.

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
            # Recursively merge nested dictionaries
            result[key] = merge_configs(value, result[key])
        else:
            # Overwrite with user value
            result[key] = value

    return result


def load_env_overrides(prefix: str = "MATSIMPY") -> Dict[str, Any]:
    """
    Load configuration overrides from environment variables.

    Environment variables should be in format:
    MATSIMPY_<SECTION>__<SUBSECTION>__<KEY>=value

    Double underscores (__) are converted to dots (.) in the key path.

    Args:
        prefix: Environment variable prefix (default: 'MATSIMPY')

    Returns:
        dict: Configuration overrides

    Examples:
        >>> # Set: MATSIMPY_CALCULATOR__ML__DEFAULT_DEVICE=cuda
        >>> overrides = load_env_overrides()
        >>> # Result: {'calculator': {'ml': {'default_device': 'cuda'}}}
    """
    overrides = {}
    prefix_with_underscore = f"{prefix}_"

    for env_key, env_value in os.environ.items():
        if env_key.startswith(prefix_with_underscore):
            # Remove prefix and convert __ to .
            key_path = env_key[len(prefix_with_underscore) :].replace("__", ".")
            # Convert to lowercase for consistency with config keys
            key_path = key_path.lower()

            # Try to convert value to appropriate type
            value = _parse_env_value(env_value)

            # Set in nested structure
            set_nested_value(overrides, key_path, value)

    return overrides


def _parse_env_value(value: str) -> Any:
    """
    Parse environment variable value to appropriate Python type.

    Args:
        value: String value from environment

    Returns:
        Parsed value (bool, int, float, None, or str)
    """
    # Try boolean
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False

    # Try None/null
    if value.lower() in ("none", "null"):
        return None

    # Try integer
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Return as string
    return value


__all__ = [
    "expand_path",
    "get_nested_value",
    "set_nested_value",
    "merge_configs",
    "load_env_overrides",
]
