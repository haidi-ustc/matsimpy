"""Translation-, permutation-, and lattice-basis-invariant crystal matching."""

from collections import Counter
import itertools

import numpy as np
from scipy.optimize import linear_sum_assignment


def _minimum_image_distances(delta, lattice):
    """Return exact Cartesian minimum-image lengths for fractional vectors.

    Component-wise fractional rounding is only exact for orthogonal cells.  The
    singular-value bound below makes the finite enumeration exact for any
    nonsingular three-dimensional lattice.
    """
    vectors = np.asarray(delta, dtype=float)
    matrix = np.asarray(lattice, dtype=float)
    shape = vectors.shape[:-1]
    result = np.empty(int(np.prod(shape, dtype=int)), dtype=float)
    sigma_min = np.min(np.linalg.svd(matrix, compute_uv=False))
    for index, displacement in enumerate(vectors.reshape(-1, 3)):
        rounded = displacement - np.rint(displacement)
        upper = np.linalg.norm(rounded @ matrix)
        bound = upper / sigma_min + 1e-12
        ranges = [
            range(
                int(np.ceil(-component - bound)),
                int(np.floor(-component + bound)) + 1,
            )
            for component in displacement
        ]
        translations = np.asarray(list(itertools.product(*ranges)), dtype=float)
        result[index] = np.min(
            np.linalg.norm((displacement + translations) @ matrix, axis=1)
        )
    return result.reshape(shape)


def _lengths_angles(matrix):
    lengths = np.linalg.norm(matrix, axis=1)
    pairs = ((1, 2), (0, 2), (0, 1))
    angles = np.array(
        [
            np.degrees(
                np.arccos(
                    np.clip(
                        np.dot(matrix[i], matrix[j]) / (lengths[i] * lengths[j]),
                        -1.0,
                        1.0,
                    )
                )
            )
            for i, j in pairs
        ]
    )
    return lengths, angles


class StructureMatcher:
    def __init__(self, ltol=0.2, stol=0.3, angle_tol=5):
        self.ltol = float(ltol)
        self.stol = float(stol)
        self.angle_tol = float(angle_tol)

    def _basis_candidates(self, target, source):
        """Yield unimodular ``C`` for which ``C @ source`` matches target."""
        target_lengths, target_angles = _lengths_angles(target)
        sigma_min = np.min(np.linalg.svd(source, compute_uv=False))
        row_choices = []
        for length in target_lengths:
            bound = int(np.ceil(length * (1.0 + self.ltol) / sigma_min))
            choices = []
            for coefficients in itertools.product(range(-bound, bound + 1), repeat=3):
                if coefficients == (0, 0, 0):
                    continue
                candidate_length = np.linalg.norm(np.asarray(coefficients) @ source)
                relative = abs(candidate_length - length) / max(candidate_length, length)
                if relative <= self.ltol + 1e-12:
                    choices.append(coefficients)
            row_choices.append(choices)

        for rows in itertools.product(*row_choices):
            transform = np.asarray(rows, dtype=int)
            determinant = np.linalg.det(transform)
            if abs(abs(determinant) - 1.0) > 1e-8:
                continue
            candidate = transform @ source
            lengths, angles = _lengths_angles(candidate)
            if np.any(
                np.abs(lengths - target_lengths)
                / np.maximum(lengths, target_lengths)
                > self.ltol + 1e-12
            ):
                continue
            if np.any(np.abs(angles - target_angles) > self.angle_tol + 1e-12):
                continue
            yield transform

    def _fit_basis(self, a, b, transform):
        groups_a = {s: np.flatnonzero(np.asarray(a.species) == s) for s in set(a.species)}
        groups_b = {s: np.flatnonzero(np.asarray(b.species) == s) for s in set(b.species)}
        anchor = min(groups_a, key=lambda s: (len(groups_a[s]), s))
        positions_b = np.asarray(b.frac_positions) @ np.linalg.inv(transform)
        origin = a.frac_positions[groups_a[anchor][0]]
        lattice = np.asarray(a.lattice.matrix)
        free_length = (abs(np.linalg.det(lattice)) / len(a)) ** (1.0 / 3.0)

        for candidate in groups_b[anchor]:
            translation = origin - positions_b[candidate]
            valid = True
            for species, indices_a in groups_a.items():
                indices_b = groups_b[species]
                delta = (
                    a.frac_positions[indices_a, None, :]
                    - (positions_b[indices_b, :] + translation)[None, :, :]
                )
                distances = _minimum_image_distances(delta, lattice)
                rows, columns = linear_sum_assignment(distances)
                if np.any(distances[rows, columns] / free_length > self.stol + 1e-12):
                    valid = False
                    break
            if valid:
                return True
        return False

    def fit(self, a, b):
        if len(a) != len(b) or Counter(a.species) != Counter(b.species):
            return False
        lattice_a = np.asarray(a.lattice.matrix, dtype=float)
        lattice_b = np.asarray(b.lattice.matrix, dtype=float)
        for transform in self._basis_candidates(lattice_a, lattice_b):
            if self._fit_basis(a, b, transform):
                return True
        return False
