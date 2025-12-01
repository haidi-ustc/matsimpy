import numpy as np
import warnings
from typing import List, Optional, Union, Dict, Any
from monty.json import MSONable
from .lattice import Lattice
from .periodic_table import Element


class Site(MSONable):
    """
    A base class representing a site (atom) in a structure.

    A Site represents a single atom at a specific position with optional properties.
    Used for molecules and non-periodic structures. Coordinates are always Cartesian
    (no lattice, so fractional coordinates don't apply).

    Args:
        position: 3D position coordinates [x, y, z] in Angstroms (always Cartesian)
        specie: Atomic species (string symbol, atomic number, or Element object)
        properties: Optional dictionary of site properties (e.g., charge, magmom)

    Examples:
        >>> site = Site([0, 0, 0], 'Fe')
        >>> site = Site([0.5, 0.5, 0.5], 'Si', properties={'charge': 2.0})
        >>> site = Site([0, 0, 0], 26)  # Atomic number
    """

    def __init__(
        self,
        position: Union[List[float], np.ndarray],
        specie: Union[str, int, Element] = "X",
        properties: Optional[Dict[str, Any]] = None,
    ):
        self._position = self._validate_position(position)
        self._specie = self._validate_specie(specie)
        self._properties = self._validate_properties(properties)

    def as_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the Site.

        Returns:
            Dictionary containing position, specie, and properties.
            Note: coords_are_cartesian is not included as Site always uses Cartesian coordinates.
        """
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "position": self.position.tolist(),
            "specie": self.specie,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Site":
        """
        Creates a Site object from a dictionary representation.

        Args:
            d: Dictionary containing position, specie, and properties.
               Old dicts may contain coords_are_cartesian, which is ignored
               (Site always uses Cartesian coordinates).

        Returns:
            Site object
        """
        # Ignore coords_are_cartesian from old dicts for backward compatibility
        # Site always uses Cartesian coordinates (no lattice)
        return cls(
            position=d["position"],
            specie=d.get("specie", "X"),
            properties=d.get("properties"),
        )

    def _validate_specie(self, specie: Optional[Union[str, int, Element]]) -> str:
        """
        Validate and normalize atomic species.

        Args:
            specie: Atomic species as string, integer, or Element object

        Returns:
            Normalized species as string symbol

        Raises:
            TypeError: If specie is not valid type
            ValueError: If atomic number is invalid
        """
        if specie is None:
            return "X"

        if not isinstance(specie, (str, int, Element)):
            raise TypeError("Specie must be a string, integer, or Element object.")

        if isinstance(specie, int):
            # Validate atomic number before creating Element
            if not (1 <= specie <= 118):  # Extended to current periodic table
                raise ValueError(
                    f"Invalid atomic number: {specie}. Must be between 1 and 118."
                )
            return Element.from_Z(specie).symbol
        elif isinstance(specie, str):
            # Basic validation for element symbols
            if len(specie) < 1 or len(specie) > 2:
                warnings.warn(f"Element symbol '{specie}' may be invalid", UserWarning)
            return specie
        elif isinstance(specie, Element):
            return specie.symbol

    def _validate_properties(
        self, properties: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate and normalize properties dictionary.

        Args:
            properties: Optional dictionary of properties

        Returns:
            Validated properties dictionary (empty dict if None)

        Raises:
            TypeError: If properties is not a dictionary
        """
        if properties is not None and not isinstance(properties, dict):
            raise TypeError("Properties must be a dictionary or None.")
        return properties or {}

    def _validate_position(
        self, position: Union[List[float], np.ndarray]
    ) -> np.ndarray:
        """
        Validate and normalize position to numpy array.

        Args:
            position: Position as list or numpy array

        Returns:
            Validated position as numpy array

        Raises:
            TypeError: If position is not a list or numpy array
            ValueError: If position doesn't have 3 elements or contains NaN/inf

        Warnings:
            UserWarning: If position coordinates are unusually large (> 1e6 Angstroms)
        """
        if isinstance(position, np.ndarray):
            if position.shape != (3,):
                raise ValueError(
                    f"Position array must have shape (3,), got {position.shape}"
                )
            position = position.astype(np.float64)
        elif isinstance(position, list):
            if len(position) != 3:
                raise ValueError("Position must have exactly three elements.")
            for coord in position:
                if not isinstance(coord, (int, float)):
                    raise TypeError("Position elements must be integers or floats.")
            position = np.array(position, dtype=np.float64)
        else:
            raise TypeError("Position must be a list or numpy array.")

        # Check for NaN or inf
        if not np.all(np.isfinite(position)):
            raise ValueError(
                "Position coordinates must be finite numbers (no NaN or inf)"
            )

        # Check if coordinates are in reasonable range
        # 1e6 Angstroms = 100 km, clearly unreasonable for atomic structures
        if np.any(np.abs(position) > 1e6):
            warnings.warn(
                f"Position coordinates seem unusually large: {position}. "
                f"Values > 1e6 Angstroms may indicate an error.",
                UserWarning,
            )

        return position

    @property
    def coords_are_cartesian(self) -> bool:
        """
        Get whether coordinates are Cartesian.
        
        Always returns True for Site (molecules/non-periodic structures always use Cartesian).
        This property exists for backward compatibility and consistency with CrystalSite.
        """
        return True

    @property
    def coords_type(self) -> str:
        """Get coordinate type as string. Always returns 'cartesian' for Site."""
        return "cartesian"

    @property
    def properties(self) -> Dict[str, Any]:
        """Get site properties dictionary."""
        return self._properties

    @properties.setter
    def properties(self, properties: Optional[Dict[str, Any]]) -> None:
        """Set site properties dictionary."""
        self._properties = self._validate_properties(properties)

    @property
    def specie(self) -> str:
        """
        Get atomic species symbol.

        Returns:
            Species as string symbol (always normalized to string)
        """
        return self._specie

    @specie.setter
    def specie(self, specie: Union[str, int, Element]) -> None:
        """Set atomic species."""
        self._specie = self._validate_specie(specie)

    @property
    def position(self) -> np.ndarray:
        """
        Get position as numpy array.

        Returns:
            3D position array [x, y, z]
        """
        return np.array(self._position, dtype=np.float64)

    @position.setter
    def position(self, position: Union[List[float], np.ndarray]) -> None:
        """Set position coordinates."""
        self._position = self._validate_position(position)

    def __repr__(self) -> str:
        """Unambiguous string representation (concise, developer-friendly)."""
        props_str = f", {self.properties}" if self.properties else ""
        return (
            f"{self.specie} @ {self.position.tolist()} (cartesian){props_str}"
        )

    def __str__(self) -> str:
        """Human-readable string representation (verbose, user-friendly)."""
        props_str = f", properties={self.properties}" if self.properties else ""
        return f"Site(position={self.position.tolist()}, specie='{self.specie}'{props_str})"

    def __eq__(self, other) -> bool:
        """Check equality with another Site."""
        if not isinstance(other, Site):
            return False
        return (
            self.specie == other.specie
            and np.allclose(self.position, other.position)
            and self.properties == other.properties
        )


