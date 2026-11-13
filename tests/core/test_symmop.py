"""Tests for SymmOp: construction and immutability."""

import numpy as np
import pytest

from matsimpy.core.symmop import SymmOp


def test_affine_matrix_is_read_only_and_cannot_change_operation():
    op = SymmOp.from_rotation_and_translation(np.eye(3), np.array([1.0, 2.0, 3.0]))

    with pytest.raises(ValueError):
        op.affine_matrix[0, 3] = 99.0

    np.testing.assert_array_equal(op.operate(np.array([0.0, 0.0, 0.0])), [1.0, 2.0, 3.0])


def test_rotation_matrix_is_read_only_snapshot():
    op = SymmOp.from_rotation_and_translation(np.eye(3), np.array([1.0, 2.0, 3.0]))
    rotation = op.rotation_matrix

    with pytest.raises(ValueError):
        rotation[0, 0] = 99.0

    np.testing.assert_array_equal(op.rotation_matrix, np.eye(3))
    np.testing.assert_array_equal(op.operate(np.array([1.0, 0.0, 0.0])), [2.0, 2.0, 3.0])


def test_translation_vector_is_read_only_snapshot():
    op = SymmOp.from_rotation_and_translation(np.eye(3), np.array([1.0, 2.0, 3.0]))
    translation = op.translation_vector

    with pytest.raises(ValueError):
        translation[0] = 99.0

    np.testing.assert_array_equal(op.translation_vector, [1.0, 2.0, 3.0])
    np.testing.assert_array_equal(op.operate(np.array([0.0, 0.0, 0.0])), [1.0, 2.0, 3.0])


def test_from_origin_axis_angle_is_right_handed_in_degrees():
    op = SymmOp.from_origin_axis_angle([0, 0, 0], [0, 0, 1], 90)
    np.testing.assert_allclose(op.operate([1, 0, 0]), [0, 1, 0], atol=1e-12)
    op_rad = SymmOp.from_origin_axis_angle([0, 0, 0], [0, 0, 1], np.pi / 2, angle_in_radians=True)
    np.testing.assert_allclose(op_rad.affine_matrix, op.affine_matrix, atol=1e-12)


def test_from_origin_axis_angle_matches_pymatgen():
    pmg = pytest.importorskip("pymatgen.core.operations")
    origin, axis, angle = [1.0, -2.0, 0.5], [0.3, -0.2, 0.9], 37.0
    ours = SymmOp.from_origin_axis_angle(origin, axis, angle)
    ref = pmg.SymmOp.from_origin_axis_angle(origin, axis, angle)
    np.testing.assert_allclose(ours.affine_matrix, ref.affine_matrix, atol=1e-10)


@pytest.mark.parametrize("origin, angle", [([0, 0], 90), ([0, 0, 0], float("nan"))])
def test_from_origin_axis_angle_rejects_bad_input(origin, angle):
    with pytest.raises(ValueError):
        SymmOp.from_origin_axis_angle(origin, [0, 0, 1], angle)


def test_operate_multi_matches_operate():
    rotation = SymmOp.from_origin_axis_angle([0, 0, 0], [1, 1, 0], 37.0).rotation_matrix
    op = SymmOp.from_rotation_and_translation(rotation, [0.1, -0.2, 0.3])
    pts = np.random.default_rng(1).random((5, 3))
    np.testing.assert_allclose(op.operate_multi(pts), [op.operate(p) for p in pts], atol=1e-14, rtol=0)


def test_translation_defaults_to_zero():
    assert np.array_equal(SymmOp.from_rotation_and_translation(np.eye(3)).translation_vector, np.zeros(3))
