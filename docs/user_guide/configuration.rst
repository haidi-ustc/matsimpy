Configuration System
====================

MatSimPy provides a global configuration system for managing default settings.

Config Manager
--------------

.. automodule:: matsimpy.config
   :members:
   :undoc-members:

Usage Examples
--------------

.. code-block:: python

   from matsimpy.config import get_config, ConfigManager

   # Get configuration values
   device = get_config('calculator.ml.default_device')  # 'cpu'
   model_dir = get_config('paths.models')  # '~/.matsimpy/models'

   # Modify configuration
   config = ConfigManager()
   config.set('calculator.ml.default_device', 'cuda', save=True)

