import os
from datetime import datetime
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import json

from matsimpy.ui.cli.parameter_manager import CLIParameterManager, ParameterDefinition


# Interface codes for menu registration
STRUCTURE_SEARCH_INTERFACE_CODE = "[z111]"
PROPERTY_SEARCH_INTERFACE_CODE = "[z112]"
PHASE_DIAGRAM_SEARCH_INTERFACE_CODE = "[z113]"


def _validate_api_key() -> bool:
    """Validate Materials Project API key."""
    api_key = os.getenv("MP_API_KEY")
    return api_key is not None and len(api_key) > 10


def _validate_elements(elements_str: str) -> bool:
    """Validate elements format."""
    try:
        from matsimpy.core import Element

        if "," in elements_str:
            elements = [el.strip() for el in elements_str.split(",")]
        else:
            elements = elements_str.split()

        for element in elements:
            if element:
                Element.get_element(element)  # Use matsimpy's Element API
        return True
    except:
        return False


def _parse_elements(elements_str: str) -> List[str]:
    """Parse elements from string."""
    if "," in elements_str:
        return [el.strip() for el in elements_str.split(",") if el.strip()]
    return [el.strip() for el in elements_str.split() if el.strip()]


def structure_search(style: Optional[str] = None) -> None:
    """
    Materials Project structure search interface.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Check API key first
        if not _validate_api_key():
            print("Error: MP_API_KEY environment variable not found.")
            print("Please set your Materials Project API key:")
            print("export MP_API_KEY='your_api_key_here'")
            print("Get your key at: https://materialsproject.org/api")
            return

        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Simple search parameters
        param_manager.define_parameter(
            name="query",
            description="Search query (elements: 'Si O', material ID: 'mp-149', formula: 'SiO2')",
            param_type=str,
            required=True,
            default="Si O",
        )

        param_manager.define_parameter(
            name="max_results",
            description="Maximum number of results",
            param_type=int,
            required=False,
            default=10,
            validator=lambda x: 1 <= x <= 100,
        )

        # Get parameters
        params = param_manager.get_parameters()
        if not params:
            return

        # Import MP API
        try:
            from mp_api.client import MPRester
        except ImportError:
            print("Error: mp-api package not installed.")
            print("Please install it with: pip install mp-api")
            return

        print(f"\n=== Materials Project Structure Search ===")
        query = params["query"].strip()
        max_results = params["max_results"]

        # Auto-detect query type
        search_params = {
            "fields": ["structure", "material_id", "formula_pretty", "band_gap"]
        }

        if query.startswith(("mp-", "mvc-")):
            # Material ID search
            search_params["material_ids"] = [query]
            print(f"Searching by material ID: {query}")
        elif any(char.isdigit() for char in query) and not any(
            char.isalpha() for char in query.replace("-", "")
        ):
            # Likely a material ID without mp- prefix
            query = f"mp-{query}" if not query.startswith("mp-") else query
            search_params["material_ids"] = [query]
            print(f"Searching by material ID: {query}")
        elif _validate_elements(query):
            # Elements search
            elements = _parse_elements(query)
            search_params["elements"] = elements
            print(f"Searching by elements: {elements}")
        else:
            # Try formula search
            search_params["formula"] = query
            print(f"Searching by formula: {query}")

        # Perform search
        api_key = os.getenv("MP_API_KEY")
        print(f"Connecting to Materials Project...")

        with MPRester(api_key) as mpr:
            try:
                docs = mpr.materials.summary.search(**search_params)
                docs = docs[:max_results]

                print(f"Found {len(docs)} materials")

                if not docs:
                    print("No materials found. Try different search terms.")
                    return

                # Display results
                print(f"\n=== Search Results ===")
                for i, doc in enumerate(docs, 1):
                    print(f"\n{i}. {doc.material_id}")
                    print(f"   Formula: {getattr(doc, 'formula_pretty', 'N/A')}")
                    if hasattr(doc, "band_gap") and doc.band_gap is not None:
                        print(f"   Band gap: {doc.band_gap:.3f} eV")

                    if hasattr(doc, "structure") and doc.structure is not None:
                        structure = doc.structure
                        print(f"   Atoms: {len(structure)}")
                        print(f"   Space group: {structure.get_space_group_info()[1]}")

                # Save structures
                save_option = (
                    input(f"\nSave structures to files? (y/n): ").strip().lower()
                )
                if save_option == "y":
                    output_dir = Path("mp_structures")
                    output_dir.mkdir(exist_ok=True)

                    saved_count = 0
                    for doc in docs:
                        if hasattr(doc, "structure") and doc.structure is not None:
                            filename = f"{doc.material_id}.cif"
                            filepath = output_dir / filename
                            doc.structure.to(filename=str(filepath), fmt="cif")
                            saved_count += 1

                    print(f"Saved {saved_count} structures to {output_dir}/")

                print(f"\n=== Search Complete ===")

            except Exception as e:
                print(f"Search error: {str(e)}")
                return

    except Exception as e:
        print(f"Error: {str(e)}")
        return


def property_search(style: Optional[str] = None) -> None:
    """
    Materials Project property search interface.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Check API key first
        if not _validate_api_key():
            print("Error: MP_API_KEY environment variable not found.")
            print("Please set your Materials Project API key:")
            print("export MP_API_KEY='your_api_key_here'")
            return

        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Simple property search parameters
        param_manager.define_parameter(
            name="elements",
            description="Elements (e.g., 'Si O')",
            param_type=str,
            required=True,
            default="Si O",
            validator=_validate_elements,
        )

        param_manager.define_parameter(
            name="band_gap_min",
            description="Minimum band gap (eV, leave empty for no limit)",
            param_type=str,
            required=False,
            default="0.5",
        )

        param_manager.define_parameter(
            name="band_gap_max",
            description="Maximum band gap (eV, leave empty for no limit)",
            param_type=str,
            required=False,
            default="2.0",
        )

        param_manager.define_parameter(
            name="stable_only",
            description="Only stable materials (True/False)",
            param_type=bool,
            required=False,
            default=True,
        )

        param_manager.define_parameter(
            name="max_results",
            description="Maximum number of results",
            param_type=int,
            required=False,
            default=20,
            validator=lambda x: 1 <= x <= 100,
        )

        # Get parameters
        params = param_manager.get_parameters()
        if not params:
            return

        # Import MP API
        try:
            from mp_api.client import MPRester
        except ImportError:
            print("Error: mp-api package not installed.")
            print("Please install it with: pip install mp-api")
            return

        print(f"\n=== Materials Project Property Search ===")

        # Parse parameters
        elements = _parse_elements(params["elements"])
        stable_only = params["stable_only"]
        max_results = params["max_results"]

        # Prepare search parameters
        search_params = {
            "elements": elements,
            "fields": [
                "material_id",
                "formula_pretty",
                "band_gap",
                "formation_energy_per_atom",
                "energy_above_hull",
            ],
        }

        # Add band gap filter
        band_gap_range = []
        if params["band_gap_min"]:
            try:
                band_gap_range.append(float(params["band_gap_min"]))
            except:
                band_gap_range.append(0.0)
        else:
            band_gap_range.append(0.0)

        if params["band_gap_max"]:
            try:
                band_gap_range.append(float(params["band_gap_max"]))
            except:
                band_gap_range.append(10.0)
        else:
            band_gap_range.append(10.0)

        if len(band_gap_range) == 2:
            search_params["band_gap"] = tuple(band_gap_range)

        # Add stability filter
        if stable_only:
            search_params["energy_above_hull"] = (0, 0.01)  # Very stable materials

        print(f"Elements: {elements}")
        print(f"Band gap: {band_gap_range[0]:.1f} - {band_gap_range[1]:.1f} eV")
        print(f"Stable only: {stable_only}")

        # Perform search
        api_key = os.getenv("MP_API_KEY")
        print(f"Connecting to Materials Project...")

        with MPRester(api_key) as mpr:
            try:
                docs = mpr.materials.summary.search(**search_params)
                docs = docs[:max_results]

                print(f"Found {len(docs)} materials")

                if not docs:
                    print("No materials found. Try broader search criteria.")
                    return

                # Display results in table format
                print(f"\n=== Property Search Results ===")
                print(
                    f"{'ID':<12} {'Formula':<15} {'Band Gap':<10} {'Form. E':<10} {'E Hull':<8}"
                )
                print("-" * 65)

                for doc in docs:
                    material_id = doc.material_id
                    formula = getattr(doc, "formula_pretty", "N/A")
                    band_gap = (
                        f"{doc.band_gap:.3f}"
                        if hasattr(doc, "band_gap") and doc.band_gap is not None
                        else "N/A"
                    )
                    form_energy = (
                        f"{doc.formation_energy_per_atom:.3f}"
                        if hasattr(doc, "formation_energy_per_atom")
                        and doc.formation_energy_per_atom is not None
                        else "N/A"
                    )
                    e_hull = (
                        f"{doc.energy_above_hull:.3f}"
                        if hasattr(doc, "energy_above_hull")
                        and doc.energy_above_hull is not None
                        else "N/A"
                    )

                    print(
                        f"{material_id:<12} {formula:<15} {band_gap:<10} {form_energy:<10} {e_hull:<8}"
                    )

                # Save results
                output_dir = Path("mp_properties")
                output_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                results_file = output_dir / f"property_search_{timestamp}.json"

                results_data = {
                    "search_elements": elements,
                    "band_gap_range": band_gap_range,
                    "stable_only": stable_only,
                    "num_results": len(docs),
                    "results": [],
                }

                for doc in docs:
                    result_data = {"material_id": doc.material_id}
                    for field in [
                        "formula_pretty",
                        "band_gap",
                        "formation_energy_per_atom",
                        "energy_above_hull",
                    ]:
                        if hasattr(doc, field):
                            value = getattr(doc, field)
                            if value is not None:
                                result_data[field] = value
                    results_data["results"].append(result_data)

                with open(results_file, "w") as f:
                    json.dump(results_data, f, indent=2)

                print(f"\n=== Search Complete ===")
                print(f"Results saved to: {results_file}")

            except Exception as e:
                print(f"Search error: {str(e)}")
                return

    except Exception as e:
        print(f"Error: {str(e)}")
        return


