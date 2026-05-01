"""
Basic structure editing operations for MatSimPy CLI.

This module provides interfaces for adding, moving, and deleting atoms
using matsimpy's native API.
"""

import os
from datetime import datetime
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText

from matsimpy.ui.cli.parameter_manager import CLIParameterManager, ParameterDefinition
from matsimpy.core import Element, Composition, Crystal, Molecule
from matsimpy.io import read, write
from matsimpy.transformation.atomic import move_atoms
from matsimpy.utils.selection import AtomSelection


# Interface code for menu registration
INTERFACE_CODE = "[e111]"


def _validate_element(element_str: str) -> bool:
    """Validate element symbol using matsimpy."""
    try:
        Element.get_element(element_str)
        return True
    except (ValueError, KeyError, AttributeError):
        return False


def _validate_coordinates_list(coords_str: str) -> bool:
    """Validate coordinates list format."""
    try:
        coords_str = coords_str.strip()
        if not (coords_str.startswith("[") and coords_str.endswith("]")):
            return False

        inner = coords_str[1:-1]
        if not inner:
            return False

        coord_pairs = inner.split("],[")
        for pair in coord_pairs:
            pair = pair.strip("[]")
            coords = [float(x.strip()) for x in pair.split(",")]
            if len(coords) != 3:
                return False
        return True
    except:
        return False


def _parse_coordinates_list(coords_str: str) -> List[List[float]]:
    """Parse coordinates list from string."""
    coords_str = coords_str.strip()
    inner = coords_str[1:-1]
    coord_pairs = inner.split("],[")

    coordinates = []
    for pair in coord_pairs:
        pair = pair.strip("[]")
        coords = [float(x.strip()) for x in pair.split(",")]
        coordinates.append(coords)

    return coordinates


def _validate_element_list(elements_str: str) -> bool:
    """Validate element list format. Accepts ['Fe', 'O'], 'Fe,O', or 'Fe'."""
    try:
        elements_str = elements_str.strip()
        if not elements_str:
            return False

        # Try to parse as list format ['Fe', 'O'] or ["Fe", "O"]
        if elements_str.startswith("[") and elements_str.endswith("]"):
            inner = elements_str[1:-1].strip()
            if not inner:
                return False
            elements = [el.strip().strip("\"'") for el in inner.split(",")]
        else:
            # Try comma-separated format 'Fe,O' or single element 'Fe'
            elements = [el.strip().strip("\"'") for el in elements_str.split(",")]

        # Validate each element
        for element in elements:
            if not element or not _validate_element(element):
                return False
        return True
    except:
        return False


def _parse_element_list(elements_str: str) -> List[str]:
    """Parse element list from string. Handles multiple formats:
    - 'Fe' (single element, no quotes)
    - 'Fe,O' (comma-separated, no quotes)
    - 'Fe, O' (with spaces)
    - ['Fe', 'O'] (list format with quotes)
    - [Fe, O] (list format without quotes)
    """
    elements_str = elements_str.strip()

    # Try to parse as list format ['Fe', 'O'], [Fe, O], or ["Fe", "O"]
    if elements_str.startswith("[") and elements_str.endswith("]"):
        inner = elements_str[1:-1].strip()
        if inner:
            # Split by comma and strip quotes/spaces from each element
            elements = [el.strip().strip("\"'") for el in inner.split(",")]
        else:
            elements = []
    else:
        # Parse comma-separated format 'Fe,O' or single element 'Fe' (no quotes needed)
        elements = [el.strip().strip("\"'") for el in elements_str.split(",")]

    # Filter out empty strings
    elements = [el for el in elements if el]

    return elements


def _calculate_min_distance(structure: Union[Crystal, Molecule]) -> float:
    """Calculate minimum distance between atoms."""
    if len(structure) < 2:
        return float("inf")

    neighbors = structure.get_neighbor_list(10.0)  # Large cutoff
    min_dist = float("inf")
    for i, neighbor_list in neighbors.items():
        for j, dist in neighbor_list:
            min_dist = min(min_dist, dist)
    return min_dist if min_dist < float("inf") else 0.0


