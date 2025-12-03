Symmetry Analysis
=================

MatSimPy provides symmetry analysis capabilities for crystal structures.

For complete API documentation, see :doc:`../api_reference/symmetry`.

Usage Examples
--------------

.. code-block:: python

   from matsimpy.builders.bulk import from_prototype
   from matsimpy.symmetry import get_conventional_cell

   # Create crystal structure
   crystal = from_prototype('diamond', 'Si', 5.43)

   # Get symmetry information
   sym_info = crystal.get_symmetry_info()
   print(f"Space group: {sym_info['space_group_symbol']}")  # Fd-3m
   print(f"Point group: {sym_info['point_group']}")        # m-3m
   print(f"Crystal system: {sym_info['crystal_system']}")  # Cubic

   # Get conventional cell
   conventional = crystal.get_conventional_cell()
   print(f"Primitive: {len(crystal)} atoms")         # 2 atoms
   print(f"Conventional: {len(conventional)} atoms") # 8 atoms

