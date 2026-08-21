"""
Crystal prototype identification.

Computes a deterministic, representation-invariant prototype identifier for
crystal structures of the form::

    {anonymized_formula}_{pearson_symbol}_{space_group_symbol}_{wyckoff_fingerprint}

e.g. ``AB_cF2_Fm-3m_a_b`` for rocksalt.

Ported from the CrystalPrototype reference implementation and reimplemented
natively on MatSimPy objects. Prototype analysis requires the optional
``MatSimPy[analysis]`` dependency.

The identifier is deterministic and invariant under repeated runs, atom
ordering, element substitution, and supercell scaling of the input cell.
Wyckoff letters come from
the spglib-standardized primitive cell; for a few space groups, different
input cell settings of the same crystal can standardize to different origin
conventions (e.g. diamond described with a rhombohedral vs a conventional
cubic cell yields Wyckoff letters ``a`` vs ``b``). This caveat is inherited
from the reference algorithm.
"""

from __future__ import annotations

import json
import logging
import math
import os
from collections import Counter
from collections.abc import Sequence
from itertools import islice, product
from numbers import Real
from pathlib import Path

import numpy as np

from ..core import Crystal, Element, get_el_sp
from . import analyzer as _analyzer
from ._spglib import to_spglib_cell

logger = logging.getLogger(__name__)


