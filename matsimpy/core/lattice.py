import numpy as np
from typing import List, Union, Optional
from monty.json import MSONable
from scipy.spatial.distance import pdist, squareform

class Lattice(MSONable):
    def __init__(self, lattice_vectors: List[List[float]]):
        """
        Initialize a Lattice object with the given lattice vectors.
        
        Args:
            lattice_vectors: A list of 3 lists representing the lattice vectors.
        """
        self.lattice_vectors = np.array(lattice_vectors, dtype=float)
        self._validate_lattice_vectors()
        # Cache inverse matrix
        self._inv_matrix: Optional[np.ndarray] = None

    def _validate_lattice_vectors(self) -> None:
        """
        Validate the lattice vectors.
    
        Raises:
            ValueError: If the lattice vectors are not 3D or are linearly dependent.
        """
        if len(self.lattice_vectors) != 3:
            raise ValueError("Lattice vectors must be 3-dimensional.")
        det = np.linalg.det(self.matrix)
        if np.isclose(det, 0):
            raise ValueError("Lattice vectors must be linearly independent.")

    def as_dict(self):
        d = {

            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "lattice_vectors": self.lattice_vectors.tolist()
        }
        return d

    @classmethod
    def from_dict(cls, d):
        lattice_vectors = d["lattice_vectors"]
        return cls(lattice_vectors)

    @property
    def matrix(self) -> np.ndarray:
        """
        Get the lattice vectors as a matrix.

        Returns:
            (np.ndarray): Lattice vectors as a 3x3 matrix.
        """
        return np.array(self.lattice_vectors , dtype=np.float64).reshape((3, 3))
    
    @property
    def inv_matrix(self) -> np.ndarray:
        """
        Cached inverse of lattice matrix.

        Returns:
            (np.ndarray): Inverse of lattice matrix.
        """
        if self._inv_matrix is None:
            self._inv_matrix = np.linalg.inv(self.matrix)
        return self._inv_matrix

    @property
    def a(self) -> float:
        """Get the length of the a lattice vector."""
        return np.linalg.norm(self.lattice_vectors[0])

    @property
    def b(self) -> float:
        """Get the length of the b lattice vector."""
        return np.linalg.norm(self.lattice_vectors[1])

    @property
    def c(self) -> float:
        """Get the length of the c lattice vector."""
        return np.linalg.norm(self.lattice_vectors[2])

    @property
    def alpha(self) -> float:
        """Get the angle between the b and c lattice vectors in degrees."""
        return np.degrees(np.arccos(np.dot(self.lattice_vectors[1], self.lattice_vectors[2])
                                    / (self.b * self.c)))

    @property
    def beta(self) -> float:
        """Get the angle between the a and c lattice vectors in degrees."""
        return np.degrees(np.arccos(np.dot(self.lattice_vectors[0], self.lattice_vectors[2])
                                    / (self.a * self.c)))

    @property
    def gamma(self) -> float:
        """Get the angle between the a and b lattice vectors in degrees."""
        return np.degrees(np.arccos(np.dot(self.lattice_vectors[0], self.lattice_vectors[1])
                                    / (self.a * self.b)))

    def volume(self) -> float:
        """Calculate the volume of the unit cell."""
        a, b, c = self.lattice_vectors
        volume = np.dot(a, np.cross(b, c))
        return abs(volume)

    def __str__(self) -> str:
        vectors = [f" {vector[0]:.4f} {vector[1]:.4f} {vector[2]:.4f}" for vector in self.lattice_vectors]
        return f"Lattice with lattice vectors:\n{vectors[0]}\n{vectors[1]}\n{vectors[2]}"

        
    def __repr__(self) -> str:
        return f"Lattice(lattice_vectors={self.lattice_vectors.tolist()})"


    @classmethod
    def from_parameters(cls, a: float, b: float, c: float, alpha: float, beta: float, gamma: float):
        """
        Initialize a Lattice object with lattice parameters.

        Args:
            a: The length of the a lattice vector.
            b: The length of the b lattice vector.
            c: The length of the c lattice vector.
            alpha: The angle between the b and c lattice vectors in degrees.
            beta: The angle between the a and c lattice vectors in degrees.
            gamma: The angle between the a and b lattice vectors in degrees.
            
        Raises:
            ValueError: If gamma is 0 or 180 degrees (a and b vectors would be parallel,
                       making the lattice linearly dependent)
        """
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
        c3 = np.sqrt(c ** 2 - a3 ** 2 - b3 ** 2)

        lattice_vectors = [
            [a1, 0.0, 0.0],
            [a2, b2, 0.0],
            [a3, b3, c3]
        ]

        return cls(lattice_vectors)

    @classmethod
    def cubic(cls, a: float):
        """
        Initialize a Lattice object with lattice parameters.

        Args:
            a: The length of the a lattice vector.
        """
        lattice_vectors = [
            [a, 0.0, 0.0],
            [0.0, a, 0.0],
            [0.0, 0.0, a]
        ]
        return cls(lattice_vectors)
    
    @classmethod
    def tetragonal(cls, a: float, c: float):
        """
        Initialize a Lattice object with lattice parameters.

        Args:
            a: The length of the a lattice vector.
            c: The length of the c lattice vector.
        """
        lattice_vectors = [
            [a, 0.0, 0.0],
            [0.0, a, 0.0],
            [0.0, 0.0, c]
        ]
        return cls(lattice_vectors)

    @classmethod
    def orthorhomic(cls, a: float, b: float, c: float):
        """
        Initialize a Lattice object with lattice parameters.

        Args:
            a: The length of the a lattice vector.
            b: The length of the a lattice vector.
            c: The length of the c lattice vector.
        """
        lattice_vectors = [
            [a, 0.0, 0.0],
            [0.0, b, 0.0],
            [0.0, 0.0, c]
        ]
        return cls(lattice_vectors)

    @classmethod
    def hexagonal(cls, a: float, c: float):
        """
        Initialize a hexagonal Lattice object.

        Args:
            a: The length of the a (and b) lattice vector.
            c: The length of the c lattice vector.
        """
        # Standard hexagonal lattice vectors
        # a = b, alpha = beta = 90°, gamma = 120°
        lattice_vectors = [
            [a, 0.0, 0.0],
            [-a/2, a*np.sqrt(3)/2, 0.0],
            [0.0, 0.0, c]
        ]
        return cls(lattice_vectors)

    @classmethod
    def rhombohedral(cls, a: float, alpha: float):
        """
        Initialize a rhombohedral Lattice object.

        Args:
            a: The length of all three lattice vectors (a = b = c).
            alpha: The angle between all three lattice vectors (alpha = beta = gamma) in degrees.
        """
        # Use from_parameters for rhombohedral (a = b = c, alpha = beta = gamma)
        return cls.from_parameters(a=a, b=a, c=a, alpha=alpha, beta=alpha, gamma=alpha)

    @classmethod
    def monoclinic(cls, a: float, b: float, c: float, beta: float):
        """
        Initialize a monoclinic Lattice object.

        Args:
            a: The length of the a lattice vector.
            b: The length of the b lattice vector.
            c: The length of the c lattice vector.
            beta: The angle between the a and c lattice vectors in degrees.
        """
        # Monoclinic: alpha = gamma = 90°, beta can vary
        return cls.from_parameters(a=a, b=b, c=c, alpha=90.0, beta=beta, gamma=90.0)