def add_atoms(style: Optional[str] = None) -> None:
    """
    Add atoms to structure interface using matsimpy API.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Define parameters including structure file
        param_manager.define_parameter(
            name="structure_file",
            description="Input structure file path (e.g., 'configs/test.cif')",
            param_type=str,
            required=True,
        )

        param_manager.define_parameter(
            name="elements",
            description="Element symbols to add. Formats: 'Fe', 'Fe,O', or ['Fe', 'O']",
            param_type=str,
            required=True,
            default="['Fe']",
            validator=_validate_element_list,
        )

        param_manager.define_parameter(
            name="position_type",
            description="Position specification type ('coordinates', 'relative', 'random')",
            param_type=str,
            required=False,
            default="coordinates",
            validator=lambda x: x in ["coordinates", "relative", "random"],
        )

        param_manager.define_parameter(
            name="coordinates",
            description="List of atomic coordinates [[x1,y1,z1], [x2,y2,z2], ...] in Angstroms (skipped for 'random' position type)",
            param_type=str,
            required=False,
            default="[[0,0,0]]",
            validator=_validate_coordinates_list,
        )

        # Get all parameters (coordinates will be automatically skipped if position_type is 'random')
        params = param_manager.get_parameters()
        if not params:
            return

        # Load structure using matsimpy.io
        structure_file = params["structure_file"]
        if not os.path.exists(structure_file):
            print(f"Error: File not found: {structure_file}")
            return

        input_structure = read(structure_file)

        # Display initial structure information
        print(f"\n=== Initial Structure Information ===")
        print(f"Formula: {input_structure.formula}")
        print(f"Number of atoms: {len(input_structure)}")
        if isinstance(input_structure, Crystal):
            print(
                f"Lattice parameters: a={input_structure.lattice.a:.3f}, b={input_structure.lattice.b:.3f}, c={input_structure.lattice.c:.3f}"
            )
            print(
                f"Lattice angles: α={input_structure.lattice.alpha:.3f}°, β={input_structure.lattice.beta:.3f}°, γ={input_structure.lattice.gamma:.3f}°"
            )
            print(f"Volume: {input_structure.volume:.3f} Å³")
        print(f"Composition: {input_structure.composition.formula}")

        # Parse parameters
        elements = _parse_element_list(params["elements"])
        position_type = params["position_type"]

        print(f"\n=== Adding Atoms ===")
        print(f"Elements: {elements}")
        print(f"Position type: {position_type}")

        # Work with a copy of the structure
        working_structure = input_structure.copy()

        # Add atoms based on position type
        if position_type == "coordinates":
            # Parse coordinates
            coordinates = _parse_coordinates_list(params["coordinates"])
            print(f"Coordinates: {coordinates}")

            # Ensure we have enough coordinates for all elements
            if len(coordinates) < len(elements):
                last_coord = coordinates[-1] if coordinates else [0, 0, 0]
                while len(coordinates) < len(elements):
                    coordinates.append(last_coord)
                print(f"Extended coordinates: {coordinates}")

            # Add atoms at specified coordinates
            for i, (element, coords) in enumerate(zip(elements, coordinates)):
                if isinstance(working_structure, Crystal):
                    # For Crystal, convert Cartesian to fractional
                    frac_coords = np.dot(
                        coords, working_structure.lattice.inv_matrix
                    ).tolist()
                    working_structure = working_structure.add_atom(element, frac_coords)
                else:
                    # For Molecule, use Cartesian directly
                    working_structure = working_structure.add_atom(element, coords)
                print(f"Added {element} atom {i+1} at coordinates {coords}")

        elif position_type == "relative":
            # Add atoms at relative positions (fractional for Crystal, Cartesian for Molecule)
            coordinates = _parse_coordinates_list(params["coordinates"])
            print(f"Relative coordinates: {coordinates}")

            # Ensure we have enough coordinates for all elements
            if len(coordinates) < len(elements):
                last_coord = coordinates[-1] if coordinates else [0, 0, 0]
                while len(coordinates) < len(elements):
                    coordinates.append(last_coord)
                print(f"Extended coordinates: {coordinates}")

            for i, (element, coords) in enumerate(zip(elements, coordinates)):
                if isinstance(working_structure, Crystal):
                    # For Crystal, use fractional coordinates
                    # If values > 1.0, assume Cartesian and convert
                    if any(c > 1.0 for c in coords):
                        frac_coords = np.dot(
                            coords, working_structure.lattice.inv_matrix
                        ).tolist()
                        print(
                            f"Converted {element} coordinates to fractional: {frac_coords}"
                        )
                    else:
                        frac_coords = coords
                    working_structure = working_structure.add_atom(element, frac_coords)
                else:
                    # For Molecule, use Cartesian
                    working_structure = working_structure.add_atom(element, coords)
                print(f"Added {element} atom {i+1} at coordinates {coords}")

        elif position_type == "random":
            # Add atoms at random positions
            print(f"Adding {len(elements)} atoms at random positions...")

            for i, element in enumerate(elements):
                if isinstance(working_structure, Crystal):
                    # Generate random fractional coordinates
                    frac_coords = np.random.random(3).tolist()
                    working_structure = working_structure.add_atom(element, frac_coords)
                    # Convert to cartesian for display
                    cart_coords = np.dot(frac_coords, working_structure.lattice.matrix)
                    print(
                        f"Added {element} atom {i+1} at random position: {cart_coords}"
                    )
                else:
                    # Generate random Cartesian coordinates
                    cart_coords = (np.random.random(3) * 10.0).tolist()
                    working_structure = working_structure.add_atom(element, cart_coords)
                    print(
                        f"Added {element} atom {i+1} at random position: {cart_coords}"
                    )

        # Check final structure
        print(f"\n=== Final Structure Information ===")
        final_structure = working_structure
        print(f"Formula: {final_structure.formula}")
        print(f"Number of atoms: {len(final_structure)}")
        if isinstance(final_structure, Crystal):
            print(
                f"Lattice parameters: a={final_structure.lattice.a:.3f}, b={final_structure.lattice.b:.3f}, c={final_structure.lattice.c:.3f}"
            )
            print(
                f"Lattice angles: α={final_structure.lattice.alpha:.3f}°, β={final_structure.lattice.beta:.3f}°, γ={final_structure.lattice.gamma:.3f}°"
            )
            print(f"Volume: {final_structure.volume:.3f} Å³")
        print(f"Composition: {final_structure.composition.formula}")

        # Check minimum distances
        min_dist = _calculate_min_distance(final_structure)
        if min_dist < float("inf"):
            print(f"Minimum distance between atoms: {min_dist:.3f} Å")

        # Save modified structure
        output_dir = Path("configs")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        elements_str = "_".join(elements)

        # Use appropriate file format based on structure type
        if isinstance(working_structure, Molecule):
            file_ext = ".xyz"
        else:
            file_ext = ".cif"

        output_file = (
            output_dir / f"structure_with_added_{elements_str}_{timestamp}{file_ext}"
        )

        write(working_structure, str(output_file))
        print(f"\n=== Structure Saved ===")
        print(f"Output file: {output_file}")
        print(
            f"Successfully added {len(elements)} atoms. Total atoms: {len(final_structure)}"
        )

    except Exception as e:
        print(f"Error in add atoms interface: {str(e)}")
        import traceback

        traceback.print_exc()
        return


def move_atoms_interface(style: Optional[str] = None) -> None:
    """
    Move atoms in structure interface using matsimpy's move_atoms function.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Define parameters
        param_manager.define_parameter(
            name="structure_file",
            description="Input structure file path (e.g., 'configs/test.cif')",
            param_type=str,
            required=True,
        )

        param_manager.define_parameter(
            name="selection_string",
            description="Atom selection (indices like '1 2 3' or species like 'Si O')",
            param_type=str,
            required=True,
            default="1",
            validator=None,
        )

        param_manager.define_parameter(
            name="displacement",
            description="Displacement vector (x,y,z) in Angstroms",
            param_type=str,
            required=True,
            default="1,0,0",
            validator=lambda x: len(x.split(",")) == 3,
        )

        param_manager.define_parameter(
            name="cartesian",
            description="Use Cartesian coordinates (True) or fractional (False)",
            param_type=bool,
            required=False,
            default=True,
        )

        # Get parameters
        params = param_manager.get_parameters()
        if not params:
            return

        # Load structure
        structure_file = params["structure_file"]
        if not os.path.exists(structure_file):
            print(f"Error: File not found: {structure_file}")
            return

        input_structure = read(structure_file)

        # Display initial structure information
        print(f"\n=== Initial Structure Information ===")
        print(f"Formula: {input_structure.formula}")
        print(f"Number of atoms: {len(input_structure)}")
        if isinstance(input_structure, Crystal):
            print(
                f"Lattice parameters: a={input_structure.lattice.a:.3f}, b={input_structure.lattice.b:.3f}, c={input_structure.lattice.c:.3f}"
            )
            print(f"Volume: {input_structure.volume:.3f} Å³")
        print(f"Composition: {input_structure.composition.formula}")

        # Parse selection string
        selection_string = params["selection_string"]
        displacement_str = params["displacement"]
        displacement = [float(x.strip()) for x in displacement_str.split(",")]
        use_cartesian = params["cartesian"]

        print(f"\n=== Atom Selection ===")
        print(f"Selection string: '{selection_string}'")

        # Parse selection - support indices and species
        selected_indices = []
        parts = selection_string.replace(",", " ").split()

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Try range (e.g., "1-5")
            if "-" in part and part[0].isdigit():
                try:
                    start, end = map(int, part.split("-"))
                    selected_indices.extend(range(start - 1, end))  # Convert to 0-based
                    continue
                except:
                    pass

            # Try index
            if part.isdigit():
                idx = int(part) - 1  # Convert to 0-based
                if 0 <= idx < len(input_structure):
                    selected_indices.append(idx)
                continue

            # Try species
            try:
                sel = AtomSelection(input_structure).by_species(part)
                selected_indices.extend(sel.indices)
            except:
                pass

        # Remove duplicates and sort
        selected_indices = sorted(list(set(selected_indices)))

        if not selected_indices:
            print("No atoms selected. Please check your selection string.")
            return

        print(
            f"Selected {len(selected_indices)} atoms: {[i+1 for i in selected_indices]}"
        )

        # Show selected atoms
        print(f"\n=== Selected Atoms Information ===")
        for i, idx in enumerate(selected_indices):
            if isinstance(input_structure, Crystal):
                pos = input_structure.cart_positions[idx]
                species = input_structure.species[idx]
            else:
                pos = input_structure.positions[idx]
                species = input_structure.species[idx]
            print(
                f"  {i+1:2d}. Atom {idx+1:2d}: {species:>4} at [{pos[0]:6.3f}, {pos[1]:6.3f}, {pos[2]:6.3f}]"
            )

        # Move atoms using matsimpy's move_atoms function
        print(f"\n=== Moving Atoms ===")
        print(f"Displacement: {displacement}")
        print(f"Coordinate system: {'Cartesian' if use_cartesian else 'Fractional'}")

        moved_structure = move_atoms(
            input_structure,
            selected_indices,
            displacement,
            cartesian=use_cartesian,
            inplace=False,
        )

        # Check final structure
        print(f"\n=== Final Structure Information ===")
        print(f"Formula: {moved_structure.formula}")
        print(f"Number of atoms: {len(moved_structure)}")
        if isinstance(moved_structure, Crystal):
            print(
                f"Lattice parameters: a={moved_structure.lattice.a:.3f}, b={moved_structure.lattice.b:.3f}, c={moved_structure.lattice.c:.3f}"
            )
            print(f"Volume: {moved_structure.volume:.3f} Å³")
        print(f"Composition: {moved_structure.composition.formula}")

        # Check minimum distances
        min_dist = _calculate_min_distance(moved_structure)
        if min_dist < float("inf"):
            print(f"Minimum distance between atoms: {min_dist:.3f} Å")

        # Save modified structure
        output_dir = Path("configs")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"structure_moved_atoms_{timestamp}.cif"

        write(moved_structure, str(output_file))
        print(f"\n=== Structure Saved ===")
        print(f"Output file: {output_file}")
        print(f"Successfully moved {len(selected_indices)} atoms.")

    except Exception as e:
        print(f"Error in move atoms interface: {str(e)}")
        import traceback

        traceback.print_exc()
        return


