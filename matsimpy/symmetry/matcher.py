"""Translation- and permutation-invariant crystal matching."""

from collections import Counter

import numpy as np
from scipy.optimize import linear_sum_assignment


class StructureMatcher:
    def __init__(self, ltol=0.2, stol=0.3, angle_tol=5):
        self.ltol = float(ltol)
        self.stol = float(stol)
        self.angle_tol = float(angle_tol)

    @staticmethod
    def _parameters(structure):
        lattice = structure.lattice
        return np.array([lattice.a, lattice.b, lattice.c]), np.array(
            [lattice.alpha, lattice.beta, lattice.gamma]
        )

    def fit(self, a, b):
        if len(a) != len(b) or Counter(a.species) != Counter(b.species):
            return False
        lengths_a, angles_a = self._parameters(a)
        lengths_b, angles_b = self._parameters(b)
        if np.any(np.abs(lengths_a - lengths_b) / np.maximum(lengths_a, lengths_b) > self.ltol):
            return False
        if np.any(np.abs(angles_a - angles_b) > self.angle_tol):
            return False

        groups_a = {s: np.flatnonzero(np.asarray(a.species) == s) for s in set(a.species)}
        groups_b = {s: np.flatnonzero(np.asarray(b.species) == s) for s in set(b.species)}
        anchor = min(groups_a, key=lambda s: (len(groups_a[s]), s))
        origin = a.frac_positions[groups_a[anchor][0]]
        free_length = (abs(np.linalg.det(a.lattice.matrix)) / len(a)) ** (1.0 / 3.0)

        for candidate in groups_b[anchor]:
            translation = origin - b.frac_positions[candidate]
            valid = True
            for species, indices_a in groups_a.items():
                indices_b = groups_b[species]
                delta = (
                    a.frac_positions[indices_a, None, :]
                    - (b.frac_positions[indices_b, :] + translation)[None, :, :]
                )
                delta -= np.rint(delta)
                distances = np.linalg.norm(delta @ a.lattice.matrix, axis=2)
                rows, columns = linear_sum_assignment(distances)
                if np.any(distances[rows, columns] / free_length > self.stol):
                    valid = False
                    break
            if valid:
                return True
        return False
