"""
File Format Converter module for MatSimPy CLI.

This module provides functions to convert between different structure file formats
including CIF, POSCAR, XYZ, PDB, and other formats.
"""

import os
import glob
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

from matsimpy.ui.cli.parameter_manager import CLIParameterManager, ParameterDefinition
from matsimpy.io import read, write
from matsimpy.core import Crystal, Molecule


def _expand_wildcard_path(path_pattern: str) -> List[Path]:
    """
    Expand wildcard patterns to list of actual file paths

    Args:
        path_pattern: Path pattern with wildcards (*, **, ?)

    Returns:
        List[Path]: List of matching file paths
    """
    # Use glob to expand wildcards
    expanded_paths = glob.glob(path_pattern, recursive=True)
    # Convert to Path objects and filter only files
    file_paths = [Path(p) for p in expanded_paths if Path(p).is_file()]
    return sorted(file_paths)


def _generate_output_path(input_path: Path, output_pattern: str) -> Path:
    """
    Generate output path based on input path and output pattern

    Args:
        input_path: Input file path
        output_pattern: Output pattern (may contain wildcards or directory)

    Returns:
        Path: Generated output path
    """
    output_path = Path(output_pattern)

    # If output pattern contains wildcards, replace with input filename
    if "*" in output_pattern:
        # Replace wildcards with input filename (without extension)
        stem = input_path.stem
        output_str = output_pattern.replace("*", stem)
        output_path = Path(output_str)
    else:
        # If output is a directory, use input filename with new extension
        if output_path.is_dir() or output_pattern.endswith("/"):
            output_dir = Path(output_pattern)
            # Determine output extension from directory pattern or keep original
            output_filename = input_path.name
            output_path = output_dir / output_filename

    return output_path


def any_to_any(style: Optional[str] = None) -> bool:
    """
    Universal file format converter - supports conversion between any formats

    Supported formats:
    - VASP (POSCAR, CONTCAR, vasprun.xml, OUTCAR)
    - CIF (.cif)
    - XYZ (.xyz)
    - JSON (.json)
    - PDB (.pdb)
    - Other formats supported by ASE

    Batch conversion examples:
    - configs/*.cif -> configs-vasp/*.vasp
    - *.vasp -> configs/*.cif
    - a-*.vasp -> b-*.json

    Args:
        style: Optional style parameter for parameter manager

    Returns:
        bool: Whether conversion was successful
    """
    print("\n" + "=" * 60)
    print("Universal File Format Converter")
    print("=" * 60)
    print("Supports conversion between any structure file formats")
    print()
    print("Supported formats:")
    print("  * VASP: .vasp, .poscar, POSCAR, CONTCAR, vasprun.xml, OUTCAR")
    print("  * CIF: .cif")
    print("  * XYZ: .xyz")
    print("  * JSON: .json")
    print("  * PDB: .pdb")
    print("  * Other formats supported by ASE")
    print()
    print("Usage:")
    print("  - Single file: input.cif output.vasp")
    print("  - Batch conversion with wildcards:")
    print("    * configs/*.cif configs-vasp/*.vasp")
    print("    * *.vasp configs/*.cif")
    print("    * a-*.vasp b-*.json")
    print("  - Input/output formats auto-detected from file extensions")
    print("  - Structure validation performed by default")
    print()

    # Parameter manager
    param_manager = CLIParameterManager(style=style)

    # Define parameters
    param_manager.define_parameter(
        name="input_file",
        description="Input file path or pattern (supports wildcards: *, **, ?)",
        param_type=str,
        required=True,
    )

    param_manager.define_parameter(
        name="output_file",
        description="Output file path or pattern (supports wildcards: *, **, ?)",
        param_type=str,
        required=True,
    )

    param_manager.define_parameter(
        name="validate",
        description="Validate structure",
        param_type=bool,
        required=False,
        default=True,
    )

    # Get parameters
    try:
        params = param_manager.get_parameters()
        if not params:
            return False

        input_pattern = params["input_file"]
        output_pattern = params["output_file"]
        validate = params["validate"]

    except Exception as e:
        print(f"Error getting parameters: {e}")
        return False

    # Expand input pattern to get list of files
    input_files = _expand_wildcard_path(input_pattern)

    if not input_files:
        print(f"No files found matching pattern: {input_pattern}")
        return False

    # Show batch conversion info
    print(f"\nBatch conversion:")
    print(f"  Input pattern: {input_pattern}")
    print(f"  Output pattern: {output_pattern}")
    print(f"  Files found: {len(input_files)}")
    print()

    # Process each file
    success_count = 0
    total_count = len(input_files)

    for i, input_path in enumerate(input_files, 1):
        print(f"[{i}/{total_count}] Processing: {input_path.name}")

        try:
            # Generate output path
            output_path = _generate_output_path(input_path, output_pattern)

            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Show file info
            print(f"  -> {output_path}")
            print(f"     Size: {input_path.stat().st_size} bytes")

            # Load structure using matsimpy.io
            structure = read(str(input_path))

            # Validate structure if requested
            if validate:
                # Check minimum distances using get_neighbor_list
                if len(structure) > 1:
                    neighbors = structure.get_neighbor_list(10.0)  # Large cutoff
                    min_dist = float("inf")
                    for i, neighbor_list in neighbors.items():
                        for j, dist in neighbor_list:
                            min_dist = min(min_dist, dist)

                    if min_dist < 0.5:
                        print(f"     Warning: Min distance {min_dist:.3f} A")

            # Save in target format
            write(structure, str(output_path))

            # Show result
            print(f"     Output size: {output_path.stat().st_size} bytes")
            print(f"     Status: SUCCESS")
            success_count += 1

        except Exception as e:
            print(f"     Status: FAILED - {e}")
            continue

        print()

    # Show summary
    print("=" * 60)
    print(f"Batch conversion completed:")
    print(f"  Total files: {total_count}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {total_count - success_count}")

    if success_count > 0:
        print(f"\nFirst converted file info:")
        try:
            # Show info for first successful conversion
            first_input = input_files[0]
            first_output = _generate_output_path(first_input, output_pattern)

            if first_output.exists():
                structure = read(str(first_output))

                print(f"  File: {first_output}")
                if isinstance(structure, Crystal):
                    print(
                        f"  Lattice: a={structure.lattice.a:.3f}, b={structure.lattice.b:.3f}, c={structure.lattice.c:.3f}"
                    )
                    print(f"  Volume: {structure.volume:.3f} A^3")
                print(f"  Atoms: {len(structure)}")
                print(f"  Formula: {structure.formula}")
                print(f"  Composition: {structure.composition.formula}")

                # Show first few atoms
                print(f"  First 3 atoms:")
                for j in range(min(3, len(structure))):
                    species = structure.species[j]
                    if isinstance(structure, Crystal):
                        coords = structure.cart_positions[j]
                    else:
                        coords = structure.positions[j]
                    print(
                        f"    {j+1}. {species:>4} [{coords[0]:6.3f}, {coords[1]:6.3f}, {coords[2]:6.3f}]"
                    )

                if len(structure) > 3:
                    print(f"    ... and {len(structure)-3} more atoms")
        except:
            pass

    return success_count == total_count
