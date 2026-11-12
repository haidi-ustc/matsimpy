"""Crystal prototype identifiers and a read-only prototype database.

A prototype identifier groups crystals that share a structure type,
independent of the elements, atom order, cell choice and origin::

    {anonymized_formula}_{pearson_symbol}_{space_group_number}_{wyckoff_fingerprint}

e.g. ``AB_cF8_225_a_b`` for rocksalt (NaCl, MgO, ...), in the style of AFLOW
prototype labels.

* ``pearson_symbol``: crystal family, centering and the number of atoms in
  the conventional cell (rocksalt ``cF8``, also for a primitive input); for
  rhombohedral lattices the rhombohedral cell (corundum ``hR10``).
* ``wyckoff_fingerprint``: per element, the sorted Wyckoff letters of its
  inequivalent sites, run-length encoded (``aaaa`` -> ``4a``).
* ``anonymized_formula``: reduced formula with elements renamed A, B, ...,
  ordered by count and then by Wyckoff letters.  Unlike AFLOW, which orders
  by element name, this keeps the identifier unchanged under substitution.

Wyckoff letters depend on the origin and axis choice.  As in AFLOW, all
descriptions that keep the space-group setting are enumerated (axis
permutations and lattice symmetries combined with origin shifts on a 1/8
grid that map the space group onto itself); the one with the smallest sum of
letter values (a=1, b=2, ...) is used, ties broken by the anonymized letter
sequence.

With ``symprec=None`` the symmetry tolerance is chosen per crystal: it starts
at 1/100 of the shortest interatomic distance and is halved until the
symmetry found is consistent with the crystal (spglib succeeds, the
standardized cell has the crystal's composition, and the crystal is a
supercell of it).

Building a database from structure files and generating structures from a
prototype live in :mod:`matsimpy.builders.bulk.prototype_db` (they need I/O
and transformations, which are above this layer).
"""

from __future__ import annotations

from matsimpy.utils.tooling import tool
import itertools
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

_MIN_SYMPREC = 1e-5
_SHIFTS = np.array(list(itertools.product(range(8), repeat=3)), dtype=float) / 8
# hexagonal and trigonal normalizers contain in-plane shifts such as (1/3, 2/3, 0)
_HEXAGONAL_SHIFTS = np.array(
    [(i / 12, j / 12, k / 8) for i in range(12) for j in range(12) for k in range(8)], dtype=float
)
_SIGNED_PERMUTATIONS = [
    np.diag(signs) @ np.eye(3, dtype=int)[list(order)]
    for order in itertools.permutations(range(3))
    for signs in itertools.product((1, -1), repeat=3)
]


@dataclass(frozen=True)
class PrototypeInfo:
    """Components of a prototype identifier (see the module docstring)."""

    anonymized_formula: str
    pearson_symbol: str
    space_group_number: int
    space_group_symbol: str
    wyckoff_fingerprint: str
    prototype: str
    symprec: float

    def as_dict(self) -> dict:
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


def _validate(crystal, symprec) -> None:
    if not isinstance(crystal, Crystal):
        raise TypeError(f"Expected Crystal, got {type(crystal).__name__}")
    if not all(crystal.pbc):
        raise ValueError(
            f"prototype identifiers are defined for 3D-periodic crystals; pbc={tuple(crystal.pbc)}"
        )
    if symprec is None:
        return
    if isinstance(symprec, bool) or not isinstance(symprec, Real):
        raise TypeError("symprec must be None or a positive finite real number")
    if not math.isfinite(float(symprec)) or symprec <= 0:
        raise ValueError("symprec must be None or a positive finite real number")


def _shortest_distance(crystal: Crystal) -> float:
    """Shortest distance between two atoms, periodic images included."""
    spglib = _spacegroup.spglib
    matrix = np.asarray(crystal.lattice.matrix, float)
    reduced = spglib.niggli_reduce(matrix)
    reduced = matrix if reduced is None else np.asarray(reduced, float)
    frac = np.asarray(crystal.frac_positions, float) @ matrix @ np.linalg.inv(reduced)
    images = np.array(list(itertools.product((-1, 0, 1), repeat=3)), float)
    shortest = np.inf
    for row in frac:  # one atom at a time keeps memory at O(N) for large cells
        delta = frac - row
        delta -= np.rint(delta)
        lengths = np.linalg.norm((delta[:, None, :] + images) @ reduced, axis=-1)
        positive = lengths[lengths > 1e-8]
        if positive.size:
            shortest = min(shortest, float(positive.min()))
    return shortest


