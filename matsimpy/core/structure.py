"""
Structure module for MatSimPy.

This module provides the Structure abstract base class for representing
atomic structures (crystals and molecules). The Structure class serves as
the foundation for both Crystal (periodic structures) and Molecule (non-periodic
structures) classes.

The Structure class provides:
- Common interface for atomic structures
- Species and position management
- Composition and formula calculation
- Atom addition/removal operations
- Serialization support (MSONable)
- Caching for performance optimization

Example:
    >>> from matsimpy.core.structure import Structure
    >>> from matsimpy.core import Crystal, Molecule, Lattice
    >>>
    >>> # Structure is abstract - use Crystal or Molecule instead
    >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
    >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
    >>>
    >>> # Common operations work on both
    >>> crystal.formula  # 'ClNa'
    >>> molecule.formula  # 'H2O'
    >>> crystal.add_atom('H', [0.1, 0, 0])
    >>> molecule.remove_atom(0)
"""

import numpy as np
from typing import List, Union, Optional, Dict, Tuple, Any, TYPE_CHECKING
import hashlib
from collections import Counter
from abc import ABC, abstractmethod
from monty.json import MSONable

from .lattice import Lattice
from .composition import Composition
from .periodic_table import Element

if TYPE_CHECKING:
    from ..utils.selection import AtomSelection


