import builtins

import numpy as np
import pytest

from matsimpy.core import Crystal, Lattice
from matsimpy.electronic_structure import ComputedStructureEntry, Dos, Spin
from matsimpy.electronic_structure.legacy import decode_legacy_pymatgen_dict


def test_decode_legacy_spin_dos_dictionary_without_importing_pymatgen(monkeypatch):
    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "pymatgen" or name.startswith("pymatgen."):
            raise AssertionError("legacy decoding must not import pymatgen")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    data = {
        "@module": "pymatgen.electronic_structure.dos",
        "@class": "Dos",
        "efermi": 0.0,
        "energies": [-1, 1],
        "densities": {"1": [2, 3]},
    }
    decoded = decode_legacy_pymatgen_dict(data)
    assert isinstance(decoded, Dos)
    assert np.array_equal(decoded.densities[Spin.up], [2, 3])


def test_unsupported_legacy_object_has_targeted_error():
    with pytest.raises(
        NotImplementedError,
        match=r"^unsupported legacy pymatgen object: pymatgen\.core\.periodic_table\.Element$",
    ):
        decode_legacy_pymatgen_dict(
            {
                "@module": "pymatgen.core.periodic_table",
                "@class": "Element",
                "element": "Si",
            }
        )


def test_decode_legacy_computed_structure_entry_with_nested_structure():
    structure = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(2))
    data = ComputedStructureEntry(structure, -1.5).as_dict()
    data["@module"] = "pymatgen.core.entries"
    data["structure"] = {
        "@module": "pymatgen.core.structure",
        "@class": "Structure",
        "lattice": {"matrix": structure.lattice.matrix.tolist(), "pbc": [True] * 3},
        "sites": [{"species": [{"element": "Si", "occu": 1}], "abc": [0, 0, 0], "properties": {}}],
    }

    decoded = decode_legacy_pymatgen_dict(data)
    assert isinstance(decoded, ComputedStructureEntry)
    assert decoded.structure == structure
