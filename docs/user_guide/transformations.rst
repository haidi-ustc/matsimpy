Transformations
===============

MatSimPy provides various transformation operations for structures.

Overview
--------

MatSimPy supports several categories of transformations:

* **Geometric Transformations**: Translation, rotation, reflection
* **Lattice Transformations**: Strain, scaling, cell modifications
* **Atomic Operations**: Adding, removing, replacing atoms
* **Chemical Transformations**: Substitution, composition changes
* **Structural Transformations**: Supercell creation, defect insertion
* **High-Throughput Tools**: Pipelines, parameter sweeps, batch processing

For complete API documentation, see :doc:`../api_reference/transformation`.

Usage Examples
---------------

Geometric Transformations
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.transformation import translate, rotate
   from matsimpy.builders.bulk import from_prototype

   crystal = from_prototype('fcc', 'Cu', 3.61)
   translated = translate(crystal, [1, 1, 1])
   rotated = rotate(translated, 90.0, [0, 0, 1])

Lattice Transformations
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.transformation import apply_strain, scale_lattice

   strained = apply_strain(crystal, [0.05, 0, 0])  # Uniaxial strain
   scaled = scale_lattice(crystal, 1.1)            # Scale by 10%

Chemical Transformations
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.transformation import substitute

   substituted = substitute(crystal, [0, 1], ['Ge', 'Ge'])

High-Throughput Tools
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.transformation.composite import (
       TransformationPipeline, ParameterSweep, BatchProcessor
   )

   # Create a transformation pipeline
   pipeline = TransformationPipeline([
       lambda s: translate(s, [0.1, 0, 0]),
       lambda s: rotate(s, 45.0, [0, 0, 1]),
   ])
   result = pipeline.apply(crystal)

   # Parameter sweep
   sweep = ParameterSweep(
       lambda s, angle: rotate(s, angle, [0, 0, 1]),
       angles=range(0, 360, 10)
   )
   for transformed in sweep.generate(crystal):
       # Process each transformed structure
       pass

   # Batch processing
   processor = BatchProcessor(n_workers=4)
   results = processor.process([crystal1, crystal2, crystal3], pipeline)

