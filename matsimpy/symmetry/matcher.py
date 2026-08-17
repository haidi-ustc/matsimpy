"""Native periodic structure matching utilities."""

from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from matsimpy.core import Crystal


class StructureMatcher:
    """Compare crystals by composition, lattice, and periodic fractional sites."""

    def __init__(
        self,
        ltol: float = 0.2,
        stol: float = 0.3,
        angle_tol: float = 5.0,
    ) -> None:
        self.ltol = ltol
        self.stol = stol
        self.angle_tol = angle_tol

    def fit(self, first: Crystal, second: Crystal) -> bool:
        """Return True when two crystals match within configured tolerances."""
        if Counter(first.species) != Counter(second.species):
            return False
        if not self._lattices_match(first, second):
            return False

        unmatched = defaultdict(list)
        for index, symbol in enumerate(second.species):
            unmatched[symbol].append(index)

        for symbol, frac_position in zip(first.species, first.frac_positions):
            match_index = self._find_site_match(
                frac_position,
                second.frac_positions,
                unmatched[symbol],
            )
            if match_index is None:
                return False
            unmatched[symbol].remove(match_index)

        return True

    def _lattices_match(self, first: Crystal, second: Crystal) -> bool:
        lengths1 = np.array([first.lattice.a, first.lattice.b, first.lattice.c])
        lengths2 = np.array([second.lattice.a, second.lattice.b, second.lattice.c])
        length_scale = np.maximum(np.maximum(np.abs(lengths1), np.abs(lengths2)), 1.0)
        if np.any(np.abs(lengths1 - lengths2) > self.ltol * length_scale):
            return False

        angles1 = np.array(
            [first.lattice.alpha, first.lattice.beta, first.lattice.gamma]
        )
        angles2 = np.array(
            [second.lattice.alpha, second.lattice.beta, second.lattice.gamma]
        )
        return bool(np.all(np.abs(angles1 - angles2) <= self.angle_tol))

    def _find_site_match(
        self,
        frac_position: np.ndarray,
        other_frac_positions: np.ndarray,
        candidate_indices: list[int],
    ) -> int | None:
        for index in candidate_indices:
            delta = np.asarray(frac_position) - other_frac_positions[index]
            delta -= np.round(delta)
            if float(np.linalg.norm(delta)) <= self.stol:
                return index
        return None
