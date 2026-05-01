Changelog
=========

All notable changes to MatSimPy will be documented in this file.

Version 0.1.0 (Alpha)
---------------------

Initial release of MatSimPy.

Version 0.3.0 (Beta)
--------------------

Core modules stabilized.

Highlights
~~~~~~~~~~

* Stable core data model semantics (Cartesian ``Structure.positions``; Crystal supports both frac/cart access)
* Immutability and thread-safety improvements in caches and internal arrays
* Faster mutation paths via lightweight constructors and reduced recomputation

Features
~~~~~~~~

* Core data structures (Crystal, Molecule, Lattice, Composition, Site, Element)
* Structure builders (bulk, surface, alloy, molecule, defects, nanostructures)
* Transformations (geometric, lattice, atomic, chemical, structural)
* High-throughput transformation tools (Pipeline, ParameterSweep, BatchProcessor)
* Graph analysis with OOP API
* Calculators (Lennard-Jones, ML potentials)
* Symmetry analysis
* File I/O for multiple formats (VASP, CIF, XYZ, PDB, MOL, XSF, JSON, ASE)
* Configuration system
* Data storage with maggma
* CLI interface
* LaTeX export for publications

