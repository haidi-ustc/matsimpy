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
    get_config_manager,
    get_default_config,
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
    
    def test_init_creates_config_file(self):
        """Test that initialization creates config file."""
        config = ConfigManager(config_dir=self.config_dir)
        self.assertTrue(self.config_file.exists())
    
    def test_get_default_value(self):
        """Test getting default configuration value."""
        config = ConfigManager(config_dir=self.config_dir)
        device = config.get('calculator.ml.default_device')
        self.assertEqual(device, 'cpu')
    
    def test_get_nested_value(self):
        """Test getting nested configuration value."""
        config = ConfigManager(config_dir=self.config_dir)
        model_type = config.get('calculator.ml.mattersim.default_model_type')
        self.assertEqual(model_type, 'mace')
    
    def test_get_with_default(self):
        """Test getting value with custom default."""
        config = ConfigManager(config_dir=self.config_dir)
        value = config.get('nonexistent.key', default='custom_default')
        self.assertEqual(value, 'custom_default')
    
    def test_set_and_get(self):
        """Test setting and getting configuration value."""
        config = ConfigManager(config_dir=self.config_dir)
        config.set('calculator.ml.default_device', 'cuda')
        device = config.get('calculator.ml.default_device')
        self.assertEqual(device, 'cuda')
    
    def test_set_and_save(self):
        """Test setting and saving configuration."""
        config = ConfigManager(config_dir=self.config_dir)
        config.set('calculator.ml.default_device', 'cuda', save=True)
        
        # Reload and verify
        config2 = ConfigManager(config_dir=self.config_dir, auto_create=False)
        device = config2.get('calculator.ml.default_device')
        self.assertEqual(device, 'cuda')
    
    def test_user_config_override_defaults(self):
        """Test that user config overrides defaults."""
        # Create user config file
        self.config_dir.mkdir(parents=True, exist_ok=True)
        user_config = {
            'calculator': {
                'ml': {
                    'default_device': 'cuda'
                }
            }
        }
        with open(self.config_file, 'w') as f:
            yaml.dump(user_config, f)
        
        config = ConfigManager(config_dir=self.config_dir, auto_create=False)
        device = config.get('calculator.ml.default_device')
        self.assertEqual(device, 'cuda')
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        config = ConfigManager(config_dir=self.config_dir)
        config.set('calculator.ml.default_device', 'cuda', save=True)
        config.reset()
        
        device = config.get('calculator.ml.default_device')
        self.assertEqual(device, 'cpu')  # Back to default
    
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
        device = get_config('calculator.ml.default_device')
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
    
    def test_env_override(self):
        """Test that environment variables override config."""
        # Set environment variable
        os.environ['MATSIMPY_CALCULATOR__ML__DEFAULT_DEVICE'] = 'cuda'
        
        # Create new config manager to pick up env var
        config = ConfigManager(config_dir=self.config_dir, auto_create=False)
        device = config.get('calculator.ml.default_device')
        self.assertEqual(device, 'cuda')
        
        # Clean up
        del os.environ['MATSIMPY_CALCULATOR__ML__DEFAULT_DEVICE']
    
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

class TestDefaultConfig(unittest.TestCase):
    """Tests for default configuration."""
    
    def test_default_config_structure(self):
        """Test that default config has expected structure."""
        defaults = get_default_config()
        
        # Check top-level keys
        self.assertIn('calculator', defaults)
        self.assertIn('paths', defaults)
        self.assertIn('io', defaults)
        self.assertIn('units', defaults)
        self.assertIn('logging', defaults)
        self.assertIn('performance', defaults)
    
    def test_default_calculator_settings(self):
        """Test default calculator settings."""
        defaults = get_default_config()
        
        self.assertEqual(defaults['calculator']['ml']['default_device'], 'cpu')
        self.assertEqual(
            defaults['calculator']['ml']['mattersim']['default_model_type'],
            'mace'
        )

if __name__ == '__main__':
    unittest.main()

