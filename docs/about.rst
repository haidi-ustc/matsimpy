About MatSimPy
==============

MatSimPy (Materials Simulation in Python) is a comprehensive Python package for molecular and materials simulation, designed to provide a modern, efficient, and user-friendly interface for materials science research.

Project Information
--------------------

**Version**: 0.3.0

**Status**: Beta (core modules stable)

**License**: MIT License

**Author**: haidi wang

**Email**: haidi@hfut.edu.cn

**Repository**: https://gitee.com/haidi-hfut/MatSimPy

**Homepage**: https://gitee.com/haidi-hfut/MatSimPy

Features
--------

MatSimPy provides a wide range of features for materials simulation:

* **Core Data Structures**: Crystal, Molecule, Lattice, Composition, Site, Element
* **Structure Builders**: Bulk, surface, alloy, molecule, defects, nanostructures
* **Transformations**: Geometric, lattice, atomic, chemical operations
* **High-Throughput Tools**: Transformation pipelines, parameter sweeps, batch processing
* **Graph Analysis**: 13+ graph methods, OOP API, connectivity analysis, NetworkX integration
* **Calculators**: Classical potentials (LJ), ML potentials (Mattersim), DFT interfaces
* **Symmetry Analysis**: Space group determination, conventional cell conversion
* **Configuration System**: Global config with environment variable overrides
* **Data Storage**: Persistent storage for structures and calculation results (maggma)
* **File I/O**: High-level `read()`/`write()` interface with auto-format detection
* **LaTeX Export**: Professional tables for publications with mhchem support
* **CLI Interface**: Interactive menu system for easy access to all features

Python Version Support
-----------------------

MatSimPy supports Python 3.9 through 3.12. The package is tested on:

* Python 3.9 ✓
* Python 3.10 ✓
* Python 3.11 ✓
* Python 3.12 ✓

Dependencies
-------------

Core Dependencies
~~~~~~~~~~~~~~~~~

* **NumPy** >=1.20.0 - Numerical computing
* **SciPy** >=1.7.0 - Scientific computing
* **monty** >=2021.0 - MSONable serialization
* **tabulate** >=0.9.0 - Formatted output

Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~

MatSimPy supports optional features through extra dependencies:

* **CLI Interface**: ``prompt-toolkit``
* **Machine Learning**: ``torch`` >=2.0.0, ``torch-geometric`` >=2.0.0
* **I/O Converters**: ``pymatgen`` >=2024.0.0, ``ase`` >=3.20.0
* **Structure Builders**: ``pyxtal`` >=1.0.0, ``rdkit``
* **Analysis**: ``spglib``
* **Storage**: ``maggma`` >=0.70.0

Installation
------------

Install MatSimPy using pip:

.. code-block:: bash

   pip install MatSimPy

For development installation:

.. code-block:: bash

   git clone https://gitee.com/haidi-hfut/MatSimPy.git
   cd MatSimPy
   pip install -e .

For installation with optional dependencies, see :doc:`installation`.

Acknowledgments
---------------

MatSimPy is inspired by:

* `pymatgen <https://github.com/materialsproject/pymatgen>`_ - Materials Project's Python Materials Genomics library
* `ASE <https://wiki.fysik.dtu.dk/ase/>`_ - Atomic Simulation Environment

MatSimPy aims to provide a modern, efficient alternative for materials simulation with comprehensive structure building capabilities.

Contributing
------------

Contributions are welcome! Please see :doc:`contributing` for guidelines on how to contribute to MatSimPy.

License
-------

This project is licensed under the MIT License. See the LICENSE file for details.

History
-------

MatSimPy is currently in Alpha development. The API may change in future versions.

For detailed changelog, see :doc:`changelog`.

