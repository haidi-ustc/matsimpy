Core Structures
===============

MatSimPy provides several core data structures for representing materials:

* :class:`~matsimpy.core.crystal.Crystal` - Crystal structures with periodic boundary conditions
* :class:`~matsimpy.core.molecule.Molecule` - Molecular structures
* :class:`~matsimpy.core.lattice.Lattice` - Lattice vectors and cell parameters
* :class:`~matsimpy.core.composition.Composition` - Chemical composition
* :class:`~matsimpy.core.site.Site` - Atomic sites
* :class:`~matsimpy.core.periodic_table.Element` - Chemical elements

For complete API documentation, see :doc:`../api_reference/core`.

Usage Examples
--------------

Creating Crystals
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy import Crystal, Lattice

   # Create a simple crystal
   crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice(5.64))
   print(crystal.formula)   # ClNa
   print(crystal.volume)     # 179.4 Å³

   # Add multiple atoms at once
   crystal.add_atom(['H', 'O'], [[0.1, 0, 0], [0.9, 0, 0]])

Creating Molecules
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy import Molecule

   # Create a water molecule
   molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
   print(molecule.formula)  # H2O
   print(molecule.get_center_of_mass())

Working with Lattices
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy import Lattice

   # Convenient constructors
   lattice = Lattice(5.43)          # Cubic lattice
   lattice = Lattice([3, 4, 5])     # Orthorhombic lattice
   lattice = Lattice.cubic(5.0)     # Traditional (still works)

Working with Composition
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from matsimpy import Composition

   comp = Composition('Fe2O3')
   print(comp['Fe'])     # 2
   print(comp['O'])      # 3
   print(comp.mass)       # Fast! (cached)

