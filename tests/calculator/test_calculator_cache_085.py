"""0.8.5: calculator-side result cache keyed by the structure's exact fingerprint."""

import warnings

import numpy as np
import pytest

from matsimpy.calculator import LennardJones
from matsimpy.calculator.base import Calculator
from matsimpy.core import Crystal, Lattice, Molecule


class CountingLJ(LennardJones):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.n_compute = 0

    def _calculate(self, structure):
        self.n_compute += 1
        return super()._calculate(structure)


def _ar(a=5.3):
    return Crystal(["Ar", "Ar"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(a))


def test_results_are_cached_per_structure_and_recomputed_on_change():
    calc = CountingLJ(sigma=3.4, epsilon=0.0104)
    a, b = _ar(), _ar(5.6)
    ea = calc.get_potential_energy(a)
    calc.get_forces(a)
    calc.get_stress(a, voigt=True)
    assert calc.n_compute == 1
    eb = calc.get_potential_energy(b)
    assert calc.n_compute == 2 and eb != ea
    # 0.8.7: LRU cache keeps both structures -> switching back is free
    assert calc.get_potential_energy(a) == ea and calc.n_compute == 2
    # an equal copy shares the fingerprint -> no recomputation
    assert calc.get_potential_energy(a.copy()) == ea and calc.n_compute == 2


def test_cache_key_includes_site_properties_and_pbc():
    calc = CountingLJ(sigma=3.4, epsilon=0.0104)
    a = _ar()
    calc.get_potential_energy(a)
    calc.get_potential_energy(a.with_site_properties([{"magmom": 1.0}, {"magmom": 0.0}]))
    calc.get_potential_energy(a.set_pbc([True, True, False]))
    assert calc.n_compute == 3


def test_results_as_dict_returns_independent_copies():
    calc = LennardJones(sigma=3.4, epsilon=0.0104)
    m = Molecule(["Ar", "Ar"], [[0, 0, 0], [3.6, 0, 0]])
    r = calc.compute(m).as_dict()
    r["forces"][0, 0] = 1e9
    r["energy"] = 0.0
    assert calc.get_forces(m)[0, 0] != 1e9
    assert calc.get_potential_energy(m) != 0.0


def test_structures_no_longer_carry_calculators():
    """Attachment API (deprecated in 0.8.5) removed in 0.8.6."""
    a = _ar()
    for name in ("calc", "get_potential_energy", "get_forces", "get_stress"):
        assert not hasattr(a, name)
    with pytest.raises(AttributeError, match="calc.get_potential_energy"):
        a.calc = LennardJones()  # must fail loudly, not create a silent attribute


def test_structure_argument_must_be_a_structure():
    calc = LennardJones(sigma=3.4, epsilon=0.0104)
    with pytest.raises(TypeError):
        calc.get_stress(True)  # not a structure
    with pytest.raises(TypeError):
        calc.get_stress(voigt=True)  # 0.9.0: the structure is required (no "last structure")
    assert calc.get_stress(_ar(), voigt=True).shape == (6,)
    assert calc.get_stress(_ar(), voigt=False).shape == (3, 3)


def test_get_valid_magmom_struct_never_mutates_input():
    from matsimpy.calculator.vasp.sets import get_valid_magmom_struct

    c = _ar().with_site_properties([{"magmom": 1}, {}])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = get_valid_magmom_struct(c)
    assert [p["magmom"] for p in out.site_properties] == [1.0, 1.0]
    assert c.site_properties[1] == {}
    with pytest.raises(TypeError):
        get_valid_magmom_struct(c, inplace=False)


def test_substitute_is_shared_and_keeps_cartesian_bit_exact():
    lat = Lattice([[4.1, 0.3, 0.0], [0.2, 4.7, 0.0], [0.1, 0.4, 5.9]])
    c = Crystal(["Fe", "O"], [[0.123456789, 1.1, 2.2], [3.3, 0.7, 4.4]], lat, coords_are_cartesian=True)
    assert "substitute" not in Crystal.__dict__ and "substitute" not in Molecule.__dict__
    for new in (c.substitute(0, "Co"), c.substitute_all("O", "S")):
        assert np.array_equal(new.cart_positions, c.cart_positions)
        assert np.array_equal(new.frac_positions, c.frac_positions)
    assert isinstance(Calculator, type)
