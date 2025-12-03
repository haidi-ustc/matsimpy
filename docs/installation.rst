Installation
============

Basic Installation
------------------

Install MatSimPy using pip:

.. code-block:: bash

   pip install MatSimPy

This installs the core package with required dependencies:
* numpy
* scipy
* monty
* tabulate

Installation from Source
-------------------------

Clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://gitee.com/haidi-hfut/MatSimPy.git
   cd MatSimPy
   pip install -e .

For development with testing support:

.. code-block:: bash

   pip install -e .[dev]

Optional Dependencies
---------------------

MatSimPy supports optional features through extra dependencies:

.. code-block:: bash

   # CLI interface (interactive menu)
   pip install -e .[cli]

   # Machine learning calculators (torch, torch-geometric)
   pip install -e .[ml]

   # I/O converters (pymatgen, ase)
   pip install -e .[io]

   # Structure builders (pyxtal, rdkit)
   pip install -e .[builders]

   # Symmetry analysis (spglib)
   pip install -e .[analysis]

   # Data storage (maggma)
   pip install -e .[storage]

   # All optional features
   pip install -e .[all]

Requirements
------------

Core Dependencies
~~~~~~~~~~~~~~~~~~

* **Python** >=3.9 (tested up to 3.12)
* **NumPy** >=1.20.0
* **SciPy** >=1.7.0
* **monty** >=2021.0 (for MSONable serialization)
* **tabulate** >=0.9.0 (for formatted output)

Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~

* **CLI Interface**: ``prompt-toolkit``
* **Machine Learning**: ``torch`` >=2.0.0, ``torch-geometric`` >=2.0.0
* **I/O Converters**: ``pymatgen`` >=2024.0.0, ``ase`` >=3.20.0
* **Structure Builders**: ``pyxtal`` >=1.0.0, ``rdkit``
* **Analysis**: ``spglib``
* **Storage**: ``maggma`` >=0.70.0

