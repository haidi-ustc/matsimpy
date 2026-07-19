"""Core electronic-structure types."""

from matsimpy.electronic_structure.core import Magmom, Orbital, OrbitalType, Spin
from matsimpy.electronic_structure.bandstructure import BandStructure, BandStructureSymmLine, Kpoint, get_reconstructed_band_structure
from matsimpy.electronic_structure.dos import CompleteDos, Dos
from matsimpy.electronic_structure.entries import ComputedEntry, ComputedStructureEntry


def decode_legacy_pymatgen_dict(data):
    """Decode a supported legacy pymatgen result dictionary."""
    from matsimpy.electronic_structure.legacy import decode_legacy_pymatgen_dict as decode

    return decode(data)

__all__ = ["BandStructure", "BandStructureSymmLine", "CompleteDos", "ComputedEntry", "ComputedStructureEntry", "Dos", "Kpoint", "Magmom", "Orbital", "OrbitalType", "Spin", "decode_legacy_pymatgen_dict", "get_reconstructed_band_structure"]