def _reduced_counts(numbers) -> dict[int, int]:
    counts = Counter(int(z) for z in numbers)
    divisor = math.gcd(*counts.values())
    return {z: n // divisor for z, n in counts.items()}


def _standardize(crystal: Crystal, symprec: float):
    """Standardized conventional cell and its dataset, or None if inconsistent."""
    spglib = _spacegroup.spglib
    cell = _spacegroup._cell(crystal)
    primitive = spglib.standardize_cell(cell, to_primitive=True, no_idealize=False, symprec=symprec)
    conventional = spglib.standardize_cell(cell, to_primitive=False, no_idealize=False, symprec=symprec)
    if primitive is None or conventional is None:
        return None
    dataset = spglib.get_symmetry_dataset(conventional, symprec=symprec)
    if dataset is None:
        return None
    composition = _reduced_counts(cell[2])
    if _reduced_counts(primitive[2]) != composition or _reduced_counts(conventional[2]) != composition:
        return None
    if len(cell[2]) % len(primitive[2]):
        return None
    return conventional, dataset, len(primitive[2])


def _symmetry(crystal: Crystal, symprec):
    """Return (conventional cell, dataset, primitive atom count, tolerance used)."""
    _spacegroup._require_spglib()
    shortest = _shortest_distance(crystal)
    if symprec is not None:
        # Atoms closer than the tolerance are merged, which is meaningless; spglib
        # 2.8 also crashes (segmentation fault) from about 0.45 of the distance.
        if symprec > shortest / 4:
            raise ValueError(
                f"symprec={symprec} is too large: it must not exceed a quarter of the "
                f"shortest interatomic distance ({shortest:.4g} A)"
            )
        result = _standardize(crystal, float(symprec))
        if result is None:
            raise ValueError(
                f"spglib found no symmetry consistent with the crystal at symprec={symprec}"
            )
        return (*result, float(symprec))
    tolerance = shortest / 100
    while True:
        result = _standardize(crystal, tolerance)
        if result is not None:
            return (*result, tolerance)
        if tolerance <= _MIN_SYMPREC:
            raise ValueError("spglib found no symmetry consistent with the crystal at any tolerance")
        tolerance = max(tolerance / 2, _MIN_SYMPREC)


def _normalizer(dataset, lattice, symprec):
    """Affine maps x -> Lx + p that map the space group onto itself in this setting.

    L runs over axis permutations (with signs) and lattice symmetries, one per
    coset of the group's point group (L and LW give the same descriptions up to
    a symmetry operation); p runs over a 1/8 grid (1/12 in-plane for
    hexagonal groups)."""
    rotations = np.asarray(dataset.rotations, dtype=int)
    translations = np.asarray(dataset.translations, dtype=float)
    by_rotation: dict[bytes, list[np.ndarray]] = {}
    for rotation, translation in zip(rotations, translations):
        by_rotation.setdefault(rotation.tobytes(), []).append(translation)
    keys = list(by_rotation)
    width = max(len(v) for v in by_rotation.values())
    # all translations of each rotation, padded by repetition: (rotations, width, 3)
    allowed = np.array([[v[i % len(v)] for i in range(width)] for v in by_rotation.values()])
    # one operation per rotation plus the pure (centering) translations generate the group
    generators_w = np.array([np.frombuffer(k, dtype=int).reshape(3, 3) for k in keys])
    generators_t = allowed[:, 0, :]
    identity = np.eye(3, dtype=int).tobytes()
    centering = np.asarray(by_rotation[identity])
    generators_w = np.concatenate([generators_w, np.repeat(np.eye(3, dtype=int)[None], len(centering), 0)])
    generators_t = np.concatenate([generators_t, centering])
    index = {k: i for i, k in enumerate(keys)}

    lattice_ops = _spacegroup.spglib.get_symmetry(
        (lattice, [[0.0, 0.0, 0.0]], [1]), symprec=symprec
    )["rotations"]
    point_group = [np.frombuffer(k, dtype=int).reshape(3, 3) for k in keys]
    candidates = {}
    for matrix in [*_SIGNED_PERMUTATIONS, *lattice_ops]:
        matrix = np.asarray(matrix, dtype=int)
        coset = min((matrix @ w).tobytes() for w in point_group)
        candidates.setdefault(coset, matrix)
    shifts = _HEXAGONAL_SHIFTS if 143 <= int(dataset.number) <= 194 else _SHIFTS
    for linear in candidates.values():
        inverse = np.rint(np.linalg.inv(linear)).astype(int)
        conjugated = linear[None] @ generators_w @ inverse[None]
        try:
            targets = allowed[[index[c.tobytes()] for c in conjugated]]
        except KeyError:  # L does not map the point group onto itself
            continue
        # translation part of (L,p)(W,w)(L,p)^-1 = L w + p - W' p, for every shift p
        moved = (generators_t @ linear.T)[:, None, :] + shifts[None] - shifts[None] @ conjugated.transpose(0, 2, 1)
        difference = moved[:, :, None, :] - targets[:, None, :, :]
        difference -= np.rint(difference)
        matches = np.all(np.abs(difference) < 1e-5, axis=-1).any(axis=-1)
        for shift in shifts[matches.all(axis=0)]:
            yield linear, shift


def _letters(dataset, numbers) -> dict[int, list[str]]:
    _, representatives = np.unique(dataset.equivalent_atoms, return_index=True)
    letters: dict[int, list[str]] = {}
    for index in representatives:
        letters.setdefault(int(numbers[index]), []).append(str(dataset.wyckoffs[index]))
    return letters


def _letter_value(letter: str) -> int:
    """a=1 ... z=26; spglib names the 27th Wyckoff position "A" (e.g. Pmmm 8A)."""
    return ord(letter) - ord("a") + 1 if letter.islower() else 26 + ord(letter) - ord("A") + 1


def _anonymous(letters: dict[int, list[str]], counts: dict[int, int]):
    """(letter-value sum, groups sorted for the anonymized identifier)."""
    total = sum(_letter_value(letter) for group in letters.values() for letter in group)
    groups = sorted((counts[z], _run_length("".join(sorted(letters[z])))) for z in counts)
    return total, groups


def _canonical_groups(conventional, dataset, counts, symprec):
    """Groups of the description with the smallest letter sum (then sequence)."""
    lattice, positions, numbers = (np.asarray(x) for x in conventional)
    best = _anonymous(_letters(dataset, numbers), counts)
    if int(dataset.number) == 1:  # every site is 1a
        return best[1]
    hall = int(dataset.hall_number)
    seen = set()
    for linear, shift in _normalizer(dataset, lattice, symprec):
        # Wyckoff letters depend only on the coordinates in the setting, so the
        # new coordinates are placed in the unchanged standardized lattice: an
        # axis permutation must not change the cell lengths, or spglib would
        # re-sort the axes and undo it.
        new_positions = np.mod(positions @ linear.T + shift, 1.0)
        key = tuple(sorted(zip(numbers.tolist(), map(tuple, np.round(new_positions, 5) % 1.0))))
        if key in seen:
            continue
        seen.add(key)
        candidate = _spacegroup.spglib.get_symmetry_dataset((lattice, new_positions, numbers), symprec=symprec)
        if candidate is None or int(candidate.hall_number) != hall:
            continue
        scored = _anonymous(_letters(candidate, numbers), counts)
        if (scored[0], "_".join(g for _, g in scored[1])) < (best[0], "_".join(g for _, g in best[1])):
            best = scored
    return best[1]


@tool
def get_prototype_info(crystal: Crystal, symprec: float | None = None) -> PrototypeInfo:
    """Return the components of the crystal's prototype identifier.

    Args:
        crystal: A 3D-periodic crystal.
        symprec: spglib symmetry tolerance in Angstrom, or None to choose it
            from the structure (see the module docstring).

    Raises:
        TypeError: ``crystal`` is not a Crystal, or ``symprec`` has a wrong type.
        ValueError: Not 3D-periodic, invalid ``symprec``, or no consistent symmetry.
        ImportError: spglib is not installed.
    """
    _validate(crystal, symprec)
    conventional, dataset, primitive_count, used = _symmetry(crystal, symprec)
    number = int(dataset.number)
    counts = _reduced_counts(_spacegroup._cell(crystal)[2])
    if len(counts) > 26:
        raise ValueError("the anonymized formula supports at most 26 elements")

    centering = str(_spacegroup.spglib.get_spacegroup_type(int(dataset.hall_number)).international)[0]
    centering = "C" if centering in ("A", "B") else centering
    atoms = primitive_count if centering == "R" else len(conventional[2])
    pearson = f"{_crystal_family(number)}{centering}{atoms}"

    groups = _canonical_groups(conventional, dataset, counts, used)
    formula = "".join(
        f"{chr(ord('A') + index)}{count if count > 1 else ''}" for index, (count, _) in enumerate(groups)
    )
    fingerprint = "_".join(letters for _, letters in groups)
    return PrototypeInfo(
        anonymized_formula=formula,
        pearson_symbol=pearson,
        space_group_number=number,
        space_group_symbol=str(dataset.international),
        wyckoff_fingerprint=fingerprint,
        prototype=f"{formula}_{pearson}_{number}_{fingerprint}",
        symprec=used,
    )


@tool
def get_prototype(crystal: Crystal, symprec: float | None = None) -> str:
    """Return the prototype identifier, e.g. ``AB_cF8_225_a_b`` for rocksalt.

    See :func:`get_prototype_info` for arguments and errors.
    """
    return get_prototype_info(crystal, symprec).prototype


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
        symprec: float | None = None,
    ) -> PrototypeDatabase:
        """Return a database that also contains the given ``(id, crystal)`` pairs.

        Any analysis error propagates, so a partial result is never returned.
        """
        pairs = structures.items() if isinstance(structures, Mapping) else structures
        added: dict[str, list[str]] = {}
        for structure_id, crystal in pairs:
            prototype = get_prototype(crystal, symprec=symprec)
            added.setdefault(prototype, []).append(structure_id)
        return self.merge(added)
