File I/O
========

MatSimPy supports reading and writing structures in various formats.

For complete API documentation, see :doc:`../api_reference/io`.

Supported Formats
-----------------

MatSimPy supports multiple file formats:
* VASP (POSCAR, CONTCAR)
* CIF (Crystallographic Information File)
* XYZ (atomic coordinates)
* PDB (Protein Data Bank)
* MOL (molecular structure)
* XSF (XCrySDen Structure File)
* ASE (Atomic Simulation Environment)
* JSON (structured data)

Usage Examples
---------------

High-Level Interface
~~~~~~~~~~~~~~~~~~~~

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

