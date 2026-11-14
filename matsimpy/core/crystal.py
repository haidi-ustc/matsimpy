"""
Crystal module for MatSimPy.

This module provides the Crystal class for representing periodic crystal structures
with lattice information and periodic boundary conditions. Crystals are atomic
structures with periodic repetition in one, two, or three dimensions.

The Crystal class extends Structure and provides:
- Periodic structure representation with lattice
- Fractional and Cartesian coordinate systems
- Periodic boundary conditions (PBC) support
- Neighbor finding with PBC
- Volume, area, and length calculations
- Density calculations
- Site-based access to atoms
- File I/O support (POSCAR, CIF, JSON, etc.)
- Converter support (pymatgen, ASE)
- DFT code interface
- Calculator integration

Example:
    >>> from matsimpy.core.crystal import Crystal
    >>> from matsimpy.core import Lattice
    >>>
    >>> # Create a crystal structure
    >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
    >>> crystal.formula  # 'NaCl'
    >>> crystal.volume  # 179.4 A^3
    >>>
    >>> # Access fractional and Cartesian coordinates
    >>> crystal.frac_positions  # Fractional coordinates
    >>> crystal.cart_positions  # Cartesian coordinates
    >>>
    >>> # Set periodic boundary conditions
    >>> crystal = crystal.set_pbc([True, True, False])  # 2D slab
    >>>
    >>> # Neighbor finding with PBC
    >>> neighbors = crystal.get_neighbor_list(5.0, use_pbc=True)
"""

import numpy as np
import warnings
from typing import List, Mapping, Optional, Sequence, Union, Dict, Tuple, Any, NamedTuple
from scipy.spatial import cKDTree
from .structure import Structure
from .lattice import Lattice
from .periodic_table import Element
from matsimpy.constants import AMU_TO_GRAM
from .site import CrystalSite
from ._validation import (
    validate_lattice,
    validate_pbc,
)


_MAX_PERIODIC_IMAGE_CACHE_ATOMS = 1_000_000


class _NeighborCache(NamedTuple):
    """Bundled KD-tree cache stored as a single atomic attribute on Crystal."""
    tree: cKDTree
    cutoff: float
    positions: np.ndarray
    use_pbc: bool
    pbc: Tuple[bool, bool, bool]


