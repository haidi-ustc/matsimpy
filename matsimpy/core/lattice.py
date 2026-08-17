"""
Lattice module for MatSimPy.

This module provides the Lattice class for representing crystal lattice structures.
The Lattice class supports flexible input formats and provides convenient constructors
for common crystal systems (cubic, tetragonal, orthorhombic, hexagonal, etc.).

The Lattice class handles:
- Multiple input formats (scalar, list, full matrix)
- Coordinate transformations (fractional ↔ Cartesian)
- Lattice parameter calculations (a, b, c, α, β, γ)
- Reciprocal lattice calculations
- Validation and error checking

Example:
    >>> from matsimpy.core.lattice import Lattice
    >>>
    >>> # Create cubic lattice (convenient syntax)
    >>> lat = Lattice(5.0)
    >>> print(lat.a)  # 5.0
    >>>
    >>> # Create orthorhombic lattice
    >>> lat = Lattice([3, 4, 5])
    >>> print(lat.a, lat.b, lat.c)  # 3.0 4.0 5.0
    >>>
    >>> # Create from full lattice vectors
    >>> lat = Lattice([[5, 0, 0], [0, 5, 0], [0, 0, 5]])
    >>>
    >>> # Use class methods for specific crystal systems
    >>> lat = Lattice.cubic(5.0)
    >>> lat = Lattice.hexagonal(3.0, 5.0)
    >>> lat = Lattice.from_parameters(5.0, 5.0, 5.0, 90, 90, 90)
"""

import numpy as np
from typing import List, Union, Optional, Dict, Any
from monty.json import MSONable
from matsimpy.constants import LATTICE_TOL


