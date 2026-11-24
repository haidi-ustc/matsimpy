"""Tests for matsimpy.analysis.neighbors."""
import numpy as np
import pytest

from matsimpy.analysis.neighbors import _find_points_in_spheres_numpy, find_points_in_spheres


# find_points_in_spheres uses pymatgen's kernel when it is installed; the NumPy fallback
# must return the same rows, so the result does not depend on what is installed.
@pytest.mark.parametrize("search", [find_points_in_spheres, _find_points_in_spheres_numpy])
def test_one_atom_cube_lists_itself_and_its_six_images(search):
    lattice = 3.0 * np.eye(3)
    coords = np.zeros((1, 3))
    centers, neighbors, images, distances = search(
        coords, coords, r=3.01, pbc=np.array([1, 1, 1]), lattice=lattice, tol=1e-8
    )
    assert centers.tolist() == [0] * 7
    assert neighbors.tolist() == [0] * 7
    rows = sorted((tuple(int(x) for x in image), round(float(d), 12)) for image, d in zip(images, distances))
    expected = sorted(
        [((0, 0, 0), 0.0)]
        + [(tuple(int(x) for x in s * np.eye(3, dtype=int)[axis]), 3.0) for axis in range(3) for s in (-1, 1)]
    )
    assert rows == expected