class CrystalSite(Site):
    """
    A Site class for crystal structures with lattice information.

    Extends Site to include fractional and Cartesian coordinates, and lattice reference.
    Used for periodic crystal structures.

    Args:
        position: Position coordinates (fractional or Cartesian)
        specie: Atomic species (string symbol, atomic number, or Element object)
        lattice: Lattice object or list of lattice vectors
        properties: Optional dictionary of site properties
        coords_are_cartesian: If True, position is Cartesian; if False, fractional (default)

    Examples:
        >>> from matsimpy.core import Lattice
        >>> lattice = Lattice.cubic(10)
        >>> site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
        >>> site = CrystalSite([5, 5, 5], 'Fe', lattice, coords_are_cartesian=True)
    """

    def __init__(
        self,
        position: Union[List[float], np.ndarray],
        specie: Union[str, int, Element],
        lattice: Union[List[List[float]], Lattice],
        properties: Optional[Dict[str, Any]] = None,
        coords_are_cartesian: bool = False,
    ):
        self._lattice = self._validate_lattice(lattice)
        self._coords_are_cartesian = coords_are_cartesian

        # Calculate both coordinate representations
        if coords_are_cartesian:
            self._cart_position = self._validate_position(position)
            self._frac_position = self._convert_to_fractional()
        else:
            self._frac_position = self._validate_position(position)
            self._cart_position = self._convert_to_cartesian()

        # Pass Cartesian position to parent Site
        # Site always uses Cartesian coordinates (no lattice, so no fractional coords)
        super().__init__(
            position=self._cart_position,
            specie=specie,
            properties=properties,
        )

    def as_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the CrystalSite.

        Returns:
            Dictionary containing position, specie, properties, lattice, and coordinate type.
            Position stored is the original input (fractional or Cartesian based on coords_are_cartesian).
        """
        d = super().as_dict()
        # Override position with the original input position (fractional or Cartesian)
        # not the base position from Site (which is always Cartesian)
        if self._coords_are_cartesian:
            d["position"] = self._cart_position.tolist()
        else:
            d["position"] = self._frac_position.tolist()
        d["lattice"] = self.lattice.as_dict()
        d["coords_are_cartesian"] = self._coords_are_cartesian
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CrystalSite":
        """
        Creates a CrystalSite object from a dictionary representation.

        Args:
            d: Dictionary containing position, specie, properties, and lattice

        Returns:
            CrystalSite object
        """
        position = d["position"]
        specie = d.get("specie", "X")
        properties = d.get("properties")
        lattice_dict = d.get("lattice")
        coords_are_cartesian = d.get("coords_are_cartesian", False)

        if lattice_dict is None:
            raise ValueError("Lattice is required for CrystalSite")

        lattice = Lattice.from_dict(lattice_dict)
        return cls(
            position=position,
            specie=specie,
            lattice=lattice,
            properties=properties,
            coords_are_cartesian=coords_are_cartesian,
        )

    def _validate_lattice(self, lattice: Union[List[List[float]], Lattice]) -> Lattice:
        """
        Validate and convert lattice input to Lattice object.

        Args:
            lattice: Lattice object or list of lattice vectors

        Returns:
            Validated Lattice object

        Raises:
            TypeError: If lattice is not valid type
        """
        if isinstance(lattice, Lattice):
            return lattice
        elif isinstance(lattice, list):
            return Lattice(lattice_vectors=lattice)
        else:
            raise TypeError(
                f"Lattice must be Lattice object or list, got {type(lattice)}"
            )

    @property
    def lattice(self) -> Lattice:
        """Get the lattice object."""
        return self._lattice

    @lattice.setter
    def lattice(self, lattice: Union[List[List[float]], Lattice]) -> None:
        """Set lattice and recalculate coordinates."""
        old_lattice = self._lattice
        self._lattice = self._validate_lattice(lattice)

        # Recalculate coordinates if lattice changed
        if old_lattice is not None:
            # Keep fractional position consistent, recalculate Cartesian
            self._cart_position = self._convert_to_cartesian()

    @property
    def position(self) -> np.ndarray:
        """
        Get position as numpy array.
        
        Returns the original input position (fractional or Cartesian based on coords_are_cartesian).
        This overrides the parent Site.position which always returns Cartesian.

        Returns:
            3D position array [x, y, z] - original input format
        """
        if self._coords_are_cartesian:
            return np.array(self._cart_position, dtype=np.float64)
        else:
            return np.array(self._frac_position, dtype=np.float64)

    @property
    def frac_position(self) -> np.ndarray:
        """
        Get fractional coordinates.

        Returns:
            Fractional coordinates as numpy array
        """
        return np.array(self._frac_position, dtype=np.float64)

    @property
    def cart_position(self) -> np.ndarray:
        """
        Get Cartesian coordinates.

        Returns:
            Cartesian coordinates as numpy array
        """
        return np.array(self._cart_position, dtype=np.float64)

    def _convert_to_fractional(self) -> np.ndarray:
        """
        Convert Cartesian coordinates to fractional coordinates.

        Uses cached inverse matrix for better performance.

        Returns:
            Fractional coordinates as numpy array
        """
        return np.dot(self._cart_position, self.lattice.inv_matrix)

    def _convert_to_cartesian(self) -> np.ndarray:
        """
        Convert fractional coordinates to Cartesian coordinates.

        Returns:
            Cartesian coordinates as numpy array
        """
        return np.dot(self._frac_position, self.lattice.matrix)

    def __repr__(self) -> str:
        """Unambiguous string representation (concise, developer-friendly)."""
        props_str = f", {self.properties}" if self.properties else ""
        coord_type = "cart" if self._coords_are_cartesian else "frac"
        return f"{self.specie} @ {self.position.tolist()} ({coord_type}){props_str}"

    def __str__(self) -> str:
        """Human-readable string representation (verbose, user-friendly)."""
        props_str = f", properties={self.properties}" if self.properties else ""
        coord_type = "cartesian" if self._coords_are_cartesian else "fractional"
        return f"CrystalSite(position={self.position.tolist()}, specie='{self.specie}'{props_str}, lattice={self.lattice}, coords_type='{coord_type}')"

    def __eq__(self, other) -> bool:
        """Check equality with another CrystalSite."""
        if not isinstance(other, CrystalSite):
            return False

        return (
            super().__eq__(other)
            and np.allclose(self.lattice.matrix, other.lattice.matrix)
            and self._coords_are_cartesian == other._coords_are_cartesian
        )
