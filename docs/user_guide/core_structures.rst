Core Structures
===============

MatSimPy provides several core data structures for representing materials:

* :class:`~matsimpy.core.crystal.Crystal` - Crystal structures with periodic boundary conditions
* :class:`~matsimpy.core.molecule.Molecule` - Molecular structures
* :class:`~matsimpy.core.lattice.Lattice` - Lattice vectors and cell parameters
* :class:`~matsimpy.core.composition.Composition` - Chemical composition
* :class:`~matsimpy.core.site.Site` - Atomic sites
* :class:`~matsimpy.core.periodic_table.Element` - Chemical elements

Crystal
-------

.. autoclass:: matsimpy.core.crystal.Crystal
   :members:
   :special-members: __init__
   :exclude-members: calc
   :no-index:

Molecule
--------

.. autoclass:: matsimpy.core.molecule.Molecule
   :members:
   :special-members: __init__
   :exclude-members: calc
   :no-index:

Lattice
-------

.. autoclass:: matsimpy.core.lattice.Lattice
   :members:
   :special-members: __init__

Composition
-----------

.. autoclass:: matsimpy.core.composition.Composition
   :members:
   :special-members: __init__

Element
-------

.. autoclass:: matsimpy.core.periodic_table.Element
   :members:
   :special-members: __init__

