import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the modules you want to test
from matsimpy.core import Composition, Crystal, Lattice, Molecule, Structure

