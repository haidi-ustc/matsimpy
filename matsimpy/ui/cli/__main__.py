#!/usr/bin/env python3
"""
MatSimPy CLI Entry Point

This module provides the main entry point for the MatSimPy interactive CLI.
"""
import sys
import os
from pathlib import Path

def main():
    """Main CLI entry point for MatSimPy."""
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
    
    # Import and run the menu
    from matsimpy.ui.cli.menu import AdvancedInteractiveMenu
    
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

