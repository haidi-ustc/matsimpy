"""
Crystal prototype identification.

Computes a deterministic, representation-invariant prototype identifier for
crystal structures of the form::

    {anonymized_formula}_{pearson_symbol}_{space_group_symbol}_{wyckoff_fingerprint}

e.g. ``AB_cF2_Fm-3m_a_b`` for rocksalt.

Ported from the CrystalPrototype reference implementation and reimplemented
natively on MatSimPy objects. spglib is a required dependency of this module.

The identifier is deterministic and invariant under repeated runs, atom
ordering, and supercell scaling of the input cell. Wyckoff letters come from
the spglib-standardized primitive cell; for a few space groups, different
input cell settings of the same crystal can standardize to different origin
conventions (e.g. diamond described with a rhombohedral vs a conventional
cubic cell yields Wyckoff letters ``a`` vs ``b``). This caveat is inherited
from the reference algorithm.
"""

import json
import math
import os
from collections import Counter
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import spglib

from ..core import Crystal, Element
from ..core.periodic_table import ELEMENTS


def _anonymized_formula(crystal: Crystal) -> str:
    """Return the anonymized formula, e.g. ``AB2C3`` for a three-element crystal.

    Element counts are gcd-reduced; elements are ordered by (count ascending,
    electronegativity ascending, atomic number ascending) and labeled A, B, C,
    ... in that order, matching the pymatgen reference convention.
    """
    counts = Counter(crystal.species)
    divisor = 0
    for count in counts.values():
        divisor = math.gcd(divisor, count)
    if divisor > 1:
        counts = Counter({symbol: count // divisor for symbol, count in counts.items()})

    def sort_key(symbol: str) -> Tuple[int, float, int]:
        element = Element.get_element(symbol)
        electronegativity = element.X if element.X is not None else float("inf")
        return (counts[symbol], electronegativity, element.atomic_no)

    symbols = sorted(counts, key=sort_key)
    if len(symbols) > 26:
        raise ValueError("anonymized formula supports at most 26 unique elements")
    parts = []
    for index, symbol in enumerate(symbols):
        letter = chr(ord("A") + index)
        count = counts[symbol]
        parts.append(f"{letter}{count}" if count > 1 else letter)
    return "".join(parts)


def _simplify_fingerprint(fingerprint: str) -> str:
    """Run-length encode repeated characters, e.g. ``aaaa`` -> ``4a``."""
    result = []
    if len(fingerprint) == 0:
        return ""
    current_char = fingerprint[0]
    count = 1
    for index in range(1, len(fingerprint)):
        if fingerprint[index] == current_char:
            count += 1
        else:
            result.append(f"{count}{current_char}" if count > 1 else current_char)
            current_char = fingerprint[index]
            count = 1
    result.append(f"{count}{current_char}" if count > 1 else current_char)
    return "".join(result)


def _spglib_cell(crystal: Crystal) -> Tuple[np.ndarray, np.ndarray, List[int]]:
    """Convert a Crystal to an spglib cell (lattice, frac positions, atomic numbers)."""
    return (
        np.asarray(crystal.lattice.lattice_vectors, dtype=float),
        np.asarray(crystal.frac_positions, dtype=float),
        [Element.get_element(symbol).atomic_no for symbol in crystal.species],
    )


def _dataset_value(dataset, name: str):
    """Read a symmetry dataset field via spglib's attribute or dict interface."""
    if hasattr(dataset, name):
        return getattr(dataset, name)
    return dataset[name]


def _symmetry_signature(
    crystal: Crystal, symprec: float, to_primitive: bool
) -> Tuple[str, str, str]:
    """Return (pearson_symbol, space_group_symbol, wyckoff_fingerprint)."""
    std_cell = spglib.standardize_cell(
        _spglib_cell(crystal),
        to_primitive=to_primitive,
        no_idealize=False,
        symprec=symprec,
    )
    if std_cell is None:
        raise ValueError(
            "spglib.standardize_cell returned None; cannot compute a prototype "
            "for this crystal. Try a different symprec."
        )
    dataset = spglib.get_symmetry_dataset(std_cell, symprec=symprec)
    if dataset is None:
        raise ValueError(
            "spglib.get_symmetry_dataset returned None; cannot compute a "
            "prototype for this crystal. Try a different symprec."
        )

    number = int(_dataset_value(dataset, "number"))
    symbol = _dataset_value(dataset, "international")
    hall_number = int(_dataset_value(dataset, "hall_number"))
    wyckoffs = list(_dataset_value(dataset, "wyckoffs"))
    equivalent_atoms = _dataset_value(dataset, "equivalent_atoms")

    # Pearson symbol: crystal class + lattice type + atom count of the
    # standardized cell (primitive by default).
    if number <= 2:
        crystal_class = "a"
    elif number <= 15:
        crystal_class = "m"
    elif number <= 74:
        crystal_class = "o"
    elif number <= 142:
        crystal_class = "t"
    elif number <= 194:
        crystal_class = "h"
    else:
        crystal_class = "c"
    lattice_type = spglib.get_spacegroup_type(hall_number)["international"][0]
    if lattice_type in ("A", "B"):
        lattice_type = "C"
    pearson = crystal_class + lattice_type + str(len(std_cell[2]))

    # Wyckoff fingerprint: one letter per unique site, grouped by element
    # atomic number (ascending), letters sorted within each group, groups
    # joined with '_', then run-length simplified.
    _, unique_indices = np.unique(equivalent_atoms, return_index=True)
    pairs = [(int(std_cell[2][index]), wyckoffs[index]) for index in unique_indices]
    pairs.sort(key=lambda pair: pair[0])
    groups: Dict[int, List[str]] = {}
    for atomic_number, letter in pairs:
        groups.setdefault(atomic_number, []).append(letter)
    fingerprint_parts = [
        "".join(sorted(groups[atomic_number])) for atomic_number in sorted(groups)
    ]
    fingerprint = _simplify_fingerprint("_".join(fingerprint_parts))

    return pearson, symbol, fingerprint


def _validate_crystal(crystal) -> None:
    if not isinstance(crystal, Crystal):
        raise TypeError(f"Expected Crystal, got {type(crystal).__name__}")


def get_prototype(
    crystal: Crystal, symprec: float = 1e-5, to_primitive: bool = True
) -> str:
    """Return the prototype identifier string for a crystal.

    Format: ``{anonymized_formula}_{pearson_symbol}_{space_group_symbol}_{wyckoff_fingerprint}``

    Args:
        crystal: Crystal to identify.
        symprec: Symmetry tolerance passed to spglib (default 1e-5).
        to_primitive: Standardize to the primitive cell (True) or the
            conventional cell (False) before fingerprinting.

    Returns:
        str: Prototype identifier, e.g. ``AB_cF2_Fm-3m_a_b``.

    Raises:
        TypeError: If crystal is not a Crystal.
        ValueError: If spglib cannot determine a symmetry dataset.
    """
    _validate_crystal(crystal)
    anonymized_formula = _anonymized_formula(crystal)
    pearson, symbol, fingerprint = _symmetry_signature(crystal, symprec, to_primitive)
    return f"{anonymized_formula}_{pearson}_{symbol}_{fingerprint}"


def get_prototype_info(
    crystal: Crystal, symprec: float = 1e-5, to_primitive: bool = True
) -> Dict[str, str]:
    """Return the prototype identifier components as a dict.

    Keys: ``anonymized_formula``, ``pearson_symbol``, ``space_group_symbol``,
    ``wyckoff_fingerprint``, and the joined ``prototype`` string.
    """
    _validate_crystal(crystal)
    anonymized_formula = _anonymized_formula(crystal)
    pearson, symbol, fingerprint = _symmetry_signature(crystal, symprec, to_primitive)
    return {
        "anonymized_formula": anonymized_formula,
        "pearson_symbol": pearson,
        "space_group_symbol": symbol,
        "wyckoff_fingerprint": fingerprint,
        "prototype": f"{anonymized_formula}_{pearson}_{symbol}_{fingerprint}",
    }


class CrystalPrototype:
    """Crystal prototype analysis and identification.

    Computes prototype identifier strings for crystals and maintains a
    prototype database mapping prototype strings to structure file names.

    Args:
        prototype_file: Optional path to a JSON file (a dict mapping prototype
            strings to lists of structure file names) to pre-load.
    """

    def __init__(self, prototype_file: Optional[str] = None):
        self.prototype_data: Dict[str, List[str]] = {}
        if prototype_file:
            try:
                with open(prototype_file) as file_handle:
                    self.prototype_data = json.load(file_handle)
            except FileNotFoundError:
                pass

    def get_prototype_string(
        self, crystal: Crystal, symprec: float = 1e-5, to_primitive: bool = True
    ) -> str:
        """Return the prototype identifier string for a crystal (see get_prototype)."""
        return get_prototype(crystal, symprec=symprec, to_primitive=to_primitive)

    def save_prototype_data(self, output_file: str, indent: int = 4) -> None:
        """Save the current prototype data to a JSON file."""
        with open(output_file, "w") as file_handle:
            json.dump(self.prototype_data, file_handle, indent=indent)

    def get_structure_from_prototype(
        self, prototype: str, return_all: bool = False
    ) -> Optional[Union[str, List[str]]]:
        """Return structure file name(s) associated with a prototype.

        Returns None if the prototype is not in the database. With
        return_all=True, returns the full list.
        """
        data = self.prototype_data.get(prototype, None)
        if data is None:
            return None
        return data if return_all else data[0]

    def build_prototype_database(
        self,
        structure_files: List[str],
        symprec: float = 1e-5,
        to_primitive: bool = True,
    ) -> Dict[str, List[str]]:
        """Build a prototype database from structure files.

        Reads each file via matsimpy.io.read, computes its prototype string,
        and maps the string to the file basenames that produced it. Files that
        fail to read or analyze are skipped with an error message, matching
        the reference implementation.

        Args:
            structure_files: Paths to structure files (any format supported by
                matsimpy.io.read).
            symprec: Symmetry tolerance passed to spglib (default 1e-5).
            to_primitive: Standardize to the primitive cell before
                fingerprinting (default True).

        Returns:
            Dict mapping prototype strings to lists of file basenames.
        """
        from ..io import read

        results: Dict[str, List[str]] = {}
        for file_path in structure_files:
            structure_id = os.path.basename(str(file_path))
            try:
                structure = read(str(file_path))
                key = self.get_prototype_string(
                    structure, symprec=symprec, to_primitive=to_primitive
                )
                results.setdefault(key, []).append(structure_id)
            except Exception as exc:
                print(f"Error processing file {file_path}: {exc}")
        self.prototype_data.update(results)
        return results
