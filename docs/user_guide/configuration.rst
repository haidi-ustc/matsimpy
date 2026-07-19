Configuration System
====================

MatSimPy provides a global configuration system for managing default settings.

For complete API documentation, see :doc:`../api_reference/config`.

Usage Examples
--------------

.. code-block:: python

   from matsimpy.config import get_config, ConfigManager

   # Get configuration values
   device = get_config('calculator.mattersim.default_device')  # 'cpu'
   model_dir = get_config('paths.models')  # '~/.matsimpy/models'

   # Modify configuration
   config = ConfigManager()
   config.set('calculator.mattersim.default_device', 'cuda', save=True)

