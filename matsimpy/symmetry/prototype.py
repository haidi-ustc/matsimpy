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

    def suggest_element_substitutions(
        self, elements: List[str]
    ) -> Dict[str, List[str]]:
        """Suggest same-family element substitutions for each element.

        Non-transition metals get elements from the same periodic-table group
        (up to period 6). Transition metals (Sc-Zn, Y-Cd, Lu-Hg) get all other
        transition metals. Results are sorted for determinism; unknown
        elements fall back to themselves.
        """
        transition_metal_symbols = set()
        for atomic_number in list(range(21, 31)) + list(range(39, 49)) + list(
            range(71, 81)
        ):
            try:
                transition_metal_symbols.add(Element.from_Z(atomic_number).symbol)
            except (ValueError, AttributeError):
                pass

        result = {}
        for element_symbol in elements:
            try:
                element = Element.get_element(element_symbol)
                if element_symbol in transition_metal_symbols:
                    result[element_symbol] = sorted(
                        symbol
                        for symbol in transition_metal_symbols
                        if Element.get_element(symbol).period <= 6
                    )
                else:
                    same_group = []
                    for symbol in ELEMENTS:
                        try:
                            candidate = Element.get_element(symbol)
                        except (ValueError, AttributeError):
                            continue
                        if (
                            candidate.period is not None
                            and candidate.period <= 6
                            and candidate.group == element.group
                        ):
                            same_group.append(symbol)
                    result[element_symbol] = (
                        same_group if same_group else [element_symbol]
                    )
            except Exception:
                result[element_symbol] = [element_symbol]
        return result

    def generate_structures_from_prototype(
        self,
        prototype: str,
        structures_dir: str = "./",
        element_substitutions: Optional[Dict[str, List[str]]] = None,
        max_structures: Optional[int] = None,
    ) -> List[Crystal]:
        """Generate structures from a prototype by element substitution.

        Reads the first template structure file mapped to the prototype in
        structures_dir and produces the Cartesian product of the substitution
        options. If element_substitutions is None, same-family suggestions
        from suggest_element_substitutions are used.

        Args:
            prototype: Prototype identifier string.
            structures_dir: Directory containing the template structure files.
            element_substitutions: Optional mapping of original element symbol
                to a list of replacement symbols.
            max_structures: Optional cap on the number of generated structures.

        Returns:
            List of new Crystal structures with substituted elements.
        """
        from itertools import product

        from ..io import read
        from ..transformation.chemical import substitute_all

        template_files = self.prototype_data.get(prototype, None)
        if not template_files or not template_files[0]:
            raise ValueError(f"No template structure found for prototype: {prototype}")
        template_file_path = os.path.join(structures_dir, template_files[0])
        try:
            template_structure = read(template_file_path)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Template structure file not found: {template_file_path}"
            )

        unique_elements = sorted(set(template_structure.species))
        if element_substitutions is None:
            element_substitutions = self.suggest_element_substitutions(unique_elements)

        print("Original elements in the structure:", unique_elements)
        print("Suggested element substitutions:")
        for original_element, substitutes in element_substitutions.items():
            print(f"  {original_element} -> {substitutes}")

        element_keys = list(element_substitutions.keys())
        substitution_lists = [element_substitutions[key] for key in element_keys]
        all_combinations = list(product(*substitution_lists))
        total_combinations = len(all_combinations)
        if max_structures and total_combinations > max_structures:
            all_combinations = all_combinations[:max_structures]
            print(
                f"Limited to {max_structures} combinations out of "
                f"{total_combinations} possible."
            )

        result_structures = []
        for combination in all_combinations:
            substitution_map = dict(zip(element_keys, combination))
            new_structure = template_structure
            for original_element, substitute_element in substitution_map.items():
                if original_element != substitute_element:
                    new_structure = substitute_all(
                        new_structure, original_element, substitute_element
                    )
            result_structures.append(new_structure)
        return result_structures
