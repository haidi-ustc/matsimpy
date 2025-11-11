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
    Used for molecules and non-periodic structures.
    
    Args:
        position: 3D position coordinates [x, y, z]
        specie: Atomic species (string symbol, atomic number, or Element object)
        properties: Optional dictionary of site properties (e.g., charge, magmom)
        
    Examples:
        >>> site = Site([0, 0, 0], 'Fe')
        >>> site = Site([0.5, 0.5, 0.5], 'Si', properties={'charge': 2.0})
        >>> site = Site([0, 0, 0], 26)  # Atomic number
    """
    def __init__(self, position: Union[List[float], np.ndarray], 
            specie: Union[str, int, Element] = 'X',
            properties: Optional[Dict[str, Any]] = None):
        self._position = self._validate_position(position)
        self._specie = self._validate_specie(specie)
        self._properties = self._validate_properties(properties)

    def as_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the Site.
        
        Returns:
            Dictionary containing position, specie, and properties
        """
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "position": self.position.tolist(),
            "specie": self.specie,
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Site':
        """
        Creates a Site object from a dictionary representation.
        
        Args:
            d: Dictionary containing position, specie, and properties
            
        Returns:
            Site object
        """
        return cls(
            position=d["position"],
            specie=d.get("specie", 'X'),
            properties=d.get("properties")
        )

    def _validate_specie(self, specie: Optional[Union[str, int, Element]]) -> Optional[Union[str, int, Element]]:
        if specie is not None:
            if not isinstance(specie, (str, int, Element)):
                raise TypeError("Specie must be a string, integer, or Element object.")
            if isinstance(specie, int):
                # Validate atomic number before creating Element
                if not (0 < specie <= 103):  # Valid atomic numbers
                    raise ValueError(f"Invalid atomic number: {specie}. Must be between 1 and 103.")
                return Element.from_Z(specie).symbol
            if isinstance(specie, str):
                return specie
            if isinstance(specie, Element):
                return specie.symbol

        return specie

    def _validate_properties(self, properties: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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
            raise TypeError("Properties must be a dictionary.")
        return properties or {}

    def _validate_position(self, position: Union[List[float], np.ndarray]) -> np.ndarray:
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
                raise ValueError(f"Position array must have shape (3,), got {position.shape}")
            position = position.astype(np.float64)
        elif isinstance(position, list):
            if len(position) != 3:
                raise ValueError("Position must have three elements.")
            for coord in position:
                if not isinstance(coord, (int, float)):
                    raise TypeError("Position elements must be integers or floats.")
            position = np.array(position, dtype=np.float64)
        else:
            raise TypeError("Position must be a list or numpy array.")
        
        # Check for NaN or inf
        if not np.all(np.isfinite(position)):
            raise ValueError("Position coordinates must be finite numbers (no NaN or inf)")
        
        # Check if coordinates are in reasonable range
        # 1e6 Angstroms = 100 km, clearly unreasonable for atomic structures
        if np.any(np.abs(position) > 1e6):
            warnings.warn(
                f"Position coordinates seem unusually large: {position}. "
                f"Values > 1e6 Angstroms may indicate an error.",
                UserWarning
            )
        
        return position

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
        """String representation of Site."""
        props_str = f", properties={self.properties}" if self.properties else ""
        return f"Site(position={self.position.tolist()}, specie='{self.specie}'{props_str})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        props_str = f", {self.properties}" if self.properties else ""
        return f"{self.specie} @ {self.position.tolist()}{props_str}"

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
        coords_are_cartesian: bool = False
    ):
        self._lattice = self._validate_lattice(lattice)
       
        if coords_are_cartesian:
            self.cart_position = np.array(position, dtype=np.float64)
            self.frac_position = self._convert_to_fractional()
        else:
            self.frac_position = np.array(position, dtype=np.float64)
            self.cart_position = self._convert_to_cartesian()

        # Store fractional position as base position (Site uses this)
        position = self.frac_position
        super().__init__(position, specie, properties)


    def as_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the CrystalSite.
        
        Returns:
            Dictionary containing position, specie, properties, and lattice
        """
        d = super().as_dict()
        d["lattice"] = self._lattice.as_dict()
        d["coords_are_cartesian"] = False  # Always store as fractional
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'CrystalSite':
        """
        Creates a CrystalSite object from a dictionary representation.
        
        Args:
            d: Dictionary containing position, specie, properties, and lattice
            
        Returns:
            CrystalSite object
        """
        position = d["position"]
        specie = d.get("specie", 'X')
        properties = d.get("properties")
        lattice_dict = d.get("lattice")
        if lattice_dict is None:
            raise ValueError("Lattice is required for CrystalSite")
        lattice = Lattice.from_dict(lattice_dict)
        return cls(
            position=position,
            specie=specie,
            properties=properties,
            lattice=lattice,
            coords_are_cartesian=False  # Always stored as fractional
        )

    def __repr__(self) -> str:
        """String representation of CrystalSite."""
        props_str = f", properties={self.properties}" if self.properties else ""
        return f"CrystalSite(position={self.frac_position.tolist()}, specie='{self.specie}'{props_str}, lattice={self.lattice})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        props_str = f", {self.properties}" if self.properties else ""
        return f"{self.specie} @ frac={self.frac_position.tolist()} cart={self.cart_position.tolist()}{props_str}"

    def _validate_lattice(self, lattice: Union[List[List[float]],Lattice]) -> Lattice:

        if  isinstance(lattice, Lattice):
            return lattice

        if not isinstance(lattice, list):
            raise TypeError("Lattice must be a list of lists of floats.")
        if len(lattice) != 3:
            raise ValueError("Lattice must have three vectors.")
        for vector in lattice:
            if not isinstance(vector, list):
                raise TypeError("Lattice vectors must be lists of floats.")
            if len(vector) != 3:
                raise ValueError("Lattice vectors must have three elements.")
            for coord in vector:
                if not isinstance(coord, (int, float)):
                    raise TypeError("Lattice vector elements must be integers or floats.")
        return Lattice(lattice_vectors=lattice)

    @property
    def lattice(self) -> Lattice:
        return self._lattice

    @lattice.setter
    def lattice(self, lattice: Union[List[List[float]], Lattice]) -> None:
        """Set lattice and recalculate coordinates."""
        old_lattice = self._lattice
        self._lattice = self._validate_lattice(lattice)
        # Recalculate coordinates if lattice changed
        if old_lattice is not None:
            # Keep fractional position, recalculate Cartesian
            self.cart_position = self._convert_to_cartesian()

    def _convert_to_fractional(self) -> np.ndarray:
        """
        Convert Cartesian coordinates to fractional coordinates.
        
        Uses cached inverse matrix for better performance.
        
        Returns:
            Fractional coordinates as numpy array
        """
        return np.dot(self.cart_position, self.lattice.inv_matrix)

    def _convert_to_cartesian(self) -> np.ndarray:
        """
        Convert fractional coordinates to Cartesian coordinates.
        
        Returns:
            Cartesian coordinates as numpy array
        """
        return np.dot(self.frac_position, self.lattice.matrix)
    
    @property
    def frac_coords(self) -> np.ndarray:
        """
        Get fractional coordinates.
        
        Returns:
            Fractional coordinates as numpy array
        """
        return self.frac_position
    
    @property
    def cart_coords(self) -> np.ndarray:
        """
        Get Cartesian coordinates.
        
        Returns:
            Cartesian coordinates as numpy array
        """
        return self.cart_position
