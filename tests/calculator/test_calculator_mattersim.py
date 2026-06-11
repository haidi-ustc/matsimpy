"""Tests for MatterSim calculator.

Tests that do NOT require torch or MatterSim library run unconditionally.
Torch-dependent tests use @pytest.mark.requires_torch marker and skip gracefully.
"""

import pytest
import numpy as np
import unittest


class TestMattersimBasic(unittest.TestCase):
    """Tests that do NOT require torch or MatterSim library."""

    def test_import_without_torch(self):
        """Mattersim should be importable (lazy) even without torch."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            # Import should succeed — class may be None if torch missing
            self.assertTrue(Mattersim is not None)
        except ImportError:
            self.skipTest("mattersim subpackage not importable")

    def test_legacy_ml_import_path_aliases_mattersim(self):
        """The old matsimpy.calculator.ml path remains a compatibility alias."""
        from matsimpy.calculator.mattersim import Mattersim as canonical
        from matsimpy.calculator.ml import Mattersim as legacy

        self.assertIs(legacy, canonical)

    def test_default_init_no_model(self):
        """Mattersim with no model_path should initialize (lazy load)."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            calc = Mattersim()
            self.assertEqual(calc.device, "cpu")
            self.assertTrue(calc.run)
        except ImportError:
            self.skipTest("mattersim not importable")

    def test_run_parameter(self):
        """Mattersim should accept run parameter."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            calc = Mattersim(run=True)
            self.assertTrue(calc.run)
            calc2 = Mattersim(run=False)
            self.assertFalse(calc2.run)
        except ImportError:
            self.skipTest("mattersim not importable")

    def test_as_dict_no_model(self):
        """Serialization without loaded model (no model_path, no auto-load)."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            calc = Mattersim(device="cpu")
            d = calc.as_dict()
            self.assertIn("parameters", d)
            self.assertEqual(d["parameters"].get("device"), "cpu")
        except ImportError:
            self.skipTest("mattersim not importable")

    def test_calculate_requires_model(self):
        """calculate() without model should raise ValueError."""
        try:
            from matsimpy.calculator.mattersim import Mattersim
            from matsimpy.core import Crystal, Lattice

            crystal = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
            calc = Mattersim()
            with self.assertRaises(ValueError):
                calc.calculate(crystal)
        except ImportError:
            self.skipTest("mattersim not importable")


if __name__ == "__main__":
    unittest.main()
