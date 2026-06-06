"""
High-level I/O interface for convenient file operations.

This module provides simple read() and write() functions that automatically
detect file formats and handle structure reading/writing.
"""

from pathlib import Path
from typing import Union, Optional
from ..core import Crystal, Molecule, Structure
from .utils import (
    detect_format,
    get_reader_writer,
    is_crystal_format,
    is_molecule_format,
    normalize_format,
)


def read(
    filename: str, format: Optional[str] = None, **kwargs
) -> Union[Crystal, Molecule]:
    """
    Read a structure from a file with automatic format detection.

    This is a high-level convenience function that automatically detects
    the file format from the extension and calls the appropriate reader.

    Args:
        filename: Path to the structure file
        format: Optional format specification (e.g., 'vasp', 'cif', 'xyz').
               If None, format is detected from file extension.
        **kwargs: Additional arguments passed to the format-specific reader
                 (e.g., as_crystal for PDB format)

    Returns:
        Crystal or Molecule: Structure object from the file

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If format is not supported or cannot be detected
        TypeError: If format is ambiguous (e.g., PDB can be crystal or molecule)

    Examples:
        >>> from matsimpy.io import read
        >>> # Auto-detect format from extension
        >>> crystal = read('structure.vasp')
        >>> molecule = read('molecule.xyz')
        >>> # Explicitly specify format
        >>> crystal = read('structure.txt', format='cif')
        >>> # PDB with options
        >>> structure = read('protein.pdb', as_crystal=True)
    """
    filepath = Path(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    # Detect format if not specified
    if format is None:
        format_ext = detect_format(filename)
        if format_ext is None:
            raise ValueError(
                f"Could not detect file format from extension: {filename}\n"
                f"Please specify format explicitly using format='...'"
            )
    else:
        format_ext = normalize_format(format)
        if format_ext is None:
            raise ValueError(f"Unknown format: {format}")

    # Get reader function name
    reader_name, _ = get_reader_writer(format_ext)
    if reader_name is None:
        raise ValueError(f"Unsupported format: {format_ext}")

    # Import and call the appropriate reader
    if reader_name == "read_POSCAR":
        from .vasp import read_POSCAR

        return read_POSCAR(filename, **kwargs)
    elif reader_name == "read_CONTCAR":
        from .vasp import read_CONTCAR

        return read_CONTCAR(filename, **kwargs)
    elif reader_name == "read_CIF":
        from .cif import read_CIF

        return read_CIF(filename, **kwargs)
    elif reader_name == "read_XSF":
        from .xsf import read_XSF

        return read_XSF(filename, **kwargs)
    elif reader_name == "read_XYZ":
        from .xyz import read_XYZ

        return read_XYZ(filename, **kwargs)
    elif reader_name == "read_PDB":
        from .pdb import read_PDB

        return read_PDB(filename, **kwargs)
    elif reader_name == "read_MOL":
        from .mol import read_MOL

        return read_MOL(filename, **kwargs)
    elif reader_name == "read_ASE":
        from .ase import read_ASE

        return read_ASE(filename, **kwargs)
    elif reader_name == "from_json":
        from .json import from_json

        return from_json(filename=filename, **kwargs)
    else:
        raise ValueError(f"Reader function not implemented: {reader_name}")


def write(
    structure: Union[Crystal, Molecule, Structure],
    filename: str,
    format: Optional[str] = None,
    **kwargs,
) -> None:
    """
    Write a structure to a file with automatic format detection.

    This is a high-level convenience function that automatically detects
    the file format from the extension and calls the appropriate writer.

    Args:
        structure: Structure object to write (Crystal or Molecule)
        filename: Path to the output file
        format: Optional format specification (e.g., 'vasp', 'cif', 'xyz').
               If None, format is detected from file extension.
        **kwargs: Additional arguments passed to the format-specific writer
                 (e.g., title for file headers)

    Raises:
        ValueError: If format is not supported, cannot be detected, or
                   structure type is incompatible with format
        TypeError: If structure type is not supported

    Examples:
        >>> from matsimpy.io import write
        >>> from matsimpy.core import Crystal, Lattice
        >>>
        >>> crystal = Crystal(['Si', 'Si'], [[0,0,0], [0.25,0.25,0.25]], Lattice.cubic(5.43))
        >>> # Auto-detect format from extension
        >>> write(crystal, 'structure.vasp')
        >>> write(crystal, 'structure.cif', title='Silicon')
        >>>
        >>> # Explicitly specify format
        >>> write(crystal, 'structure.txt', format='vasp')
        >>>
        >>> # Molecule formats
        >>> from matsimpy.core import Molecule
        >>> molecule = Molecule(['H', 'O', 'H'], [[0,0,0], [0.96,0,0], [-0.24,0.93,0]])
        >>> write(molecule, 'molecule.xyz')
        >>> write(molecule, 'molecule.pdb', title='Water')
    """
    # Detect format if not specified
    if format is None:
        format_ext = detect_format(filename)
        if format_ext is None:
            raise ValueError(
                f"Could not detect file format from extension: {filename}\n"
                f"Please specify format explicitly using format='...'"
            )
    else:
        format_ext = normalize_format(format)
        if format_ext is None:
            raise ValueError(f"Unknown format: {format}")

    # Check format compatibility
    if isinstance(structure, Crystal):
        # JSON, ASE, and PDB can handle both Crystal and Molecule
        if not is_crystal_format(format_ext) and format_ext not in [".json", ".ase", ".pdb"]:
            raise ValueError(
                f"Format {format_ext} is not suitable for Crystal structures. "
                f"Use crystal formats (.vasp, .cif, .xsf, .json, .ase, .pdb) for crystals."
            )
    elif isinstance(structure, Molecule):
        if not is_molecule_format(format_ext) and format_ext not in [".json", ".ase"]:
            # JSON and ASE can handle both
            raise ValueError(
                f"Format {format_ext} is not suitable for Molecule structures. "
                f"Use molecule formats (.xyz, .pdb, .mol) for molecules."
            )
    else:
        raise TypeError(f"Unsupported structure type: {type(structure)}")

    # Get writer function name
    _, writer_name = get_reader_writer(format_ext)
    if writer_name is None:
        raise ValueError(f"Unsupported format: {format_ext}")

    # Import and call the appropriate writer
    if writer_name == "write_POSCAR":
        from .vasp import write_POSCAR

        write_POSCAR(structure, filename, **kwargs)
    elif writer_name == "write_CONTCAR":
        from .vasp import write_CONTCAR

        write_CONTCAR(structure, filename, **kwargs)
    elif writer_name == "write_CIF":
        from .cif import write_CIF

        write_CIF(structure, filename, **kwargs)
    elif writer_name == "write_XSF":
        from .xsf import write_XSF

        write_XSF(structure, filename, **kwargs)
    elif writer_name == "write_XYZ":
        from .xyz import write_XYZ

        write_XYZ(structure, filename, **kwargs)
    elif writer_name == "write_PDB":
        from .pdb import write_PDB

        write_PDB(structure, filename, **kwargs)
    elif writer_name == "write_MOL":
        from .mol import write_MOL

        write_MOL(structure, filename, **kwargs)
    elif writer_name == "write_ASE":
        from .ase import write_ASE

        write_ASE(structure, filename, **kwargs)
    elif writer_name == "to_json":
        from .json import to_json

        to_json(structure, filename=filename, **kwargs)
    else:
        raise ValueError(f"Writer function not implemented: {writer_name}")


__all__ = ["read", "write"]
