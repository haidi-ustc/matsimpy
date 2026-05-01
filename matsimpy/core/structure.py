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
    from ..calculator.base import Calculator


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

    # ======================================================================
    # Construction & core data model
    # ======================================================================

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

        # Backing field for species (use property later for external mutation)
        self._species = tuple(species_list)  # Make immutable backing field

        self._positions = self._validate_positions(positions)

        # Validate positions match species count
        if len(self._positions) != len(self._species):
            raise ValueError(
                f"Number of positions ({len(self._positions)}) must match "
                f"number of species ({len(self._species)})"
            )

        self.lattice = lattice

        # Compute-once caches (never invalidated — structure is immutable)
        self._composition: Optional[Composition] = None
        self._formula: Optional[str] = None

    @property
    def species(self) -> Tuple[str, ...]:
        """Get the species as a tuple of strings."""
        return self._species

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

        # Handle empty positions (0 atoms)
        if len(positions_array) == 0:
            return positions_array.reshape(0, 3)

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

    # ======================================================================
    # Coordinate accessors
    # ======================================================================

    @property
    def positions(self) -> np.ndarray:
        """
        Atomic positions as a read-only numpy array, shape (n_atoms, 3), in Angstroms.

        Always returns **Cartesian** coordinates for all structure types
        (both Molecule and Crystal).  For Crystal, use ``frac_positions``
        to access fractional coordinates explicitly.

        The returned array is a read-only view; mutating it raises ValueError.
        Use the immutable modification methods (add_atom, remove_atom, etc.) to
        produce a new structure with updated positions.
        """
        view = self._positions.view()
        view.flags.writeable = False
        return view

    # ======================================================================
    # (De)serialization
    # ======================================================================

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
            'NaCl'
        """
        species = d["species"]
        positions = d["positions"]
        lattice = (
            Lattice.from_dict(d["lattice"]) if d.get("lattice") is not None else None
        )
        return cls(species, positions, lattice)

    # ======================================================================
    # Chemistry-derived properties (cached)
    # ======================================================================

    @property
    def formula(self) -> str:
        """Get the chemical formula of the structure (cached)."""
        if self._formula is None:
            self._formula = self._compute_formula()
        return self._formula

    def _compute_formula(self) -> str:
        element_counter = Counter(self.species)
        seen = set()
        formula = ""
        for element in self.species:
            if element not in seen:
                count = element_counter[element]
                formula += element + (str(count) if count > 1 else "")
                seen.add(element)
        return formula

    # ======================================================================
    # Convenience properties
    # ======================================================================

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

    # ======================================================================
    # Copy / hashing / equality
    # ======================================================================

    def copy(self) -> "Structure":
        """
        Create a deep copy of the structure.

        Creates a new Structure instance (Crystal or Molecule) with copied
        data. The copy is independent of the original — modifications to
        one will not affect the other.

        Returns:
            Structure: A new instance of the structure with copied data.
                     Type matches the original (Crystal or Molecule).

        Note:
            The attached calculator (``calc``) is **not** copied.  The returned
            structure always has ``calc = None``.  Copy and re-attach the
            calculator explicitly if needed::

                new = crystal.copy()
                new.calc = crystal.calc  # share, or pass a new instance

        Example:
            >>> from matsimpy.core import Crystal, Lattice
            >>> crystal = Crystal(['Si', 'Si'], [[0,0,0], [0.25,0.25,0.25]], Lattice.cubic(5.43))
            >>> crystal_copy = crystal.copy()
            >>> crystal_copy is not crystal  # Different objects
            True
            >>> crystal_copy.species == crystal.species  # Same data
            True
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
        # Round positions to 7 decimal places.  The equality tolerance in
        # __eq__ is atol=1e-7, which is strictly less than the rounding bucket
        # (5e-8), so any two positions considered equal will round identically
        # and produce the same hash — satisfying the hash contract.
        hash_dict = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": list(self.species),
            "positions": np.round(self.positions, decimals=7).tolist(),
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

        # Check positions with tolerance.  atol=1e-7 keeps the equality window
        # strictly inside the hash rounding bucket (5e-8 for 7 d.p.), ensuring
        # a == b ⟹ hash(a) == hash(b).
        if not np.allclose(self.positions, other.positions, atol=1e-7, rtol=0):
            return False

        # Check lattice (if both have lattices)
        if self.lattice is not None and other.lattice is not None:
            # Compare lattice matrices using the same tolerance as Lattice.__eq__
            if not np.allclose(
                self.lattice.matrix, other.lattice.matrix, atol=1e-6, rtol=0
            ):
                return False
        elif self.lattice is not None or other.lattice is not None:
            # One has lattice, other doesn't
            return False

        return True

    @property
    def composition(self) -> Composition:
        """Get the Composition object for the structure (cached)."""
        if self._composition is None:
            self._composition = Composition(self.formula)
        return self._composition

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

    # ------------------------------------------------------------------
    # Calculator attachment
    # ------------------------------------------------------------------

    @property
    def calc(self) -> Optional["Calculator"]:
        """
        Get the attached calculator.

        Returns:
            :obj:`~matsimpy.calculator.base.Calculator` or None

        Example:
            >>> from matsimpy.calculator import LennardJones
            >>> structure.calc = LennardJones()
            >>> structure.calc = None  # detach
        """
        return getattr(self, "_calculator", None)

    @calc.setter
    def calc(self, calculator: Optional["Calculator"]) -> None:
        """
        Attach or detach a calculator.

        Args:
            calculator: A Calculator instance, or None to detach.

        Raises:
            TypeError: If *calculator* is not a Calculator instance or None.
        """
        from ..calculator.base import Calculator

        if calculator is not None and not isinstance(calculator, Calculator):
            raise TypeError(
                f"Calculator must be a Calculator instance, got {type(calculator)}"
            )
        self._calculator = calculator

    def _needs_calculation(self) -> bool:
        """Return True if a (re-)calculation is required."""
        calc = self.calc
        if calc is None:
            return False
        return (
            not calc._calculation_performed
            or getattr(calc, "_last_structure_hash", None) != hash(self)
        )

    def get_potential_energy(self) -> float:
        """
        Get potential energy from the attached calculator.

        Triggers ``calculator.calculate(self)`` automatically if the results
        are not yet available or if the structure has changed since the last run.

        Returns:
            float: Potential energy in eV.

        Raises:
            ValueError: If no calculator is attached.
        """
        if self.calc is None:
            raise ValueError(
                f"No calculator attached. Set {self.__class__.__name__.lower()}"
                f".calc = calculator first."
            )
        if self._needs_calculation():
            self.calc.calculate(self)
        return self.calc.get_potential_energy()

    def get_forces(self) -> np.ndarray:
        """
        Get atomic forces from the attached calculator.

        Triggers ``calculator.calculate(self)`` automatically if needed.

        Returns:
            np.ndarray: Forces array of shape (N, 3) in eV/Å.

        Raises:
            ValueError: If no calculator is attached.
        """
        if self.calc is None:
            raise ValueError(
                f"No calculator attached. Set {self.__class__.__name__.lower()}"
                f".calc = calculator first."
            )
        if self._needs_calculation():
            self.calc.calculate(self)
        return self.calc.get_forces()

    def get_stress(self) -> np.ndarray:
        """
        Get the stress tensor from the attached calculator.

        The base implementation raises ``NotImplementedError`` — only subclasses
        that support stress (e.g. ``Crystal``) override this method.

        Raises:
            NotImplementedError: Always (in the base class).
            ValueError: If no calculator is attached (in subclasses).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support stress calculations."
        )

    # ------------------------------------------------------------------

    # ======================================================================
    # Subclass extension hooks
    # ======================================================================

    def _extra_dict_fields(self) -> Dict[str, Any]:
        """
        Return extra fields required to reconstruct this structure via ``from_dict``.

        **Subclass contract** — override this method when your subclass stores
        state beyond ``species`` and ``positions``:

        1. Every key returned here must be accepted by ``from_dict`` (or by
           the subclass ``__init__`` which ``from_dict`` calls).
        2. Values must be JSON-serialisable (use ``.tolist()`` for ndarrays,
           ``as_dict()`` for nested ``MSONable`` objects).
        3. ``add_atom`` / ``remove_atom`` / ``sort_atoms`` in the **base class**
           forward these fields unchanged.  If any field contains a **per-atom**
           list (e.g. ``site_properties``), also override
           ``_filter_per_atom_data`` and ``_reorder_per_atom_data`` so that
           those lists are correctly adjusted when atoms are removed or reordered.
        4. Do **not** include ``species`` or ``positions`` — those are always
           managed by the base class.

        Returns:
            dict: Extra serialisation fields (empty dict for the base class).
        """
        return {}

    # ======================================================================
    # Per-atom metadata adjustment hooks (used by base mutation helpers)
    # ======================================================================

    def _filter_per_atom_data(self, kept_indices: List[int]) -> Dict[str, Any]:
        """
        Return per-atom serialisation fields filtered to *kept_indices*.

        Called by :meth:`remove_atom` (base) to correct any per-atom lists
        (e.g. ``site_properties``) that would otherwise be passed stale via
        :meth:`_extra_dict_fields`.  The returned dict is merged **after**
        ``_extra_dict_fields()``, so it overrides matching keys.

        Override in subclasses that store per-atom lists::

            def _filter_per_atom_data(self, kept_indices):
                if not self.site_properties:
                    return {}
                return {"site_properties":
                        [self.site_properties[i] for i in kept_indices]}

        Returns:
            dict: Filtered per-atom fields (empty dict in the base class).
        """
        return {}

    def _reorder_per_atom_data(self, new_order: List[int]) -> Dict[str, Any]:
        """
        Return per-atom serialisation fields reordered to *new_order*.

        Called by :meth:`sort_atoms` (base) to correct any per-atom lists
        that would otherwise be passed in original order via
        :meth:`_extra_dict_fields`.  The returned dict is merged **after**
        ``_extra_dict_fields()``, overriding matching keys.

        Override in subclasses that store per-atom lists::

            def _reorder_per_atom_data(self, new_order):
                if not self.site_properties:
                    return {}
                return {"site_properties":
                        [self.site_properties[i] for i in new_order]}

        Returns:
            dict: Reordered per-atom fields (empty dict in the base class).
        """
        return {}

    # ======================================================================
    # Structure editing (immutable: returns new instances)
    # ======================================================================

    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
        site_properties: Optional[Union[dict, List[dict]]] = None,
    ) -> "Structure":
        """
        Add one or more atoms and return a new structure.

        Args:
            species: Element symbol or list of symbols.
            position: 3D position or list of 3D positions (coordinate system
                      depends on the concrete subclass — Cartesian for Molecule,
                      fractional by default for Crystal).
            site_properties: Per-atom property dict or list thereof.  The base
                implementation accepts the parameter for API consistency but
                **ignores it**.  Crystal and Molecule override this method to
                handle site properties correctly.

        Returns:
            Structure: New structure with the added atom(s).

        Warning:
            Subclasses that store per-atom state beyond ``site_properties``
            must override this method entirely; the base round-trip via
            ``from_dict`` will not preserve state that is not captured by
            ``_extra_dict_fields`` + ``_filter_per_atom_data``.
        """

        # Handle single atom case
        if isinstance(species, str):
            species = [species]
            position = [position]

        if len(species) != len(position):
            raise ValueError(
                f"Number of species ({len(species)}) must match "
                f"number of positions ({len(position)})"
            )

        if not species:
            return self.copy()

        positions_array = np.array(position, dtype=np.float64)
        if positions_array.ndim == 1:
            if len(positions_array) != 3:
                raise ValueError("Position must be a 3D coordinate")
            positions_array = positions_array.reshape(1, 3)
        elif positions_array.ndim == 2:
            if positions_array.shape[1] != 3:
                raise ValueError("Positions must be 3D coordinates")
        else:
            raise ValueError(
                "Position must be a 3D coordinate or list of 3D coordinates"
            )

        new_species = list(self.species)
        new_species.extend(species)
        new_positions = np.vstack([self._positions, positions_array])

        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": new_species,
            "positions": new_positions.tolist(),
            **self._extra_dict_fields(),
        })

    def remove_atom(
        self,
        index: Union[int, List[int], "AtomSelection"],
    ) -> "Structure":
        """
        Remove one or more atoms by index and return a new structure.

        Args:
            index: A single atom index, a list of indices, or an AtomSelection.
                   Duplicates are silently ignored.

        Raises:
            IndexError: If any index is out of range.

        Warning:
            Subclasses that store per-atom lists (e.g. ``site_properties``)
            must override ``_filter_per_atom_data`` so that those lists are
            trimmed correctly.
        """
        from ..utils.selection import AtomSelection

        if isinstance(index, AtomSelection):
            if index.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            index = index.indices
        if isinstance(index, int):
            index = [index]

        n = len(self.species)
        indices_to_remove = sorted(set(index), reverse=True)
        for idx in indices_to_remove:
            if not (0 <= idx < n):
                raise IndexError(f"Atom index {idx} out of range [0, {n - 1}]")

        kept_indices = [i for i in range(n) if i not in set(index)]

        species_list = list(self.species)
        new_positions = self._positions.copy()
        for idx in indices_to_remove:
            species_list.pop(idx)
            new_positions = np.delete(new_positions, idx, axis=0)

        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": species_list,
            "positions": new_positions.tolist(),
            **self._extra_dict_fields(),
            # Overrides any stale per-atom lists (e.g. site_properties) that
            # _extra_dict_fields() may have emitted with the old atom count.
            **self._filter_per_atom_data(kept_indices),
        })

    # ------------------------------------------------------------------
    # Species editing
    # ------------------------------------------------------------------

    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> "Structure":
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        if isinstance(indices, int):
            indices = [indices]

        if isinstance(new_species, dict):
            new_species_list = []
            for idx in indices:
                old_spec = self.species[idx]
                if old_spec not in new_species:
                    raise KeyError(
                        f"Species '{old_spec}' at index {idx} "
                        f"not found in substitution mapping"
                    )
                new_species_list.append(new_species[old_spec])
            new_species = new_species_list

        if isinstance(new_species, str):
            new_species = [new_species] * len(indices)

        if len(indices) != len(new_species):
            raise ValueError(
                f"Number of indices ({len(indices)}) must match "
                f"number of new species ({len(new_species)})"
            )

        species_list = list(self.species)
        for idx, new_spec in zip(indices, new_species):
            species_list[idx] = new_spec

        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": species_list,
            "positions": self._positions.tolist(),
            **self._extra_dict_fields(),
        })

    def substitute_all(self, old_species: str, new_species: str) -> "Structure":
        species_list = [
            new_species if s == old_species else s for s in self.species
        ]
        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": species_list,
            "positions": self._positions.tolist(),
            **self._extra_dict_fields(),
        })

    # ------------------------------------------------------------------
    # Reordering
    # ------------------------------------------------------------------

    def sort_atoms(self, sort_by: str = "element") -> "Structure":
        """
        Sort atoms and return a new structure.

        Warning:
            Subclasses that store per-atom lists (e.g. ``site_properties``)
            must override ``_reorder_per_atom_data`` so that those lists are
            reordered to match the new atom order, or override this method
            entirely.
        """
        atoms = list(zip(range(len(self.species)), self.species, self._positions))

        if sort_by == "element":
            elements = self.elements
            sorted_atoms = sorted(
                atoms,
                key=lambda a: (
                    elements[a[0]].atomic_no,
                    a[2][0], a[2][1], a[2][2],
                ),
            )
        elif sort_by == "alphabet":
            sorted_atoms = sorted(
                atoms, key=lambda a: (a[1], a[2][0], a[2][1], a[2][2])
            )
        else:
            raise ValueError("sort_by must be 'element' or 'alphabet'")

        sorted_species = [a[1] for a in sorted_atoms]
        sorted_positions = np.array([a[2] for a in sorted_atoms])
        sorted_indices = [a[0] for a in sorted_atoms]

        return self.__class__.from_dict({
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": sorted_species,
            "positions": sorted_positions.tolist(),
            **self._extra_dict_fields(),
            # Overrides any per-atom lists in _extra_dict_fields() that need
            # to be reordered to match the new atom sequence.
            **self._reorder_per_atom_data(sorted_indices),
        })

    # ======================================================================
    # Abstract API
    # ======================================================================

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
