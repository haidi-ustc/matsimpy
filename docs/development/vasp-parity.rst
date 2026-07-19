Reproducing VASP parity tests
=============================

Oracle: ``pymatgen==2025.6.14``

Install:

.. code-block:: bash

   python -m pip install -e '.[dev,parity]'

Run:

.. code-block:: bash

   pytest -m requires_pymatgen tests/calculator/test_vasp_outputs_parity.py tests/symmetry/test_vasp_services.py

For the complete pinned parity selection used by the native-runtime audit:

.. code-block:: bash

   python -c "import pymatgen.core; from importlib.metadata import version; assert version('pymatgen') == '2025.6.14'"
   pytest tests/electronic_structure tests/symmetry/test_vasp_services.py tests/calculator/test_vasp_outputs_parity.py tests/calculator/test_vasp_sets_native.py -m requires_pymatgen -v

Copying and attribution policy
------------------------------

Pymatgen is a black-box behavioral oracle. Production implementations are
original unless a source file contains an explicit adaptation notice with
source path, version, scope, copyright, and license.

The VASP input, output, and set modules are historical pymatgen adaptations
that predate this native-runtime project and retain their original file-level
MIT notices. The new Setyawan--Curtarolo k-path work is instead a narrow
adaptation from ASE 3.29.0; its exact source paths, functions, adapted scope,
copyright, and BSD-2-Clause terms are recorded in
``matsimpy/symmetry/kpath.py`` and ``THIRD_PARTY_NOTICES.md``. New native
electronic-structure objects and symmetry services are not copied from
pymatgen.
