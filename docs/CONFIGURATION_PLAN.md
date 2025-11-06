# Global Configuration System Plan

## Overview

Add a global configuration system for MatSimPy to allow users to customize default settings, paths, and preferences without modifying code.

## Use Cases

1. **Calculator Defaults**: Default parameters for calculators (cutoff, convergence, etc.)
2. **Path Configuration**: Default paths for models, DFT codes, output directories
3. **DFT Code Settings**: Default commands, parallelization, memory settings
4. **ML Model Paths**: Default locations for ML models
5. **Units and Formatting**: Default units, decimal precision
6. **Logging**: Log level, output format
7. **Cache Settings**: Cache directory, cache size limits
8. **API Keys**: Keys for external services (if needed in future)

## Proposed Structure

### Config File Location
- **Primary**: `~/.matsimpy/config.yaml`
- **Fallback**: System-wide config (optional)
- **Override**: Environment variables

### Config File Format (YAML)

```yaml
# MatSimPy Configuration File
# Location: ~/.matsimpy/config.yaml

# Calculator defaults
calculator:
  classical:
    lennard_jones:
      default_cutoff: null  # Auto-calculate as 3*sigma
      default_rc_smooth: null
  
  ml:
    default_device: "cpu"
    default_model_dir: "~/.matsimpy/models"
    mattersim:
      default_model_type: "mace"
  
  dft:
    default_directory: "./calc"
    default_restart: true
    vasp:
      default_command: "vasp"
      default_npar: 1
      default_ncore: 1
    quantum_espresso:
      default_command: "pw.x"
      default_mpirun: "mpirun -np"

# Paths
paths:
  models: "~/.matsimpy/models"
  cache: "~/.matsimpy/cache"
  output: "./output"
  dft_workdir: "./calc"

# I/O settings
io:
  default_format: "vasp"  # For crystals
  precision: 8  # Decimal places
  significant_figures: 6

# Units
units:
  energy: "eV"
  length: "angstrom"
  force: "eV/angstrom"
  pressure: "GPa"

# Logging
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null  # null = no file logging

# Performance
performance:
  cache_enabled: true
  cache_size_mb: 100
  num_threads: null  # null = auto-detect

# Visualization (future)
visualization:
  backend: "matplotlib"
  style: "default"
  figure_size: [10, 8]
```

## Implementation Design

### ConfigManager Class

```python
class ConfigManager:
    """Manages global configuration for MatSimPy."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".matsimpy"
        self.config_file = self.config_dir / "config.yaml"
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file or create default."""
        if self.config_file.exists():
            self._config = yaml.safe_load(self.config_file.read_text())
        else:
            self._config = self._get_default_config()
            self._save_config()  # Create default config
    
    def get(self, key_path, default=None):
        """Get config value using dot-notation (e.g., 'calculator.ml.default_device')."""
        # Navigate nested dict
        
    def set(self, key_path, value):
        """Set config value."""
        
    def save(self):
        """Save current config to file."""
    
    def reset(self):
        """Reset to default configuration."""
```

### Usage Examples

```python
from matsimpy.config import get_config

# Get config value
device = get_config('calculator.ml.default_device')  # 'cpu'
model_dir = get_config('paths.models')  # '~/.matsimpy/models'

# Use in calculators
from matsimpy.calculator.ml import Mattersim
calc = Mattersim(model_path='model.pth')  # Uses default device from config

# Override with environment variable
# MATSIMPY_CALCULATOR__ML__DEFAULT_DEVICE=cuda python script.py
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. Create `matsimpy/config/` module
2. Implement `ConfigManager` class
3. Create default config template
4. Add config file creation on first use
5. Add environment variable support

### Phase 2: Integration
1. Integrate with calculators (use config defaults)
2. Add config support to I/O modules
3. Add logging configuration
4. Add cache directory configuration

### Phase 3: Utilities
1. Add `matsimpy.config` CLI command (optional)
2. Add config validation
3. Add config migration for version updates

## File Structure

```
matsimpy/config/
├── __init__.py           # Main exports (ConfigManager, get_config)
├── manager.py            # ConfigManager class
├── defaults.py            # Default configuration
├── validator.py           # Config validation
└── utils.py               # Helper functions
```

## Environment Variable Support

Environment variables can override config values:
- Format: `MATSIMPY_<SECTION>__<SUBSECTION>__<KEY>`
- Example: `MATSIMPY_CALCULATOR__ML__DEFAULT_DEVICE=cuda`

## Benefits

1. **User Customization**: Users can set preferences without code changes
2. **Consistent Defaults**: Same defaults across all scripts
3. **Path Management**: Centralized path configuration
4. **Team Settings**: Shared config for team workflows
5. **Version Control**: Config can be version-controlled (optional)
6. **Development**: Easy to test with different configs

## Questions

1. Should config be optional or required? (Proposed: Optional with defaults)
2. Should we support multiple config files? (Proposed: User + system)
3. Should config be version-controlled in project? (Proposed: No, user-specific)
4. Should we add a CLI tool for config management? (Proposed: Optional, Phase 3)

## Timeline

- **Phase 1** (Core): 2-3 hours
- **Phase 2** (Integration): 2-3 hours
- **Phase 3** (Utilities): 1-2 hours

**Total**: ~5-8 hours

