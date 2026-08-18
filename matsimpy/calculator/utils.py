"""Shared utility functions for calculator subpackages.

These replace simple pymatgen utilities so IO classes don't need
a direct pymatgen dependency for basic operations.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from os import PathLike
from typing import TYPE_CHECKING, Any, Callable

from monty.io import zopen
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Physical constants
Ha_to_eV = 27.211386245988  # Hartree to eV conversion


def clean_lines(
    string_list: Iterable[str],
    remove_empty_lines: bool = True,
    rstrip_only: bool = False,
) -> Iterator[str]:
    """Strip comments/whitespace and optionally remove empty lines.

    Adapted from pymatgen.util.io_utils.clean_lines.
    """
    for line in string_list:
        cleaned = line.split("#", 1)[0]
        cleaned = cleaned.rstrip() if rstrip_only else cleaned.strip()
        if cleaned or not remove_empty_lines:
            yield cleaned


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
    """Format two-dimensional rows as a delimited text block.

    Adapted from pymatgen.util.string.str_delimited.
    """
    lines: list[str] = []
    if header is not None:
        lines.append(delimiter.join(str(item) for item in header))
    for row in rows:
        lines.append(delimiter.join(str(item) for item in row))
    return "\n".join(lines)


SearchPredicate = Callable[[Any, str], bool]
SearchAction = Callable[[Any, re.Match[str]], Any]


def micro_pyawk(
    filename: str | PathLike[str],
    search: Sequence[Sequence[Any]],
    results: Any = None,
    debug: Callable[[Any, re.Match[str]], Any] | None = None,
    postdebug: Callable[[Any, str], Any] | None = None,
) -> Any:
    """Run ordered regex/predicate/action records over a text file."""
    if results is None:
        results = {}
    if isinstance(search, dict):
        raise TypeError("micro_pyawk search must be an ordered sequence of (regex, predicate, action) records")

    compiled: list[tuple[re.Pattern[str], SearchPredicate | None, SearchAction]] = []
    for record in search:
        if len(record) != 3:
            raise ValueError("micro_pyawk search records must contain exactly regex, predicate, and action")
        pattern, predicate, action = record
        if predicate is not None and not callable(predicate):
            raise TypeError("micro_pyawk predicate must be callable or None")
        if not callable(action):
            raise TypeError("micro_pyawk action must be callable")
        compiled.append((re.compile(pattern), predicate, action))

    with zopen(filename, mode="rt", encoding="utf-8") as file:
        for line in file:
            for pattern, predicate, action in compiled:
                match = pattern.search(line)
                if match is None:
                    continue
                if predicate is not None and not predicate(results, line):
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
    "make_symmetric_matrix_from_upper_tri",
    "get_angle",
    "str_delimited",
    "micro_pyawk",
]
