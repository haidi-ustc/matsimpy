"""
Configuration manager for MatSimPy.

Handles loading, saving, and accessing global configuration.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from .defaults import get_default_config
from .utils import (
    expand_path,
    get_nested_value,
    set_nested_value,
    merge_configs,
    load_env_overrides,
)


class ConfigManager:
    """
    Manages global configuration for MatSimPy.

    Configuration is loaded from:
    1. Default configuration (built-in)
    2. User config file (~/.matsimpy/config.yaml)
    3. Environment variables (MATSIMPY_*)

    Priority: Environment variables > User config > Defaults

    Example:
        >>> from matsimpy.config import ConfigManager
        >>> config = ConfigManager()
        >>> device = config.get('calculator.ml.default_device')
        >>> config.set('calculator.ml.default_device', 'cuda')
        >>> config.save()
    """

    def __init__(self, config_dir: Optional[Path] = None, auto_create: bool = True):
        """
        Initialize configuration manager.

        Args:
            config_dir: Custom configuration directory (default: ~/.matsimpy)
            auto_create: If True, create config file if it doesn't exist
        """
        if config_dir is None:
            config_dir = expand_path("~/.matsimpy")

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.yaml"
        self._config: Optional[Dict[str, Any]] = None

        # Load configuration
        self._load_config(auto_create=auto_create)

    def _load_config(self, auto_create: bool = True) -> None:
        """
        Load configuration from file or create default.

        Args:
            auto_create: If True, create config file if it doesn't exist
        """
        # Start with defaults
        default_config = get_default_config()

        # Load user config if exists
        user_config = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    user_config = yaml.safe_load(f) or {}
            except Exception as e:
                # If loading fails, warn but continue with defaults
                import warnings

                warnings.warn(
                    f"Failed to load config file {self.config_file}: {e}. "
                    "Using defaults."
                )

        # Merge user config with defaults
        merged_config = merge_configs(user_config, default_config)

        # Load environment variable overrides
        env_overrides = load_env_overrides()

        # Merge environment overrides (highest priority)
        self._config = merge_configs(env_overrides, merged_config)

        # Save merged config if file doesn't exist and auto_create is True
        if auto_create and not self.config_file.exists():
            self._save_config()

    def _save_config(self) -> None:
        """Save current configuration to file."""
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Save to file
        try:
            with open(self.config_file, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            import warnings

            warnings.warn(f"Failed to save config file {self.config_file}: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot-notation.

        Args:
            key_path: Dot-separated path (e.g., 'calculator.ml.default_device')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> config.get('calculator.ml.default_device')
            'cpu'
            >>> config.get('paths.models')
            '~/.matsimpy/models'
        """
        if self._config is None:
            return default

        value = get_nested_value(self._config, key_path, default=None)
        if value is None:
            return default

        # Expand paths for path-related keys
        if "path" in key_path.lower() or key_path.startswith("paths."):
            if isinstance(value, str):
                return str(expand_path(value))

        return value

    def set(self, key_path: str, value: Any, save: bool = False) -> None:
        """
        Set configuration value.

        Args:
            key_path: Dot-separated path
            value: Value to set
            save: If True, save to file immediately

        Examples:
            >>> config.set('calculator.ml.default_device', 'cuda')
            >>> config.set('paths.models', '~/my_models', save=True)
        """
        if self._config is None:
            self._config = get_default_config()

        set_nested_value(self._config, key_path, value)

        if save:
            self.save()

    def save(self) -> None:
        """Save current configuration to file."""
        self._save_config()

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = get_default_config()
        self._save_config()

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config(auto_create=False)

    def get_config_file(self) -> Path:
        """Get path to configuration file."""
        return self.config_file

    def get_config_dir(self) -> Path:
        """Get path to configuration directory."""
        return self.config_dir


# Global instance
_global_config: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get global configuration manager instance.

    Returns:
        ConfigManager: Global configuration manager
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config


def get_config(key_path: str, default: Any = None) -> Any:
    """
    Get configuration value from global config.

    Convenience function for accessing global configuration.

    Args:
        key_path: Dot-separated path (e.g., 'calculator.ml.default_device')
        default: Default value if key not found

    Returns:
        Configuration value or default

    Examples:
        >>> from matsimpy.config import get_config
        >>> device = get_config('calculator.ml.default_device')
        >>> model_dir = get_config('paths.models')
    """
    return get_config_manager().get(key_path, default)


__all__ = ["ConfigManager", "get_config_manager", "get_config"]
