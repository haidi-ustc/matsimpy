import unittest

from matsimpy.core import Composition


class TestCompositionParserNested(unittest.TestCase):

    def test_mismatched_grouping_raises(self):
        with self.assertRaises(ValueError):
            Composition("Ca(OH]2")

    def test_unbalanced_grouping_raises(self):
        with self.assertRaises(ValueError):
            Composition("Ca(OH2")

    def test_unexpected_number_raises(self):
        with self.assertRaises(ValueError):
            Composition("2H")

    def test_zero_group_multiplier_raises(self):
        with self.assertRaises(ValueError):
            Composition("Ca(OH)0")

    def test_leading_zero_count_raises(self):
        with self.assertRaises(ValueError):
            Composition("H02")

