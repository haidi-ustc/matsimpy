import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matsimpy.core import Crystal
from matsimpy.core import Lattice
from matsimpy.core import Composition
from monty.serialization import dumpfn, loadfn



class TestCrystal(unittest.TestCase):

    def test_conversion(self):
        """Test the conversion of fractional and cartesian coordinates."""
        species = ['H', 'He']
        positions = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        lattice = Lattice.from_parameters(a=1.0, b=1.0, c=1.0, alpha=90, beta=90, gamma=90)

        crystal_frac = Crystal(species, positions, lattice)
        crystal_cart = Crystal(species, positions, lattice, coords_are_cartesian=True)

        # Check that converting from fractional to cartesian and back gives the same result
        np.testing.assert_array_almost_equal(
            crystal_frac._convert_to_fractional(),
            np.array(positions),
            decimal=6
        )
        np.testing.assert_array_almost_equal(
            crystal_frac._convert_to_cartesian(),
            crystal_cart.cart_positions,
            decimal=6
        )
        np.testing.assert_array_almost_equal(
            crystal_cart._convert_to_cartesian(),
            np.array(positions),
            decimal=6
        )
        np.testing.assert_array_almost_equal(
            crystal_cart._convert_to_fractional(),
            crystal_frac.frac_positions,
            decimal=6
        )

    def test_volume(self):
        """Test the calculation of the volume."""
        species = ['H', 'He']
        positions = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        lattice = Lattice.from_parameters(a=2.0, b=3.0, c=4.0, alpha=90, beta=90, gamma=90)

        crystal = Crystal(species, positions, lattice)

        self.assertAlmostEqual(crystal.volume, 24.0, places=6)


if __name__ == '__main__':
    unittest.main()

