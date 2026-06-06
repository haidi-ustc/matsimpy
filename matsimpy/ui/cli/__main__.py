#!/usr/bin/env python3
"""
MatSimPy CLI Entry Point

This module provides the main entry point for the MatSimPy interactive CLI.
"""
import sys
import os
from pathlib import Path


_CLI_EXTRA_HINT = (
    "MatSimPy interactive CLI requires the optional 'cli' dependencies. "
    "Install them with: pip install MatSimPy[cli]"
)


def main():
    """Main CLI entry point for MatSimPy."""
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print("Usage: matsimpy [path_to_menu.json]")
        print()
        print("Launch the MatSimPy interactive CLI.")
        print(_CLI_EXTRA_HINT)
        return

    # Try to find the menu JSON file
    # First, check if provided as argument
    json_file = None
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        if not os.path.exists(json_file):
            print(f"Error: JSON file '{json_file}' not found.")
            sys.exit(1)

    # If not provided, try to find it in common locations
    if json_file is None:
        # First, try to find it as package data (if installed)
        try:
            import pkg_resources

            json_file = pkg_resources.resource_filename(
                "matsimpy.ui.cli", "matsimpy_menu.json"
            )
            if not os.path.exists(json_file):
                json_file = None
        except (
            ImportError,
            pkg_resources.DistributionNotFound,
            pkg_resources.ResourceNotFound,
        ):
            json_file = None

        # If not found as package data, check other locations
        if json_file is None:
            # Check current directory
            current_dir_json = Path("matsimpy_menu.json")
            if current_dir_json.exists():
                json_file = str(current_dir_json)
            else:
                # Check in the package directory
                package_dir = Path(__file__).parent
                package_json = package_dir / "matsimpy_menu.json"
                if package_json.exists():
                    json_file = str(package_json)
                else:
                    # Check in parent directories
                    for parent in Path(__file__).parents:
                        parent_json = parent / "matsimpy_menu.json"
                        if parent_json.exists():
                            json_file = str(parent_json)
                            break

    if json_file is None:
        print("Error: Could not find matsimpy_menu.json file.")
        print("Please provide the path to the menu JSON file as an argument:")
        print("  matsimpy <path_to_menu.json>")
        print("\nOr ensure matsimpy_menu.json exists in:")
        print("  - Current directory")
        print("  - Package directory")
        sys.exit(1)

    # Import and run the menu. Keep this import guarded so a base install can
    # expose the console script without crashing on a missing optional extra.
    try:
        from matsimpy.ui.cli.menu import AdvancedInteractiveMenu
    except ModuleNotFoundError as e:
        if e.name and e.name.startswith("prompt_toolkit"):
            print(f"Error: {_CLI_EXTRA_HINT}", file=sys.stderr)
            sys.exit(2)
        raise

    try:
        menu = AdvancedInteractiveMenu(json_file)
        menu.run()
    except KeyboardInterrupt:
        print("\n\nThank you for using MatSimPy!")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
