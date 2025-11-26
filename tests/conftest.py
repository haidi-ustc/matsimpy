"""
Pytest configuration file.

This file is automatically loaded by pytest and sets up the test environment.
It ensures the matsimpy package is importable by adding the parent directory
to sys.path. This eliminates the need for sys.path.insert in individual test files.
"""
import sys
import os

# Add the parent directory to the path so matsimpy can be imported
# This is only needed if the package is not installed in development mode
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

