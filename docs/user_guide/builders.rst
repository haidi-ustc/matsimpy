Structure Builders
==================

MatSimPy provides comprehensive builders for creating various types of structures.

For complete API documentation, see :doc:`../api_reference/builders`.

Usage Examples
--------------

Bulk Structures
~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.builders.bulk import from_prototype

   # Build bulk structures from prototypes
   fcc_cu = from_prototype('fcc', 'Cu', 3.61)
   bcc_fe = from_prototype('bcc', 'Fe', 2.87)
   diamond_c = from_prototype('diamond', 'C', 3.57)

Surface Structures
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.builders.surface import generate_slab

   # Create surface slabs
   slab = generate_slab(fcc_cu, (1, 1, 1), min_slab_size=10.0, min_vacuum_size=15.0)

Molecule Builders
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.builders.molecule import build_tetrahedral

   # Build molecules
   ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)

Defect Creation
~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.builders.defects import create_vacancy, create_interstitial

   # Create defects
   with_vacancy = create_vacancy(fcc_cu, 0)
   with_interstitial = create_interstitial(fcc_cu, 'H', positions=[0.5, 0.5, 0.5])

