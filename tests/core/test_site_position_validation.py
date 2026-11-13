"""Tests for Site and CrystalSite position validation."""

import warnings

import numpy as np
import pytest

from matsimpy.core import Lattice
from matsimpy.core.site import CrystalSite, Site


def test_very_large_position_warns():
    with pytest.warns(UserWarning):
        Site([1.1e6, 0, 0], "C")


@pytest.mark.parametrize("position", [
    "invalid",
    123,
    ["a", "b", "c"],
    [1, 2, "three"],
    [True, 0, 0],
    np.array([True, False, False]),
])
def test_non_numeric_positions_raise(position):
    with pytest.raises(TypeError):
        Site(position, "C")


def test_infinite_fractional_position_raises():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        with pytest.raises(ValueError):
            CrystalSite([np.inf, 0.5, 0.5], "Si", Lattice.cubic(10.0))


def test_from_dict_validates_the_position():
    d = {"@module": "matsimpy.core.site", "@class": "Site", "position": [0, 0, 0],
         "specie": "C", "properties": {}}
    assert Site.from_dict(d).specie == "C"
    with pytest.raises(ValueError):
        Site.from_dict({**d, "position": [np.nan, 0, 0]})
