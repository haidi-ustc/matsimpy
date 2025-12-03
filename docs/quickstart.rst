Quick Start
===========

This guide will help you get started with MatSimPy quickly.

Core Structures
---------------

.. code-block:: python

   from matsimpy import Crystal, Molecule, Lattice, Composition
   from matsimpy.builders.bulk import from_prototype

   # Convenient Lattice constructors
   lattice = Lattice(5.43)          # Cubic lattice
   lattice = Lattice([3, 4, 5])     # Orthorhombic lattice
   lattice = Lattice.cubic(5.0)     # Traditional (still works)

   # Create crystal structure
   crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice(5.64))
   print(crystal.formula)   # ClNa
   print(crystal.volume)    # 179.4 Å³

   # Add multiple atoms at once
   crystal.add_atom(['H', 'O'], [[0.1, 0, 0], [0.9, 0, 0]])

   # Create a molecule
   molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
   print(molecule.formula)  # H2O
   print(molecule.get_center_of_mass())

   # Work with composition
   comp = Composition('Fe2O3')
   print(comp['Fe'])     # 2
   print(comp['O'])      # 3
   print(comp.mass)      # Fast! (cached)

Structure Builders
------------------

.. code-block:: python

   from matsimpy.builders import (
       from_prototype, generate_slab, create_interstitial,
       build_tetrahedral, create_vacancy
   )

   # Build bulk structures from prototypes
   fcc_cu = from_prototype('fcc', 'Cu', 3.61)
   bcc_fe = from_prototype('bcc', 'Fe', 2.87)
   diamond_c = from_prototype('diamond', 'C', 3.57)

   # Create surface slabs
   slab = generate_slab(fcc_cu, (1, 1, 1), min_slab_size=10.0, min_vacuum_size=15.0)

   # Build molecules
   ch4 = build_tetrahedral('C', ['H', 'H', 'H', 'H'], 1.09)

   # Create defects
   with_vacancy = create_vacancy(fcc_cu, 0)
   with_interstitial = create_interstitial(fcc_cu, 'H', positions=[0.5, 0.5, 0.5])

Transformations
---------------

.. code-block:: python

   from matsimpy.transformation import (
       translate, rotate, apply_strain, scale_lattice,
       substitute, make_supercell
   )

   # Geometric transformations
   translated = translate(crystal, [1, 1, 1])
   rotated = rotate(translated, 90.0, [0, 0, 1])

   # Lattice transformations
   strained = apply_strain(crystal, [0.05, 0, 0])  # Uniaxial strain
   scaled = scale_lattice(crystal, 1.1)            # Scale by 10%

   # Chemical transformations
   substituted = substitute(crystal, [0, 1], ['Ge', 'Ge'])

   # Structural transformations
   supercell = make_supercell(crystal, [2, 2, 2])  # 2x2x2 supercell

File I/O
--------

.. code-block:: python

   from matsimpy.io import read, write

   # Auto-detect format from file extension
   write(crystal, 'structure.vasp')
   write(molecule, 'molecule.xyz')

   # Read structures (format auto-detected)
   crystal = read('structure.vasp')
   molecule = read('molecule.xyz')

   # Or use class methods
   crystal = Crystal.from_file('structure.vasp')
   crystal.to_file('output.cif', title='My Crystal')

Calculators
-----------

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

For more examples, see the :doc:`examples` page or check the ``examples/`` directory in the repository.