def _reduced_element_counts(crystal: Crystal) -> dict[int, int]:
    """Return gcd-reduced element counts keyed by atomic number."""
    counts = Counter(get_el_sp(symbol).atomic_no for symbol in crystal.species)
    divisor = 0
    for count in counts.values():
        divisor = math.gcd(divisor, count)
    if divisor > 1:
        return {atomic_number: count // divisor for atomic_number, count in counts.items()}
    return dict(counts)


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


def _dataset_value(dataset, name: str):
    """Read a symmetry dataset field via spglib's attribute or dict interface."""
    if hasattr(dataset, name):
        return getattr(dataset, name)
    return dataset[name]


def _symmetry_signature(
    crystal: Crystal, symprec: float, to_primitive: bool
) -> tuple[str, str, dict[int, str]]:
    """Return the Pearson symbol, space-group symbol, and per-element Wyckoffs."""
    spglib = _require_spglib()
    std_cell = spglib.standardize_cell(
        to_spglib_cell(crystal),
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
    symbol = str(_dataset_value(dataset, "international"))
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
    spacegroup_type = spglib.get_spacegroup_type(hall_number)
    lattice_type = _dataset_value(spacegroup_type, "international")[0]
    if lattice_type in ("A", "B"):
        lattice_type = "C"
    pearson = crystal_class + lattice_type + str(len(std_cell[2]))

    # Wyckoff fingerprint: one letter per unique site, grouped by element;
    # letters are sorted and run-length encoded within each group. The groups
    # are canonically aligned with reduced counts in _prototype_components.
    _, unique_indices = np.unique(equivalent_atoms, return_index=True)
    pairs = [(int(std_cell[2][index]), wyckoffs[index]) for index in unique_indices]
    pairs.sort(key=lambda pair: pair[0])
    groups: dict[int, list[str]] = {}
    for atomic_number, letter in pairs:
        groups.setdefault(atomic_number, []).append(letter)
    wyckoffs_by_element = {
        atomic_number: _simplify_fingerprint("".join(sorted(letters)))
        for atomic_number, letters in groups.items()
    }

    return pearson, symbol, wyckoffs_by_element


def _require_spglib():
    """Return spglib or raise the package's actionable optional-dependency error."""
    if not _analyzer.HAS_SPGLIB:
        raise ImportError(_analyzer._SPGLIB_IMPORT_ERROR)
    return _analyzer.spglib


def _validate_options(symprec: float, to_primitive: bool) -> None:
    if isinstance(symprec, bool) or not isinstance(symprec, Real):
        raise TypeError("symprec must be a positive finite real number")
    if not math.isfinite(float(symprec)) or symprec <= 0:
        raise ValueError("symprec must be a positive finite real number")
    if not isinstance(to_primitive, bool):
        raise TypeError("to_primitive must be a bool")


def _prototype_components(
    crystal: Crystal, symprec: float, to_primitive: bool
) -> dict[str, str]:
    """Compute mutually aligned, chemically anonymous prototype components."""
    _validate_crystal(crystal)
    _validate_options(symprec, to_primitive)
    pearson, symbol, wyckoffs_by_element = _symmetry_signature(
        crystal, float(symprec), to_primitive
    )
    counts = _reduced_element_counts(crystal)
    if counts.keys() != wyckoffs_by_element.keys():
        raise ValueError("standardized symmetry data does not match crystal composition")
    if len(counts) > 26:
        raise ValueError("anonymized formula supports at most 26 unique elements")

    anonymous_sites = sorted(
        (
            counts[atomic_number],
            wyckoffs_by_element[atomic_number],
        )
        for atomic_number in counts
    )
    formula_parts = []
    fingerprint_parts = []
    for index, (count, fingerprint) in enumerate(anonymous_sites):
        letter = chr(ord("A") + index)
        formula_parts.append(f"{letter}{count}" if count > 1 else letter)
        fingerprint_parts.append(fingerprint)

    anonymized_formula = "".join(formula_parts)
    fingerprint = "_".join(fingerprint_parts)
    return {
        "anonymized_formula": anonymized_formula,
        "pearson_symbol": pearson,
        "space_group_symbol": symbol,
        "wyckoff_fingerprint": fingerprint,
        "prototype": f"{anonymized_formula}_{pearson}_{symbol}_{fingerprint}",
    }


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
    return _prototype_components(crystal, symprec, to_primitive)["prototype"]


def get_prototype_info(
    crystal: Crystal, symprec: float = 1e-5, to_primitive: bool = True
) -> dict[str, str]:
    """Return the prototype identifier components as a dict.

    Keys: ``anonymized_formula``, ``pearson_symbol``, ``space_group_symbol``,
    ``wyckoff_fingerprint``, and the joined ``prototype`` string.
    """
    return _prototype_components(crystal, symprec, to_primitive)


class CrystalPrototype:
    """Crystal prototype analysis and identification.

    Computes prototype identifier strings for crystals and maintains a
    prototype database mapping prototype strings to structure file names.

    Args:
        prototype_file: Optional path to a JSON file (a dict mapping prototype
            strings to lists of structure file names) to pre-load.
    """

    def __init__(self, prototype_file: str | os.PathLike[str] | None = None):
        self.prototype_data: dict[str, list[str]] = {}
        if prototype_file is not None:
            with Path(prototype_file).open(encoding="utf-8") as file_handle:
                loaded = json.load(file_handle)
            self.prototype_data = self._validate_prototype_data(loaded)

    @staticmethod
    def _validate_prototype_data(data) -> dict[str, list[str]]:
        if not isinstance(data, dict) or not all(
            isinstance(prototype, str)
            and isinstance(files, list)
            and files
            and all(isinstance(file_name, str) and file_name for file_name in files)
            for prototype, files in data.items()
        ):
            raise ValueError(
                "prototype data must map strings to non-empty lists of structure file names"
            )
        return {prototype: list(files) for prototype, files in data.items()}

    def get_prototype_string(
        self, crystal: Crystal, symprec: float = 1e-5, to_primitive: bool = True
    ) -> str:
        """Return the prototype identifier string for a crystal (see get_prototype)."""
        return get_prototype(crystal, symprec=symprec, to_primitive=to_primitive)

    def save_prototype_data(
        self, output_file: str | os.PathLike[str], indent: int = 4
    ) -> None:
        """Save the current prototype data to a JSON file."""
        data = self._validate_prototype_data(self.prototype_data)
        with Path(output_file).open("w", encoding="utf-8") as file_handle:
            json.dump(data, file_handle, indent=indent)

    def get_structure_from_prototype(
        self, prototype: str, return_all: bool = False
    ) -> str | list[str] | None:
        """Return structure file name(s) associated with a prototype.

        Returns None if the prototype is not in the database. With
        return_all=True, returns the full list.
        """
        data = self.prototype_data.get(prototype, None)
        if not data:
            return None
        return list(data) if return_all else data[0]

    def build_prototype_database(
        self,
        structure_files: list[str],
        symprec: float = 1e-5,
        to_primitive: bool = True,
    ) -> dict[str, list[str]]:
        """Build a prototype database from structure files.

        Reads each file via matsimpy.io.read, computes its prototype string,
        and maps the string to the file basenames that produced it. Read and
        analysis failures propagate so callers cannot mistake partial output
        for a complete database.

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

        results: dict[str, list[str]] = {}
        for file_path in structure_files:
            structure_id = os.path.basename(str(file_path))
            structure = read(str(file_path))
            key = self.get_prototype_string(
                structure, symprec=symprec, to_primitive=to_primitive
            )
            results.setdefault(key, []).append(structure_id)
        for prototype, structure_ids in results.items():
            existing = self.prototype_data.setdefault(prototype, [])
            existing.extend(
                structure_id
                for structure_id in structure_ids
                if structure_id not in existing
            )
        return results

    def suggest_element_substitutions(
        self, elements: list[str]
    ) -> dict[str, list[str]]:
        """Suggest same-family element substitutions for each element.

        Non-transition metals get elements from the same periodic-table group
        (up to period 6). D-block transition metals get all other period-6-or-
        earlier transition metals. Results are sorted for determinism; unknown
        elements fall back to themselves.
        """
        transition_metal_symbols = {
            element.symbol
            for atomic_number in range(1, 119)
            if (element := get_el_sp(atomic_number)).is_transition_metal
            and element.period is not None
            and element.period <= 6
        }

        result = {}
        for element_symbol in elements:
            try:
                element = get_el_sp(element_symbol)
                if element.is_transition_metal:
                    result[element_symbol] = sorted(transition_metal_symbols)
                elif element.group is not None:
                    same_group = [
                        candidate.symbol
                        for candidate in Element.get_elements_by_group(element.group)
                        if candidate.period is not None and candidate.period <= 6
                    ]
                    result[element_symbol] = same_group or [element.symbol]
                else:
                    result[element_symbol] = [element.symbol]
            except (TypeError, ValueError):
                result[element_symbol] = [element_symbol]
        return result

    def generate_structures_from_prototype(
        self,
        prototype: str,
        structures_dir: str = "./",
        element_substitutions: dict[str, list[str]] | None = None,
        max_structures: int | None = None,
    ) -> list[Crystal]:
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
        from ..io import read
        from ..transformation.chemical import substitute

        if isinstance(max_structures, bool) or (
            max_structures is not None and not isinstance(max_structures, int)
        ):
            raise TypeError("max_structures must be a non-negative integer or None")
        if max_structures is not None and max_structures < 0:
            raise ValueError("max_structures must be a non-negative integer or None")

        template_files = self.prototype_data.get(prototype, None)
        if not template_files or not template_files[0]:
            raise ValueError(f"No template structure found for prototype: {prototype}")
        template_file_path = os.path.join(structures_dir, template_files[0])
        try:
            template_structure = read(template_file_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Template structure file not found: {template_file_path}"
            ) from exc
        _validate_crystal(template_structure)

        unique_elements = sorted(set(template_structure.species))
        if element_substitutions is None:
            element_substitutions = self.suggest_element_substitutions(unique_elements)
        else:
            normalized_substitutions: dict[str, list[str]] = {}
            for original_element, substitutes in element_substitutions.items():
                canonical_original = get_el_sp(original_element).symbol
                if canonical_original in normalized_substitutions:
                    raise ValueError(
                        f"duplicate substitution key after normalization: {canonical_original}"
                    )
                if isinstance(substitutes, (str, bytes)) or not isinstance(
                    substitutes, Sequence
                ):
                    raise TypeError(
                        f"substitutions for {canonical_original} must be a "
                        "non-empty sequence of elements"
                    )
                if not substitutes:
                    raise ValueError(
                        f"substitutions for {canonical_original} must be a "
                        "non-empty sequence of elements"
                    )
                try:
                    normalized_substitutions[canonical_original] = [
                        get_el_sp(substitute).symbol for substitute in substitutes
                    ]
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"substitutions for {canonical_original} contain an "
                        f"invalid element: {exc}"
                    ) from exc
            absent_elements = sorted(
                set(normalized_substitutions).difference(unique_elements)
            )
            if absent_elements:
                raise ValueError(
                    "substitution elements not present in template: "
                    + ", ".join(absent_elements)
                )
            element_substitutions = normalized_substitutions

        element_keys = list(element_substitutions.keys())
        substitution_lists = [element_substitutions[key] for key in element_keys]
        total_combinations = math.prod(len(options) for options in substitution_lists)
        combinations = product(*substitution_lists)
        if max_structures is not None:
            combinations = islice(combinations, max_structures)
        logger.info(
            "Generating up to %s structures from %s substitution combinations",
            max_structures if max_structures is not None else total_combinations,
            total_combinations,
        )

        result_structures = []
        all_indices = list(range(len(template_structure)))
        for combination in combinations:
            substitution_map = dict(zip(element_keys, combination))
            complete_map = {
                symbol: substitution_map.get(symbol, symbol)
                for symbol in unique_elements
            }
            new_structure = substitute(template_structure, all_indices, complete_map)
            result_structures.append(new_structure)
        return result_structures
