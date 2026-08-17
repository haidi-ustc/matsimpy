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

        first_by_species = self._indices_by_species(first)
        second_by_species = self._indices_by_species(second)
        for symbol, first_indices in sorted(first_by_species.items()):
            if not self._species_sites_match(
                first.frac_positions,
                first_indices,
                second.frac_positions,
                second_by_species[symbol],
            ):
                return False

        return True

    @staticmethod
    def _indices_by_species(crystal: Crystal) -> dict[str, list[int]]:
        indices = defaultdict(list)
        for index, symbol in enumerate(crystal.species):
            indices[symbol].append(index)
        return dict(indices)

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

    def _species_sites_match(
        self,
        first_frac_positions: np.ndarray,
        first_indices: list[int],
        other_frac_positions: np.ndarray,
        candidate_indices: list[int],
    ) -> bool:
        candidate_rows = []
        for first_index in first_indices:
            candidates = []
            for second_index in candidate_indices:
                distance = self._periodic_fractional_distance(
                    first_frac_positions[first_index],
                    other_frac_positions[second_index],
                )
                if distance <= self.stol:
                    candidates.append((second_index, distance))
            if not candidates:
                return False
            candidate_rows.append(
                (
                    first_index,
                    sorted(candidates, key=lambda item: (item[1], item[0])),
                )
            )

        candidate_rows.sort(key=lambda item: (len(item[1]), item[0]))
        return self._has_complete_assignment(candidate_rows, set())

    def _has_complete_assignment(
        self,
        candidate_rows: list[tuple[int, list[tuple[int, float]]]],
        used_indices: set[int],
    ) -> bool:
        if not candidate_rows:
            return True

        _, candidates = candidate_rows[0]
        for second_index, _ in candidates:
            if second_index in used_indices:
                continue
            used_indices.add(second_index)
            if self._has_complete_assignment(candidate_rows[1:], used_indices):
                return True
            used_indices.remove(second_index)
        return False

    @staticmethod
    def _periodic_fractional_distance(
        first_frac_position: np.ndarray,
        second_frac_position: np.ndarray,
    ) -> float:
        delta = np.asarray(first_frac_position) - np.asarray(second_frac_position)
        delta -= np.round(delta)
        return float(np.linalg.norm(delta))