class Crystal(Structure):
    """
    A class representing a periodic crystal structure.

    Crystal extends :class:`~matsimpy.core.structure.Structure` to represent
    atomic structures with periodic boundary conditions and lattice information.
    Crystals are used for bulk materials, surfaces, wires, and other periodic systems.

    The Crystal class provides:
    - Periodic structure representation with lattice
    - Dual coordinate systems (fractional and Cartesian)
    - Periodic boundary conditions (PBC) support (3D, 2D, 1D, 0D)
    - Neighbor finding with PBC
    - Volume, area, and length calculations
    - Density calculations
    - Site-based access to atoms
    - Converter support (pymatgen, ASE)
    - DFT code interface
    - Calculator integration

    Attributes:
        species (Tuple[str]): Immutable tuple of atomic species symbols.
        positions (np.ndarray): Cartesian coordinates in Angstroms (ASE-style).
        frac_positions (np.ndarray): Fractional coordinates with shape (n_atoms, 3).
        cart_positions (np.ndarray): Cartesian coordinates in Angstroms with shape (n_atoms, 3).
        lattice (Lattice): Lattice object defining the unit cell.
        sites (List[CrystalSite]): List of CrystalSite objects for each atom.
        site_properties (List[Dict[str, Any]]): List of site property dictionaries.
        pbc (List[bool]): Periodic boundary conditions [a, b, c] (default: [True, True, True]).
        formula (str): Chemical formula of the crystal (cached property).
        composition (Composition): Composition object (cached property).
        volume (float): Unit cell volume in cubic Angstroms (property).
        area (float): Unit cell area in square Angstroms for 2D systems (property).
        length (float): Unit cell length in Angstroms for 1D systems (property).

    Args:
        species: List of atomic species. Can be:
            - List[str]: Element symbols (e.g., ['Na', 'Cl', 'Na'])
            - List[int]: Atomic numbers (e.g., [11, 17, 11])
            - List[Element]: Element objects
        positions: List of atomic positions. Format depends on coords_are_cartesian:
            - If coords_are_cartesian=False (default): Fractional coordinates [0-1]
            - If coords_are_cartesian=True: Cartesian coordinates in Angstroms
        lattice: Lattice object defining the unit cell (required).
        pbc: Periodic boundary conditions as list of 3 booleans [a, b, c].
            Default is [True, True, True] for 3D periodic system.
            - [True, True, True]: 3D bulk material
            - [True, True, False]: 2D slab/surface
            - [True, False, False]: 1D wire
            - [False, False, False]: 0D cluster (non-periodic)
        coords_are_cartesian: If True, positions are Cartesian; if False, fractional (default).
        site_properties: Optional list of site property dictionaries.
                       Each dict can contain properties like 'charge', 'magmom', etc.

    Raises:
        ValueError: If species and positions have different lengths.
        ValueError: If positions are not 3D coordinates or contain invalid values.
        ValueError: If lattice is None (required for crystals).

    Note:
        Crystals always have a lattice (unlike molecules). Positions can be specified
        in either fractional or Cartesian coordinates, and both are maintained internally.
        The default coordinate system is fractional.

    Examples:
        >>> from matsimpy.core.crystal import Crystal
        >>> from matsimpy.core import Lattice
        >>>
        >>> # Create a crystal with fractional coordinates (default)
        >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
        >>> crystal.formula
        'NaCl'
        >>> crystal.volume
        179.406...
        >>>
        >>> # Create with Cartesian coordinates
        >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [2.82, 2.82, 2.82]],
        ...                   Lattice.cubic(5.64), coords_are_cartesian=True)
        >>>
        >>> # Access both coordinate systems
        >>> crystal.frac_positions  # Fractional coordinates
        >>> crystal.cart_positions  # Cartesian coordinates
        >>>
        >>> # Set periodic boundary conditions
        >>> crystal = crystal.set_pbc([True, True, False])  # 2D slab
        >>> crystal.area  # Area for 2D system
        >>>
        >>> # With site properties
        >>> crystal = Crystal(['Fe', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(4.0),
        ...                   site_properties=[{'magmom': 2.5}, {'magmom': 0.0}])
        >>> crystal.sites[0].properties['magmom']
        2.5
    """

    # ======================================================================
    # Construction & internal state
    # ======================================================================

    def _set_state(
        self,
        species: Sequence[Any],
        positions: Any,
        lattice: Lattice,
        pbc: Tuple[bool, bool, bool] = (True, True, True),
        site_properties: Optional[List[dict]] = None,
        _cart_positions: Optional[np.ndarray] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Assign state; ``positions`` are fractional.

        ``_cart_positions`` (optional) is an exact Cartesian array to keep instead
        of recomputing ``frac @ matrix`` (e.g. user-supplied Cartesian input).
        """
        lattice = validate_lattice(lattice)
        super()._set_state(species, positions, lattice, site_properties=site_properties, metadata=metadata)
        if _cart_positions is not None:
            cart = np.array(_cart_positions, dtype=np.float64, copy=True)
            if cart.shape != self._coords.shape:
                raise ValueError("Cartesian and fractional positions differ in shape")
        else:
            cart = np.dot(self._coords, lattice.matrix)
        cart.flags.writeable = False
        self._cart = cart
        self._pbc = validate_pbc(pbc)
        # Bundled KD-tree cache — replaced as one atomic write.
        self._neighbor_cache: Optional[_NeighborCache] = None

    def _construct_kwargs(self) -> Dict[str, Any]:
        return {**super()._construct_kwargs(), "pbc": self.pbc}

    def _clone_kwargs(self) -> Dict[str, Any]:
        # Carry the exact Cartesian array: for coords_are_cartesian=True input it
        # is the user's data, and recomputing frac @ matrix differs in the last ulp.
        return {**self._construct_kwargs(), "_cart_positions": self._cart}

    def _take_per_atom(self, indices: List[int]) -> Dict[str, Any]:
        # Keep the exact Cartesian rows (remove_atom / sort_atoms used to recompute them).
        return {**super()._take_per_atom(indices), "_cart_positions": self._cart[np.asarray(indices, dtype=int)]}

    @property
    def pbc(self) -> Tuple[bool, bool, bool]:
        """Periodic boundary flags (read-only; use :meth:`set_pbc` for a new Crystal)."""
        return self._pbc

    def __init__(
        self,
        species: Union[List[str], List[int], List[Element]],
        positions: List[List[float]],
        lattice: Lattice,
        pbc: Optional[List[bool]] = None,
        coords_are_cartesian: bool = False,
        site_properties: Optional[List[dict]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """
        Initialize a Crystal object.

        Args:
            species: List of atomic species. Can be:
                - List[str]: Element symbols (e.g., ['Na', 'Cl', 'Na'])
                - List[int]: Atomic numbers (e.g., [11, 17, 11])
                - List[Element]: Element objects
            positions: List of atomic positions. Format depends on coords_are_cartesian:
                - If coords_are_cartesian=False (default): Fractional coordinates [0-1]
                - If coords_are_cartesian=True: Cartesian coordinates in Angstroms
            lattice: Lattice object defining the unit cell (required).
            pbc: Periodic boundary conditions as list of 3 booleans [a, b, c].
                Default is [True, True, True] for 3D periodic system.
            coords_are_cartesian: If True, positions are Cartesian; if False, fractional (default).
            site_properties: Optional list of site property dictionaries.
            metadata: Optional structure-level metadata mapping (see :attr:`metadata`).

        Raises:
            ValueError: If species and positions have different lengths.
            ValueError: If positions are not 3D coordinates or contain invalid values.
            ValueError: If lattice is None (required for crystals).

        Note:
            Both fractional and Cartesian coordinates are maintained internally.
            The default coordinate system is fractional.
        """
        lattice = validate_lattice(lattice)
        species_list = self._normalize_species_input(species)
        if len(species_list) != len(positions):
            raise ValueError(
                f"Number of species ({len(species_list)}) must match "
                f"number of positions ({len(positions)})"
            )
        if coords_are_cartesian:
            cart = self._validate_positions(positions)
            frac = np.dot(cart, lattice.inv_matrix)
        else:
            frac, cart = self._validate_positions(positions), None
        self._set_state(
            species_list,
            frac,
            lattice,
            pbc=pbc,
            site_properties=site_properties,
            _cart_positions=cart,
            metadata=metadata,
        )

    # ======================================================================
    # Coordinate accessors
    # ======================================================================

    @property
    def positions(self) -> np.ndarray:
        """
        Cartesian coordinates in Ångströms as a read-only numpy array of shape (n_atoms, 3).

        Consistent with the ``Structure.positions`` contract (always Cartesian) and
        with the ASE convention.  Use ``frac_positions`` to access fractional
        coordinates explicitly.
        """
        return self.cart_positions

    @property
    def frac_positions(self) -> np.ndarray:
        """
        Fractional coordinates as a read-only numpy array of shape (n_atoms, 3).

        The returned array is a read-only view; mutating it raises ValueError.
        Use the immutable modification methods (add_atom, remove_atom, etc.) to
        produce a new Crystal with updated positions.
        """
        view = self._coords.view()
        view.flags.writeable = False
        return view

    @property
    def cart_positions(self) -> np.ndarray:
        """
        Cartesian coordinates in Ångströms as a read-only numpy array of shape (n_atoms, 3).

        The returned array is a read-only view; mutating it raises ValueError.
        Use the immutable modification methods (add_atom, remove_atom, etc.) to
        produce a new Crystal with updated positions.
        """
        view = self._cart.view()
        view.flags.writeable = False
        return view

    def set_pbc(self, pbc: Union[List[bool], Tuple[bool, bool, bool]]) -> "Crystal":
        """
        Set periodic boundary conditions for the crystal.

        Args:
            pbc: List or tuple of 3 booleans indicating periodicity along a, b, c axes.
                 [True, True, True] for 3D, [True, True, False] for 2D, etc.

        Returns:
            Crystal: New Crystal with updated periodic boundary conditions.

        Raises:
            ValueError: If pbc is not a list/tuple of 3 booleans.

        Examples:
            >>> crystal = crystal.set_pbc([True, True, True])  # 3D material
            >>> crystal = crystal.set_pbc([True, True, False])  # 2D material (slab)
            >>> crystal = crystal.set_pbc([True, False, False])  # 1D material (wire)
            >>> crystal = crystal.set_pbc([False, False, False])  # 0D (cluster)
        """
        return self._replace(pbc=validate_pbc(pbc))

    # ======================================================================
    # Structure editing (immutable: returns new instances)
    # ======================================================================

    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]], np.ndarray],
        site_properties: Optional[Union[dict, List[dict]]] = None,
        coords_are_cartesian: bool = False,
    ) -> "Crystal":
        """Return a new Crystal with atoms appended (see :meth:`Structure.add_atom`).

        *position* is fractional unless ``coords_are_cartesian=True``.  Distance
        checks use the minimum-image convention along periodic axes.

        Example:
            >>> Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5.0)).add_atom('H', [0.5, 0.5, 0.5])
        """
        return self._add_atoms(species, position, site_properties, cartesian=coords_are_cartesian)

    def _native_and_cart(self, coords: np.ndarray, cartesian: bool):
        if cartesian:
            return coords @ self._lattice.inv_matrix, coords
        return coords, coords @ self._lattice.matrix

    def _appended_cart(self, new_cart: np.ndarray) -> Dict[str, Any]:
        return {"_cart_positions": np.vstack([self._cart, new_cart])}

    def _initialize_sites(self) -> List[CrystalSite]:
        """Build a fresh CrystalSite snapshot for every atom."""
        return [self._site_snapshot(i) for i in range(len(self._species))]

    def _site_snapshot(self, index: int) -> CrystalSite:
        """Return a detached CrystalSite snapshot for one atom (O(1)).

        Built directly from the immutable backing arrays.  0.8.0 kept a second,
        cached copy of every site (``_sites``) which went stale when
        ``site_properties`` was reassigned; there is no such cache any more.
        """
        props = self._site_properties[index] if self._site_properties else None
        # rows of the frozen backing arrays; cart is the crystal's exact Cartesian row
        return CrystalSite._snapshot(self._species[index], self._coords[index], self._cart[index], self._lattice, props)

    @property
    def sites(self) -> Tuple[CrystalSite, ...]:
        """
        Get the list of CrystalSite objects for all atoms.

        Returns:
            Tuple[CrystalSite, ...]: Fresh CrystalSite snapshots, one for each atom in the crystal.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
            >>> crystal.sites[0].specie  # 'Na'
            >>> crystal.sites[0].frac_position  # [0, 0, 0]
            >>> len(crystal.sites)
            2
        """
        return tuple(self._initialize_sites())

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert crystal to dictionary representation for serialization.

        Implements the MSONable interface for JSON serialization.
        The dictionary includes module and class information for proper
        deserialization.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - @module: Module path of the class
                - @class: Class name ('Crystal')
                - pbc: Periodic boundary conditions list
                - lattice: Lattice dictionary
                - species: List of species symbols
                - positions: List of positions (fractional, converted from numpy array)
                - site_properties: List of site property dictionaries (if any)

        Example:
            >>> d = crystal.as_dict()
            >>> d['@class']
            'Crystal'
            >>> d['pbc']
            [True, True, True]
            >>> d['species']
            ['Na', 'Cl']
        """
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "pbc": list(self.pbc),
            "lattice": self.lattice.as_dict(),
            "species": list(self.species),
            "positions": self.frac_positions.tolist(),
        }
        # Crystal keeps fractional and Cartesian arrays.  When the Cartesian one is
        # not bit-identical to frac @ matrix (e.g. coords_are_cartesian=True input),
        # store it too so from_dict() restores both exactly.  Older readers ignore
        # the extra key and fall back to the 0.8.3 behaviour.
        if not np.array_equal(self._cart, np.dot(self._coords, self.lattice.matrix)):
            d["cart_positions"] = self._cart.tolist()
        d.update(self._site_properties_dict())
        d.update(self._metadata_dict())
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Crystal":
        """
        Create Crystal object from dictionary representation.

        Implements the MSONable interface for JSON deserialization.
        Restores a Crystal object from its dictionary representation.

        Args:
            d: Dictionary containing:
                - species: List of species symbols
                - positions: List of positions
                - lattice: Lattice dictionary
                - pbc: Optional periodic boundary conditions list
                - site_properties: Optional list of site property dictionaries
                - coords_are_cartesian: Optional boolean (default: False)

        Returns:
            Crystal: A new Crystal instance.

        Raises:
            KeyError: If required keys ('species', 'positions', 'lattice') are missing.
            ValueError: If species and positions have different lengths.

        Example:
            >>> d = {
            ...     '@module': 'matsimpy.core.crystal',
            ...     '@class': 'Crystal',
            ...     'species': ['Na', 'Cl'],
            ...     'positions': [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            ...     'lattice': {...},
            ...     'pbc': [True, True, True]
            ... }
            >>> crystal = Crystal.from_dict(d)
            >>> crystal.formula
            'NaCl'
        """
        species = d["species"]
        positions = d["positions"]
        lattice_data = d["lattice"]
        if lattice_data is None:
            lattice = None
        else:
            lattice = (
                lattice_data
                if isinstance(lattice_data, Lattice)
                else Lattice.from_dict(lattice_data)
            )
        lattice = validate_lattice(lattice)
        site_properties = cls._site_properties_from_dict(d)
        coords_are_cartesian = d.get("coords_are_cartesian", False)
        pbc = validate_pbc(d.get("pbc"))
        crystal = cls(
            species=species,
            positions=positions,
            lattice=lattice,
            pbc=pbc,
            coords_are_cartesian=coords_are_cartesian,
            site_properties=site_properties,
            metadata=cls._metadata_from_dict(d),
        )
        cart = d.get("cart_positions")
        if cart is None or coords_are_cartesian:
            return crystal
        cart = np.array(cart, dtype=np.float64)
        if not np.all(np.isfinite(cart)):
            raise ValueError("cart_positions must be finite")
        if cart.shape != crystal._cart.shape:
            raise ValueError(
                f"cart_positions has shape {cart.shape}, expected {crystal._cart.shape}"
            )
        # cart_positions only carries the last bits lost in the frac -> cart round
        # trip; a real disagreement means the dict was edited inconsistently.
        if not np.allclose(cart, crystal._cart, rtol=0.0, atol=1e-8):
            raise ValueError(
                "cart_positions is inconsistent with the fractional positions and "
                "lattice (max deviation "
                f"{np.max(np.abs(cart - crystal._cart)):.3g} Å)"
            )
        return crystal._replace(_cart_positions=cart)

    @property
    def volume(self) -> float:
        """
        Calculate the volume of the unit cell.

        Returns:
            float: Unit cell volume in cubic Angstroms (A^3).

        Note:
            This property is only meaningful for 3D periodic systems
            (PBC = [True, True, True]). For 2D systems, use :attr:`area`.
            For 1D systems, use :attr:`length`.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
            >>> crystal.volume
            179.406...
        """
        a, b, c = self.lattice.matrix
        volume = np.dot(a, np.cross(b, c))
        return abs(volume)

    @property
    def area(self) -> float:
        """
        Calculate the area for 2D materials (when exactly one PBC is False).

        Returns:
            float: Unit cell area in square Angstroms (A^2).

        Raises:
            ValueError: If the crystal is not a 2D material (exactly 2 PBC True).

        Note:
            This property is only defined for 2D periodic systems
            (e.g., PBC = [True, True, False] for a slab).

        Example:
            >>> crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
            >>> crystal = crystal.set_pbc([True, True, False])  # 2D slab
            >>> crystal.area
            100.0
        """
        a, b, c = self.lattice.matrix
        pbc_count = sum(self.pbc)
        if pbc_count != 2:
            raise ValueError(
                "Area is only defined for 2D materials (exactly 2 PBC True)"
            )

        # Find which dimension is non-periodic
        non_periodic_idx = [i for i, p in enumerate(self.pbc) if not p][0]

        if non_periodic_idx == 0:
            # a is non-periodic, use b and c
            area = np.linalg.norm(np.cross(b, c))
        elif non_periodic_idx == 1:
            # b is non-periodic, use a and c
            area = np.linalg.norm(np.cross(a, c))
        else:  # non_periodic_idx == 2
            # c is non-periodic, use a and b
            area = np.linalg.norm(np.cross(a, b))

        return abs(area)

    @property
    def length(self) -> float:
        """
        Calculate the length for 1D materials (when exactly two PBC are False).

        Returns:
            float: Unit cell length in Angstroms (A).

        Raises:
            ValueError: If the crystal is not a 1D material (exactly 1 PBC True).

        Note:
            This property is only defined for 1D periodic systems
            (e.g., PBC = [True, False, False] for a wire).

        Example:
            >>> crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
            >>> crystal = crystal.set_pbc([True, False, False])  # 1D wire
            >>> crystal.length
            10.0
        """
        a, b, c = self.lattice.matrix
        pbc_count = sum(self.pbc)
        if pbc_count != 1:
            raise ValueError(
                "Length is only defined for 1D materials (exactly 1 PBC True)"
            )

        # Find which dimension is periodic
        periodic_idx = [i for i, p in enumerate(self.pbc) if p][0]

        if periodic_idx == 0:
            length = np.linalg.norm(a)
        elif periodic_idx == 1:
            length = np.linalg.norm(b)
        else:  # periodic_idx == 2
            length = np.linalg.norm(c)

        return abs(length)

    def _summary_lines(self) -> List[str]:
        lines = [
            "  PBC: [" + " ".join("T" if p else "F" for p in self.pbc) + "]",
            f"  Lattice: {self.lattice._format_lattice_params(include_units=True)}",
        ]
        dim = sum(self.pbc)
        try:
            if dim == 2:
                lines += [f"  Area: {self.area:.4f} Å²", f"  Density: {self.density:.6e} g/cm²"]
            elif dim == 1:
                lines += [f"  Length: {self.length:.4f} Å", f"  Density: {self.density:.6e} g/cm"]
            else:  # 3D, and 0D still reports the cell volume
                rho = self.density
                fmt = ".6e" if rho < 0.01 or rho > 1000 else ".4f"
                lines += [f"  Volume: {self.volume:.4f} Å³", f"  Density: {rho:{fmt}} g/cm³"]
        except (ValueError, AttributeError):
            pass
        return lines

    def _coordinate_columns(self) -> Dict[str, np.ndarray]:
        return {"Fractional Coordinates": self._coords, "Cartesian Coordinates": self._cart}

    def __repr__(self):
        """Unambiguous string representation of Crystal for debugging."""
        # Compact representation with key info
        # Use shorter lattice format: axbxc, alpha/beta/gamma
        lattice_str = (
            f"{self.lattice.a:.4f}x{self.lattice.b:.4f}x{self.lattice.c:.4f}, "
            f"{self.lattice.alpha:.1f}°/{self.lattice.beta:.1f}°/{self.lattice.gamma:.1f}°"
        )
        # Compact PBC format: [T,T,T] or [T,F,T]
        pbc_str = "[" + ",".join("T" if p else "F" for p in self.pbc) + "]"
        return (
            f"{self.__class__.__name__}(formula='{self.formula}', "
            f"nsites={len(self)}, lattice={lattice_str}, pbc={pbc_str})"
        )

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self.sites[item]
        return self._site_snapshot(self._site_index(item))

    def _convert_to_cartesian(self) -> np.ndarray:
        """
        Convert fractional coordinates to Cartesian coordinates.

        Uses the lattice matrix to transform fractional coordinates to Cartesian
        coordinates in Angstroms.

        Returns:
            np.ndarray: Cartesian positions array of shape (n_atoms, 3) in Angstroms.

        Note:
            This is an internal method used for coordinate conversion.
        """
        return np.dot(self.frac_positions, self.lattice.matrix)

    def _convert_to_fractional(self) -> np.ndarray:
        """
        Convert Cartesian coordinates to fractional coordinates.

        Uses the cached inverse lattice matrix to transform Cartesian coordinates
        to fractional coordinates (0-1 range).

        Returns:
            np.ndarray: Fractional positions array of shape (n_atoms, 3).

        Note:
            This is an internal method used for coordinate conversion.
            Uses the cached inverse matrix for performance.
        """
        # Use cached inverse matrix
        return np.dot(self.cart_positions, self.lattice.inv_matrix)

    def wrap(self) -> "Crystal":
        """
        Wrap all fractional coordinates to the unit cell [0, 1) range.

        Wraps fractional coordinates into [0, 1) along the periodic axes; along
        non-periodic axes (e.g. the vacuum direction of a slab) they are kept.

        Returns:
            Crystal: New Crystal with wrapped coordinates.

        Example:
            >>> from matsimpy.core import Crystal, Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> crystal = Crystal(['Fe', 'O'], [[1.5, -0.3, 0.5], [0.2, 0.2, 0.2]], lattice)
            >>> wrapped = crystal.wrap()
            >>> wrapped.frac_positions[0].tolist()
            [0.5, 0.7, 0.5]
            >>>
            >>> # Method chaining
            >>> wrapped = Crystal(['Fe'], [[2.1, 0.5, 0.5]], lattice).wrap()
            >>> wrapped.frac_positions[0].tolist()
            [0.1, 0.5, 0.5]
        """
        new_frac = np.array(self.frac_positions, dtype=np.float64)
        periodic = np.array(self.pbc, dtype=bool)
        new_frac[:, periodic] = np.mod(new_frac[:, periodic], 1.0)
        return self.__class__._construct(
            species=tuple(self.species),
            positions=new_frac,
            lattice=self.lattice,
            **self._construct_kwargs(),
        )

    def _get_periodic_images(self, cutoff: float) -> np.ndarray:
        """
        Get all periodic images within cutoff using vectorized operations.

        Args:
            cutoff: Cutoff radius for neighbor finding

        Returns:
            np.ndarray: All positions including periodic images

        Note:
            For large structures with large cutoffs, this can create very large
            arrays. Consider using a smaller cutoff or disabling PBC if memory
            is a concern.
        """
        pbc_mask = np.array(self.pbc, dtype=bool)
        if not np.any(pbc_mask):
            return self.cart_positions.copy()
        base = self._wrapped_cart_positions()

        image_ranges = self._get_periodic_image_ranges(cutoff)

        n_atoms = len(self.cart_positions)
        n_total_images = int(np.prod([len(r) for r in image_ranges])) - 1

        # Check for excessive memory usage
        estimated_atoms = n_atoms * n_total_images
        if estimated_atoms > _MAX_PERIODIC_IMAGE_CACHE_ATOMS:
            warnings.warn(
                f"Large periodic image cache: {estimated_atoms:,} atoms. "
                f"This may use significant memory. Consider using a smaller cutoff "
                f"or disabling PBC if memory is limited.",
                UserWarning,
            )

        # Generate all translation vectors at once using meshgrid
        i_range, j_range, k_range = image_ranges
        i_grid, j_grid, k_grid = np.meshgrid(i_range, j_range, k_range, indexing="ij")

        # Flatten and remove (0,0,0)
        i_flat = i_grid.flatten()
        j_flat = j_grid.flatten()
        k_flat = k_grid.flatten()
        mask = ~((i_flat == 0) & (j_flat == 0) & (k_flat == 0))
        i_flat = i_flat[mask]
        j_flat = j_flat[mask]
        k_flat = k_flat[mask]

        # Calculate all shifts at once using vectorized operations
        # Shape: (n_images, 3)
        shifts = (
            i_flat[:, np.newaxis] * self.lattice.matrix[0]
            + j_flat[:, np.newaxis] * self.lattice.matrix[1]
            + k_flat[:, np.newaxis] * self.lattice.matrix[2]
        )

        # Add shifts to all positions using broadcasting
        # self.cart_positions: (n_atoms, 3)
        # shifts: (n_images, 3)
        # Result: (n_images, n_atoms, 3) -> reshape to (n_images * n_atoms, 3)
        image_positions = (
            base[np.newaxis, :, :] + shifts[:, np.newaxis, :]
        ).reshape(-1, 3)

        # Stack original positions with image positions
        return np.vstack([base, image_positions])

    def _wrapped_cart_positions(self) -> np.ndarray:
        """Cartesian positions with fractional coordinates wrapped into [0, 1) on periodic axes.

        The periodic images used for neighbour searches are built around these, so
        atoms stored far outside the cell still find their neighbours.
        """
        frac = np.array(self.frac_positions, dtype=np.float64)
        periodic = np.array(self.pbc, dtype=bool)
        frac[:, periodic] = np.mod(frac[:, periodic], 1.0)
        return frac @ self.lattice.matrix

    def _get_periodic_image_ranges(
        self, cutoff: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return image index ranges using reciprocal lattice heights."""
        ranges = []
        inv_matrix = self.lattice.inv_matrix
        for axis, periodic in enumerate(self.pbc):
            if not periodic:
                ranges.append(np.array([0], dtype=int))
                continue

            plane_spacing = 1.0 / np.linalg.norm(inv_matrix[:, axis])
            n_images = int(np.ceil(cutoff / plane_spacing)) + 1
            ranges.append(np.arange(-n_images, n_images + 1, dtype=int))
        return tuple(ranges)

    # ======================================================================
    # Neighbor finding & geometry
    # ======================================================================

    def get_neighbor_list(
        self, cutoff: float, atom_index: Optional[int] = None, use_pbc: bool = True
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Get neighbor list with optimized KDTree and consistent interface.

        Uses a cached KDTree for efficient neighbor finding. The tree is
        automatically rebuilt when the structure changes or when a different
        cutoff is used.

        Args:
            cutoff: Cutoff radius in Angstroms for neighbor finding.
            atom_index: Optional atom index. If None, returns neighbors for all atoms.
                       If specified, returns neighbors only for that atom.
            use_pbc: Whether to use periodic boundary conditions (default: True).
                    If True, considers neighbors across unit cell boundaries.

        Returns:
            Dict[int, List[Tuple[int, float]]]: Dictionary mapping atom index to
            list of (neighbor_index, distance) tuples, sorted by neighbour index.
            Each neighbouring atom appears once, at the distance of its nearest
            periodic image (so this is a bonding graph, not a coordination count:
            an atom whose periodic images are within the cutoff lists itself once,
            and several images of the same atom count once). Atoms at exactly
            ``cutoff`` are included. Distances are in Angstroms.
            - If atom_index is provided: dict contains only that entry {atom_index: [(neighbor, dist), ...]}
            - If atom_index is None: dict contains entries for all atoms

        Raises:
            IndexError: If atom_index is out of range.

        Note:
            The KDTree is cached and automatically invalidated when the structure
            changes. For large structures with PBC, periodic images are generated
            and cached for efficient neighbor finding.

        Example:
            >>> crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], lattice)
            >>> # Get neighbors for all atoms
            >>> neighbors = crystal.get_neighbor_list(5.0)
            >>> neighbors[0]  # Neighbors of atom 0
            [(1, 2.35), ...]
            >>>
            >>> # Get neighbors for specific atom
            >>> neighbors = crystal.get_neighbor_list(5.0, atom_index=0)
            >>> neighbors
            {0: [(1, 2.35), ...]}
            >>>
            >>> # Without PBC
            >>> neighbors = crystal.get_neighbor_list(5.0, use_pbc=False)
        """
        # Check if we need to rebuild tree
        from ._validation import validate_cutoff
        validate_cutoff(cutoff)
        n_atoms = len(self.cart_positions)
        cache = self._neighbor_cache
        rebuild_tree = (
            cache is None
            or cache.cutoff != cutoff
            or cache.use_pbc != use_pbc
            or cache.pbc != tuple(self.pbc)
            or (use_pbc and cache.positions is None)
            or (
                cache.positions is not None
                # NOTE: this only catches the case where MORE atoms are present than
                # in the cached tree (atom count grew).  It does NOT detect position
                # changes or atom removals.  Because Crystal is immutable every
                # mutation returns a new object whose _neighbor_cache starts as None,
                # so stale-tree reads on a live Crystal are not possible in practice.
                and len(cache.positions) < n_atoms
            )
        )

        if rebuild_tree:
            if use_pbc:
                positions = self._get_periodic_images(cutoff)
            else:
                positions = self.cart_positions

            # All five fields are written in a single attribute assignment,
            # reducing the inconsistency window compared to five separate writes.
            self._neighbor_cache = _NeighborCache(
                tree=cKDTree(positions),
                cutoff=cutoff,
                positions=positions,
                use_pbc=use_pbc,
                pbc=tuple(self.pbc),
            )

        # Validate atom_index if provided
        n_atoms = len(self.cart_positions)
        if atom_index is not None:
            if not (0 <= atom_index < n_atoms):
                raise IndexError(
                    f"Atom index {atom_index} is out of range [0, {n_atoms-1}]"
                )

        # Optimization: For single-atom queries without PBC on small structures,
        # direct calculation is faster than building KDTree
        if atom_index is not None and not use_pbc and n_atoms < 1000:
            pos = self.cart_positions[atom_index]
            distances = np.linalg.norm(self.cart_positions - pos, axis=1)
            neighbors = [
                (i, float(distances[i]))
                for i in range(n_atoms)
                if i != atom_index and distances[i] <= cutoff
            ]
            return {atom_index: neighbors}

        # Query neighbors using KDTree
        neighbors_dict = {}
        # Determine which atoms to query
        atoms_to_query = [atom_index] if atom_index is not None else range(n_atoms)

        cache = self._neighbor_cache  # single local reference; safe under GIL
        query_positions = self._wrapped_cart_positions() if use_pbc else self.cart_positions
        for i in atoms_to_query:
            pos = query_positions[i]
            indices = cache.tree.query_ball_point(pos, cutoff)
            neighbors_by_index: Dict[int, float] = {}
            for idx in indices:
                if idx < n_atoms:
                    # Original atom
                    if idx != i:
                        dist = np.linalg.norm(pos - cache.positions[idx])
                        if idx not in neighbors_by_index or dist < neighbors_by_index[idx]:
                            neighbors_by_index[idx] = float(dist)
                else:
                    # Periodic image
                    image_idx = idx % n_atoms
                    dist = np.linalg.norm(pos - cache.positions[idx])
                    if (
                        image_idx not in neighbors_by_index
                        or dist < neighbors_by_index[image_idx]
                    ):
                        neighbors_by_index[image_idx] = float(dist)

            neighbors_dict[i] = sorted(neighbors_by_index.items())

        return neighbors_dict

    @property
    def density(self) -> float:
        """
        Density of the crystal, adapted to the PBC dimensionality.

        Consistent with ``volume``, ``area``, and ``length``, this is exposed
        as a read-only property rather than a method.

        .. note::
            This was changed from a method (``crystal.density()``) to a property
            (``crystal.density``) for API consistency.  Call sites using
            ``crystal.density()`` should be updated to ``crystal.density``.

        Returns:
            float: Density in appropriate units:
                   - 3D (all PBC True): g/cm^3
                   - 2D (two PBC True): g/cm^2
                   - 1D (one PBC True): g/cm
                   - 0D (no PBC): g/cm^3 (uses volume)

        Raises:
            ValueError: If crystal volume/area/length is zero or negative.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
            >>> crystal.density  # 3D density in g/cm^3
            2.165...
            >>>
            >>> # 2D material
            >>> crystal = crystal.set_pbc([True, True, False])
            >>> crystal.density  # 2D density in g/cm^2
            0.123...
        """
        # Mass is in atomic mass units (amu)
        mass_amu = self.composition.mass
        pbc_count = sum(self.pbc)

        if pbc_count == 3:
            # 3D material: use volume
            size = self.volume
            if size <= 0:
                raise ValueError(
                    "Cannot calculate density: crystal volume is zero or negative"
                )
            # Convert: (mass in amu * amu_to_g) / (volume in A^3 * A^3_to_cm^3)
            # 1 A^3 = 1e-24 cm^3
            return (mass_amu * AMU_TO_GRAM) / (size * 1e-24)
        elif pbc_count == 2:
            # 2D material: use area
            size = self.area
            if size <= 0:
                raise ValueError(
                    "Cannot calculate density: crystal area is zero or negative"
                )
            # Convert: (mass in amu * amu_to_g) / (area in A^2 * A^2_to_cm^2)
            # 1 A^2 = 1e-16 cm^2
            return (mass_amu * AMU_TO_GRAM) / (size * 1e-16)
        elif pbc_count == 1:
            # 1D material: use length
            size = self.length
            if size <= 0:
                raise ValueError(
                    "Cannot calculate density: crystal length is zero or negative"
                )
            # Convert: (mass in amu * amu_to_g) / (length in A * A_to_cm)
            # 1 A = 1e-8 cm
            return (mass_amu * AMU_TO_GRAM) / (size * 1e-8)
        else:
            # 0D material (no PBC) - not periodic, use volume for display
            size = self.volume
            if size <= 0:
                raise ValueError(
                    "Cannot calculate density: crystal volume is zero or negative"
                )
            return (mass_amu * AMU_TO_GRAM) / (size * 1e-24)


    # ======================================================================
    # Builders / convenience constructors
    # ======================================================================

    # ======================================================================
    # Calculator results (Crystal overrides)
    # ======================================================================

