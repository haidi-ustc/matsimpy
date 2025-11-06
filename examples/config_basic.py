"""
MatSimPy Configuration System - Basic Examples

Demonstrates usage of the global configuration system.
"""

from matsimpy.config import get_config, ConfigManager
from matsimpy import Crystal, Lattice
from matsimpy.calculator.ml import Mattersim

print("=" * 70)
print("MatSimPy Configuration System - Basic Examples")
print("=" * 70)

# ======================================================================
# 1. Getting Configuration Values
# ======================================================================
print("\n1. Getting Configuration Values")
print("-" * 70)

# Get default values
device = get_config('calculator.ml.default_device')
model_dir = get_config('paths.models')
log_level = get_config('logging.level')
precision = get_config('io.precision')

print(f"ML default device: {device}")
print(f"Models directory: {model_dir}")
print(f"Log level: {log_level}")
print(f"IO precision: {precision}")

# Get nested values
model_type = get_config('calculator.ml.mattersim.default_model_type')
print(f"Mattersim default model type: {model_type}")

# ======================================================================
# 2. Using Config in Calculators
# ======================================================================
print("\n2. Using Config Defaults in Calculators")
print("-" * 70)

# ML calculator uses config default device
try:
    mock_model = object()
    ml_calc = Mattersim(model=mock_model, model_type='custom')
    print(f"Mattersim calculator device (from config): {ml_calc.device}")
except Exception as e:
    print(f"ML calculator example: {type(e).__name__}")

# ======================================================================
# 3. Modifying Configuration
# ======================================================================
print("\n3. Modifying Configuration")
print("-" * 70)

config = ConfigManager()

# Get current value
current_device = config.get('calculator.ml.default_device')
print(f"Current ML device: {current_device}")

# Set new value (without saving)
config.set('calculator.ml.default_device', 'test_device')
new_device = config.get('calculator.ml.default_device')
print(f"Set to: {new_device}")

# Reload to get original value
config.reload()
reloaded_device = config.get('calculator.ml.default_device')
print(f"After reload: {reloaded_device}")

# Set and save
config.set('calculator.ml.default_device', 'cuda', save=True)
saved_device = config.get('calculator.ml.default_device')
print(f"Saved value: {saved_device}")

# Reset to defaults
config.reset()
reset_device = config.get('calculator.ml.default_device')
print(f"After reset: {reset_device}")

# ======================================================================
# 4. Configuration File Location
# ======================================================================
print("\n4. Configuration File Information")
print("-" * 70)

config_file = config.get_config_file()
config_dir = config.get_config_dir()

print(f"Config directory: {config_dir}")
print(f"Config file: {config_file}")
print(f"Config file exists: {config_file.exists()}")

# ======================================================================
# 5. All Configuration Sections
# ======================================================================
print("\n5. Configuration Sections Overview")
print("-" * 70)

sections = {
    'Calculator defaults': [
        'calculator.ml.default_device',
        'calculator.ml.mattersim.default_model_type',
        'calculator.dft.default_directory',
    ],
    'Paths': [
        'paths.models',
        'paths.cache',
        'paths.output',
    ],
    'I/O settings': [
        'io.default_format',
        'io.precision',
    ],
    'Units': [
        'units.energy',
        'units.length',
    ],
    'Logging': [
        'logging.level',
    ],
    'Performance': [
        'performance.cache_enabled',
        'performance.cache_size_mb',
    ],
    'Storage': [
        'storage.default_path',
        'storage.default_store_type',
    ],
}

for section, keys in sections.items():
    print(f"\n{section}:")
    for key in keys:
        value = get_config(key)
        print(f"  {key}: {value}")

print("\n" + "=" * 70)
print("Configuration examples completed!")
print("=" * 70)

