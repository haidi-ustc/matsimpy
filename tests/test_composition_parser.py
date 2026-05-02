import unittest

from matsimpy.core import Composition


class TestCompositionParserNested(unittest.TestCase):
    def test_nested_brackets_and_parentheses(self):
        # K4[ON(SO3)2]2
        # Inside []: O1 N1 (SO3)2 -> S2 O6 => O7 total
        # times 2 => O14 N2 S4, plus K4
        comp = Composition("K4[ON(SO3)2]2")
        self.assertEqual(comp["K"], 4)
        self.assertEqual(comp["O"], 14)
        self.assertEqual(comp["N"], 2)
        self.assertEqual(comp["S"], 4)

    def test_mismatched_grouping_raises(self):
        with self.assertRaises(ValueError):
            Composition("Ca(OH]2")

    def test_unbalanced_grouping_raises(self):
        with self.assertRaises(ValueError):
            Composition("Ca(OH2")

    def test_unexpected_number_raises(self):
        with self.assertRaises(ValueError):
            Composition("2H")

    def test_zero_element_count_raises(self):
        with self.assertRaises(ValueError):
            Composition("H0")

    def test_zero_group_multiplier_raises(self):
        with self.assertRaises(ValueError):
            Composition("Ca(OH)0")

    def test_leading_zero_count_raises(self):
        with self.assertRaises(ValueError):
            Composition("H02")

    def test_transactinide_formula_from_periodic_table_json(self):
        comp = Composition("Og")
        self.assertEqual(comp["Og"], 1)
        self.assertEqual(comp.formula, "Og")
