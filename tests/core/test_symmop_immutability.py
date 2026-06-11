"""Regression tests for SymmOp matrix immutability."""

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
