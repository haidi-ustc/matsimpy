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

import copy
import json
import sys
import warnings
from types import MappingProxyType

import numpy as np
from typing import List, Mapping, Sequence, Union, Optional, Dict, Tuple, Any, TYPE_CHECKING
import hashlib
from collections import Counter
from abc import ABC, abstractmethod
from monty.json import MSONable, MontyDecoder, MontyEncoder

from .lattice import Lattice
from .composition import Composition
from .periodic_table import Element
from ..utils.dict_utils import copy_properties
from ._validation import _MISSING, _validate_metadata, normalize_species, reject_bool_coordinates, resolve_indices, validate_site_properties
from matsimpy.constants import POSITION_TOL, LATTICE_TOL

if TYPE_CHECKING:
    from ..analysis.selection import AtomSelection


def _require_finite_positions(positions: np.ndarray) -> None:
    """Raise ValueError if ``positions`` contains NaN or +/-Inf."""
    if not np.isfinite(positions).all():
        kind = "NaN" if np.isnan(positions).any() else "infinite"
        raise ValueError(f"Positions cannot contain {kind} values.")


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
        positions (np.ndarray): Cartesian atomic positions with shape (n_atoms, 3).
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
        positions: List of atomic positions. The public ``positions`` API is
                  always Cartesian; Crystal also exposes ``frac_positions`` for
                  fractional coordinates.
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

    def _set_state(
        self,
        species: Sequence[Any],
        positions: Any,
        lattice: Optional[Lattice] = None,
        site_properties: Optional[Sequence[Mapping[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Single place where a structure's state is assigned (0.8.7).

        Both ``__init__`` (after input validation/conversion) and ``_construct``
        (internal fast path) end here, so the two construction paths can no
        longer drift apart (the cause of several 0.8.x bugs).
        """
        self._species = tuple(normalize_species(s) for s in species)
        pos = np.array(positions, dtype=np.float64, copy=True)
        if pos.size == 0:
            pos = pos.reshape(0, 3)
        if pos.ndim != 2 or pos.shape[1] != 3:
            raise ValueError("positions must have shape (n_atoms, 3)")
        if len(pos) != len(self._species):
            raise ValueError(
                f"Number of positions ({len(pos)}) must match "
                f"number of species ({len(self._species)})"
            )
        # Checked here, not only in __init__, so _construct and add_atom
        # (which both end here) cannot create atoms at NaN/Inf positions.
        _require_finite_positions(pos)
        pos.flags.writeable = False
        self._coords = pos  # native: fractional (Crystal) / Cartesian (Molecule)
        self._lattice = lattice
        self._site_properties = validate_site_properties(site_properties, len(self._species))
        self._metadata = _validate_metadata(metadata)
        # Compute-once caches (never invalidated — structure is immutable)
        self._composition = None
        self._formula = None

    @classmethod
    def _construct(cls, species: Sequence[Any], positions: Any, lattice: Optional[Lattice] = None, **kwargs: Any) -> "Structure":
        """Internal fast constructor: skips input-type conversion, not validation."""
        obj = cls.__new__(cls)
        obj._set_state(species, positions, lattice, **kwargs)
        return obj

    @staticmethod
    def _normalize_species_input(species: Sequence[Any]) -> List[str]:
        """Validate the user-facing species argument (homogeneous str / int / Element)."""
        if all(isinstance(s, str) for s in species):
            pass
        elif all(isinstance(s, (int, np.integer)) and not isinstance(s, (bool, np.bool_)) for s in species):
            pass
        elif all(isinstance(s, Element) for s in species):
            pass
        else:
            raise TypeError(
                "Invalid type for species. Must be a list of atomic symbols, "
                "a list of atomic numbers, or a list of Element objects."
            )
        return [normalize_species(s) for s in species]

    def _construct_kwargs(self) -> Dict[str, Any]:
        """State carried over by atom-changing operations (metadata is not)."""
        return {"site_properties": self._site_properties or None}

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
            positions: List of 3D atomic positions. The public ``positions`` API
                     is always Cartesian; Crystal also exposes ``frac_positions``
                     for fractional coordinates.
            lattice: Optional Lattice object. Required for Crystal, None for Molecule.

        Raises:
            TypeError: If species contains mixed types or invalid types.
            ValueError: If species and positions have different lengths.
            ValueError: If positions are not 3D coordinates or contain NaN/Inf.

        Note:
            This is an abstract base class constructor. Use Crystal or Molecule
            subclasses instead of instantiating Structure directly.
        """
        species_list = self._normalize_species_input(species)
        if len(species_list) != len(positions):
            raise ValueError(
                f"Number of species ({len(species_list)}) must match "
                f"number of positions ({len(positions)})"
            )
        self._set_state(species_list, self._validate_positions(positions), lattice)

    @property
    def species(self) -> Tuple[str, ...]:
        """Get the species as a tuple of strings."""
        return self._species

    # ------------------------------------------------------------------
    # Per-site properties (row view + column API) and structure metadata
    # ------------------------------------------------------------------

    @property
    def site_properties(self) -> Tuple[Dict[str, Any], ...]:
        """Per-site properties as deep-copied dicts (one per atom; ``()`` if none)."""
        return tuple(copy.deepcopy(p) for p in self._site_properties)

    def site_property(self, name: str, default: Any = _MISSING) -> List[Any]:
        """Return one per-site property as a list (one value per atom).

        Raises ``KeyError`` if some site lacks *name* and no *default* is given.

        Example:
            >>> magmoms = crystal.site_property("magmom")
        """
        if not self._site_properties and default is _MISSING:
            raise KeyError(name)
        rows = self._site_properties or [{}] * len(self._species)
        out = []
        for idx, props in enumerate(rows):
            if name in props:
                out.append(copy.deepcopy(props[name]))
            elif default is _MISSING:
                raise KeyError(f"site {idx} has no property {name!r}")
            else:
                out.append(copy.deepcopy(default))
        return out

    def with_site_property(self, name: str, values: Sequence[Any]) -> "Structure":
        """Return a new structure with per-site property *name* set to *values*.

        *values* has one entry per atom (an ndarray is converted with
        ``tolist()``, so an (N, 3) array becomes N lists).  Other properties
        and the metadata are kept.

        Example:
            >>> afm = crystal.with_site_property("magmom", [2.0, -2.0])
        """
        if not isinstance(name, str):
            raise TypeError("site property name must be a string")
        if isinstance(values, np.ndarray):
            values = values.tolist()
        values = list(values)
        if len(values) != len(self._species):
            raise ValueError(
                f"{name!r} needs one value per atom ({len(self._species)}), got {len(values)}"
            )
        rows = self._site_properties or [{}] * len(self._species)
        return self.with_site_properties([{**p, name: v} for p, v in zip(rows, values)])

    def without_site_property(self, *names: str) -> "Structure":
        """Return a new structure with the given per-site properties removed."""
        rows = [{k: v for k, v in p.items() if k not in names} for p in self._site_properties]
        return self.with_site_properties(rows if any(rows) else None)

    @property
    def metadata(self) -> Mapping[str, Any]:
        """Structure-level metadata (read-only, deep-copied view).

        Use it for data attached to the structure as a whole, e.g. parsed
        forces of an MD frame.  It is preserved by ``copy()``, ``with_*()``,
        ``set_pbc()`` and serialization, and dropped by operations that change
        atoms or positions (add/remove/substitute/sort/wrap/transformations),
        because such data would no longer describe the new structure.
        """
        return MappingProxyType(copy.deepcopy(self._metadata))

    def with_metadata(self, **updates: Any) -> "Structure":
        """Return a new structure whose metadata is updated with *updates*."""
        return self._replace(metadata={**self._metadata, **updates})

    def without_metadata(self, *keys: str) -> "Structure":
        """Return a new structure without the given metadata keys (all if none given)."""
        kept = {k: v for k, v in self._metadata.items() if keys and k not in keys}
        return self._replace(metadata=kept)

    @property
    def lattice(self) -> Optional[Lattice]:
        """The (immutable) lattice, or ``None`` for non-periodic structures.

        Read-only: Cartesian positions, sites and neighbour caches are derived
        from it at construction time.  Build a new structure to change it.
        """
        return self._lattice

    # Attribute names renamed to private backing fields in 0.8.1.
    def __setstate__(self, state: Dict[str, Any]) -> None:
        """Restore from pickle/deepcopy and re-freeze arrays.

        ``pickle``/``copy.deepcopy`` recreate ndarrays as writeable owner arrays,
        which would let ``obj.positions.flags.writeable = True`` mutate the
        private state behind every derived cache.
        """
        self.__dict__.update(state)
        for value in self.__dict__.values():
            if isinstance(value, np.ndarray):
                value.flags.writeable = False

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
        reject_bool_coordinates(positions)
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
        view = self._coords.view()
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
        d.update(self._site_properties_dict())
        d.update(self._metadata_dict())
        return d

    def _metadata_dict(self) -> Dict[str, Any]:
        """``{"metadata": ...}`` encoded with MontyEncoder (ndarrays keep dtype and values)."""
        if not self._metadata:
            return {}
        return {"metadata": json.loads(json.dumps(self._metadata, cls=MontyEncoder))}

    @staticmethod
    def _metadata_from_dict(d: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        raw = d.get("metadata")
        return None if raw is None else MontyDecoder().process_decoded(raw)

    def _site_properties_dict(self) -> Dict[str, Any]:
        """``{"site_properties": ...}`` encoded with MontyEncoder (ndarrays survive JSON)."""
        if not self._site_properties:
            return {}
        return {"site_properties": json.loads(json.dumps(list(self._site_properties), cls=MontyEncoder))}

    @staticmethod
    def _site_properties_from_dict(d: Mapping[str, Any]) -> Optional[List[Dict[str, Any]]]:
        raw = d.get("site_properties")
        return None if raw is None else MontyDecoder().process_decoded(raw)

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
            Calculators are independent of structures:
            ``calc.get_potential_energy(new)`` works for the copy and reuses the
            cached result, since the copy has the same exact fingerprint.

        Example:
            >>> from matsimpy.core import Crystal, Lattice
            >>> crystal = Crystal(['Si', 'Si'], [[0,0,0], [0.25,0.25,0.25]], Lattice.cubic(5.43))
            >>> crystal_copy = crystal.copy()
            >>> crystal_copy is not crystal  # Different objects
            True
            >>> crystal_copy.species == crystal.species  # Same data
            True
        """
        # Bit-exact clone from internal state.  The <=0.8.0 implementation
        # round-tripped through as_dict(), which rounds the lattice to 1e-8 and
        # recomputes Cartesian coordinates, so ``copy()`` silently changed data.
        return self._replace()

    def _replace(self, **changes: Any) -> "Structure":
        """Exact clone (incl. metadata) with selected state fields replaced."""
        kwargs = {**self._clone_kwargs(), "metadata": self._metadata, **changes}
        return self.__class__._construct(
            species=self._species, positions=self._coords, lattice=self._lattice, **kwargs
        )

    def _clone_kwargs(self) -> Dict[str, Any]:
        """Kwargs for an exact ``_construct`` clone (subclasses may add caches)."""
        return self._construct_kwargs()

    def with_site_properties(self, site_properties: Optional[List[dict]]) -> "Structure":
        """Return a new structure with *site_properties* replaced (structures are immutable).

        Args:
            site_properties: One dict per atom, or ``None``/``[]`` to clear.
        """
        return self._replace(site_properties=site_properties)

    __hash__ = None

    # ------------------------------------------------------------------
    # Text representation (one implementation; subclasses supply two hooks)
    # ------------------------------------------------------------------

    def _summary_lines(self) -> List[str]:
        """Extra indented header lines for ``__str__``."""
        return []

    def _coordinate_columns(self) -> Dict[str, np.ndarray]:
        """``{header: (n, 3) array}`` coordinate columns for ``__str__``."""
        return {"Cartesian Coordinates": self.positions}

    def __str__(self) -> str:
        """Human-readable summary followed by a per-atom table (insertion order)."""
        from tabulate import tabulate

        columns = self._coordinate_columns()
        headers = ["Element", *columns]
        rows = [
            [sp, *("({:.4f}, {:.4f}, {:.4f})".format(*arr[i]) for arr in columns.values())]
            for i, sp in enumerate(self._species)
        ]
        if any(self._site_properties):
            headers.append("Properties")
            for row, props in zip(rows, self._site_properties):
                row.append(", ".join(f"{k}={v}" for k, v in props.items()))
        head = [f"{type(self).__name__}: {self.formula}", f"  Sites: {len(self)} atoms", *self._summary_lines()]
        return "\n".join(head) + "\n" + tabulate(rows, headers=headers, tablefmt="plain", stralign="left")

    def _structural_hash(self) -> int:
        """Exact fingerprint of every input a calculator may depend on.

        Used only for calculator-result staleness detection.  It is bit-exact
        (no rounding: a 1e-8 Å displacement must trigger a recalculation) and
        covers lattice, PBC and per-site properties (e.g. MAGMOM), which the
        <=0.8.0 implementation ignored.
        """
        h = hashlib.sha256()
        h.update(f"{self.__class__.__module__}.{self.__class__.__name__}".encode())
        h.update("\x1f".join(self.species).encode())
        h.update(np.ascontiguousarray(self._coords, dtype=np.float64).tobytes())
        if self.lattice is not None:
            h.update(np.ascontiguousarray(self.lattice.matrix, dtype=np.float64).tobytes())
        h.update(repr(getattr(self, "pbc", None)).encode())
        # Full-precision, unsummarised repr so ndarray-valued properties hash exactly.
        with np.printoptions(threshold=sys.maxsize, floatmode="unique"):
            h.update(repr(getattr(self, "_site_properties", ())).encode())
        return int.from_bytes(h.digest()[:8], byteorder="big", signed=True)

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
            Periodic boundary conditions are compared.  Site properties and
            metadata are *not* compared: equality is geometric (like pymatgen's
            ``Structure.__eq__``).  Compare ``site_properties``/``metadata``
            explicitly when they matter.

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

        # Check positions with absolute tolerance POSITION_TOL.  Structures are
        # unhashable (``__hash__ = None``), so no hash contract is involved.
        if not np.allclose(self.positions, other.positions, atol=POSITION_TOL, rtol=0):
            return False

        # Check lattice (if both have lattices)
        if self.lattice is not None and other.lattice is not None:
            # Compare lattice matrices using LATTICE_TOL, consistent with Lattice.__eq__
            if not np.allclose(
                self.lattice.matrix, other.lattice.matrix, atol=LATTICE_TOL, rtol=0
            ):
                return False
        elif self.lattice is not None or other.lattice is not None:
            # One has lattice, other doesn't
            return False

        # Periodicity is part of the physical system (a slab is not the bulk
        # crystal with the same cell); _structural_hash already includes it.
        if getattr(self, "pbc", None) != getattr(other, "pbc", None):
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
    # Calculators (structures never carry one)
    # ------------------------------------------------------------------

    _CALC_REMOVED = (
        "Structures no longer carry a calculator (removed in 0.8.6). Use "
        "calc.get_potential_energy(structure), calc.get_forces(structure), "
        "calc.get_stress(structure) or calc.compute(structure)."
    )

    @property
    def calc(self):
        # Without this, `structure.calc = calc` would silently create a plain
        # attribute (Structure has a __dict__) and old code would misbehave quietly.
        raise AttributeError(self._CALC_REMOVED)

    @calc.setter
    def calc(self, _value) -> None:
        raise AttributeError(self._CALC_REMOVED)

    # ------------------------------------------------------------------

    # ======================================================================
    # Per-atom data adjustment (used by remove_atom / sort_atoms)
    # ======================================================================

    def _take_per_atom(self, indices: List[int]) -> Dict[str, Any]:
        """Construct kwargs for the atoms *indices* (subset and/or reorder)."""
        if not self._site_properties:
            return {}
        # index the private tuple: the public property deep-copies every site
        return {"site_properties": [self._site_properties[i] for i in indices]}

    # ======================================================================
    # Structure editing (immutable: returns new instances)
    # ======================================================================

    # Minimum allowed interatomic distance for add_atom (Angstrom).
    _MIN_ADD_DISTANCE = 0.5
    _DUPLICATE_DISTANCE = 1e-6

    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]], np.ndarray],
        site_properties: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    ) -> "Structure":
        """Return a new structure with one or more atoms appended.

        Args:
            species: Element symbol or list of symbols.
            position: One 3D coordinate or a list of them, in the structure's
                native coordinates (Cartesian for Molecule, fractional for
                Crystal unless ``coords_are_cartesian=True``).
            site_properties: One dict (copied to every new atom) or one dict per atom.

        Raises:
            ValueError: count mismatch, malformed coordinates, or a new atom
                closer than 0.5 Angstrom to another atom (minimum image under PBC).
        """
        return self._add_atoms(species, position, site_properties, cartesian=self.lattice is None)

    def _add_atoms(self, species, position, site_properties, cartesian: bool) -> "Structure":
        species_list = [species] if isinstance(species, str) else list(species)
        reject_bool_coordinates(position)
        try:
            new = np.array(position, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Each position must be a 3D coordinate [x, y, z]: {exc}") from None
        if new.size == 0:
            new = new.reshape(0, 3)
        elif new.ndim == 1:
            new = new.reshape(1, -1)
        if new.ndim != 2 or new.shape[1] != 3:
            raise ValueError("Each position must be a 3D coordinate [x, y, z].")
        # before any distance or frac/cart arithmetic turns inf into NaN
        _require_finite_positions(new)
        if len(species_list) != len(new):
            raise ValueError(
                f"Number of species ({len(species_list)}) must match "
                f"number of positions ({len(new)})"
            )
        if site_properties is not None:
            if isinstance(site_properties, Mapping):
                # independent copy per atom (a list-multiply would share one dict)
                site_properties = [copy_properties(site_properties) for _ in species_list]
            site_properties = list(site_properties)
            if len(site_properties) != len(species_list):
                raise ValueError(
                    f"Number of site_properties ({len(site_properties)}) "
                    f"must match number of atoms added ({len(species_list)})"
                )
        if not species_list:
            return self.copy()

        native, cart = self._native_and_cart(new, cartesian)
        self._check_new_atom_distances(native, cart)

        props = None
        if self._site_properties or site_properties:
            if not self._site_properties:
                warnings.warn(
                    f"Adding atoms with site_properties to a {type(self).__name__} that has none. "
                    "All existing atoms will receive an empty ({}) property dict. "
                    "Initialise site_properties on the original structure first to "
                    "suppress this warning.",
                    UserWarning,
                    stacklevel=3,
                )
            old = list(self._site_properties) or [{} for _ in self._species]
            props = old + (site_properties or [{} for _ in species_list])

        kwargs = {**self._construct_kwargs(), "site_properties": props}
        kwargs.update(self._appended_cart(cart))
        return self.__class__._construct(
            species=self._species + tuple(species_list),
            positions=np.vstack([self._coords, native]),
            lattice=self.lattice,
            **kwargs,
        )

    def _native_and_cart(self, coords: np.ndarray, cartesian: bool):
        """(native, Cartesian) forms of new coordinates; Molecule: both Cartesian."""
        return coords, coords

    def _appended_cart(self, new_cart: np.ndarray) -> Dict[str, Any]:
        """Extra construct kwargs carrying exact Cartesian rows (Crystal only)."""
        return {}

    def _min_image_distances(self, a_cart: np.ndarray, b_cart: np.ndarray) -> np.ndarray:
        """Pairwise distances (len(a), len(b)); minimum image along periodic axes."""
        diff = a_cart[:, None, :] - b_cart[None, :, :]
        pbc = np.array(getattr(self, "pbc", (False, False, False)), dtype=bool)
        if self.lattice is not None and pbc.any():
            frac = diff @ self.lattice.inv_matrix
            frac[..., pbc] -= np.round(frac[..., pbc])
            # rounding alone is not the minimum image in skewed cells: try the
            # neighbouring images along the periodic axes as well
            steps = [(-1, 0, 1) if periodic else (0,) for periodic in pbc]
            shifts = np.array([[i, j, k] for i in steps[0] for j in steps[1] for k in steps[2]], dtype=float)
            images = (frac[..., None, :] + shifts) @ self.lattice.matrix
            return np.linalg.norm(images, axis=-1).min(axis=-1)
        return np.linalg.norm(diff, axis=-1)

    def _check_new_atom_distances(self, native: np.ndarray, cart: np.ndarray) -> None:
        among = self._min_image_distances(cart, cart)
        np.fill_diagonal(among, np.inf)
        if among.size and among.min() < self._MIN_ADD_DISTANCE:
            i, j = np.unravel_index(np.argmin(among), among.shape)
            i, j = min(i, j), max(i, j)
            d = among[i, j]
            if d < self._DUPLICATE_DISTANCE:
                raise ValueError(
                    f"Duplicate positions detected in new atoms: positions {i} and {j} "
                    f"are at the same location ({native[i].tolist()})."
                )
            raise ValueError(
                f"Atoms being added are too close: distance between positions {i} and {j} "
                f"is {d:.6f} Angstrom. Minimum allowed distance is {self._MIN_ADD_DISTANCE} Angstrom."
            )
        if not len(self._species):
            return
        nearest = self._min_image_distances(cart, self.positions).min(axis=1)
        for idx, d in enumerate(nearest):
            if d < self._DUPLICATE_DISTANCE:
                raise ValueError(
                    f"Cannot add atom at position {native[idx].tolist()}: atom already "
                    f"exists at this location (distance: {d:.6f} Angstrom)."
                )
            if d < self._MIN_ADD_DISTANCE:
                raise ValueError(
                    f"Cannot add atom at position {native[idx].tolist()}: too close to "
                    f"existing atom (distance: {d:.6f} Angstrom). "
                    f"Minimum allowed distance is {self._MIN_ADD_DISTANCE} Angstrom."
                )

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
            must override ``_take_per_atom``.
        """
        index = resolve_indices(self, index)
        n = len(self.species)
        indices_to_remove = sorted(set(self._validate_atom_indices(index)), reverse=True)

        removed = set(indices_to_remove)
        kept_indices = [i for i in range(n) if i not in removed]

        new_species = [self.species[i] for i in kept_indices]
        new_positions = self._coords[np.array(kept_indices, dtype=int)] if kept_indices else np.empty((0, 3), dtype=np.float64)

        # Propagate per-atom metadata via hooks when present.
        per_atom = self._take_per_atom(kept_indices)
        return self.__class__._construct(
            species=tuple(new_species),
            positions=new_positions,
            lattice=self.lattice,
            # per_atom overrides the stale per-atom lists in _construct_kwargs();
            # passing both as separate ** expansions raised "multiple values for
            # keyword argument 'site_properties'" in 0.8.0.
            **{**self._construct_kwargs(), **per_atom},
        )

    # ------------------------------------------------------------------
    # Species editing
    # ------------------------------------------------------------------

    def _site_index(self, item: Any) -> int:
        """Normalize a single ``structure[item]`` index (negative allowed, bools rejected)."""
        if isinstance(item, (bool, np.bool_)) or not isinstance(item, (int, np.integer)):
            raise TypeError(
                f"{type(self).__name__} indices must be integers or slices, got {type(item).__name__}"
            )
        n = len(self._species)
        idx = int(item)
        if not -n <= idx < n:
            raise IndexError(f"Atom index {idx} out of range for {n} atoms")
        return idx % n

    def _validate_atom_indices(
        self,
        indices: Union[int, np.integer, List[int], Tuple[int, ...]],
    ) -> List[int]:
        """Normalize atom indices and reject negative or out-of-range values."""
        if isinstance(indices, (bool, np.bool_)):
            raise TypeError("Atom index must be an integer, got bool")
        if isinstance(indices, (int, np.integer)):
            normalized = [int(indices)]
        else:
            if isinstance(indices, (str, bytes)) or np.ndim(indices) != 1:
                raise TypeError(
                    f"Atom indices must be an integer or a 1-D sequence of integers, got {indices!r}"
                )
            normalized = [
                int(idx)
                if isinstance(idx, np.integer) and not isinstance(idx, np.bool_)
                else idx
                for idx in list(indices)
            ]

        n_atoms = len(self.species)
        for idx in normalized:
            if isinstance(idx, bool) or not isinstance(idx, int):
                raise TypeError(
                    f"Atom index must be an integer, got {type(idx).__name__}"
                )
            if idx < 0 or idx >= n_atoms:
                raise IndexError(f"Atom index {idx} out of range [0, {n_atoms - 1}]")
        return normalized

    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> "Structure":
        """
        Substitute atoms with new species and return a new structure.

        Args:
            indices: Atom index, list of indices, or AtomSelection to substitute.
            new_species: New species symbol, list of symbols, or dict mapping
                old->new species.

        Returns:
            Structure: New structure of the same type; positions (fractional and
            Cartesian for Crystal), lattice, PBC and site properties are carried
            over bit-exactly.

        Raises:
            IndexError: If an index is out of range.
            ValueError: If the number of indices and species differ.
            KeyError: If a dict mapping lacks a species.

        Examples:
            >>> new = crystal.substitute(0, 'Ge')
            >>> new = crystal.substitute([0, 1], ['Ge', 'Ge'])
            >>> new = crystal.substitute(AtomSelection(crystal).by_species('Si'), 'Ge')
            >>> new = crystal.substitute([0, 1, 2], {'Si': 'Ge', 'O': 'S'})
        """
        # (0.8.4 and earlier: Crystal carried a near-identical copy of this method.)
        indices = resolve_indices(self, indices)

        indices = self._validate_atom_indices(indices)

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

        return self.__class__._construct(
            species=tuple(species_list),
            positions=self._coords,
            lattice=self.lattice,
            **self._clone_kwargs(),
        )

    def substitute_all(self, old_species: str, new_species: str) -> "Structure":
        species_list = [
            new_species if s == old_species else s for s in self.species
        ]
        return self.__class__._construct(
            species=tuple(species_list),
            positions=self._coords,
            lattice=self.lattice,
            **self._clone_kwargs(),
        )

    # ------------------------------------------------------------------
    # Reordering
    # ------------------------------------------------------------------

    def sort_atoms(self, sort_by: str = "element") -> "Structure":
        """
        Sort atoms and return a new structure.

        Warning:
            Subclasses that store per-atom lists (e.g. ``site_properties``)
            must override ``_take_per_atom``.
        """
        atoms = list(zip(range(len(self.species)), self.species, self._coords))

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

        per_atom = self._take_per_atom(sorted_indices)
        return self.__class__._construct(
            species=tuple(sorted_species),
            positions=sorted_positions,
            lattice=self.lattice,
            # per_atom overrides the stale per-atom lists in _construct_kwargs();
            # passing both as separate ** expansions raised "multiple values for
            # keyword argument 'site_properties'" in 0.8.0.
            **{**self._construct_kwargs(), **per_atom},
        )

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