class Lattice(MSONable):
    """
    Represents a crystal lattice with flexible input formats.

    The Lattice class provides a convenient interface for working with crystal
    lattices. It supports multiple input formats and provides methods for
    coordinate transformations, parameter calculations, and lattice operations.

    Attributes:
        lattice_vectors (np.ndarray): 3x3 array of lattice vectors.
        matrix (np.ndarray): Lattice vectors as a 3x3 matrix (property).
        inv_matrix (np.ndarray): Cached inverse of lattice matrix (property).
        a (float): Length of a lattice vector (property).
        b (float): Length of b lattice vector (property).
        c (float): Length of c lattice vector (property).
        alpha (float): Angle between b and c vectors in degrees (property).
        beta (float): Angle between a and c vectors in degrees (property).
        gamma (float): Angle between a and b vectors in degrees (property).

    Args:
        lattice_vectors: Can be:
            - float/int: Single value for cubic lattice (a=b=c)
            - List[float]: Three values [a, b, c] for orthorhombic lattice
            - List[List[float]]: Full 3x3 lattice vectors matrix

    Raises:
        ValueError: If input format is invalid, lattice parameters are non-positive,
                   lattice vectors are degenerate, or volume is too small.
        TypeError: If lattice_vectors is not a valid type.

    Examples:
        >>> # Cubic lattice (convenient syntax)
        >>> lat = Lattice(5.0)
        >>> lat.a, lat.b, lat.c
        (5.0, 5.0, 5.0)
        >>>
        >>> # Orthorhombic lattice
        >>> lat = Lattice([3, 4, 5])
        >>> lat.a, lat.b, lat.c
        (3.0, 4.0, 5.0)
        >>>
        >>> # Full lattice vectors
        >>> lat = Lattice([[5, 0, 0], [0, 5, 0], [0, 0, 5]])
        >>> lat.volume
        125.0
        >>>
        >>> # Use class methods
        >>> lat = Lattice.cubic(5.0)
        >>> lat = Lattice.hexagonal(3.0, 5.0)
        >>> lat = Lattice.from_parameters(5.0, 5.0, 5.0, 90, 90, 90)
    """

    def __init__(
        self, lattice_vectors: Union[float, int, List[float], List[List[float]]]
    ):
        """
        Initialize a Lattice object with flexible input formats.

        Supports multiple convenient input formats:
        - Full lattice vectors: [[a1,a2,a3], [b1,b2,b3], [c1,c2,c3]]
        - Cubic: single number (e.g., 5 or 5.0) -> cubic lattice with that parameter
        - Orthorhombic box: list of 3 numbers [a, b, c] -> orthorhombic lattice

        Args:
            lattice_vectors: Can be:
                - List[List[float]]: Full 3x3 lattice vectors
                - float/int: Single value for cubic lattice (a=b=c)
                - List[float]: Three values [a, b, c] for orthorhombic lattice

        Raises:
            ValueError: If input format is invalid or lattice vectors are degenerate.

        Examples:
            >>> # Traditional full lattice vectors
            >>> lat = Lattice([[5, 0, 0], [0, 5, 0], [0, 0, 5]])

            >>> # Convenient cubic syntax
            >>> lat = Lattice(5)  # cubic with a=5

            >>> # Convenient orthorhombic box syntax
            >>> lat = Lattice([3, 4, 5])  # orthorhombic with a=3, b=4, c=5
        """
        # Handle different input formats
        if isinstance(lattice_vectors, (int, float, np.integer, np.floating)):
            # Single number -> cubic lattice
            a = float(lattice_vectors)
            if a <= 0:
                raise ValueError(f"Lattice parameter must be positive, got {a}")
            self.lattice_vectors = np.array(
                [[a, 0.0, 0.0], [0.0, a, 0.0], [0.0, 0.0, a]], dtype=float
            )
        elif isinstance(lattice_vectors, (list, np.ndarray)):
            # Convert to numpy array for uniform handling
            arr = np.array(lattice_vectors, dtype=float, copy=True)
            if arr.ndim == 1 and len(arr) == 3:
                # List of 3 numbers -> orthorhombic lattice
                a, b, c = arr
                if a <= 0 or b <= 0 or c <= 0:
                    raise ValueError(
                        f"Lattice parameters must be positive, got [{a}, {b}, {c}]"
                    )
                self.lattice_vectors = np.array(
                    [[a, 0.0, 0.0], [0.0, b, 0.0], [0.0, 0.0, c]], dtype=float
                )
            elif arr.ndim == 2 and arr.shape == (3, 3):
                # Full 3x3 lattice vectors
                self.lattice_vectors = arr
            else:
                raise ValueError(
                    f"Invalid lattice_vectors shape: {arr.shape}. "
                    f"Expected 3x3 matrix, 1x3 array, or scalar."
                )
        else:
            raise TypeError(
                f"lattice_vectors must be numeric scalar, list, or numpy array, "
                f"got {type(lattice_vectors)}"
            )

        self._validate_lattice_vectors()
        # Make lattice_vectors read-only so that in-place mutation cannot
        # silently invalidate the cached _inv_matrix or other derived quantities.
        self.lattice_vectors.flags.writeable = False
        # Cache inverse matrix eagerly to avoid thread-unsafe lazy init.
        inv = np.linalg.inv(self.matrix)
        inv.flags.writeable = False
        self._inv_matrix: np.ndarray = inv

    def _validate_lattice_vectors(self) -> None:
        """
        Validate lattice vectors for correctness.

        Performs comprehensive validation including:
        - Dimensionality check (must be 3D)
        - Finite value check (no NaN or Inf)
        - Linear independence check (determinant must be non-zero)
        - Volume check (volume must be reasonable)

        Raises:
            ValueError: If the lattice vectors are invalid, contain non-finite values,
                       are linearly dependent, or have too small volume.

        Note:
            This is an internal method called automatically during initialization.
        """
        if len(self.lattice_vectors) != 3:
            raise ValueError("Lattice vectors must be 3-dimensional.")

        # Check for NaN or Inf values
        if not np.all(np.isfinite(self.lattice_vectors)):
            raise ValueError("Lattice vectors must contain finite values.")

        # Check determinant
        det = np.linalg.det(self.matrix)
        if np.isclose(det, 0, atol=1e-10):
            raise ValueError("Lattice vectors must be linearly independent.")

        # Check volume is reasonable
        volume = self.volume
        if volume <= 1e-10:  # Very small volume
            raise ValueError(f"Lattice volume is too small: {volume}")

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation for serialization.

        Implements the MSONable interface for JSON serialization.
        The dictionary includes module and class information for proper
        deserialization.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - @module: Module path of the class
                - @class: Class name
                - lattice_vectors: Lattice vectors as list (rounded to 8 decimals)

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> d = lat.as_dict()
            >>> d['lattice_vectors']
            [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]]
        """
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "lattice_vectors": np.round(self.lattice_vectors, decimals=8).tolist(),
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Lattice":
        """
        Create Lattice object from dictionary representation.

        Implements the MSONable interface for JSON deserialization.
        Restores a Lattice object from its dictionary representation.

        Args:
            d: Dictionary containing 'lattice_vectors' key and optionally
               '@module' and '@class' keys.

        Returns:
            Lattice: A new Lattice instance.

        Raises:
            KeyError: If 'lattice_vectors' key is missing from dictionary.
            ValueError: If lattice_vectors are invalid.

        Example:
            >>> d = {
            ...     '@module': 'matsimpy.core.lattice',
            ...     '@class': 'Lattice',
            ...     'lattice_vectors': [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 5.0]]
            ... }
            >>> lat = Lattice.from_dict(d)
            >>> lat.a
            5.0
        """
        lattice_vectors = d["lattice_vectors"]
        return cls(lattice_vectors)

    @property
    def matrix(self) -> np.ndarray:
        """
        Get the lattice vectors as a matrix.

        Returns:
            np.ndarray: Lattice vectors as a 3x3 matrix where each row is a lattice vector.

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> mat = lat.matrix
            >>> mat.shape
            (3, 3)
            >>> mat[0]  # First lattice vector
            array([5., 0., 0.])
        """
        return self.lattice_vectors.reshape((3, 3))

    @property
    def inv_matrix(self) -> np.ndarray:
        """
        Get the cached inverse of the lattice matrix.

        The inverse matrix is computed once and cached for performance.
        Used for converting Cartesian coordinates to fractional coordinates.

        Returns:
            np.ndarray: Inverse of the lattice matrix (3x3).

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> inv = lat.inv_matrix
            >>> np.dot(lat.matrix, inv)  # Should be identity matrix
            array([[1., 0., 0.],
                   [0., 1., 0.],
                   [0., 0., 1.]])
        """
        return self._inv_matrix

    @property
    def a(self) -> float:
        """
        Get the length of the a lattice vector.

        Returns:
            float: Length of the first lattice vector in Angstroms.

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> lat.a
            5.0
        """
        return np.linalg.norm(self.lattice_vectors[0])

    @property
    def b(self) -> float:
        """
        Get the length of the b lattice vector.

        Returns:
            float: Length of the second lattice vector in Angstroms.

        Example:
            >>> lat = Lattice([3, 4, 5])
            >>> lat.b
            4.0
        """
        return np.linalg.norm(self.lattice_vectors[1])

    @property
    def c(self) -> float:
        """
        Get the length of the c lattice vector.

        Returns:
            float: Length of the third lattice vector in Angstroms.

        Example:
            >>> lat = Lattice([3, 4, 5])
            >>> lat.c
            5.0
        """
        return np.linalg.norm(self.lattice_vectors[2])

    @property
    def alpha(self) -> float:
        """
        Get the angle between the b and c lattice vectors.

        Returns:
            float: Angle α in degrees (0-180°).

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> lat.alpha
            90.0
        """
        return np.degrees(
            np.arccos(
                np.dot(self.lattice_vectors[1], self.lattice_vectors[2])
                / (self.b * self.c)
            )
        )

    @property
    def beta(self) -> float:
        """
        Get the angle between the a and c lattice vectors.

        Returns:
            float: Angle β in degrees (0-180°).

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> lat.beta
            90.0
        """
        return np.degrees(
            np.arccos(
                np.dot(self.lattice_vectors[0], self.lattice_vectors[2])
                / (self.a * self.c)
            )
        )

    @property
    def gamma(self) -> float:
        """
        Get the angle between the a and b lattice vectors.

        Returns:
            float: Angle γ in degrees (0-180°).

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> lat.gamma
            90.0
            >>> lat = Lattice.hexagonal(3.0, 5.0)
            >>> lat.gamma
            120.0
        """
        return np.degrees(
            np.arccos(
                np.dot(self.lattice_vectors[0], self.lattice_vectors[1])
                / (self.a * self.b)
            )
        )

    @property
    def volume(self) -> float:
        """
        Calculate the volume of the unit cell.

        The volume is calculated as the absolute value of the determinant
        of the lattice matrix.

        Returns:
            float: Unit cell volume in cubic Angstroms (Å³).

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> lat.volume
            125.0
            >>> lat = Lattice([3, 4, 5])
            >>> lat.volume
            60.0
        """
        return abs(np.linalg.det(self.matrix))

    def _format_lattice_params(self, include_units: bool = True) -> str:
        """
        Format lattice parameters as a string.

        Helper method to avoid duplication between Lattice and Crystal __str__ methods.
        Matches the format used in Crystal.__str__.

        Args:
            include_units: If True, include Å units for lengths (default: True).

        Returns:
            str: Formatted string with lattice parameters on two lines.
                 First line: lengths (a, b, c)
                 Second line: angles (α, β, γ)

        Note:
            This is an internal method used by __str__.

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> lat._format_lattice_params()
            'a=5.0000 Å, b=5.0000 Å, c=5.0000 Å\\n           α=90.00°, β=90.00°, γ=90.00°'
        """
        if include_units:
            lengths = f"a={self.a:.4f} Å, b={self.b:.4f} Å, c={self.c:.4f} Å"
        else:
            lengths = f"a={self.a:.4f}, b={self.b:.4f}, c={self.c:.4f}"

        angles = f"α={self.alpha:.2f}°, β={self.beta:.2f}°, γ={self.gamma:.2f}°"

        return f"{lengths}\n           {angles}"

    def __str__(self) -> str:
        """
        Human-readable string representation of the lattice.

        Returns:
            String showing lattice parameters and vectors.
        """
        # Format lattice parameters (matching Crystal format)
        params = self._format_lattice_params(include_units=True)

        # Format lattice vectors
        vectors = [
            f"  [{vector[0]:8.4f} {vector[1]:8.4f} {vector[2]:8.4f}]"
            for vector in self.lattice_vectors
        ]

        return (
            f"Lattice: {params}\n"
            f"Lattice vectors:\n{vectors[0]}\n{vectors[1]}\n{vectors[2]}"
        )

    def __repr__(self) -> str:
        """
        Unambiguous string representation for debugging.

        Returns a string that can be used to recreate the Lattice object.

        Returns:
            String representation that can be evaluated to recreate the lattice.
        """
        # Round to 8 decimal places for consistency with as_dict
        rounded_vectors = np.round(self.lattice_vectors, decimals=8).tolist()
        return f"Lattice(lattice_vectors={rounded_vectors})"

    @classmethod
    def from_parameters(
        cls, a: float, b: float, c: float, alpha: float, beta: float, gamma: float
    ) -> "Lattice":
        """
        Create a Lattice object from lattice parameters.

        Constructs a lattice from the six lattice parameters (a, b, c, α, β, γ).
        This is the standard way to specify a crystal lattice.

        Args:
            a: Length of the a lattice vector in Angstroms.
            b: Length of the b lattice vector in Angstroms.
            c: Length of the c lattice vector in Angstroms.
            alpha: Angle between b and c vectors in degrees (0-180°).
            beta: Angle between a and c vectors in degrees (0-180°).
            gamma: Angle between a and b vectors in degrees (0-180°).

        Returns:
            Lattice: A new Lattice instance.

        Raises:
            ValueError: If any lattice parameter is non-positive.
            ValueError: If gamma is 0 or 180 degrees (would make a and b vectors parallel,
                       resulting in a linearly dependent lattice).

        Example:
            >>> # Cubic lattice
            >>> lat = Lattice.from_parameters(5.0, 5.0, 5.0, 90, 90, 90)
            >>> lat.a, lat.alpha
            (5.0, 90.0)
            >>>
            >>> # Hexagonal lattice
            >>> lat = Lattice.from_parameters(3.0, 3.0, 5.0, 90, 90, 120)
            >>> lat.gamma
            120.0
        """
        for param in [a, b, c]:
            if param <= 0:
                raise ValueError(f"Lattice parameter must be positive, got {param}")

        for angle_name, angle in [("alpha", alpha), ("beta", beta), ("gamma", gamma)]:
            if not (0 < angle < 180):
                raise ValueError(
                    f"Invalid {angle_name} angle: {angle} degrees. "
                    f"Angles must be between 0 and 180 degrees (exclusive)."
                )

        alpha = np.radians(alpha)
        beta = np.radians(beta)
        gamma = np.radians(gamma)

        cos_alpha = np.cos(alpha)
        cos_beta = np.cos(beta)
        cos_gamma = np.cos(gamma)
        sin_gamma = np.sin(gamma)

        # Check for invalid gamma values (0 or 180 degrees)
        # This would make a and b vectors parallel, resulting in a linearly dependent lattice
        if np.isclose(abs(sin_gamma), 0, atol=1e-10):
            raise ValueError(
                f"Invalid gamma angle: {np.degrees(gamma):.2f} degrees. "
                "Gamma cannot be 0 or 180 degrees as this would make the a and b "
                "lattice vectors parallel, resulting in a linearly dependent lattice."
            )

        a1 = a
        a2 = b * cos_gamma
        a3 = c * cos_beta
        b2 = b * sin_gamma
        b3 = (c * (cos_alpha - cos_beta * cos_gamma)) / sin_gamma
        c3 = np.sqrt(c**2 - a3**2 - b3**2)

        lattice_vectors = [[a1, 0.0, 0.0], [a2, b2, 0.0], [a3, b3, c3]]

        return cls(lattice_vectors)

    @classmethod
    def cubic(cls, a: float) -> "Lattice":
        """
        Create a cubic lattice.

        All three lattice vectors have the same length and are mutually perpendicular.

        Args:
            a: Length of all three lattice vectors in Angstroms (a = b = c).

        Returns:
            Lattice: A new cubic Lattice instance.

        Raises:
            ValueError: If a is non-positive.

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> lat.a, lat.b, lat.c
            (5.0, 5.0, 5.0)
            >>> lat.alpha, lat.beta, lat.gamma
            (90.0, 90.0, 90.0)
        """
        lattice_vectors = [[a, 0.0, 0.0], [0.0, a, 0.0], [0.0, 0.0, a]]
        return cls(lattice_vectors)

    @classmethod
    def tetragonal(cls, a: float, c: float) -> "Lattice":
        """
        Create a tetragonal lattice.

        Two lattice vectors have the same length (a = b), and all angles are 90°.

        Args:
            a: Length of a and b lattice vectors in Angstroms (a = b).
            c: Length of c lattice vector in Angstroms.

        Returns:
            Lattice: A new tetragonal Lattice instance.

        Raises:
            ValueError: If a or c is non-positive.

        Example:
            >>> lat = Lattice.tetragonal(4.0, 5.0)
            >>> lat.a, lat.b, lat.c
            (4.0, 4.0, 5.0)
            >>> lat.alpha, lat.beta, lat.gamma
            (90.0, 90.0, 90.0)
        """
        lattice_vectors = [[a, 0.0, 0.0], [0.0, a, 0.0], [0.0, 0.0, c]]
        return cls(lattice_vectors)

    @classmethod
    def orthorhombic(cls, a: float, b: float, c: float) -> "Lattice":
        """
        Create an orthorhombic lattice.

        All three lattice vectors have different lengths, and all angles are 90°.

        Args:
            a: Length of a lattice vector in Angstroms.
            b: Length of b lattice vector in Angstroms.
            c: Length of c lattice vector in Angstroms.

        Returns:
            Lattice: A new orthorhombic Lattice instance.

        Raises:
            ValueError: If any parameter is non-positive.

        Example:
            >>> lat = Lattice.orthorhombic(3.0, 4.0, 5.0)
            >>> lat.a, lat.b, lat.c
            (3.0, 4.0, 5.0)
            >>> lat.alpha, lat.beta, lat.gamma
            (90.0, 90.0, 90.0)
        """
        lattice_vectors = [[a, 0.0, 0.0], [0.0, b, 0.0], [0.0, 0.0, c]]
        return cls(lattice_vectors)

    @classmethod
    def hexagonal(cls, a: float, c: float) -> "Lattice":
        """
        Create a hexagonal lattice.

        Two lattice vectors have the same length (a = b), with γ = 120° and α = β = 90°.

        Args:
            a: Length of a and b lattice vectors in Angstroms (a = b).
            c: Length of c lattice vector in Angstroms.

        Returns:
            Lattice: A new hexagonal Lattice instance.

        Raises:
            ValueError: If a or c is non-positive.

        Example:
            >>> lat = Lattice.hexagonal(3.0, 5.0)
            >>> lat.a, lat.b, lat.c
            (3.0, 3.0, 5.0)
            >>> lat.alpha, lat.beta, lat.gamma
            (90.0, 90.0, 120.0)
        """
        # Standard hexagonal lattice vectors
        # a = b, alpha = beta = 90°, gamma = 120°
        lattice_vectors = [
            [a, 0.0, 0.0],
            [-a / 2, a * np.sqrt(3) / 2, 0.0],
            [0.0, 0.0, c],
        ]
        return cls(lattice_vectors)

    @classmethod
    def rhombohedral(cls, a: float, alpha: float) -> "Lattice":
        """
        Create a rhombohedral lattice.

        All three lattice vectors have the same length, and all angles are equal.

        Args:
            a: Length of all three lattice vectors in Angstroms (a = b = c).
            alpha: Angle between all lattice vectors in degrees (α = β = γ).

        Returns:
            Lattice: A new rhombohedral Lattice instance.

        Raises:
            ValueError: If a is non-positive or alpha is invalid.

        Example:
            >>> lat = Lattice.rhombohedral(5.0, 60.0)
            >>> lat.a, lat.b, lat.c
            (5.0, 5.0, 5.0)
            >>> lat.alpha, lat.beta, lat.gamma
            (60.0, 60.0, 60.0)
        """
        # Use from_parameters for rhombohedral (a = b = c, alpha = beta = gamma)
        return cls.from_parameters(a=a, b=a, c=a, alpha=alpha, beta=alpha, gamma=alpha)

    @classmethod
    def monoclinic(cls, a: float, b: float, c: float, beta: float) -> "Lattice":
        """
        Create a monoclinic lattice.

        All three lattice vectors have different lengths, with α = γ = 90° and β variable.

        Args:
            a: Length of a lattice vector in Angstroms.
            b: Length of b lattice vector in Angstroms.
            c: Length of c lattice vector in Angstroms.
            beta: Angle between a and c vectors in degrees (α = γ = 90°).

        Returns:
            Lattice: A new monoclinic Lattice instance.

        Raises:
            ValueError: If any length parameter is non-positive or beta is invalid.

        Example:
            >>> lat = Lattice.monoclinic(5.0, 6.0, 7.0, 100.0)
            >>> lat.a, lat.b, lat.c
            (5.0, 6.0, 7.0)
            >>> lat.alpha, lat.beta, lat.gamma
            (90.0, 100.0, 90.0)
        """
        # Monoclinic: alpha = gamma = 90°, beta can vary
        return cls.from_parameters(a=a, b=b, c=c, alpha=90.0, beta=beta, gamma=90.0)

    @classmethod
    def triclinic(
        cls, a: float, b: float, c: float, alpha: float, beta: float, gamma: float
    ) -> "Lattice":
        """
        Create a triclinic lattice.

        All three lattice vectors have different lengths, and all angles can vary.

        Args:
            a: Length of a lattice vector in Angstroms.
            b: Length of b lattice vector in Angstroms.
            c: Length of c lattice vector in Angstroms.
            alpha: Angle between b and c vectors in degrees.
            beta: Angle between a and c vectors in degrees.
            gamma: Angle between a and b vectors in degrees.

        Returns:
            Lattice: A new triclinic Lattice instance.

        Raises:
            ValueError: If any length parameter is non-positive or angles are invalid.

        Example:
            >>> lat = Lattice.triclinic(5.0, 6.0, 7.0, 90, 100, 110)
            >>> lat.a, lat.b, lat.c
            (5.0, 6.0, 7.0)
            >>> lat.alpha, lat.beta, lat.gamma
            (90.0, 100.0, 110.0)
        """
        # Triclinic: all parameters can vary
        return cls.from_parameters(a=a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma)

    __hash__ = None

    def __eq__(self, other: Any) -> bool:
        """
        Check equality with another Lattice.

        Two lattices are equal if their lattice vectors are equal within
        numerical tolerance (using numpy.allclose with rtol=1e-8).

        Args:
            other: Another object to compare with.

        Returns:
            bool: True if lattices are equal within tolerance, False otherwise.

        Note:
            Uses numpy.allclose() for numerical tolerance to handle
            floating-point precision issues.

        Example:
            >>> lat1 = Lattice.cubic(5.0)
            >>> lat2 = Lattice.cubic(5.0)
            >>> lat3 = Lattice.cubic(5.0000001)  # Very close
            >>> lat1 == lat2
            True
            >>> lat1 == lat3
            True  # Within tolerance
            >>> lat1 == Lattice.cubic(6.0)
            False
        """
        if not isinstance(other, Lattice):
            return False

        # Use absolute tolerance only so the equality window is independent of
        # the magnitude of the lattice parameters.  LATTICE_TOL = 1e-6 Å is well
        # within any physically meaningful lattice precision and guarantees that
        # the hash contract (a == b → hash(a) == hash(b)) is satisfied when
        # __hash__ rounds to 5 decimal places (bucket = 5e-6 > LATTICE_TOL).
        return np.allclose(self.lattice_vectors, other.lattice_vectors, atol=LATTICE_TOL, rtol=0)

    def get_reciprocal_lattice(self) -> "Lattice":
        """
        Get the reciprocal lattice.

        The reciprocal lattice is calculated as 2π times the transpose of
        the inverse lattice matrix. This is useful for k-space calculations
        and diffraction analysis.

        Returns:
            Lattice: The reciprocal lattice object.

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> recip = lat.get_reciprocal_lattice()
            >>> recip.a  # Reciprocal lattice parameter
            1.256637...
        """
        # Reciprocal lattice vectors are 2π times the transpose of the inverse
        reciprocal_vectors = 2 * np.pi * self.inv_matrix.T
        return Lattice(reciprocal_vectors)

    def cartesian_coords(self, fractional_coords: np.ndarray) -> np.ndarray:
        """
        Convert fractional coordinates to Cartesian coordinates.

        Args:
            fractional_coords: Fractional coordinates as numpy array.
                              Can be a single coordinate (3,) or multiple (N, 3).

        Returns:
            np.ndarray: Cartesian coordinates in Angstroms.
                       Shape matches input (3,) or (N, 3).

        Example:
            >>> lat = Lattice.cubic(10.0)
            >>> frac = np.array([0.5, 0.5, 0.5])
            >>> cart = lat.cartesian_coords(frac)
            >>> cart
            array([5., 5., 5.])
            >>>
            >>> # Multiple coordinates
            >>> fracs = np.array([[0, 0, 0], [0.5, 0.5, 0.5]])
            >>> carts = lat.cartesian_coords(fracs)
            >>> carts.shape
            (2, 3)
        """
        return np.dot(fractional_coords, self.matrix)

    def fractional_coords(self, cartesian_coords: np.ndarray) -> np.ndarray:
        """
        Convert Cartesian coordinates to fractional coordinates.

        Args:
            cartesian_coords: Cartesian coordinates in Angstroms as numpy array.
                            Can be a single coordinate (3,) or multiple (N, 3).

        Returns:
            np.ndarray: Fractional coordinates.
                       Shape matches input (3,) or (N, 3).

        Example:
            >>> lat = Lattice.cubic(10.0)
            >>> cart = np.array([5.0, 5.0, 5.0])
            >>> frac = lat.fractional_coords(cart)
            >>> frac
            array([0.5, 0.5, 0.5])
            >>>
            >>> # Multiple coordinates
            >>> carts = np.array([[0, 0, 0], [5, 5, 5]])
            >>> fracs = lat.fractional_coords(carts)
            >>> fracs.shape
            (2, 3)
        """
        return np.dot(cartesian_coords, self.inv_matrix)

    def is_orthogonal(self, tol: float = 1e-8) -> bool:
        """
        Check if the lattice is orthogonal (all angles are 90°).

        A lattice is orthogonal if all three angles (α, β, γ) are 90 degrees
        within the specified tolerance.

        Args:
            tol: Tolerance for angle comparison in degrees (default: 1e-8).

        Returns:
            bool: True if all angles are 90° within tolerance, False otherwise.

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> lat.is_orthogonal()
            True
            >>> lat = Lattice.hexagonal(3.0, 5.0)
            >>> lat.is_orthogonal()
            False  # gamma = 120°
        """
        return (
            abs(self.alpha - 90) < tol
            and abs(self.beta - 90) < tol
            and abs(self.gamma - 90) < tol
        )

    def is_hexagonal(self, length_tol: float = 1e-8, angle_tol: float = 1e-8) -> bool:
        """Return True for hexagonal metric cells."""
        length_scale = max(abs(self.a), abs(self.b), 1.0)
        return (
            abs(self.a - self.b) <= length_tol * length_scale
            and abs(self.alpha - 90.0) <= angle_tol
            and abs(self.beta - 90.0) <= angle_tol
            and abs(abs(self.gamma) - 120.0) <= angle_tol
        )

    @property
    def parameters(self) -> Dict[str, float]:
        """
        Get all lattice parameters as a dictionary.

        Returns a dictionary containing all six lattice parameters plus volume.

        Returns:
            Dict[str, float]: Dictionary with keys:
                - a, b, c: Lattice vector lengths in Angstroms
                - alpha, beta, gamma: Lattice angles in degrees
                - volume: Unit cell volume in cubic Angstroms

        Example:
            >>> lat = Lattice.cubic(5.0)
            >>> params = lat.parameters
            >>> params['a']
            5.0
            >>> params['alpha']
            90.0
            >>> params['volume']
            125.0
        """
        return {
            "a": self.a,
            "b": self.b,
            "c": self.c,
            "alpha": self.alpha,
            "beta": self.beta,
            "gamma": self.gamma,
            "volume": self.volume,
        }
