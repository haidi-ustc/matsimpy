from matsimpy.electronic_structure import Magmom, Orbital, OrbitalType, Spin


def test_vasp_enum_values_and_names():
    assert Spin.up.value == 1
    assert Spin.down.value == -1
    assert Orbital(8) is Orbital.dx2
    assert Orbital.__members__["f_3"] is Orbital.f_3
    assert OrbitalType(2) is OrbitalType.d


def test_magmom_accepts_scalar_and_vector():
    assert Magmom(2.5).components == (2.5,)
    assert Magmom([1, 2, 3]).components == (1.0, 2.0, 3.0)
