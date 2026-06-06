"""
Site module for MatSimPy.

This module provides classes for representing atomic sites in structures.
It includes two main classes:
- Site: For molecules and non-periodic structures (Cartesian coordinates only)
- CrystalSite: For crystal structures with lattice (supports both fractional and Cartesian)

The Site classes are used internally by Crystal and Molecule classes to represent
individual atoms with their positions, species, and optional properties.

Example:
    >>> from matsimpy.core.site import Site, CrystalSite
    >>> from matsimpy.core import Lattice
    >>>
    >>> # Create a Site (for molecules)
    >>> site = Site([0, 0, 0], 'Fe')
    >>> print(site.position)  # [0. 0. 0.]
    >>> print(site.specie)    # 'Fe'
    >>>
    >>> # Create a CrystalSite (for crystals)
    >>> lattice = Lattice.cubic(10.0)
    >>> crystal_site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
    >>> print(crystal_site.frac_position)  # Fractional coordinates
    >>> print(crystal_site.cart_position)  # Cartesian coordinates
"""

import numpy as np
import warnings
from typing import List, Optional, Union, Dict, Any
from monty.json import MSONable
from .lattice import Lattice
from .periodic_table import Element
from ._validation import normalize_species
from ..utils.dict_utils import copy_properties


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
        """
        Initialize a Site object.

        Args:
            position: 3D position coordinates [x, y, z] in Angstroms.
                     Must be a list of 3 floats or a numpy array of shape (3,).
                     Always interpreted as Cartesian coordinates.
            specie: Atomic species. Can be:
                   - str: Element symbol (e.g., 'Fe', 'Si', 'O')
                   - int: Atomic number (e.g., 26 for Fe, 14 for Si)
                   - Element: Element object from periodic_table
                   Default is 'X' (unknown element).
            properties: Optional dictionary of site properties.
                       Common properties include:
                       - charge: Formal charge
                       - magmom: Magnetic moment
                       - occupancy: Site occupancy
                       - Any other custom properties

        Raises:
            TypeError: If position is not a list or numpy array.
            ValueError: If position doesn't have exactly 3 elements.
            ValueError: If position contains NaN or inf values.
            TypeError: If specie is not a valid type.
            ValueError: If atomic number is out of valid range (1-118).
            TypeError: If properties is not a dictionary or None.

        Examples:
            >>> # Create site with element symbol
            >>> site = Site([0, 0, 0], 'Fe')
            >>> site.specie
            'Fe'
            >>>
            >>> # Create site with atomic number
            >>> site = Site([1.0, 2.0, 3.0], 26)  # Fe
            >>> site.specie
            'Fe'
            >>>
            >>> # Create site with properties
            >>> site = Site([0, 0, 0], 'Fe', properties={'charge': 2.0, 'magmom': 5.0})
            >>> site.properties
            {'charge': 2.0, 'magmom': 5.0}
        """
        self._position = self._validate_position(position)
        self._specie = self._validate_specie(specie)
        self._properties = self._validate_properties(properties)

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
                - position: Position coordinates as list [x, y, z]
                - specie: Element symbol as string
                - properties: Properties dictionary (empty dict if no properties)

        Note:
            coords_are_cartesian is not included as Site always uses Cartesian coordinates.

        Example:
            >>> site = Site([1.0, 2.0, 3.0], 'Fe', properties={'charge': 2.0})
            >>> d = site.as_dict()
            >>> d['position']
            [1.0, 2.0, 3.0]
            >>> d['specie']
            'Fe'
            >>> d['properties']
            {'charge': 2.0}
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
        Create Site object from dictionary representation.

        Implements the MSONable interface for JSON deserialization.
        Restores a Site object from its dictionary representation.

        Args:
            d: Dictionary containing:
                - position: Position coordinates [x, y, z] (required)
                - specie: Element symbol (optional, defaults to 'X')
                - properties: Properties dictionary (optional)
                - coords_are_cartesian: Ignored if present (Site always uses Cartesian)

        Returns:
            Site: A new Site instance.

        Raises:
            KeyError: If 'position' key is missing from dictionary.

        Example:
            >>> d = {
            ...     '@module': 'matsimpy.core.site',
            ...     '@class': 'Site',
            ...     'position': [1.0, 2.0, 3.0],
            ...     'specie': 'Fe',
            ...     'properties': {'charge': 2.0}
            ... }
            >>> site = Site.from_dict(d)
            >>> site.position.tolist()
            [1.0, 2.0, 3.0]
            >>> site.specie
            'Fe'
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
        return normalize_species(specie, none_as_dummy=True)

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
        return copy_properties(properties)

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

        Returns:
            bool: Always True for Site objects.

        Example:
            >>> site = Site([0, 0, 0], 'Fe')
            >>> site.coords_are_cartesian
            True
        """
        return True

    @property
    def properties(self) -> Dict[str, Any]:
        """
        Get site properties dictionary.

        Returns:
            Dict[str, Any]: Dictionary of site properties. Returns empty dict
                           if no properties are set.

        Example:
            >>> site = Site([0, 0, 0], 'Fe', properties={'charge': 2.0})
            >>> site.properties
            {'charge': 2.0}
            >>> site2 = Site([0, 0, 0], 'Fe')
            >>> site2.properties
            {}
        """
        return copy_properties(self._properties)

    @properties.setter
    def properties(self, properties: Optional[Dict[str, Any]]) -> None:
        """
        Set site properties dictionary.

        Args:
            properties: Dictionary of properties to set. Can be None to clear properties.

        Raises:
            TypeError: If properties is not a dictionary or None.

        Example:
            >>> site = Site([0, 0, 0], 'Fe')
            >>> site.properties = {'charge': 2.0, 'magmom': 5.0}
            >>> site.properties
            {'charge': 2.0, 'magmom': 5.0}
            >>> site.properties = None  # Clear properties
            >>> site.properties
            {}
        """
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
        """
        Set atomic species.

        Args:
            specie: Atomic species. Can be:
                   - str: Element symbol (e.g., 'Fe', 'Si')
                   - int: Atomic number (e.g., 26 for Fe)
                   - Element: Element object

        Raises:
            TypeError: If specie is not a valid type.
            ValueError: If atomic number is out of valid range (1-118).

        Example:
            >>> site = Site([0, 0, 0], 'Fe')
            >>> site.specie = 'Si'
            >>> site.specie
            'Si'
            >>> site.specie = 26  # Fe
            >>> site.specie
            'Fe'
        """
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
        """
        Set position coordinates.

        Args:
            position: 3D position coordinates [x, y, z] in Angstroms.
                     Must be a list of 3 floats or a numpy array of shape (3,).

        Raises:
            TypeError: If position is not a list or numpy array.
            ValueError: If position doesn't have exactly 3 elements.
            ValueError: If position contains NaN or inf values.

        Example:
            >>> site = Site([0, 0, 0], 'Fe')
            >>> site.position = [1.0, 2.0, 3.0]
            >>> site.position.tolist()
            [1.0, 2.0, 3.0]
        """
        self._position = self._validate_position(position)

    def __repr__(self) -> str:
        """
        Unambiguous string representation for debugging.

        Returns:
            str: Concise representation showing specie, position, and properties.

        Example:
            >>> site = Site([1.0, 2.0, 3.0], 'Fe', properties={'charge': 2.0})
            >>> repr(site)
            "Fe @ [1.0, 2.0, 3.0] (cartesian), {'charge': 2.0}"
        """
        props_str = f", {self.properties}" if self.properties else ""
        return f"{self.specie} @ {self.position.tolist()} (cartesian){props_str}"

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns:
            str: Verbose representation with all site information.

        Example:
            >>> site = Site([1.0, 2.0, 3.0], 'Fe', properties={'charge': 2.0})
            >>> str(site)
            "Site(position=[1.0, 2.0, 3.0], specie='Fe', properties={'charge': 2.0})"
        """
        props_str = f", properties={self.properties}" if self.properties else ""
        return f"Site(position={self.position.tolist()}, specie='{self.specie}'{props_str})"

    def __eq__(self, other: Any) -> bool:
        """
        Check equality with another Site.

        Two sites are equal if they have the same specie, position (within
        numerical tolerance), and properties.

        Args:
            other: Another object to compare with.

        Returns:
            bool: True if sites are equal, False otherwise.

        Note:
            Position comparison uses numpy.allclose() for numerical tolerance.

        Example:
            >>> site1 = Site([1.0, 2.0, 3.0], 'Fe')
            >>> site2 = Site([1.0, 2.0, 3.0], 'Fe')
            >>> site3 = Site([1.0, 2.0, 3.0], 'Si')
            >>> site1 == site2
            True
            >>> site1 == site3
            False
        """
        if not isinstance(other, Site):
            return False
        return (
            self.specie == other.specie
            and np.allclose(self.position, other.position)
            and self.properties == other.properties
        )

    __hash__ = None


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
        """
        Initialize a CrystalSite object.

        Args:
            position: Position coordinates [x, y, z] or [a, b, c].
                     Interpretation depends on coords_are_cartesian:
                     - If True: Cartesian coordinates in Angstroms
                     - If False: Fractional coordinates (default)
            specie: Atomic species. Can be:
                   - str: Element symbol (e.g., 'Fe', 'Si')
                   - int: Atomic number (e.g., 26 for Fe)
                   - Element: Element object
            lattice: Lattice object or list of 3 lattice vectors.
                     Can be:
                     - Lattice: Lattice object
                     - List[List[float]]: List of 3 lattice vectors
            properties: Optional dictionary of site properties.
            coords_are_cartesian: If True, position is interpreted as Cartesian.
                                If False, position is interpreted as fractional (default).

        Raises:
            TypeError: If position, specie, or lattice is not a valid type.
            ValueError: If position doesn't have exactly 3 elements.
            ValueError: If position contains NaN or inf values.
            ValueError: If atomic number is out of valid range (1-118).

        Examples:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>>
            >>> # Create with fractional coordinates (default)
            >>> site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
            >>> site.frac_position.tolist()
            [0.5, 0.5, 0.5]
            >>> site.cart_position.tolist()
            [5.0, 5.0, 5.0]
            >>>
            >>> # Create with Cartesian coordinates
            >>> site = CrystalSite([5.0, 5.0, 5.0], 'Fe', lattice, coords_are_cartesian=True)
            >>> site.cart_position.tolist()
            [5.0, 5.0, 5.0]
            >>> site.frac_position.tolist()
            [0.5, 0.5, 0.5]
        """
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
        Convert to dictionary representation for serialization.

        Implements the MSONable interface for JSON serialization.
        The dictionary includes module and class information for proper
        deserialization.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - @module: Module path of the class
                - @class: Class name
                - position: Position coordinates (original input format)
                - specie: Element symbol as string
                - properties: Properties dictionary
                - lattice: Lattice dictionary representation
                - coords_are_cartesian: Boolean indicating coordinate type

        Note:
            Position stored is the original input format (fractional or Cartesian
            based on coords_are_cartesian), not the converted format.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
            >>> d = site.as_dict()
            >>> d['position']  # Fractional coordinates (original input)
            [0.5, 0.5, 0.5]
            >>> d['coords_are_cartesian']
            False
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
        Create CrystalSite object from dictionary representation.

        Implements the MSONable interface for JSON deserialization.
        Restores a CrystalSite object from its dictionary representation.

        Args:
            d: Dictionary containing:
                - position: Position coordinates (required)
                - specie: Element symbol (optional, defaults to 'X')
                - properties: Properties dictionary (optional)
                - lattice: Lattice dictionary (required)
                - coords_are_cartesian: Boolean indicating coordinate type (optional, defaults to False)

        Returns:
            CrystalSite: A new CrystalSite instance.

        Raises:
            KeyError: If 'position' or 'lattice' keys are missing.
            ValueError: If lattice dictionary is None.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> d = {
            ...     '@module': 'matsimpy.core.site',
            ...     '@class': 'CrystalSite',
            ...     'position': [0.5, 0.5, 0.5],
            ...     'specie': 'Fe',
            ...     'properties': {'charge': 2.0},
            ...     'lattice': lattice.as_dict(),
            ...     'coords_are_cartesian': False
            ... }
            >>> site = CrystalSite.from_dict(d)
            >>> site.frac_position.tolist()
            [0.5, 0.5, 0.5]
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
        """
        Get the lattice object.

        Returns:
            Lattice: The lattice object associated with this site.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
            >>> site.lattice == lattice
            True
        """
        return self._lattice

    @lattice.setter
    def lattice(self, lattice: Union[List[List[float]], Lattice]) -> None:
        """
        Set lattice and recalculate coordinates.

        When the lattice is changed, the fractional position is kept constant
        and the Cartesian position is recalculated.

        Args:
            lattice: Lattice object or list of 3 lattice vectors.

        Raises:
            TypeError: If lattice is not a valid type.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice1 = Lattice.cubic(10.0)
            >>> lattice2 = Lattice.cubic(20.0)
            >>> site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice1)
            >>> frac_pos = site.frac_position.copy()
            >>> site.lattice = lattice2
            >>> # Fractional position unchanged
            >>> np.allclose(site.frac_position, frac_pos)
            True
            >>> # Cartesian position recalculated
            >>> site.cart_position.tolist()
            [10.0, 10.0, 10.0]
        """
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

        Uses the lattice inverse matrix for conversion. This method is called
        automatically when needed and uses cached inverse matrix for better performance.

        Returns:
            np.ndarray: Fractional coordinates as numpy array of shape (3,).

        Note:
            This is an internal method. Use the frac_position property to access
            fractional coordinates.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> site = CrystalSite([5.0, 5.0, 5.0], 'Fe', lattice, coords_are_cartesian=True)
            >>> frac = site._convert_to_fractional()
            >>> frac.tolist()
            [0.5, 0.5, 0.5]
        """
        return np.dot(self._cart_position, self.lattice.inv_matrix)

    def _convert_to_cartesian(self) -> np.ndarray:
        """
        Convert fractional coordinates to Cartesian coordinates.

        Uses the lattice matrix for conversion. This method is called
        automatically when needed.

        Returns:
            np.ndarray: Cartesian coordinates as numpy array of shape (3,).

        Note:
            This is an internal method. Use the cart_position property to access
            Cartesian coordinates.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
            >>> cart = site._convert_to_cartesian()
            >>> cart.tolist()
            [5.0, 5.0, 5.0]
        """
        return np.dot(self._frac_position, self.lattice.matrix)

    def wrap(self) -> "CrystalSite":
        """
        Return a new CrystalSite with fractional coordinates wrapped to [0, 1).

        Wraps fractional coordinates using modulo, mapping any coordinate outside
        the primary unit cell back into it.  A new instance is returned to keep
        CrystalSite consistent with the immutable pattern used by Crystal.wrap().

        Returns:
            CrystalSite: New CrystalSite with wrapped fractional coordinates.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> site = CrystalSite([1.5, -0.3, 0.5], 'Fe', lattice)
            >>> wrapped = site.wrap()
            >>> wrapped.frac_position.tolist()
            [0.5, 0.7, 0.5]
            >>> site.frac_position.tolist()  # original unchanged
            [1.5, -0.3, 0.5]
            >>>
            >>> # Method chaining
            >>> wrapped = CrystalSite([2.1, 0.5, 0.5], 'Fe', lattice).wrap()
            >>> wrapped.frac_position.tolist()
            [0.1, 0.5, 0.5]
        """
        new_frac = self._frac_position % 1.0
        return CrystalSite(
            position=new_frac,
            specie=self._specie,
            lattice=self._lattice,
            properties=dict(self._properties),
            coords_are_cartesian=False,
        )

    def __repr__(self) -> str:
        """
        Unambiguous string representation for debugging.

        Returns:
            str: Concise representation showing specie, position, coordinate type, and properties.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice, properties={'charge': 2.0})
            >>> repr(site)
            "Fe @ [0.5, 0.5, 0.5] (frac), {'charge': 2.0}"
        """
        props_str = f", {self.properties}" if self.properties else ""
        coord_type = "cart" if self._coords_are_cartesian else "frac"
        return f"{self.specie} @ {self.position.tolist()} ({coord_type}){props_str}"

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns:
            str: Verbose representation with all site information including lattice.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> site = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice, properties={'charge': 2.0})
            >>> str(site)
            "CrystalSite(position=[0.5, 0.5, 0.5], specie='Fe', properties={'charge': 2.0}, ...)"
        """
        props_str = f", properties={self.properties}" if self.properties else ""
        coord_type = "cartesian" if self._coords_are_cartesian else "fractional"
        return f"CrystalSite(position={self.position.tolist()}, specie='{self.specie}'{props_str}, lattice={self.lattice}, coords_type='{coord_type}')"

    def __eq__(self, other: Any) -> bool:
        """
        Check equality with another CrystalSite.

        Two crystal sites are equal if they have the same specie, position (within
        numerical tolerance), properties, lattice, and coordinate type.

        Args:
            other: Another object to compare with.

        Returns:
            bool: True if crystal sites are equal, False otherwise.

        Note:
            Position and lattice comparison use numpy.allclose() for numerical tolerance.

        Example:
            >>> from matsimpy.core import Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> site1 = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
            >>> site2 = CrystalSite([0.5, 0.5, 0.5], 'Fe', lattice)
            >>> site3 = CrystalSite([0.5, 0.5, 0.5], 'Si', lattice)
            >>> site1 == site2
            True
            >>> site1 == site3
            False
        """
        if not isinstance(other, CrystalSite):
            return False

        return (
            super().__eq__(other)
            and np.allclose(self.lattice.matrix, other.lattice.matrix)
            and self._coords_are_cartesian == other._coords_are_cartesian
        )

    __hash__ = None
