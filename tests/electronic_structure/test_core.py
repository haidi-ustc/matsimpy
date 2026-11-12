import numpy as np
import pytest
from monty.json import MontyDecoder

from matsimpy.electronic_structure import Magmom, Orbital, OrbitalType, Spin
from matsimpy.io.errors import ParseError


def test_native_enum_member_values_match_vasp_conventions():
    assert {item.name: int(item) for item in Spin} == {"up": 1, "down": -1}
    assert {item.name: int(item) for item in OrbitalType} == {"s": 0, "p": 1, "d": 2, "f": 3}
    assert {item.name: int(item) for item in Orbital} == {
        "s": 0, "py": 1, "pz": 2, "px": 3,
        "dxy": 4, "dyz": 5, "dz2": 6, "dxz": 7, "dx2": 8,
        "f_3": 9, "f_2": 10, "f_1": 11, "f0": 12,
        "f1": 13, "f2": 14, "f3": 15,
    }


def test_native_parse_error_inheritance_and_vasp_primitive_identity():
    from matsimpy.calculator.vasp import inputs, outputs

    assert issubclass(ParseError, ValueError)
    assert issubclass(outputs.VaspParseError, ParseError)
    assert inputs.Magmom is Magmom
    assert outputs.Magmom is Magmom
    assert outputs.Orbital is Orbital
    assert outputs.OrbitalType is OrbitalType
    assert outputs.Spin is Spin


def test_magmom_scalar_vector_and_monty_roundtrip():
    scalar = Magmom(2.5)
    assert np.allclose(scalar.moment, [0.0, 0.0, 2.5])
    assert MontyDecoder().process_decoded(scalar.as_dict()) == scalar
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
    from importlib.metadata import version

    if version("pymatgen") != "2025.6.14":
        pytest.skip("enum parity is pinned to pymatgen==2025.6.14 (extra 'parity')")
    from pymatgen.electronic_structure.core import Orbital as POrbital
    from pymatgen.electronic_structure.core import OrbitalType as POrbitalType
    from pymatgen.electronic_structure.core import Spin as PSpin

    assert {item.name: int(item) for item in Spin} == {item.name: int(item) for item in PSpin}
    assert {item.name: int(item) for item in Orbital} == {item.name: int(item) for item in POrbital}
    assert {item.name: int(item) for item in OrbitalType} == {
        item.name: item.value for item in POrbitalType
    }
