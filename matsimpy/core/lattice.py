import numpy as np
from typing import List, Union, Optional
from monty.json import MSONable
from scipy.spatial.distance import pdist, squareform

class Lattice(MSONable):
    def __init__(self, lattice_vectors: Union[float, int, List[float], List[List[float]]]):
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
            self.lattice_vectors = np.array([
                [a, 0.0, 0.0],
                [0.0, a, 0.0],
                [0.0, 0.0, a]
            ], dtype=float)
        elif isinstance(lattice_vectors, (list, np.ndarray)):
            # Convert to numpy array for uniform handling
            arr = np.array(lattice_vectors, dtype=float,copy=True)
            if arr.ndim == 1 and len(arr) == 3:
                # List of 3 numbers -> orthorhombic lattice
                a, b, c = arr
                if a <= 0 or b <= 0 or c <= 0:
                    raise ValueError(f"Lattice parameters must be positive, got [{a}, {b}, {c}]")
                self.lattice_vectors = np.array([
                    [a, 0.0, 0.0],
                    [0.0, b, 0.0],
                    [0.0, 0.0, c]
                ], dtype=float)
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
        # Cache inverse matrix
        self._inv_matrix: Optional[np.ndarray] = None

    def _validate_lattice_vectors(self) -> None:
        """
        Enhanced validation of lattice vectors.
        
        Raises:
            ValueError: If the lattice vectors are invalid, contain non-finite values,
                       are linearly dependent, or have too small volume.
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
        volume = self.volume()
        if volume <= 1e-10:  # Very small volume
            raise ValueError(f"Lattice volume is too small: {volume}")

    def as_dict(self):
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "lattice_vectors": np.round(self.lattice_vectors, decimals=8).tolist() 
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
        return self.lattice_vectors.reshape((3, 3))
    
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
        return abs(np.linalg.det(self.matrix))

    def _format_lattice_params(self, include_units: bool = True) -> str:
        """
        Format lattice parameters as a string.
        
        Helper method to avoid duplication between Lattice and Crystal __str__ methods.
        Matches the format used in Crystal.__str__.
        
        Args:
            include_units: If True, include Å units for lengths (default: True).
        
        Returns:
            Formatted string with lattice parameters on two lines.
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
        for param in [a, b, c]:
            if param <= 0:
                raise ValueError(f"Lattice parameter must be positive, got {param}")
        
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
    def orthorhombic(cls, a: float, b: float, c: float):
        """
        Initialize an orthorhombic Lattice object.

        Args:
            a: The length of the a lattice vector.
            b: The length of the b lattice vector.
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

    @classmethod
    def triclinic(cls, a: float, b: float, c: float, alpha: float, beta: float, gamma: float):
        """
        Initialize a triclinic Lattice object.

        Args:
            a: The length of the a lattice vector.
            b: The length of the b lattice vector.
            c: The length of the c lattice vector.
            alpha: The angle between the b and c lattice vectors in degrees.
            beta: The angle between the a and c lattice vectors in degrees.
            gamma: The angle between the a and b lattice vectors in degrees.
        """
        # Triclinic: all parameters can vary
        return cls.from_parameters(a=a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma)


    def __hash__(self):
        """
        Generate a hash for the lattice with consistent floating-point handling.
    
        Lattice vectors are rounded to 8 decimal places to handle floating-point
        precision issues, matching the approach used in Structure.
    
        Returns:
            int: Hash value for the lattice
        """
        import hashlib
    
        hash_dict = self.as_dict()
        hash_str = str(hash_dict).encode('utf-8')
        return int(hashlib.sha256(hash_str).hexdigest(), 16)

    def __eq__(self, other):
        """
        Equality comparison with tolerance for floating-point numbers.
        
        Args:
            other: Another Lattice object to compare with.
        
        Returns:
            True if lattices are equal within tolerance, False otherwise.
        """
        if not isinstance(other, Lattice):
            return False
        
        # Compare with tolerance
        return np.allclose(self.lattice_vectors, other.lattice_vectors, rtol=1e-8)

    def get_reciprocal_lattice(self) -> 'Lattice':
        """Get the reciprocal lattice."""
        # Reciprocal lattice vectors are 2π times the transpose of the inverse
        reciprocal_vectors = 2 * np.pi * self.inv_matrix.T
        return Lattice(reciprocal_vectors)

    def get_cartesian_coords(self, fractional_coords: np.ndarray) -> np.ndarray:
        """Convert fractional coordinates to Cartesian coordinates."""
        return np.dot(fractional_coords, self.matrix)

    def get_fractional_coords(self, cartesian_coords: np.ndarray) -> np.ndarray:
        """Convert Cartesian coordinates to fractional coordinates."""
        return np.dot(cartesian_coords, self.inv_matrix)

    def is_orthogonal(self, tol: float = 1e-8) -> bool:
        """Check if the lattice is orthogonal (all angles are 90°)."""
        return (abs(self.alpha - 90) < tol and 
                abs(self.beta - 90) < tol and 
                abs(self.gamma - 90) < tol)

    @property
    def parameters(self) -> dict:
        """Get all lattice parameters as a dictionary."""
        return {
            'a': self.a, 'b': self.b, 'c': self.c,
            'alpha': self.alpha, 'beta': self.beta, 'gamma': self.gamma,
            'volume': self.volume()
        }