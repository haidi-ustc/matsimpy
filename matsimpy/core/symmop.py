"""Symmetry operation (SymmOp) for matsimpy.

Adapted from pymatgen.core.operations.SymmOp.
Provides a minimal but functional implementation for use by calculator IO modules.

Copyright (c) pymatgen Development Team.
Distributed under the MIT License.
Modifications for MatSimPy integration.
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray


class SymmOp:
    """A symmetry operation in 3D space, combining rotation and translation.

    Represented as a 4x4 affine matrix:
        [[Rxx, Rxy, Rxz, Tx],
         [Ryx, Ryy, Ryz, Ty],
         [Rzx, Rzy, Rzz, Tz],
         [  0,   0,   0,  1]]

    where R is the 3x3 rotation matrix and T is the translation vector.

    Adapted from pymatgen.core.operations.SymmOp.
    """

    def __init__(self, affine_matrix: NDArray[np.float64]):
        """Initialize from a 4x4 affine transformation matrix.

        Args:
            affine_matrix: 4x4 numpy array representing the affine transformation.
        """
        self.affine_matrix = np.array(affine_matrix, dtype=np.float64)
        if self.affine_matrix.shape != (4, 4):
            raise ValueError(f"Affine matrix must be 4x4, got {self.affine_matrix.shape}")

    @property
    def rotation_matrix(self) -> NDArray[np.float64]:
        """The 3x3 rotation matrix."""
        return self.affine_matrix[:3, :3]

    @property
    def translation_vector(self) -> NDArray[np.float64]:
        """The 3D translation vector."""
        return self.affine_matrix[:3, 3]

    def operate(self, point: NDArray[np.float64]) -> NDArray[np.float64]:
        """Apply the symmetry operation to a point.

        Args:
            point: 3D coordinate vector.

        Returns:
            Transformed 3D coordinate.
        """
        affine_point = np.append(np.array(point, dtype=np.float64), 1.0)
        return np.dot(self.affine_matrix, affine_point)[:3]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SymmOp):
            return NotImplemented
        return np.allclose(self.affine_matrix, other.affine_matrix)

    def __repr__(self) -> str:
        return f"SymmOp(\n{self.affine_matrix}\n)"

    @staticmethod
    def from_origin_axis_angle(
        origin: NDArray[np.float64],
        axis: NDArray[np.float64],
        angle: float,
    ) -> "SymmOp":
        """Create a SymmOp from a rotation about an axis through a point.

        Args:
            origin: Point the rotation axis passes through (3D vector).
            axis: Direction vector of the rotation axis (3D vector).
            angle: Rotation angle in radians.

        Returns:
            SymmOp representing the rotation about the axis through the origin.
        """
        origin = np.array(origin, dtype=np.float64)
        axis = np.array(axis, dtype=np.float64)

        # Normalize the axis
        norm = np.linalg.norm(axis)
        if norm < 1e-12:
            raise ValueError("Axis vector has zero length")
        axis = axis / norm

        a = np.cos(angle / 2)
        b, c, d = -axis * np.sin(angle / 2)

        # Rotation matrix from quaternion
        rot = np.array([
            [a*a + b*b - c*c - d*d, 2*(b*c - a*d), 2*(b*d + a*c)],
            [2*(b*c + a*d), a*a + c*c - b*b - d*d, 2*(c*d - a*b)],
            [2*(b*d - a*c), 2*(c*d + a*b), a*a + d*d - b*b - c*c],
        ])

        # Translation: origin - R * origin
        trans = origin - np.dot(rot, origin)

        return SymmOp.from_rotation_and_translation(rot, trans)

    @staticmethod
    def from_rotation_and_translation(
        rotation: NDArray[np.float64],
        translation: NDArray[np.float64],
    ) -> "SymmOp":
        """Create a SymmOp from a rotation matrix and translation vector.

        Args:
            rotation: 3x3 rotation matrix.
            translation: 3D translation vector.

        Returns:
            SymmOp combining the rotation and translation.
        """
        rotation = np.array(rotation, dtype=np.float64)
        translation = np.array(translation, dtype=np.float64)
        if rotation.shape != (3, 3):
            raise ValueError(f"Rotation matrix must be 3x3, got {rotation.shape}")
        if translation.shape != (3,):
            raise ValueError(f"Translation must be 3D, got {translation.shape}")

        affine = np.eye(4, dtype=np.float64)
        affine[:3, :3] = rotation
        affine[:3, 3] = translation
        return SymmOp(affine)

    def as_dict(self) -> dict:
        """Serialize to dictionary (MSONable-compatible)."""
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "matrix": self.affine_matrix.tolist(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SymmOp":
        """Deserialize from dictionary."""
        return cls(np.array(d["matrix"]))


__all__ = ["SymmOp"]
