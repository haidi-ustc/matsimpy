import builtins

import numpy as np
import pytest

from monty.json import MontyDecoder

from matsimpy.core import Composition, Crystal, Lattice, Trajectory
from matsimpy.calculator.vasp.outputs import Chgcar, Elfcar, Locpot, VolumetricData
from matsimpy.electronic_structure import (
    BandStructure, BandStructureSymmLine, CompleteDos, ComputedEntry,
    ComputedStructureEntry, Dos, Orbital, Spin,
)
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


def test_decode_legacy_computed_entry_preserves_fractional_composition_and_monty():
    data = {
        "@module": "pymatgen.core.entries",
        "@class": "ComputedEntry",
        "composition": {"Li": 0.5, "O": 1.25},
        "energy": -3.5,
        "correction": 0.25,
        "parameters": {"run_type": "GGA"},
        "data": {"oxidation": [1, -2]},
        "entry_id": "fractional",
    }

    decoded = decode_legacy_pymatgen_dict(data)

    assert type(decoded) is ComputedEntry
    assert type(decoded.composition) is Composition
    assert dict(decoded.composition.composition) == {"Li": 0.5, "O": 1.25}
    assert decoded.composition.reduced_formula == "Li2O5"
    assert decoded.energy_per_atom == pytest.approx(-3.25 / 1.75)
    restored = MontyDecoder().process_decoded(decoded.as_dict())
    assert type(restored) is ComputedEntry
    assert dict(restored.composition.composition) == {"Li": 0.5, "O": 1.25}


def test_decode_legacy_coords_trajectory_preserves_metadata_and_displacements():
    data = {
        "@module": "pymatgen.core.trajectory",
        "@class": "Trajectory",
        "species": [{"element": "Li"}],
        "coords": [[[0.0, 0.0, 0.0]], [[0.1, 0.0, 0.0]]],
        "lattice": [[3.0, 0, 0], [0, 3.0, 0], [0, 0, 3.0]],
        "site_properties": [{"magmom": [1.0]}, {"magmom": [2.0]}],
        "frame_properties": [{"energy": -1.0}, {"energy": -0.5}],
        "charge": 2,
        "spin_multiplicity": 3,
        "time_step": 2.5,
        "constant_lattice": True,
        "coords_are_displacement": True,
        "base_positions": [[0.25, 0.25, 0.25]],
    }

    decoded = decode_legacy_pymatgen_dict(data)

    assert type(decoded) is Trajectory
    assert decoded[0].frac_positions.tolist() == [[0.25, 0.25, 0.25]]
    assert decoded[1].frac_positions.tolist() == [[0.35, 0.25, 0.25]]
    assert decoded[1].site_properties == ({"magmom": 2.0},)
    assert decoded.frame_properties == ({"energy": -1.0}, {"energy": -0.5})
    assert decoded.charge == 2
    assert decoded.spin_multiplicity == 3
    assert decoded.time_step == 2.5
    assert decoded.coords_are_displacement is True
    assert np.array_equal(decoded.base_positions, [[0.25, 0.25, 0.25]])
    restored = MontyDecoder().process_decoded(decoded.as_dict())
    assert restored.frame_properties == decoded.frame_properties
    assert restored[1].site_properties == decoded[1].site_properties
    assert np.array_equal(restored.base_positions, decoded.base_positions)


def test_decode_legacy_frame_trajectory_preserves_frame_extras():
    structure = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(2))
    data = {
        "@module": "pymatgen.core.trajectory",
        "@class": "Trajectory",
        "frames": [
            {"structure": structure.as_dict(), "extra_properties": {"stress": [1, 2, 3]}},
            {"structure": structure.as_dict(), "energy": -2.0},
        ],
        "frame_properties": [{"step": 0}, {"step": 1}],
        "charge": -1,
        "spin": 0.5,
        "time_step": 1.0,
        "constant_lattice": True,
    }

    decoded = decode_legacy_pymatgen_dict(data)

    assert decoded[0]._extra_properties == {"stress": [1, 2, 3]}
    assert decoded[1]._extra_properties == {"energy": -2.0}
    assert decoded.frame_properties == ({"step": 0}, {"step": 1})
    assert decoded.charge == -1
    assert decoded.spin == 0.5


@pytest.mark.requires_pymatgen
def test_decode_actual_pinned_pymatgen_computed_entry_dictionary():
    pytest.importorskip("pymatgen")
    from pymatgen.core import Composition as PymatgenComposition
    from pymatgen.entries.computed_entries import ComputedEntry as PymatgenComputedEntry

    data = PymatgenComputedEntry(
        PymatgenComposition({"Li": 0.5, "O": 1.25}), -4.0, entry_id="oracle"
    ).as_dict()
    decoded = decode_legacy_pymatgen_dict(data)

    assert type(decoded) is ComputedEntry
    assert dict(decoded.composition.composition) == {"Li": 0.5, "O": 1.25}
    assert decoded.entry_id == "oracle"


def test_decode_supported_legacy_result_classes_exactly():
    structure = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(2))
    structure_data = structure.as_dict()
    pymatgen_structure = {
        "lattice": {"matrix": structure.lattice.matrix.tolist(), "pbc": [True] * 3},
        "sites": [{"species": [{"element": "Si", "occu": 1}], "abc": [0, 0, 0]}],
    }
    lattice_rec = {"matrix": Lattice.cubic(1).matrix.tolist()}
    band_payload = {
        "kpoints": [[0, 0, 0], [0.5, 0, 0]], "bands": {"1": [[-1, 1]]},
        "lattice_rec": lattice_rec, "efermi": 0, "labels_dict": {"G": [0, 0, 0]},
        "projections": {"1": [[[[1]], [[2]]]]}, "structure": pymatgen_structure,
    }
    complete_dos = {
        "efermi": 0, "energies": [-1, 1], "densities": {"1": [2, 3]},
        "structure": pymatgen_structure, "pdos": [{"s": {"densities": {"1": [1, 2]}}}],
    }
    volumetric = {"structure": structure_data, "data": {"total": np.ones((1, 1, 1)).tolist()}}
    cases = [
        ("pymatgen.electronic_structure.dos", "CompleteDos", complete_dos, CompleteDos),
        ("pymatgen.electronic_structure.bandstructure", "BandStructure", band_payload, BandStructure),
        ("pymatgen.electronic_structure.bandstructure", "BandStructureSymmLine", band_payload, BandStructureSymmLine),
        ("pymatgen.io.common", "VolumetricData", volumetric, VolumetricData),
        ("pymatgen.io.vasp.outputs", "Chgcar", volumetric, Chgcar),
        ("pymatgen.io.vasp.outputs", "Locpot", volumetric, Locpot),
        ("pymatgen.io.vasp.outputs", "Elfcar", volumetric, Elfcar),
    ]
    for module, name, payload, expected in cases:
        decoded = decode_legacy_pymatgen_dict({"@module": module, "@class": name, **payload})
        assert type(decoded) is expected
    decoded_band = decode_legacy_pymatgen_dict({
        "@module": cases[1][0], "@class": cases[1][1], **band_payload
    })
    assert decoded_band.kpoints[0].label == "G"
    assert Spin.up in decoded_band.projections
    decoded_dos = decode_legacy_pymatgen_dict({
        "@module": cases[0][0], "@class": cases[0][1], **complete_dos
    })
    assert Orbital.s in decoded_dos.pdos[decoded_dos.structure[0]]