def phase_diagram_search(style: Optional[str] = None) -> None:
    """
    Materials Project phase diagram search interface.

    Args:
        style: Optional style parameter for parameter manager
    """
    try:
        # Check API key first
        if not _validate_api_key():
            print("Error: MP_API_KEY environment variable not found.")
            print("Please set your Materials Project API key:")
            print("export MP_API_KEY='your_api_key_here'")
            return

        # Initialize parameter manager
        param_manager = CLIParameterManager(style=style)

        # Simple phase diagram parameters
        param_manager.define_parameter(
            name="elements",
            description="Elements for phase diagram (e.g., 'Li Fe P O')",
            param_type=str,
            required=True,
            default="Li Fe P O",
            validator=_validate_elements,
        )

        param_manager.define_parameter(
            name="save_plot",
            description="Save phase diagram plot (True/False)",
            param_type=bool,
            required=False,
            default=True,
        )

        # Get parameters
        params = param_manager.get_parameters()
        if not params:
            return

        # Import required packages
        try:
            from mp_api.client import MPRester

            # Note: Phase diagram plotting currently requires pymatgen
            # This is a Materials Project API dependency, not a matsimpy core feature
            try:
                from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
            except ImportError:
                print("Error: pymatgen required for phase diagram plotting.")
                print("Please install with: pip install pymatgen")
                print(
                    "Note: This is for Materials Project API integration, not matsimpy core."
                )
                return
        except ImportError:
            print("Error: Required packages not installed.")
            print("Please install with: pip install mp-api")
            print("For phase diagram plotting, also install: pip install pymatgen")
            return

        print(f"\n=== Materials Project Phase Diagram ===")

        # Parse elements
        elements = _parse_elements(params["elements"])
        save_plot = params["save_plot"]

        print(f"Elements: {elements}")

        if len(elements) > 5:
            print(
                "Warning: Phase diagrams with >5 elements are complex and may not display well."
            )

        # Perform search
        api_key = os.getenv("MP_API_KEY")
        print(f"Connecting to Materials Project...")

        with MPRester(api_key) as mpr:
            try:
                # Get phase diagram data
                print("Building phase diagram...")
                pd = mpr.get_phase_diagram_by_elements(elements)

                print(f"Phase diagram built with {len(pd.all_entries)} total phases")

                # Get stable phases
                stable_entries = pd.stable_entries
                print(f"Stable phases: {len(stable_entries)}")

                # Display stable phases
                print(f"\n=== Stable Phases ===")
                for i, entry in enumerate(stable_entries, 1):
                    material_id = getattr(entry, "entry_id", "N/A")
                    formula = entry.composition.reduced_formula
                    formation_energy = entry.energy_per_atom

                    print(
                        f"{i:2d}. {material_id:<12} {formula:<15} E={formation_energy:.3f} eV/atom"
                    )

                # Find metastable phases
                unstable_entries = [
                    e for e in pd.all_entries if e not in stable_entries
                ]
                metastable_entries = [
                    e for e in unstable_entries if pd.get_e_above_hull(e) <= 0.1
                ]

                if metastable_entries:
                    print(f"\n=== Metastable Phases (E_hull ≤ 0.1 eV/atom) ===")
                    for i, entry in enumerate(
                        metastable_entries[:10], 1
                    ):  # Show first 10
                        material_id = getattr(entry, "entry_id", "N/A")
                        formula = entry.composition.reduced_formula
                        e_hull = pd.get_e_above_hull(entry)

                        print(
                            f"{i:2d}. {material_id:<12} {formula:<15} E_hull={e_hull:.3f} eV/atom"
                        )

                    if len(metastable_entries) > 10:
                        print(
                            f"    ... and {len(metastable_entries) - 10} more metastable phases"
                        )

                # Generate phase diagram plot
                if (
                    save_plot and len(elements) <= 4
                ):  # Only plot for reasonable number of elements
                    try:
                        print(f"\nGenerating phase diagram plot...")
                        plotter = PDPlotter(pd)

                        output_dir = Path("mp_phase_diagrams")
                        output_dir.mkdir(exist_ok=True)

                        elements_str = "_".join(elements)
                        plot_file = output_dir / f"phase_diagram_{elements_str}.png"

                        plotter.get_plot().savefig(
                            plot_file, dpi=300, bbox_inches="tight"
                        )
                        print(f"Phase diagram saved: {plot_file}")

                    except Exception as e:
                        print(f"Could not generate plot: {str(e)}")

                # Save phase data
                output_dir = Path("mp_phase_diagrams")
                output_dir.mkdir(exist_ok=True)

                elements_str = "_".join(elements)
                data_file = output_dir / f"phase_data_{elements_str}.json"

                phase_data = {
                    "elements": elements,
                    "num_stable_phases": len(stable_entries),
                    "num_metastable_phases": len(metastable_entries),
                    "stable_phases": [],
                    "metastable_phases": [],
                }

                for entry in stable_entries:
                    phase_data["stable_phases"].append(
                        {
                            "material_id": getattr(entry, "entry_id", "N/A"),
                            "formula": entry.composition.reduced_formula,
                            "formation_energy_per_atom": entry.energy_per_atom,
                        }
                    )

                for entry in metastable_entries:
                    phase_data["metastable_phases"].append(
                        {
                            "material_id": getattr(entry, "entry_id", "N/A"),
                            "formula": entry.composition.reduced_formula,
                            "energy_above_hull": pd.get_e_above_hull(entry),
                        }
                    )

                with open(data_file, "w") as f:
                    json.dump(phase_data, f, indent=2)

                print(f"\n=== Phase Diagram Complete ===")
                print(f"Data saved: {data_file}")
                print(f"Stable phases: {len(stable_entries)}")
                print(f"Metastable phases: {len(metastable_entries)}")

            except Exception as e:
                print(f"Phase diagram error: {str(e)}")
                return

    except Exception as e:
        print(f"Error: {str(e)}")
        return
