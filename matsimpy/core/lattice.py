import numpy as np
from typing import List, Union
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
        #self._validate_lattice_vectors()


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
        return self.lattice_vectors

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
        return f"Lattice with lattice vectors:\n{self.lattice_vectors}"
        
    def __repr__(self) -> str:
        return f"Lattice(lattice_vectors={self.lattice_vectors.tolist()})"

    def _validate_lattice_vectors(self):
        """
        Check that the lattice vectors are non-zero, non-collinear, and form a right-handed coordinate system.
        """
        if not np.all(self.lattice_vectors):
            raise ValueError("Lattice vectors must be non-zero.")
        cross = np.cross(self.lattice_vectors[0], self.lattice_vectors[1])
        if np.dot(cross, self.lattice_vectors[2]) == 0:
            raise ValueError("Lattice vectors must be non-collinear.")
        elif np.dot(cross, self.lattice_vectors[2]) < 0:
            self.lattice_vectors[2] *= -1


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
        """
        alpha = np.radians(alpha)
        beta = np.radians(beta)
        gamma = np.radians(gamma)

        cos_alpha = np.cos(alpha)
        cos_beta = np.cos(beta)
        cos_gamma = np.cos(gamma)
        sin_gamma = np.sin(gamma)

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

