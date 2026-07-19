Electronic Structure
====================

MatSimPy provides native electronic-structure objects used directly by its
VASP parsers. They do not require pymatgen. Supported legacy pymatgen-shaped
MSON dictionaries can be decoded explicitly with
``decode_legacy_pymatgen_dict`` without importing pymatgen.

VASP example
------------

.. code-block:: python

   from matsimpy.calculator.vasp.outputs import Vasprun

   run = Vasprun("vasprun.xml")
   complete_dos = run.complete_dos
   band_structure = run.get_band_structure()
   structure_entry = run.get_computed_entry()
   energy_entry = run.get_computed_entry(inc_structure=False)
   trajectory = run.get_trajectory()

``complete_dos`` is a :class:`CompleteDos`; ``get_band_structure`` returns a
:class:`BandStructure` or :class:`BandStructureSymmLine`; entries are
:class:`ComputedEntry` or :class:`ComputedStructureEntry`; and trajectories
use :class:`matsimpy.core.trajectory.Trajectory`.

Core enums and magnetic moments
-------------------------------

.. automodule:: matsimpy.electronic_structure.core
   :members:
   :undoc-members:

Density of states
-----------------

.. automodule:: matsimpy.electronic_structure.dos
   :members:

Band structures
---------------

.. automodule:: matsimpy.electronic_structure.bandstructure
   :members:

Computed entries
----------------

.. automodule:: matsimpy.electronic_structure.entries
   :members:

Legacy decoding
---------------

.. autofunction:: matsimpy.electronic_structure.decode_legacy_pymatgen_dict
