from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator, ValidationError
from typing import Optional, Any, Dict
import os
from datetime import datetime
import numpy as np
from pathlib import Path

from matsimpy.ui.cli.parameter_manager import CLIParameterManager, ParameterDefinition
from matsimpy.core import Crystal
from matsimpy.io import read, write


# Interface code for menu registration
INTERFACE_CODE = "[b161]"


class SupercellSizeValidator(Validator):
    """Validator for supercell size input"""

    def validate(self, document):
        text = document.text
        try:
            size = int(text)
            if size < 1:
                raise ValidationError(message="Size must be positive")
        except ValueError:
            raise ValidationError(message="Please enter a valid integer")


def simple_supercell(style: Optional[str] = None) -> None:
    """
    Simple supercell builder interface.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Define parameters including structure file
        param_manager.define_structure_parameter(
            name="structure_file",
            description="Input structure file path (e.g., 'configs/test.cif')",
            required=True,
        )

        param_manager.define_parameter(
            name="size",
            description="Supercell size (e.g., 2 for 2x2x2 or 2,3,3 for 2x3x3)",
            param_type=str,
            required=True,
            default="2",
            validator=lambda x: all(int(i) > 0 for i in x.split(",")),
        )

        # Get all parameters including structure file
        params = param_manager.get_parameters()
        if not params:
            return

        # Get input structure from parameters
        input_structure = param_manager.get_structure_from_params(
            params, "structure_file"
        )
        if not input_structure:
            print("No valid input structure found.")
            return

        # Ensure it's a Crystal (supercells only work for crystals)
        if not isinstance(input_structure, Crystal):
            print(
                "Error: Supercell creation only works for Crystal structures, not Molecules."
            )
            return

        # Display initial structure information
        print(f"\n=== Initial Structure Information ===")
        print(f"Formula: {input_structure.formula}")
        print(f"Number of atoms: {len(input_structure)}")
        print(
            f"Lattice parameters: a={input_structure.lattice.a:.3f}, b={input_structure.lattice.b:.3f}, c={input_structure.lattice.c:.3f}"
        )
        print(
            f"Lattice angles: α={input_structure.lattice.alpha:.3f}°, β={input_structure.lattice.beta:.3f}°, γ={input_structure.lattice.gamma:.3f}°"
        )
        print(f"Volume: {input_structure.volume:.3f} Å³")
        print(f"Composition: {input_structure.composition}")

        # Create supercell
        try:
            # Parse size parameter
            size_str = params["size"]
            size_parts = size_str.split(",")
            if len(size_parts) == 1:
                size = int(size_parts[0])
                scaling_matrix = np.array([[size, 0, 0], [0, size, 0], [0, 0, size]])
            else:
                scaling_matrix = np.array(
                    [
                        [int(size_parts[0]), 0, 0],
                        [0, int(size_parts[1]), 0],
                        [0, 0, int(size_parts[2])],
                    ]
                )

            print(f"\n=== Creating Supercell ===")
            print(f"Scaling matrix: {scaling_matrix}")

            # Create supercell (always returns a new object)
            supercell = input_structure.make_supercell(scaling_matrix)

            # Display final structure information
            print(f"\n=== Final Structure Information ===")
            print(f"Formula: {supercell.formula}")
            print(f"Number of atoms: {len(supercell)}")
            print(
                f"Lattice parameters: a={supercell.lattice.a:.3f}, b={supercell.lattice.b:.3f}, c={supercell.lattice.c:.3f}"
            )
            print(
                f"Lattice angles: α={supercell.lattice.alpha:.3f}°, β={supercell.lattice.beta:.3f}°, γ={supercell.lattice.gamma:.3f}°"
            )
            print(f"Volume: {supercell.volume:.3f} Å³")
            print(f"Composition: {supercell.composition}")

            # Save supercell
            output_dir = Path("configs")
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"supercell_{timestamp}.cif"

            # Save using matsimpy.io
            write(supercell, str(output_file))
            print(f"\n=== Structure Saved ===")
            print(f"Output file: {output_file}")
            print(f"Supercell created successfully with {len(supercell)} atoms.")

        except Exception as e:
            print(f"Error creating supercell: {e}")
            return

    except Exception as e:
        print(f"Error in simple supercell interface: {e}")
        return
