import os
from datetime import datetime
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any

from matsimpy.ui.cli.parameter_manager import CLIParameterManager, ParameterDefinition
from matsimpy.core import Composition, Crystal, Molecule, Lattice
from matsimpy.builders.bulk import from_prototype, random_crystal
from matsimpy.builders.molecule import build_linear, build_bent, build_tetrahedral


def crystal_structure(style: Optional[str] = None) -> Dict[str, Any]:
    """
    Random crystal generator interface.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Define parameters
        param_manager.define_parameter(
            name="formula",
            description="Chemical formula (e.g., 'SiO2', 'SiC', 'Fe2O3')",
            param_type=str,
            required=False,
            default="SiO2",
            validator=lambda x: bool(Composition(x, sort_by=None)),
        )

        param_manager.define_parameter(
            name="min_distance",
            description="Minimum distance between atoms in Angstrom",
            param_type=float,
            required=False,
            default=1.0,
            validator=lambda x: x > 0,
        )

        param_manager.define_parameter(
            name="max_attempts",
            description="Maximum number of attempts to generate valid structure",
            param_type=int,
            required=False,
            default=1000,
            validator=lambda x: x > 0,
        )

        # Get parameters
        params = param_manager.get_parameters()
        if not params:
            return {"status": False, "message": "No parameters provided."}

        # Convert formula to composition
        try:
            comp = Composition(params.get("formula", "SiO2"), sort_by=None)
            composition_dict = {
                el: int(count) for el, count in comp.composition.items()
            }
        except Exception as e:
            return {"status": False, "message": f"Invalid chemical formula: {str(e)}"}

        # Generate structure using matsimpy builders
        # Try random_crystal first (requires pyxtal), fall back to prototype
        species = list(composition_dict.keys())
        num_ions = [composition_dict[el] for el in species]

        try:
            # Use space group 1 (P1 - no symmetry) for random generation
            structure = random_crystal(3, 1, species, num_ions)
        except (ImportError, RuntimeError, AttributeError, ValueError) as e:
            # Fall back to prototype-based generation if pyxtal fails
            # This handles: ImportError (pyxtal not installed), RuntimeError (pyxtal API issues),
            # AttributeError (missing attributes), ValueError (generation failed)
            if isinstance(e, ImportError):
                error_msg = "PyXtal is not installed. Install with: pip install pyxtal"
            else:
                error_msg = f"PyXtal generation failed: {str(e)}. Falling back to prototype-based generation."
                print(f"Warning: {error_msg}")

            # Fall back to prototype-based generation
            if len(species) == 1:
                # Single element - use FCC
                lattice_constant = float(params.get("min_distance", 1.0)) * 2.0
                structure = from_prototype("fcc", species[0], lattice_constant)
            elif len(species) == 2:
                # Binary - use rocksalt
                lattice_constant = float(params.get("min_distance", 1.0)) * 2.0
                structure = from_prototype("rocksalt", species, lattice_constant)
            else:
                return {
                    "status": False,
                    "message": f"Cannot generate structure for {len(species)}-element composition. "
                    f"PyXtal is required but failed: {str(e)}. "
                    f"Install with: pip install pyxtal",
                }

        # Save structure
        output_dir = Path("configs")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        formula = params.get("formula", "SiO2").replace(" ", "")
        output_file = output_dir / f"{formula}_{timestamp}.cif"

        from matsimpy.io import write

        write(structure, str(output_file))
        print(f"Random crystal created successfully with {len(structure)} atoms.")
        print(f"Saved to: {output_file}")

        return {
            "status": True,
            "message": f"Random crystal created successfully with {len(structure)} atoms.",
            "data": structure,
        }

    except Exception as e:
        return {"status": False, "message": f"Error in random crystal interface: {e}"}


def molecular_structure(style: Optional[str] = None) -> Dict[str, Any]:
    """
    Molecular structure generator interface.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Define parameters
        param_manager.define_parameter(
            name="formula",
            description="Chemical formula (e.g., 'H2O', 'CO2', 'CH4')",
            param_type=str,
            required=False,
            default="H2O",
            validator=lambda x: bool(Composition(x, sort_by=None)),
        )

        param_manager.define_parameter(
            name="min_distance",
            description="Minimum distance between atoms in Angstrom",
            param_type=float,
            required=False,
            default=1.0,
            validator=lambda x: x > 0,
        )

        param_manager.define_parameter(
            name="max_attempts",
            description="Maximum number of attempts to generate valid structure",
            param_type=int,
            required=False,
            default=1000,
            validator=lambda x: x > 0,
        )

        param_manager.define_parameter(
            name="vacuum_size",
            description="Size of the vacuum in Angstrom",
            param_type=float,
            required=False,
            default=10.0,
            validator=lambda x: x >= 0,
        )

        # Get parameters
        params = param_manager.get_parameters()
        if not params:
            return {"status": False, "message": "No parameters provided."}

        # Convert formula to composition
        try:
            comp = Composition(params.get("formula", "H2O"), sort_by=None)
            composition_dict = {
                el: int(count) for el, count in comp.composition.items()
            }
        except Exception as e:
            return {"status": False, "message": f"Invalid chemical formula: {str(e)}"}

        # Generate structure using simple random placement
        # For now, use a simple approach: place atoms randomly with minimum distance constraint
        import random

        random.seed(42)  # For reproducibility

        species_list = []
        for element, count in composition_dict.items():
            species_list.extend([element] * count)

        positions = []
        min_distance = float(params.get("min_distance", 1.0))
        max_attempts = int(params.get("max_attempts", 1000))

        # Generate random positions with minimum distance constraint
        for i, species in enumerate(species_list):
            attempts = 0
            while attempts < max_attempts:
                # Random position in a 10x10x10 box
                pos = [
                    random.uniform(0, 10),
                    random.uniform(0, 10),
                    random.uniform(0, 10),
                ]

                # Check minimum distance from existing atoms
                valid = True
                for existing_pos in positions:
                    dist = np.linalg.norm(np.array(pos) - np.array(existing_pos))
                    if dist < min_distance:
                        valid = False
                        break

                if valid:
                    positions.append(pos)
                    break

                attempts += 1

            if attempts >= max_attempts:
                return {
                    "status": False,
                    "message": f"Failed to place atom {i+1} after {max_attempts} attempts. Try increasing max_attempts or decreasing min_distance.",
                }

        # Create molecule
        from matsimpy.core import Molecule

        structure = Molecule(species_list, positions)

        # Save structure
        output_dir = Path("configs")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        formula = params.get("formula", "H2O").replace(" ", "")
        output_file = output_dir / f"{formula}_{timestamp}.xyz"

        from matsimpy.io import write

        write(structure, str(output_file))
        print(f"Molecular structure created successfully with {len(structure)} atoms.")
        print(f"Saved to: {output_file}")

        return {
            "status": True,
            "message": f"Molecular structure created successfully with {len(structure)} atoms.",
            "data": structure,
        }

    except Exception as e:
        return {
            "status": False,
            "message": f"Error in molecular structure interface: {e}",
        }
