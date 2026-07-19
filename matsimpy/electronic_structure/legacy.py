"""Explicit decoding for the pymatgen result dictionaries MatSimPy supports."""

from matsimpy.calculator.vasp.outputs import Chgcar, Elfcar, Locpot, VolumetricData
from matsimpy.core import Crystal, Lattice, Trajectory
from matsimpy.electronic_structure.bandstructure import BandStructure, BandStructureSymmLine
from matsimpy.electronic_structure.dos import CompleteDos, Dos
from matsimpy.electronic_structure.core import Orbital, OrbitalType
from matsimpy.electronic_structure.entries import ComputedEntry, ComputedStructureEntry


_SUPPORTED = {
    ("pymatgen.electronic_structure.dos", "Dos"): Dos,
    ("pymatgen.electronic_structure.dos", "CompleteDos"): CompleteDos,
    ("pymatgen.electronic_structure.bandstructure", "BandStructure"): BandStructure,
    ("pymatgen.electronic_structure.bandstructure", "BandStructureSymmLine"): BandStructureSymmLine,
    ("pymatgen.entries.computed_entries", "ComputedEntry"): ComputedEntry,
    ("pymatgen.entries.computed_entries", "ComputedStructureEntry"): ComputedStructureEntry,
    ("pymatgen.core.entries", "ComputedEntry"): ComputedEntry,
    ("pymatgen.core.entries", "ComputedStructureEntry"): ComputedStructureEntry,
    ("pymatgen.core.trajectory", "Trajectory"): Trajectory,
    ("pymatgen.io.common", "VolumetricData"): VolumetricData,
    ("pymatgen.io.vasp.outputs", "VolumetricData"): VolumetricData,
    ("pymatgen.io.vasp.outputs", "Chgcar"): Chgcar,
    ("pymatgen.io.vasp.outputs", "Locpot"): Locpot,
    ("pymatgen.io.vasp.outputs", "Elfcar"): Elfcar,
}


def decode_legacy_pymatgen_dict(data):
    """Decode one supported pymatgen MSON dictionary without importing pymatgen."""
    if not isinstance(data, dict):
        raise TypeError("legacy pymatgen data must be a dictionary")
    module = data.get("@module")
    class_name = data.get("@class")
    key = (module, class_name)
    try:
        result_type = _SUPPORTED[key]
    except KeyError:
        raise NotImplementedError(
            f"unsupported legacy pymatgen object: {module}.{class_name}"
        ) from None
    if result_type is ComputedEntry:
        return ComputedEntry(
            data["composition"], data["energy"], data.get("correction", 0),
            data.get("parameters"), data.get("data"), data.get("entry_id"),
        )
    if result_type is ComputedStructureEntry:
        return ComputedStructureEntry(
            _decode_structure(data["structure"]), data["energy"],
            data.get("correction", 0), data.get("parameters"), data.get("data"),
            data.get("entry_id"),
        )
    if result_type in (BandStructure, BandStructureSymmLine):
        lattice_data = data["lattice_rec"]
        lattice = Lattice(lattice_data.get("matrix", lattice_data.get("lattice_vectors")))
        structure = _decode_structure(data["structure"]) if data.get("structure") else None
        return result_type(
            data["kpoints"], data["bands"], lattice, data["efermi"],
            {key.strip(): value for key, value in data.get("labels_dict", {}).items()},
            structure=structure, projections=data.get("projections"),
        )
    if result_type is CompleteDos:
        structure = _decode_structure(data["structure"])
        total = Dos(data["efermi"], data["energies"], data["densities"])
        pdos = []
        for orbital_map in data["pdos"]:
            values = {}
            for name, densities in orbital_map.items():
                density_map = densities.get("densities", densities)
                try:
                    orbital = Orbital[name]
                except KeyError:
                    orbital = OrbitalType[name]
                values[orbital] = density_map
            pdos.append(values)
        return CompleteDos(structure, total, pdos)
    if result_type is Trajectory and "coords" in data:
        lattice_data = data["lattice"]
        lattices = [lattice_data] * len(data["coords"]) if data.get("constant_lattice") else lattice_data
        species = [_species_symbol(value) for value in data["species"]]
        frames = [
            Crystal(species, coords, Lattice(lattice), pbc=[True] * 3)
            for coords, lattice in zip(data["coords"], lattices)
        ]
        return Trajectory(frames, constant_lattice=data.get("constant_lattice", False))
    if result_type is Trajectory:
        frames = [item.get("structure", item) for item in data["frames"]]
        return Trajectory(
            [_decode_structure(frame) for frame in frames],
            constant_lattice=data.get("constant_lattice", False),
        )
    if issubclass(result_type, VolumetricData):
        normalized = dict(data)
        normalized["structure"] = _decode_structure(data["structure"])
        return result_type.from_dict(normalized)
    return result_type.from_dict(data)


def _species_symbol(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("element") or value.get("label") or value.get("@class")
    return str(value)


def _decode_structure(data):
    if isinstance(data, Crystal):
        return data
    if "sites" in data:
        lattice_data = data["lattice"]
        lattice = Lattice(lattice_data.get("matrix", lattice_data.get("lattice_vectors")))
        species = []
        positions = []
        properties = []
        for site in data["sites"]:
            site_species = site["species"]
            if isinstance(site_species, list):
                site_species = site_species[0]
            species.append(_species_symbol(site_species))
            positions.append(site.get("abc", site.get("frac_coords")))
            properties.append(site.get("properties", {}))
        return Crystal(species, positions, lattice, pbc=lattice_data.get("pbc", [True] * 3), site_properties=properties)
    return Crystal.from_dict(data)


__all__ = ["decode_legacy_pymatgen_dict"]
