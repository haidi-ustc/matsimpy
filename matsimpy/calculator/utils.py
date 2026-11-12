"""Shared utility functions for calculator subpackages.

These replace simple pymatgen utilities so IO classes don't need
a direct pymatgen dependency for basic operations.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Any, Callable, Iterable, Sequence

import numpy as np
from monty.io import zopen

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Physical constants
Ha_to_eV = 27.211386245988  # Hartree to eV conversion


def site_property_column(structure, key: str):
    """Return ``[props[key] for each site]`` or ``None`` if any site lacks *key*.

    Ported pymatgen code reads ``structure.site_properties[key]`` (a dict of
    per-site lists); MatSimPy stores a tuple of per-site dicts.  Use this
    adapter instead of ``site_properties.get(key)`` / ``[key]``.
    """
    props = structure.site_properties
    if not props or any(key not in p for p in props):
        return None
    return [p[key] for p in props]


def clean_lines(string_list: list[str], remove_empty_lines: bool = True) -> list[str]:
    """Remove ``#`` comments and surrounding whitespace; optionally drop empty lines.

    Both VASP and LAMMPS treat text after ``#`` as a comment, so
    ``"5.43  # a"`` becomes ``"5.43"`` and a comment-only line becomes empty.
    Adapted from pymatgen.util.io_utils.clean_lines.
    """
    stripped = [line.split("#", 1)[0].strip() for line in string_list]
    if remove_empty_lines:
        return [line for line in stripped if line]
    return stripped


def make_symmetric_matrix_from_upper_tri(
    data: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Construct a symmetric 3x3 matrix from upper-triangular elements.

    Input order: [xx, yy, zz, yz, xz, xy]

    Adapted from pymatgen.util.num.make_symmetric_matrix_from_upper_tri.
    """
    xx, yy, zz, yz, xz, xy = data[:6]
    return np.array(
        [
            [xx, xy, xz],
            [xy, yy, yz],
            [xz, yz, zz],
        ]
    )


def get_angle(v1: NDArray[np.floating], v2: NDArray[np.floating]) -> float:
    """Compute the angle in degrees between two vectors.

    Adapted from pymatgen.util.coord.get_angle.
    """
    dot = np.dot(v1, v2)
    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
    if norms < 1e-12:
        return 0.0
    cosang = max(-1.0, min(1.0, dot / norms))
    return float(np.degrees(np.arccos(cosang)))


def str_delimited(
    rows: Iterable[Iterable[Any]],
    header: Iterable[Any] | None = None,
    delimiter: str = "\t",
) -> str:
    """Join the fields of each row with ``delimiter``, one row per line.

    ``str_delimited([["ENCUT", 400]], None, " = ")`` gives ``"ENCUT = 400"``.
    Adapted from pymatgen.util.string.str_delimited. (0.8.x-0.9.0 wrote
    ``"<delimiter> <row>"``, i.e. ``" =  ['ENCUT', 400]"``, which made every
    INCAR file unreadable.)
    """
    lines: list[str] = []
    if header is not None:
        lines.append(delimiter.join(str(item) for item in header))
    for row in rows:
        lines.append(delimiter.join(str(item) for item in row))
    return "\n".join(lines)


def micro_pyawk(
    filename: str | os.PathLike[str],
    search: Sequence[Sequence[Any]],
    results: Any = None,
    debug: Callable[[Any, re.Match[str]], Any] | None = None,
    postdebug: Callable[[Any, str], Any] | None = None,
) -> Any:
    """Scan a text file line by line, running ``(regex, predicate, action)`` records.

    For every line and every record whose regex matches, ``action(results, match)``
    is called if ``predicate`` is ``None`` or ``predicate(results, line)`` is true.
    ``results`` (default ``{}``) is returned. ``debug(results, match)`` runs before
    each action and ``postdebug(results, line)`` after each line.
    Adapted from pymatgen.util.io_utils.micro_pyawk (0.8.x-0.9.0 took a
    ``{key: pattern}`` dict instead, so every OUTCAR reader built on it failed).
    """
    if results is None:
        results = {}
    if isinstance(search, dict):
        raise TypeError("search must be a sequence of (regex, predicate, action) records")
    records = []
    for record in search:
        if len(record) != 3:
            raise ValueError("each search record must be (regex, predicate, action)")
        pattern, predicate, action = record
        if predicate is not None and not callable(predicate):
            raise TypeError("predicate must be callable or None")
        if not callable(action):
            raise TypeError("action must be callable")
        records.append((re.compile(pattern), predicate, action))

    with zopen(filename, mode="rt", encoding="utf-8") as file:
        for line in file:
            for pattern, predicate, action in records:
                match = pattern.search(line)
                if match is None or (predicate is not None and not predicate(results, line)):
                    continue
                if debug is not None:
                    debug(results, match)
                action(results, match)
            if postdebug is not None:
                postdebug(results, line)
    return results


__all__ = [
    "Ha_to_eV",
    "clean_lines",
    "micro_pyawk",
    "site_property_column",
    "make_symmetric_matrix_from_upper_tri",
    "get_angle",
    "str_delimited",
]
