Calculators
===========

MatSimPy provides calculators for computing energies, forces, and stress.

For complete API documentation, see :doc:`../api_reference/calculator`.

Usage Examples
-------------

Classical Potentials
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy import Crystal, Lattice
   from matsimpy.calculator import LennardJones

   # Classical potential calculator
   crystal = Crystal(['Ar'], [[0,0,0]], Lattice.cubic(5.0))
   calc = LennardJones(sigma=3.4, epsilon=0.0104)
   crystal.calc = calc

   # Get energy and forces
   energy = crystal.get_potential_energy()
   forces = crystal.get_forces()

Machine Learning Calculators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy.calculator import Mattersim

   # ML calculator (requires torch)
   calc = Mattersim(model_path='path/to/model.pth')
   crystal.calc = calc
   energy = crystal.get_potential_energy()