def delete_atoms(style: Optional[str] = None) -> None:
    """
    Delete atoms from structure interface using matsimpy API.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Define parameters
        param_manager.define_parameter(
            name="structure_file",
            description="Input structure file path (e.g., 'configs/test.cif')",
            param_type=str,
            required=True,
        )

        param_manager.define_parameter(
            name="selection_string",
            description="Atom selection (indices like '1 2 3' or species like 'Si O')",
            param_type=str,
            required=True,
            default="1",
            validator=None,
        )

        # Get parameters
        params = param_manager.get_parameters()
        if not params:
            return

        # Load structure
        structure_file = params["structure_file"]
        if not os.path.exists(structure_file):
            print(f"Error: File not found: {structure_file}")
            return

        input_structure = read(structure_file)

        # Display initial structure information
        print(f"\n=== Initial Structure Information ===")
        print(f"Formula: {input_structure.formula}")
        print(f"Number of atoms: {len(input_structure)}")
        if isinstance(input_structure, Crystal):
            print(
                f"Lattice parameters: a={input_structure.lattice.a:.3f}, b={input_structure.lattice.b:.3f}, c={input_structure.lattice.c:.3f}"
            )
            print(f"Volume: {input_structure.volume:.3f} Å³")
        print(f"Composition: {input_structure.composition.formula}")

        # Parse selection string
        selection_string = params["selection_string"]

        print(f"\n=== Atom Selection ===")
        print(f"Selection string: '{selection_string}'")

        # Parse selection
        selected_indices = []
        parts = selection_string.replace(",", " ").split()

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Try range
            if "-" in part and part[0].isdigit():
                try:
                    start, end = map(int, part.split("-"))
                    selected_indices.extend(range(start - 1, end))
                    continue
                except:
                    pass

            # Try index
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(input_structure):
                    selected_indices.append(idx)
                continue

            # Try species
            try:
                sel = AtomSelection(input_structure).by_species(part)
                selected_indices.extend(sel.indices)
            except:
                pass

        # Remove duplicates and sort in reverse order for deletion
        selected_indices = sorted(list(set(selected_indices)), reverse=True)

        if not selected_indices:
            print("No atoms selected. Please check your selection string.")
            return

        print(
            f"Selected {len(selected_indices)} atoms: {[i+1 for i in reversed(selected_indices)]}"
        )

        # Show selected atoms
        print(f"\n=== Selected Atoms Information ===")
        for i, idx in enumerate(reversed(selected_indices)):
            if isinstance(input_structure, Crystal):
                pos = input_structure.cart_positions[idx]
                species = input_structure.species[idx]
            else:
                pos = input_structure.positions[idx]
                species = input_structure.species[idx]
            print(
                f"  {i+1:2d}. Atom {idx+1:2d}: {species:>4} at [{pos[0]:6.3f}, {pos[1]:6.3f}, {pos[2]:6.3f}]"
            )

        # Delete atoms (in reverse order to maintain indices)
        print(f"\n=== Deleting Atoms ===")
        working_structure = input_structure

        deleted_count = 0
        for idx in selected_indices:
            try:
                working_structure = working_structure.remove_atom(idx)
                deleted_count += 1
                print(f"Deleted atom {idx+1}")
            except IndexError:
                print(
                    f"Warning: Atom {idx+1} no longer exists (may have been deleted already)"
                )

        # Check final structure
        print(f"\n=== Final Structure Information ===")
        final_structure = working_structure
        print(f"Formula: {final_structure.formula}")
        print(f"Number of atoms: {len(final_structure)}")
        if isinstance(final_structure, Crystal):
            print(
                f"Lattice parameters: a={final_structure.lattice.a:.3f}, b={final_structure.lattice.b:.3f}, c={final_structure.lattice.c:.3f}"
            )
            print(f"Volume: {final_structure.volume:.3f} Å³")
        print(f"Composition: {final_structure.composition.formula}")

        # Check minimum distances
        if len(final_structure) > 1:
            min_dist = _calculate_min_distance(final_structure)
            if min_dist < float("inf"):
                print(f"Minimum distance between atoms: {min_dist:.3f} Å")

        # Save modified structure
        output_dir = Path("configs")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"structure_deleted_atoms_{timestamp}.cif"

        write(final_structure, str(output_file))
        print(f"\n=== Structure Saved ===")
        print(f"Output file: {output_file}")
        print(f"Successfully deleted {deleted_count} atoms.")

    except Exception as e:
        print(f"Error in delete atoms interface: {str(e)}")
        import traceback

        traceback.print_exc()
        return
