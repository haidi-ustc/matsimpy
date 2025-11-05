"""
I/O module for reading and writing various file formats.

This module provides support for:
- VASP (POSCAR, CONTCAR)
- CIF (Crystallographic Information File)
- XYZ (coordinate format)
- PDB (Protein Data Bank)
- XSF (XCrySDen format)
- JSON (serialization)
"""

from .vasp import read_POSCAR, write_POSCAR, read_CONTCAR, write_CONTCAR
from .cif import read_CIF, write_CIF
from .xyz import read_XYZ, write_XYZ, read_XYZ_multiframe
from .pdb import read_PDB, write_PDB
from .xsf import read_XSF, write_XSF
from .json import to_json, from_json
from .ase import read_ASE, write_ASE
from .mol import read_MOL, write_MOL
from .utils import detect_format, get_reader_writer, is_crystal_format, is_molecule_format

__all__ = [
    # VASP
    'read_POSCAR', 'write_POSCAR', 'read_CONTCAR', 'write_CONTCAR',
    # CIF
    'read_CIF', 'write_CIF',
    # XYZ
    'read_XYZ', 'write_XYZ', 'read_XYZ_multiframe',
    # PDB
    'read_PDB', 'write_PDB',
    # XSF
    'read_XSF', 'write_XSF',
    # JSON
    'to_json', 'from_json',
    # ASE
    'read_ASE', 'write_ASE',
    # MOL
    'read_MOL', 'write_MOL',
    # Utils
    'detect_format', 'get_reader_writer', 'is_crystal_format', 'is_molecule_format',
]

