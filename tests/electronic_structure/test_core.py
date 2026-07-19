import numpy as np
import pytest
from monty.json import MontyDecoder

from matsimpy.electronic_structure import Magmom, Orbital, OrbitalType, Spin


def test_spin_and_orbital_values_match_vasp_conventions():
    assert int(Spin.up) == 1
    assert int(Spin.down) == -1
    assert OrbitalType(0).name == "s"
    assert Orbital(0).name == "s"
    assert Orbital(1).name == "py"


def test_magmom_scalar_vector_and_monty_roundtrip():
    assert np.allclose(Magmom(2.5).moment, [0.0, 0.0, 2.5])
    vector = Magmom([1, 2, 3])
    assert np.allclose(vector.moment, [1, 2, 3])
    restored = MontyDecoder().process_decoded(vector.as_dict())
    assert restored == vector


def test_magmom_rejects_non_vector_values():
    with pytest.raises(ValueError, match="scalar or length-3 vector"):
        Magmom([1, 2])


@pytest.mark.requires_pymatgen
def test_enum_values_match_pymatgen_2025_6_14():
    pytest.importorskip("pymatgen")
    from pymatgen.electronic_structure.core import Orbital as POrbital
    from pymatgen.electronic_structure.core import Spin as PSpin

    assert {item.name: int(item) for item in Spin} == {item.name: int(item) for item in PSpin}
    assert {item.name: int(item) for item in Orbital} == {item.name: int(item) for item in POrbital}