class Structure(ABC, MSONable):
    """
    Abstract base class for representing crystal and molecule structures.

    This class provides a common interface for both periodic (Crystal) and
    non-periodic (Molecule) atomic structures. It should not be instantiated
    directly - use :class:`~matsimpy.core.crystal.Crystal` or
    :class:`~matsimpy.core.molecule.Molecule` instead.

    The Structure class handles:
    - Species and position management
    - Composition and formula calculation (with caching)
    - Atom addition and removal
    - Serialization (MSONable interface)
    - Equality comparison and hashing

    Attributes:
        species (Tuple[str]): Immutable tuple of atomic species symbols.
        positions (np.ndarray): Numpy array of atomic positions with shape (n_atoms, 3).
        lattice (Optional[Lattice]): Lattice object for periodic structures (None for molecules).
        formula (str): Chemical formula of the structure (cached property).
        composition (Composition): Composition object (cached property).
        symbol_set (tuple): Tuple of unique element symbols in order of first appearance.
        elements (List[Element]): List of Element objects for all species.

    Args:
        species: List of atomic species. Can be:
            - List[str]: List of element symbols (e.g., ['Na', 'Cl', 'Na'])
            - List[int]: List of atomic numbers (e.g., [11, 17, 11])
            - List[Element]: List of Element objects
        positions: List of atomic positions. Each position is a 3D coordinate [x, y, z].
                  For crystals, positions are typically fractional coordinates.
                  For molecules, positions are Cartesian coordinates in Angstroms.
        lattice: Optional Lattice object. Required for Crystal, None for Molecule.

    Raises:
        TypeError: If species contains mixed types or invalid types.
        ValueError: If species and positions have different lengths.
        ValueError: If positions are not 3D coordinates or contain invalid values.

    Note:
        This is an abstract class. Subclasses must implement:
        - :meth:`get_neighbor_list`: Neighbor finding method

    Examples:
        >>> from matsimpy.core import Crystal, Molecule, Lattice
        >>>
        >>> # Create a crystal structure
        >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        >>> crystal.formula
        'ClNa'
        >>> crystal.composition['Na']
        1
        >>>
        >>> # Create a molecule
        >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        >>> molecule.formula
        'H2O'
        >>> molecule.symbol_set
        ('O', 'H')
        >>>
        >>> # Add atoms
        >>> crystal.add_atom('H', [0.1, 0, 0])
        >>> crystal.add_atom(['H', 'O'], [[0.2, 0, 0], [0.3, 0, 0]])
        >>>
        >>> # Remove atoms
        >>> molecule.remove_atom(0)  # Remove first atom
        >>>
        >>> # Access elements
        >>> elements = crystal.elements
        >>> elements[0].atomic_no  # Atomic number of first element
    """

    def __init__(
        self,
        species: Union[List[str], List[int], List[Element]],
        positions: List[List[float]],
        lattice: Optional[Lattice] = None,
    ) -> None:
        """
        Initialize a Structure object.

        Args:
            species: List of atomic species. Can be:
                - List[str]: Element symbols (e.g., ['Na', 'Cl', 'Na'])
                - List[int]: Atomic numbers (e.g., [11, 17, 11])
                - List[Element]: Element objects
            positions: List of 3D atomic positions. Each position is [x, y, z].
                     For crystals, typically fractional coordinates.
                     For molecules, Cartesian coordinates in Angstroms.
            lattice: Optional Lattice object. Required for Crystal, None for Molecule.

        Raises:
            TypeError: If species contains mixed types or invalid types.
            ValueError: If species and positions have different lengths.
            ValueError: If positions are not 3D coordinates or contain NaN/Inf.

        Note:
            This is an abstract base class constructor. Use Crystal or Molecule
            subclasses instead of instantiating Structure directly.
        """
        # Convert to list first, then tuple for immutability
        if all(isinstance(s, str) for s in species):
            species_list = list(species)
        elif all(isinstance(s, int) for s in species):
            species_list = [Element.from_Z(s).symbol for s in species]
        elif all(isinstance(s, Element) for s in species):
            species_list = [s.symbol for s in species]
        else:
            raise TypeError(
                "Invalid type for species. \
                    Must be a list of atomic symbols, \
                    a list of atomic numbers, or a list of Element objects."
            )

        # Validate input lengths match
        if len(species_list) != len(positions):
            raise ValueError(
                f"Number of species ({len(species_list)}) must match "
                f"number of positions ({len(positions)})"
            )

        self.species = tuple(species_list)  # Make immutable
        self._positions = self._validate_positions(positions)

        # Validate positions match species count
        if len(self._positions) != len(self.species):
            raise ValueError(
                f"Number of positions ({len(self._positions)}) must match "
                f"number of species ({len(self.species)})"
            )

        self.lattice = lattice

        # Add cache attributes
        self._cached_composition: Optional[Composition] = None
        self._cached_formula: Optional[str] = None
        self._formula_dirty = True

    def _validate_positions(self, positions: Union[List, np.ndarray]) -> np.ndarray:
        """
        Validate and convert positions to proper numpy array format.

        Validates that positions are:
        - Convertible to numeric array
        - 2D array with shape (n_atoms, 3)
        - Contain only finite values (no NaN or Inf)

        Args:
            positions: Input positions. Can be:
                - List of lists: [[x1, y1, z1], [x2, y2, z2], ...]
                - Numpy array: shape (n_atoms, 3)

        Returns:
            np.ndarray: Validated positions array of shape (n_atoms, 3) with dtype float64.

        Raises:
            TypeError: If positions cannot be converted to numeric array.
            ValueError: If positions are 1D (should be 2D list of 3D coordinates).
            ValueError: If positions are not 2D with 3 columns.
            ValueError: If positions contain NaN or infinite values.

        Note:
            This is an internal method used during initialization and when setting positions.
            For a single atom, use [[x, y, z]] instead of [x, y, z].

        Example:
            >>> # Valid: 2D array
            >>> positions = [[0, 0, 0], [1, 1, 1]]
            >>> validated = structure._validate_positions(positions)
            >>> validated.shape
            (2, 3)
            >>>
            >>> # Invalid: 1D array
            >>> positions = [0, 0, 0]  # Will raise ValueError
        """
        # Convert to numpy array
        try:
            positions_array = np.array(positions, dtype=np.float64)
        except (ValueError, TypeError) as e:
            raise TypeError(
                f"Positions must be convertible to numeric array: {e}"
            ) from e

        # Handle 1D input (single position) - this should be an error for Structure
        if positions_array.ndim == 1:
            if len(positions_array) == 3:
                raise ValueError(
                    "Positions must be a 2D array (list of 3D coordinates). "
                    f"Got 1D array with shape {positions_array.shape}. "
                    "For a single atom, use [[x, y, z]] instead of [x, y, z]."
                )
            else:
                raise ValueError(
                    f"Positions must be a list of 3D coordinates. "
                    f"Got 1D array with {len(positions_array)} elements (expected 3)."
                )

        # Validate 2D shape
        if positions_array.ndim != 2:
            raise ValueError(
                f"Positions must be a 2D array (list of 3D coordinates). "
                f"Got {positions_array.ndim}D array with shape {positions_array.shape}."
            )

        if positions_array.shape[1] != 3:
            raise ValueError(
                f"Each position must have 3 coordinates (x, y, z). "
                f"Got positions with {positions_array.shape[1]} coordinates."
            )

        # Check for NaN or Inf values
        if np.any(np.isnan(positions_array)):
            raise ValueError("Positions cannot contain NaN values.")
        if np.any(np.isinf(positions_array)):
            raise ValueError("Positions cannot contain infinite values.")

        return positions_array

    @property
    def positions(self) -> np.ndarray:
        """
        Get atomic positions as numpy array.

        Returns:
            np.ndarray: Array of positions with shape (n_atoms, 3).
                      Each row is a 3D coordinate [x, y, z].

        Note:
            For Crystal structures, these are typically fractional coordinates.
            For Molecule structures, these are Cartesian coordinates in Angstroms.

        Example:
            >>> structure.positions
            array([[0. , 0. , 0. ],
                   [0.5, 0.5, 0.5]])
            >>> structure.positions.shape
            (2, 3)
        """
        return self._positions

    @positions.setter
    def positions(self, positions: Union[List, np.ndarray]) -> None:
        """
        Set atomic positions with validation.

        Validates positions and updates internal state. Also invalidates
        cached properties that depend on positions (e.g., sites, neighbor trees).

        Args:
            positions: New positions. Can be:
                - List of lists: [[x1, y1, z1], [x2, y2, z2], ...]
                - Numpy array: shape (n_atoms, 3)

        Raises:
            ValueError: If positions are invalid (not 3D, contain NaN/Inf).
            ValueError: If number of positions doesn't match number of species.

        Note:
            Setting positions invalidates cached properties like sites and
            neighbor trees, which will be recomputed on next access.

        Example:
            >>> structure.positions = [[0, 0, 0], [1, 1, 1]]
            >>> structure.positions = np.array([[0, 0, 0], [1, 1, 1]])
        """
        validated_positions = self._validate_positions(positions)

        # Check that number of positions matches number of species
        if len(validated_positions) != len(self.species):
            raise ValueError(
                f"Cannot set positions: number of positions ({len(validated_positions)}) "
                f"must match number of species ({len(self.species)})."
            )

        self._positions = validated_positions

        # Invalidate caches that depend on positions
        if hasattr(self, "_sites"):
            if hasattr(self, "_initialize_sites"):
                self._sites = self._initialize_sites()
        if hasattr(self, "_neighbor_tree"):
            self._neighbor_tree = None
            self._neighbor_tree_positions = None

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert structure to dictionary representation for serialization.

        Implements the MSONable interface for JSON serialization.
        The dictionary includes module and class information for proper
        deserialization.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - @module: Module path of the class
                - @class: Class name
                - species: List of species symbols
                - positions: List of positions (converted from numpy array)
                - lattice: Lattice dictionary (if lattice exists)

        Example:
            >>> d = structure.as_dict()
            >>> d['@class']
            'Crystal'
            >>> d['species']
            ['Na', 'Cl']
            >>> d['positions']
            [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]]
            >>> d.get('lattice')  # None for molecules, dict for crystals
        """
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": list(self.species),
            "positions": self.positions.tolist(),
        }
        if self.lattice is not None:
            d["lattice"] = self.lattice.as_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Structure":
        """
        Create Structure object from dictionary representation.

        Implements the MSONable interface for JSON deserialization.
        Restores a Structure object (Crystal or Molecule) from its dictionary
        representation.

        Args:
            d: Dictionary containing:
                - species: List of species symbols
                - positions: List of positions
                - lattice: Optional lattice dictionary (for crystals)

        Returns:
            Structure: A new Structure instance (Crystal or Molecule).

        Raises:
            KeyError: If required keys ('species', 'positions') are missing.
            ValueError: If species and positions have different lengths.

        Example:
            >>> d = {
            ...     '@module': 'matsimpy.core.crystal',
            ...     '@class': 'Crystal',
            ...     'species': ['Na', 'Cl'],
            ...     'positions': [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            ...     'lattice': {...}
            ... }
            >>> structure = Crystal.from_dict(d)
            >>> structure.formula
            'ClNa'
        """
        species = d["species"]
        positions = d["positions"]
        lattice = (
            Lattice.from_dict(d["lattice"]) if d.get("lattice") is not None else None
        )
        return cls(species, positions, lattice)

    @property
    def formula(self) -> str:
        """
        Get the chemical formula of the structure (cached).

        Calculates the chemical formula preserving the original order of elements
        as they appear in the structure, rather than sorting alphabetically or
        by atomic number. The result is cached for performance.

        Returns:
            str: Chemical formula string (e.g., 'H2O', 'NaCl', 'Fe2O3').

        Note:
            The formula preserves the order of first appearance of elements,
            matching VASP POSCAR format style. The cache is invalidated when
            atoms are added, removed, or substituted.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], lattice)
            >>> crystal.formula
            'ClNa'
            >>> molecule = Molecule(['O', 'H', 'H'], [[0,0,0], [0.96,0,0], [-0.24,0.93,0]])
            >>> molecule.formula
            'O2'
            >>> crystal.add_atom('H', [0.1, 0, 0])
            >>> crystal.formula  # Cache invalidated, recalculated
            'ClHNa'
        """
        if self._cached_formula is None or self._formula_dirty:
            element_counter = Counter(self.species)
            # Preserve original order by iterating through species in order
            # and tracking which elements we've already added
            seen = set()
            formula = ""
            for element in self.species:
                if element not in seen:
                    count = element_counter[element]
                    formula += element + (str(count) if count > 1 else "")
                    seen.add(element)
            self._cached_formula = formula
            self._formula_dirty = False
        return self._cached_formula

    @property
    def symbol_set(self) -> tuple:
        """
        Get the tuple of unique element symbols in the structure, preserving order.

        Returns elements in the order they first appear in the structure,
        matching VASP POSCAR format style.

        Note:
            This property reflects the current state of the structure. If you call
            sort_atoms() to reorder atoms, symbol_set will change to reflect the
            new order of first appearance. This affects VASP output format.

        Returns:
            tuple: Tuple of unique element symbols in order of first appearance
                   (e.g., ('Na', 'Cl') for NaCl, ('O', 'H') for H2O).

        Examples:
            >>> crystal = Crystal(['Na', 'Cl', 'Na'], [[0,0,0], [0.5,0.5,0.5], [0.25,0.25,0.25]], Lattice.cubic(5.64))
            >>> crystal.symbol_set
            ('Na', 'Cl')
            >>> crystal.sort_atoms('alphabet')  # Reorders to Cl, Na, Na
            >>> crystal.symbol_set  # Now reflects new order
            ('Cl', 'Na')
            >>> molecule = Molecule(['O', 'H', 'H'], [[0,0,0], [0.96,0,0], [-0.24,0.93,0]])
            >>> molecule.symbol_set
            ('O', 'H')
        """
        # Preserve order of first appearance (VASP format style)
        seen = set()
        unique_symbols = []
        for specie in self.species:
            if specie not in seen:
                unique_symbols.append(specie)
                seen.add(specie)
        return tuple(unique_symbols)

    def copy(self) -> "Structure":
        """
        Create a deep copy of the structure.

        Creates a new Structure instance (Crystal or Molecule) with copied
        data. The copy is independent of the original - modifications to
        one will not affect the other.

        Returns:
            Structure: A new instance of the structure with copied data.
                     Type matches the original (Crystal or Molecule).

        Example:
            >>> from matsimpy.core import Crystal, Lattice
            >>> crystal = Crystal(['Si', 'Si'], [[0,0,0], [0.25,0.25,0.25]], Lattice.cubic(5.43))
            >>> crystal_copy = crystal.copy()
            >>> crystal_copy is not crystal  # Different objects
            True
            >>> crystal_copy.species == crystal.species  # Same data
            True
            >>> crystal_copy.add_atom('H', [0.5, 0.5, 0.5])
            >>> len(crystal)  # Original unchanged
            2
            >>> len(crystal_copy)  # Copy modified
            3
        """
        return self.from_dict(self.as_dict())

    def __hash__(self) -> int:
        """
        Generate a hash for the structure.

        Positions are rounded to 8 decimal places to handle floating-point
        precision issues. This ensures that structures with nearly identical
        positions (within tolerance) hash to the same value.

        Returns:
            int: Hash value for the structure.

        Note:
            This method enables Structure objects to be used as dictionary keys
            or in sets. The hash is based on species, positions, and lattice.

        Example:
            >>> crystal1 = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(5.64))
            >>> crystal2 = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(5.64))
            >>> hash(crystal1) == hash(crystal2)
            True
            >>> {crystal1: 'value'}  # Can use as dictionary key
            {<Crystal object>: 'value'}
        """
        # Create a normalized dictionary with rounded positions
        hash_dict = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": list(self.species),
            "positions": np.round(self.positions, decimals=8).tolist(),
        }
        if self.lattice is not None:
            hash_dict["lattice"] = self.lattice.as_dict()

        # Use hashlib to generate a SHA256 hash
        hash_str = str(hash_dict).encode("utf-8")
        hash_bytes = hashlib.sha256(hash_str).digest()
        # Use first 8 bytes for standard Python hash size (64-bit)
        return int.from_bytes(hash_bytes[:8], byteorder="big", signed=True)

    def __eq__(self, other: Any) -> bool:
        """
        Check equality with another Structure.

        Two structures are equal if they have:
        - Same species (exact match)
        - Same positions (within floating-point tolerance of 1e-8)
        - Same lattice (if both have lattices, compared with tolerance)

        Args:
            other: Another object to compare with.

        Returns:
            bool: True if structures are equal within tolerance, False otherwise.

        Note:
            Uses numpy.allclose() for numerical tolerance to handle
            floating-point precision issues. Lattices are compared if both
            structures have them.

        Example:
            >>> crystal1 = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(5.64))
            >>> crystal2 = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(5.64))
            >>> crystal1 == crystal2
            True
            >>> crystal3 = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], Lattice.cubic(5.65))
            >>> crystal1 == crystal3  # Different lattice
            False
        """
        if not isinstance(other, Structure):
            return False

        # Check species
        if self.species != other.species:
            return False

        # Check positions with tolerance
        if not np.allclose(self.positions, other.positions, atol=1e-8, rtol=0):
            return False

        # Check lattice (if both have lattices)
        if self.lattice is not None and other.lattice is not None:
            # Compare lattice matrices
            if not np.allclose(
                self.lattice.matrix, other.lattice.matrix, atol=1e-8, rtol=0
            ):
                return False
        elif self.lattice is not None or other.lattice is not None:
            # One has lattice, other doesn't
            return False

        return True

    @property
    def composition(self) -> Composition:
        """
        Get the Composition object for the structure (cached).

        Returns a Composition object that provides access to element counts,
        mass calculations, and formatted output. The result is cached for
        performance.

        Returns:
            Composition: Composition object with element counts and properties.

        Note:
            The composition is derived from the formula and cached. The cache
            is invalidated when atoms are added, removed, or substituted.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], lattice)
            >>> comp = crystal.composition
            >>> comp['Na']
            1
            >>> comp['Cl']
            1
            >>> comp.mass  # Total mass in atomic mass units
            58.4428...
            >>>
            >>> molecule = Molecule(['O', 'H', 'H'], [[0,0,0], [0.96,0,0], [-0.24,0.93,0]])
            >>> comp = molecule.composition
            >>> comp['H']
            2
            >>> comp['O']
            1
        """
        if self._cached_composition is None or self._formula_dirty:
            self._cached_composition = Composition(self.formula)
        return self._cached_composition

    @property
    def elements(self) -> List[Element]:
        """
        Get Element objects for all species in the structure.

        Returns a list of Element objects corresponding to each species
        in the structure, in the same order as self.species.

        Returns:
            List[Element]: List of Element objects for all species.

        Examples:
            >>> crystal = Crystal(['Si', 'O', 'Si'], [[0,0,0], [0.5,0.5,0.5], [0.25,0.25,0.25]], lattice)
            >>> elements = crystal.elements
            >>> elements[0].atomic_no  # 14 (Si)
            14
            >>> elements[1].atomic_no  # 8 (O)
            8
        """
        return [Element.get_element(specie) for specie in self.species]

    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
    ) -> None:
        """
        Add one or more atoms to the structure (in-place).

        Adds atoms to the structure and invalidates cached properties
        (formula, composition). The operation modifies the structure directly.

        Args:
            species: Atomic species. Can be:
                - str: Single element symbol (e.g., 'H')
                - List[str]: List of element symbols (e.g., ['H', 'O'])
            position: Atomic position(s). Can be:
                - List[float]: Single 3D coordinate [x, y, z]
                - List[List[float]]: List of 3D coordinates [[x1, y1, z1], [x2, y2, z2], ...]

        Raises:
            ValueError: If position is not 3D.
            ValueError: If number of species doesn't match number of positions.

        Note:
            This method modifies the structure in-place. Cached properties
            (formula, composition) are invalidated and will be recalculated
            on next access.

        Example:
            >>> # Add single atom
            >>> structure.add_atom('H', [0, 0, 0])
            >>> len(structure)
            3
            >>>
            >>> # Add multiple atoms
            >>> structure.add_atom(['H', 'O'], [[0, 0, 0], [1, 0, 0]])
            >>> len(structure)
            5
            >>>
            >>> # Formula is recalculated
            >>> structure.formula  # Cache invalidated, recalculated
        """
        # Handle single atom case
        if isinstance(species, str):
            species = [species]
            position = [position]

        # Validate inputs
        if len(species) != len(position):
            raise ValueError(
                f"Number of species ({len(species)}) must match "
                f"number of positions ({len(position)})"
            )

        if not species:
            return  # Nothing to add

        # Validate all positions are 3D
        positions_array = np.array(position, dtype=np.float64)
        if positions_array.ndim == 1:
            # Single atom: [x, y, z]
            if len(positions_array) != 3:
                raise ValueError("Position must be a 3D coordinate")
            positions_array = positions_array.reshape(1, 3)
        elif positions_array.ndim == 2:
            # Multiple atoms: [[x1, y1, z1], ...]
            if positions_array.shape[1] != 3:
                raise ValueError("Positions must be 3D coordinates")
        else:
            raise ValueError(
                "Position must be a 3D coordinate or list of 3D coordinates"
            )

        # Add atoms
        species_list = list(self.species)
        species_list.extend(species)
        self.species = tuple(species_list)
        self.positions = np.vstack([self.positions, positions_array])

        # Invalidate caches
        self._formula_dirty = True
        self._cached_composition = None
        self._cached_formula = None
        # Properties computed lazily on access

    def remove_atom(self, index: int) -> None:
        """
        Remove an atom from the structure by index (in-place).

        Removes the atom at the specified index and invalidates cached
        properties (formula, composition). The operation modifies the
        structure directly.

        Args:
            index: Zero-based index of the atom to remove.

        Raises:
            IndexError: If index is out of range (not in [0, len(structure))).

        Note:
            This method modifies the structure in-place. Cached properties
            (formula, composition) are invalidated and will be recalculated
            on next access.

        Example:
            >>> structure = Molecule(['O', 'H', 'H'], [[0,0,0], [0.96,0,0], [-0.24,0.93,0]])
            >>> len(structure)
            3
            >>> structure.remove_atom(0)  # Remove first atom (O)
            >>> len(structure)
            2
            >>> structure.species
            ('H', 'H')
            >>> structure.formula  # Cache invalidated, recalculated
            'H2'
        """
        if not (0 <= index < len(self.species)):
            raise IndexError("Invalid atom index.")

        # Maintain tuple immutability
        species_list = list(self.species)
        species_list.pop(index)
        self.species = tuple(species_list)
        self.positions = np.delete(self.positions, index, axis=0)
        self._formula_dirty = True
        self._cached_composition = None
        # Properties computed lazily on access

    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> None:
        """
        Substitute atoms with new species (in-place).

        This is a convenience method that modifies the structure directly.
        For functional style (returning new object), use matsimpy.transformation.substitute().

        Note: This method delegates to the transformation module for the actual implementation.

        Args:
            indices: Atom index, list of indices, or :class:`~matsimpy.utils.selection.AtomSelection`
                    object to substitute.
            new_species: New species symbol, list of symbols, or dict mapping old->new species.
                       If dict, maps old species to new species (e.g., {'Si': 'Ge', 'O': 'S'}).

        Raises:
            IndexError: If index is out of range.
            ValueError: If number of indices doesn't match number of species.
            KeyError: If dict mapping doesn't contain a species.

        Examples:
            >>> structure.substitute(0, 'Ge')  # Substitute atom at index 0
            >>> structure.substitute([0, 1], ['Ge', 'Ge'])  # Substitute multiple
            >>> # Using AtomSelection
            >>> from matsimpy.utils.selection import AtomSelection
            >>> sel = AtomSelection(structure).by_species('Si')
            >>> structure.substitute(sel, 'Ge')  # Substitute selected atoms
            >>> # Using dict mapping (maps old species to new species)
            >>> structure.substitute([0, 1, 2], {'Si': 'Ge', 'O': 'S'})
        """
        # Delegate to transformation module for implementation
        from ..transformation.chemical.substitution import substitute

        substitute(self, indices, new_species, inplace=True)
        self._formula_dirty = True
        self._cached_composition = None
        self._cached_formula = None

    def substitute_all(self, old_species: str, new_species: str) -> None:
        """
        Substitute all atoms of a given species with a new species (in-place).

        This is a convenience method that modifies the structure directly.
        For functional style (returning new object), use matsimpy.transformation.substitute_all().

        Note: This method delegates to the transformation module for the actual implementation.

        Args:
            old_species: Species to replace
            new_species: Replacement species

        Examples:
            >>> structure.substitute_all('Si', 'Ge')  # Replace all Si with Ge
        """
        # Delegate to transformation module for implementation
        from ..transformation.chemical.substitution import substitute_all

        substitute_all(self, old_species, new_species, inplace=True)
        self._formula_dirty = True
        self._cached_composition = None
        self._cached_formula = None

    def sort_atoms(self, sort_by: str = "element") -> None:
        """
        Sort atoms in the structure (in-place).

        Reorders the internal species and positions arrays according to the
        specified sorting method. This affects the order of atoms in the
        structure and may change the symbol_set property.

        Args:
            sort_by: Sorting method. Options:
                - 'element': Sort by atomic number, then by position (x, y, z)
                - 'alphabet': Sort alphabetically by species symbol, then by position

        Raises:
            ValueError: If sort_by is not 'element' or 'alphabet'.

        Note:
            This method modifies the structure in-place. The symbol_set property
            will reflect the new order of first appearance after sorting.

        Example:
            >>> structure = Crystal(['Na', 'Cl', 'Na'], [[0,0,0], [0.5,0.5,0.5], [0.25,0.25,0.25]], lattice)
            >>> structure.symbol_set
            ('Na', 'Cl')
            >>> structure.sort_atoms('element')  # Sort by atomic number
            >>> structure.symbol_set  # May change based on new order
            ('Na', 'Cl')  # or ('Cl', 'Na') depending on sorting
            >>>
            >>> structure.sort_atoms('alphabet')  # Sort alphabetically
            >>> structure.symbol_set
            ('Cl', 'Na')
        """
        # Create list of (index, specie, position) tuples
        atoms = list(zip(range(len(self.species)), self.species, self.positions))

        # Sort by element
        if sort_by == "element":
            # Sort by atomic number, then by position for same element
            # Use .elements for efficient Element access
            elements = self.elements
            sorted_atoms = sorted(
                atoms,
                key=lambda a: (
                    elements[a[0]].atomic_no,
                    a[2][0],
                    a[2][1],
                    a[2][2],
                ),
            )
        elif sort_by == "alphabet":
            # Sort alphabetically by species symbol, then by position
            sorted_atoms = sorted(
                atoms, key=lambda a: (a[1], a[2][0], a[2][1], a[2][2])
            )
        else:
            raise ValueError("sort_by must be 'element' or 'alphabet'")

        # Extract sorted species and positions
        sorted_species = [a[1] for a in sorted_atoms]
        sorted_positions = np.array([a[2] for a in sorted_atoms])

        # Update internal data
        self.species = tuple(sorted_species)
        self.positions = sorted_positions

        # Invalidate caches
        self._formula_dirty = True
        self._cached_composition = None

        # Reinitialize sites if they exist
        if hasattr(self, "_sites"):
            if hasattr(self, "_initialize_sites"):
                self._sites = self._initialize_sites()

    @abstractmethod
    def get_neighbor_list(
        self, cutoff: float, atom_index: Optional[int] = None, **kwargs
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Get neighbor list with consistent interface across all subclasses.

        This is an abstract method that must be implemented by subclasses
        (Crystal or Molecule). Each subclass provides its own implementation
        that handles periodic boundary conditions appropriately.

        Args:
            cutoff: Cutoff radius in Angstroms for neighbor finding.
            atom_index: Optional atom index. If None, returns neighbors for all atoms.
                       If specified, returns neighbors only for that atom.
            **kwargs: Additional subclass-specific parameters:
                - use_pbc (Crystal only): Whether to use periodic boundary conditions
                - Other subclass-specific parameters

        Returns:
            Dict[int, List[Tuple[int, float]]]: Dictionary mapping atom index to
            list of (neighbor_index, distance) tuples. Distances are in Angstroms.
            - If atom_index is provided: dict contains only that entry {atom_index: [(neighbor, dist), ...]}
            - If atom_index is None: dict contains entries for all atoms

        Raises:
            NotImplementedError: If not implemented by subclass (should not occur
                                in normal usage as Crystal and Molecule implement this).
            IndexError: If atom_index is out of range.

        Note:
            This is an abstract method. Subclasses must implement it:
            - :class:`~matsimpy.core.crystal.Crystal`: Handles PBC
            - :class:`~matsimpy.core.molecule.Molecule`: No PBC

        Example:
            >>> # Get neighbors for all atoms
            >>> neighbors = structure.get_neighbor_list(5.0)
            >>> neighbors[0]  # Neighbors of atom 0
            [(1, 2.5), (2, 3.1), ...]
            >>>
            >>> # Get neighbors for specific atom
            >>> neighbors = structure.get_neighbor_list(5.0, atom_index=0)
            >>> neighbors
            {0: [(1, 2.5), (2, 3.1), ...]}
            >>>
            >>> # For crystals, can specify PBC usage
            >>> neighbors = crystal.get_neighbor_list(5.0, use_pbc=True)
        """
        raise NotImplementedError("get_neighbor_list must be implemented by subclasses")

    def __len__(self) -> int:
        """
        Get the number of atoms in the structure.

        Returns:
            int: Number of atoms (equal to len(species) and len(positions)).

        Example:
            >>> structure = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], lattice)
            >>> len(structure)
            2
        """
        return len(self.species)

    def __contains__(self, item: str) -> bool:
        """
        Check if an element is present in the structure.

        Enables the use of 'in' operator to check for element presence.

        Args:
            item: Element symbol to check for (e.g., 'Si', 'O', 'Fe').

        Returns:
            bool: True if the element is present in the structure, False otherwise.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], lattice)
            >>> 'Na' in crystal
            True
            >>> 'Si' in crystal
            False
            >>> molecule = Molecule(['O', 'H', 'H'], [[0,0,0], [0.96,0,0], [-0.24,0.93,0]])
            >>> 'H' in molecule
            True
            >>> 'C' in molecule
            False
        """
        return item in self.species

    def __iter__(self):
        """
        Iterate over sites in the structure.

        Yields site objects (Site for Molecule, CrystalSite for Crystal)
        for each atom in the structure. This enables using the structure
        directly in for loops.

        Yields:
            Site or CrystalSite: Site object for each atom in the structure.

        Note:
            The sites property must be implemented by subclasses (Crystal, Molecule).
            Each site contains the species, position, and any additional properties.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0,0,0], [0.5,0.5,0.5]], lattice)
            >>> for site in crystal:
            ...     print(f"{site.species} at {site.frac_position}")
            Na at [0. 0. 0.]
            Cl at [0.5 0.5 0.5]
            >>>
            >>> molecule = Molecule(['O', 'H', 'H'], [[0,0,0], [0.96,0,0], [-0.24,0.93,0]])
            >>> for site in molecule:
            ...     print(f"{site.species} at {site.position}")
            O at [0. 0. 0.]
            H at [0.96 0.   0.  ]
            H at [-0.24  0.93  0.  ]
            >>>
            >>> # Can also convert to list
            >>> sites_list = list(crystal)
            >>> len(sites_list)
            2
        """
        return iter(self.sites)
