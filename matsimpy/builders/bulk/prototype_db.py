"""Prototype databases from structure files, and structures from a prototype.

The prototype identifier and the read-only :class:`PrototypeDatabase` are in
:mod:`matsimpy.symmetry.prototype`; this module adds the parts that read
structure files and substitute elements.
"""

from __future__ import annotations

import logging
import math
import os
from collections.abc import Iterable, Mapping, Sequence
from itertools import islice, product

from ...core import Crystal, Element
from ...core._validation import normalize_species
from ...io import read
from ...symmetry.prototype import PrototypeDatabase
from ...transformation.chemical import substitute

logger = logging.getLogger(__name__)

__all__ = ["build_prototype_database", "structures_from_prototype", "suggest_element_substitutions"]


def build_prototype_database(
    structure_files: Iterable[str | os.PathLike[str]],
    symprec: float | None = None,
    database: PrototypeDatabase | None = None,
) -> PrototypeDatabase:
    """Return a database mapping each file's prototype to the file's base name.

    Files are read with :func:`matsimpy.io.read`.  If ``database`` is given,
    the new entries are merged into a copy of it.  Read and analysis errors
    propagate, so a partial database is never returned.
    """
    structures = [(os.path.basename(os.fspath(path)), read(os.fspath(path))) for path in structure_files]
    base = PrototypeDatabase() if database is None else database
    return base.with_structures(structures, symprec=symprec)


def suggest_element_substitutions(elements: Sequence[str]) -> dict[str, list[str]]:
    """Suggest same-family replacements for each element.

    Transition metals get every transition metal of periods 1-6; other
    elements get the members of their group up to period 6.  Lists are in a
    fixed order.  A symbol that is not an element is returned unchanged.
    """
    transition_metals = sorted(
        element.symbol
        for z in range(1, 119)
        if (element := Element.from_Z(z)).is_transition_metal and element.period is not None and element.period <= 6
    )
    result = {}
    for symbol in elements:
        try:
            element = Element(normalize_species(symbol, allow_dummy=False))
        except (TypeError, ValueError):
            result[symbol] = [symbol]
            continue
        if element.is_transition_metal:
            result[symbol] = list(transition_metals)
        elif element.group is not None:
            same_group = [
                candidate.symbol
                for candidate in Element.get_elements_by_group(element.group)
                if candidate.period is not None and candidate.period <= 6
            ]
            result[symbol] = same_group or [element.symbol]
        else:
            result[symbol] = [element.symbol]
    return result


def _normalized_substitutions(substitutions: Mapping[str, Sequence[str]], present: Sequence[str]):
    normalized: dict[str, list[str]] = {}
    for original, options in substitutions.items():
        key = normalize_species(original, allow_dummy=False)
        if key in normalized:
            raise ValueError(f"duplicate substitution key after normalization: {key}")
        if isinstance(options, (str, bytes)) or not isinstance(options, Sequence):
            raise TypeError(f"substitutions for {key} must be a non-empty sequence of elements")
        if not options:
            raise ValueError(f"substitutions for {key} must be a non-empty sequence of elements")
        try:
            normalized[key] = [normalize_species(option, allow_dummy=False) for option in options]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"substitutions for {key} contain an invalid element: {exc}") from exc
    absent = sorted(set(normalized) - set(present))
    if absent:
        raise ValueError("substitution elements not present in template: " + ", ".join(absent))
    return normalized


def structures_from_prototype(
    database: PrototypeDatabase,
    prototype: str,
    structures_dir: str | os.PathLike[str] = ".",
    element_substitutions: Mapping[str, Sequence[str]] | None = None,
    max_structures: int | None = None,
) -> list[Crystal]:
    """Generate crystals from a prototype's first template by element substitution.

    The template is the first structure id of ``prototype`` in ``database``,
    read from ``structures_dir``.  Every combination of the substitution
    options is generated (all elements are replaced at once), at most
    ``max_structures`` of them.  Without ``element_substitutions`` the
    suggestions of :func:`suggest_element_substitutions` are used.
    """
    if isinstance(max_structures, bool) or (max_structures is not None and not isinstance(max_structures, int)):
        raise TypeError("max_structures must be a non-negative integer or None")
    if max_structures is not None and max_structures < 0:
        raise ValueError("max_structures must be a non-negative integer or None")
    if prototype not in database:
        raise ValueError(f"No template structure found for prototype: {prototype}")

    template_path = os.path.join(os.fspath(structures_dir), database[prototype][0])
    try:
        template = read(template_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Template structure file not found: {template_path}") from exc
    if not isinstance(template, Crystal):
        raise TypeError(f"Expected Crystal template, got {type(template).__name__}")

    present = sorted(set(template.species))
    if element_substitutions is None:
        options = suggest_element_substitutions(present)
    else:
        options = _normalized_substitutions(element_substitutions, present)

    keys = list(options)
    total = math.prod(len(options[key]) for key in keys)
    combinations = product(*(options[key] for key in keys))
    if max_structures is not None:
        combinations = islice(combinations, max_structures)
    logger.info(
        "Generating up to %s structures from %s substitution combinations",
        total if max_structures is None else min(max_structures, total),
        total,
    )

    indices = list(range(len(template)))
    structures = []
    for combination in combinations:
        chosen = dict(zip(keys, combination))
        structures.append(substitute(template, indices, {s: chosen.get(s, s) for s in present}))
    return structures
