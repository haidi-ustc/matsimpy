import pytest

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


def test_magmom_is_an_immutable_sequence_and_scalar():
    scalar = Magmom(2.5)
    vector = Magmom([1, 2, 3])
    assert tuple(vector) == (1.0, 2.0, 3.0)
    assert vector[1] == 2.0
    assert float(scalar) == 2.5
    with pytest.raises(TypeError):
        float(vector)


def test_magmom_rejects_direct_component_assignment():
    magmom = Magmom([1, 2, 3])

    with pytest.raises(AttributeError, match="Magmom is immutable"):
        magmom.components = (4.0, 5.0, 6.0)


def test_magmom_mson_roundtrip():
    original = Magmom([1, 2, 3])
    restored = Magmom.from_dict(original.as_dict())
    assert restored == original
    assert repr(restored) == "Magmom([1.0, 2.0, 3.0])"


@pytest.mark.parametrize("value", [[], [1, 2], [1, 2, 3, 4]])
def test_magmom_rejects_invalid_component_counts(value):
    with pytest.raises(ValueError):
        Magmom(value)
