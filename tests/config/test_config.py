"""
Tests for configuration system.
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
from matsimpy.config import (
    ConfigManager,
    get_config,
)

class TestConfigManager(unittest.TestCase):
    """Tests for ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary config directory
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / '.matsimpy'
        self.config_file = self.config_dir / 'config.yaml'
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    
    
    
    
    def test_set_and_get(self):
        """Test setting and getting configuration value."""
        config = ConfigManager(config_dir=self.config_dir)
        config.set('calculator.mattersim.default_device', 'cuda')
        device = config.get('calculator.mattersim.default_device')
        self.assertEqual(device, 'cuda')
    
    
    
    
    def test_path_expansion(self):
        """Test that paths are expanded correctly."""
        config = ConfigManager(config_dir=self.config_dir)
        model_path = config.get('paths.models')
        # Should expand ~ to home directory
        self.assertIsInstance(model_path, str)
        self.assertNotIn('~', model_path)
    
    def test_get_config_file(self):
        """Test getting config file path."""
        config = ConfigManager(config_dir=self.config_dir)
        config_file = config.get_config_file()
        self.assertEqual(config_file, self.config_file)
    
    def test_get_config_dir(self):
        """Test getting config directory path."""
        config = ConfigManager(config_dir=self.config_dir)
        config_dir = config.get_config_dir()
        self.assertEqual(config_dir, self.config_dir)

class TestGetConfig(unittest.TestCase):
    """Tests for get_config convenience function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / '.matsimpy'
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_get_config_function(self):
        """Test get_config convenience function."""
        # This will use the global config, so we test with defaults
        device = get_config('calculator.mattersim.default_device')
        self.assertEqual(device, 'cpu')
    
    def test_get_config_with_default(self):
        """Test get_config with custom default."""
        value = get_config('nonexistent.key', default='test_default')
        self.assertEqual(value, 'test_default')

class TestEnvOverrides(unittest.TestCase):
    """Tests for environment variable overrides."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / '.matsimpy'
        self.old_env = os.environ.copy()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        os.environ.clear()
        os.environ.update(self.old_env)
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    
    def test_env_override_bool(self):
        """Test environment variable override with boolean."""
        os.environ['MATSIMPY_CALCULATOR__DFT__DEFAULT_RESTART'] = 'false'
        
        # Create new config manager to pick up env var
        config = ConfigManager(config_dir=self.config_dir, auto_create=False)
        restart = config.get('calculator.dft.default_restart')
        self.assertFalse(restart)
        
        # Clean up
        del os.environ['MATSIMPY_CALCULATOR__DFT__DEFAULT_RESTART']
    
    def test_env_override_int(self):
        """Test environment variable override with integer."""
        os.environ['MATSIMPY_PERFORMANCE__CACHE_SIZE_MB'] = '200'
        
        # Create new config manager to pick up env var
        config = ConfigManager(config_dir=self.config_dir, auto_create=False)
        cache_size = config.get('performance.cache_size_mb')
        self.assertEqual(cache_size, 200)
        
        # Clean up
        del os.environ['MATSIMPY_PERFORMANCE__CACHE_SIZE_MB']


if __name__ == '__main__':
    unittest.main()


class TestEnvOverridesAreNotPersisted(unittest.TestCase):
    """0.8.2 regression: MATSIMPY_* env values must never be written to config.yaml."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / '.matsimpy'
        self.key = 'MATSIMPY_CALCULATOR__MATTERSIM__DEFAULT_DEVICE'

    def tearDown(self):
        import shutil
        os.environ.pop(self.key, None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _file_device(self):
        with open(self.config_dir / 'config.yaml') as f:
            return yaml.safe_load(f)['calculator']['mattersim']['default_device']

    def test_auto_create_save_and_reset_do_not_persist_env(self):
        os.environ[self.key] = 'cuda'
        config = ConfigManager(config_dir=self.config_dir)  # auto-create
        self.assertEqual(config.get('calculator.mattersim.default_device'), 'cuda')
        self.assertEqual(self._file_device(), 'cpu')
        config.set('performance.cache_size_mb', 7, save=True)
        self.assertEqual(self._file_device(), 'cpu')
        del os.environ[self.key]
        self.assertEqual(ConfigManager(config_dir=self.config_dir).get('performance.cache_size_mb'), 7)
        os.environ[self.key] = 'cuda'
        config.reset()
        self.assertEqual(self._file_device(), 'cpu')
        # env still wins in memory after reset
        self.assertEqual(config.get('calculator.mattersim.default_device'), 'cuda')
        del os.environ[self.key]
        fresh = ConfigManager(config_dir=self.config_dir, auto_create=False)
        self.assertEqual(fresh.get('calculator.mattersim.default_device'), 'cpu')


class TestSuiteIsolation(unittest.TestCase):
    def test_home_is_redirected_for_tests(self):
        self.assertIn('matsimpy-test-home-', os.path.expanduser('~'))
