"""Crystal prototype identifiers and a read-only prototype database.

A prototype identifier groups crystals that share a structure type,
independent of the elements, atom order and the choice of supercell::

    {anonymized_formula}_{pearson_symbol}_{space_group_symbol}_{wyckoff_fingerprint}

e.g. ``AB_cF2_Fm-3m_a_b`` for rocksalt (NaCl, MgO, ...).

* ``anonymized_formula``: reduced formula with elements renamed A, B, ...,
  ordered by count and then by Wyckoff letters.
* ``pearson_symbol``: crystal family, centering, and the number of atoms in
  the spglib-standardized cell.  With the default ``to_primitive=True`` that
  is the *primitive* cell (rocksalt ``cF2``); a crystallographic Pearson
  symbol counts the conventional cell (``cF8``, ``to_primitive=False``).
* ``wyckoff_fingerprint``: per element, the sorted Wyckoff letters of its
  inequivalent sites, run-length encoded (``aaaa`` -> ``4a``).

The identifier format follows branch1 / the CrystalPrototype reference
implementation, so identifiers are comparable with databases built there.

Limitation: Wyckoff letters come from spglib's standardized cell and are not
reduced over the space group's Euclidean normalizer.  For a few space groups
two descriptions of the same crystal can therefore give different letters
(e.g. diamond: ``a`` from the cubic cell, ``b`` from some rhombohedral cells).

Building a database from structure files and generating structures from a
prototype live in :mod:`matsimpy.builders.bulk.prototype` (they need I/O and
transformations, which are above this layer).
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from numbers import Real
from pathlib import Path
from types import MappingProxyType

import numpy as np

from ..core import Crystal
from . import spacegroup as _spacegroup

__all__ = ["PrototypeDatabase", "PrototypeInfo", "get_prototype", "get_prototype_info"]


@dataclass(frozen=True)
class PrototypeInfo:
    """Components of a prototype identifier (see the module docstring)."""

    anonymized_formula: str
    pearson_symbol: str
    space_group_symbol: str
    wyckoff_fingerprint: str
    prototype: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _run_length(text: str) -> str:
    """``aaaab`` -> ``4ab``."""
    parts = []
    index = 0
    while index < len(text):
        end = index
        while end < len(text) and text[end] == text[index]:
            end += 1
        count = end - index
        parts.append(f"{count}{text[index]}" if count > 1 else text[index])
        index = end
    return "".join(parts)


def _crystal_family(number: int) -> str:
    for limit, letter in ((2, "a"), (15, "m"), (74, "o"), (142, "t"), (194, "h")):
        if number <= limit:
            return letter
    return "c"


def _validate(crystal, symprec, to_primitive) -> None:
    if not isinstance(crystal, Crystal):
        raise TypeError(f"Expected Crystal, got {type(crystal).__name__}")
    if not all(crystal.pbc):
        raise ValueError(
            f"prototype identifiers are defined for 3D-periodic crystals; pbc={tuple(crystal.pbc)}"
        )
    if isinstance(symprec, bool) or not isinstance(symprec, Real):
        raise TypeError("symprec must be a positive finite real number")
    if not math.isfinite(float(symprec)) or symprec <= 0:
        raise ValueError("symprec must be a positive finite real number")
    if not isinstance(to_primitive, bool):
        raise TypeError("to_primitive must be a bool")


def _symmetry_signature(crystal: Crystal, symprec: float, to_primitive: bool):
    """Pearson symbol, space-group symbol and Wyckoff fingerprint per atomic number."""
    _spacegroup._require_spglib()
    spglib = _spacegroup.spglib
    standardized = spglib.standardize_cell(
        _spacegroup._cell(crystal), to_primitive=to_primitive, no_idealize=False, symprec=symprec
    )
    if standardized is None:
        raise ValueError(f"spglib could not standardize the crystal at symprec={symprec}")
    dataset = spglib.get_symmetry_dataset(standardized, symprec=symprec)
    if dataset is None:
        raise ValueError(f"spglib could not determine the space group at symprec={symprec}")

    numbers = standardized[2]
    centering = str(spglib.get_spacegroup_type(int(dataset.hall_number)).international)[0]
    if centering in ("A", "B"):
        centering = "C"
    pearson = f"{_crystal_family(int(dataset.number))}{centering}{len(numbers)}"

    _, representatives = np.unique(dataset.equivalent_atoms, return_index=True)
    letters: dict[int, list[str]] = {}
    for index in representatives:
        letters.setdefault(int(numbers[index]), []).append(str(dataset.wyckoffs[index]))
    fingerprints = {z: _run_length("".join(sorted(group))) for z, group in letters.items()}
    return pearson, str(dataset.international), fingerprints


def get_prototype_info(
    crystal: Crystal, symprec: float = 1e-5, to_primitive: bool = True
) -> PrototypeInfo:
    """Return the components of the crystal's prototype identifier.

    Args:
        crystal: A 3D-periodic crystal.
        symprec: spglib symmetry tolerance in Angstrom.
        to_primitive: Standardize to the primitive (True) or conventional cell.

    Raises:
        TypeError: ``crystal`` is not a Crystal, or invalid option types.
        ValueError: Not 3D-periodic, invalid ``symprec``, or spglib failed.
        ImportError: spglib is not installed.
    """
    _validate(crystal, symprec, to_primitive)
    pearson, symbol, fingerprints = _symmetry_signature(crystal, float(symprec), to_primitive)

    counts = Counter(_spacegroup._atomic_number(species) for species in crystal.species)
    divisor = math.gcd(*counts.values())
    counts = {z: n // divisor for z, n in counts.items()}
    if counts.keys() != fingerprints.keys():
        raise ValueError("standardized symmetry data does not match the crystal composition")
    if len(counts) > 26:
        raise ValueError("the anonymized formula supports at most 26 elements")

    sites = sorted((counts[z], fingerprints[z]) for z in counts)
    formula = "".join(
        f"{chr(ord('A') + index)}{count if count > 1 else ''}" for index, (count, _) in enumerate(sites)
    )
    fingerprint = "_".join(letters for _, letters in sites)
    return PrototypeInfo(
        anonymized_formula=formula,
        pearson_symbol=pearson,
        space_group_symbol=symbol,
        wyckoff_fingerprint=fingerprint,
        prototype=f"{formula}_{pearson}_{symbol}_{fingerprint}",
    )


def get_prototype(crystal: Crystal, symprec: float = 1e-5, to_primitive: bool = True) -> str:
    """Return the prototype identifier, e.g. ``AB_cF2_Fm-3m_a_b`` for rocksalt.

    See :func:`get_prototype_info` for arguments and errors.
    """
    return get_prototype_info(crystal, symprec, to_primitive).prototype


class PrototypeDatabase(Mapping):
    """Read-only map from prototype identifier to structure identifiers.

    Structure identifiers are plain names (e.g. file names); the database does
    not store structures.  Every "modifying" method returns a new database.
    """

    __slots__ = ("_entries",)

    def __init__(self, entries: Mapping[str, Sequence[str]] | None = None):
        entries = {} if entries is None else entries
        if not isinstance(entries, Mapping):
            raise ValueError("prototype data must map strings to non-empty lists of structure ids")
        validated = {}
        for prototype, ids in entries.items():
            if (
                not isinstance(prototype, str)
                or isinstance(ids, (str, bytes))
                or not isinstance(ids, Sequence)
                or not ids
                or not all(isinstance(item, str) and item for item in ids)
            ):
                raise ValueError("prototype data must map strings to non-empty lists of structure ids")
            validated[prototype] = tuple(dict.fromkeys(ids))
        object.__setattr__(self, "_entries", MappingProxyType(validated))

    def __setattr__(self, name, value):
        raise AttributeError("PrototypeDatabase is immutable")

    def __getitem__(self, prototype: str) -> tuple[str, ...]:
        return self._entries[prototype]

    def __iter__(self) -> Iterator[str]:
        return iter(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"PrototypeDatabase({len(self)} prototypes)"

    def __reduce__(self):
        return (type(self), ({key: list(ids) for key, ids in self._entries.items()},))

    @classmethod
    def from_json(cls, path: str | os.PathLike[str]) -> PrototypeDatabase:
        """Load a JSON object mapping prototype identifiers to lists of structure ids."""
        with Path(path).open(encoding="utf-8") as handle:
            return cls(json.load(handle))

    def to_json(self, path: str | os.PathLike[str], indent: int = 4) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            json.dump(self.as_dict(), handle, indent=indent)

    def as_dict(self) -> dict[str, list[str]]:
        return {prototype: list(ids) for prototype, ids in self._entries.items()}

    def merge(self, other: Mapping[str, Sequence[str]]) -> PrototypeDatabase:
        """Return a database with the entries of both; existing ids come first."""
        merged = self.as_dict()
        for prototype, ids in PrototypeDatabase(other).items():
            merged[prototype] = merged.get(prototype, []) + [i for i in ids if i not in merged.get(prototype, [])]
        return PrototypeDatabase(merged)

    def with_structures(
        self,
        structures: Mapping[str, Crystal] | Iterable[tuple[str, Crystal]],
        symprec: float = 1e-5,
        to_primitive: bool = True,
    ) -> PrototypeDatabase:
        """Return a database that also contains the given ``(id, crystal)`` pairs.

        Any analysis error propagates, so a partial result is never returned.
        """
        pairs = structures.items() if isinstance(structures, Mapping) else structures
        added: dict[str, list[str]] = {}
        for structure_id, crystal in pairs:
            prototype = get_prototype(crystal, symprec=symprec, to_primitive=to_primitive)
            added.setdefault(prototype, []).append(structure_id)
        return self.merge(added)
