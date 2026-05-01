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
    >>> crystal.volume  # 179.4 Å³
    >>>
    >>> # Access fractional and Cartesian coordinates
    >>> crystal.frac_positions  # Fractional coordinates
    >>> crystal.cart_positions  # Cartesian coordinates
    >>>
    >>> # Set periodic boundary conditions
    >>> crystal.set_pbc([True, True, False])  # 2D slab
    >>>
    >>> # Neighbor finding with PBC
    >>> neighbors = crystal.get_neighbor_list(5.0, use_pbc=True)
"""

import numpy as np
import warnings
from tabulate import tabulate
from typing import List, Optional, Union, Dict, Tuple, Any, Callable, TYPE_CHECKING
from scipy.spatial import cKDTree
from scipy.spatial.distance import pdist, cdist, squareform
from collections import Counter
from .structure import Structure
from .lattice import Lattice
from .periodic_table import Element
from .site import CrystalSite

if TYPE_CHECKING:
    from ..utils.selection import AtomSelection
    from ..calculator.base import Calculator


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
    - File I/O support (POSCAR, CIF, JSON, etc.)
    - Converter support (pymatgen, ASE)
    - DFT code interface
    - Calculator integration

    Attributes:
        species (Tuple[str]): Immutable tuple of atomic species symbols.
        positions (np.ndarray): Numpy array of fractional positions (default).
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
        'ClNa'
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
        >>> crystal.set_pbc([True, True, False])  # 2D slab
        >>> crystal.area  # Area for 2D system
        >>>
        >>> # With site properties
        >>> crystal = Crystal(['Fe', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(4.0),
        ...                   site_properties=[{'magmom': 2.5}, {'magmom': 0.0}])
        >>> crystal.sites[0].properties['magmom']
        2.5
    """

    def __init__(
        self,
        species: Union[List[str], List[int], List[Element]],
        positions: List[List[float]],
        lattice: Lattice,
        pbc: Optional[List[bool]] = None,
        coords_are_cartesian: bool = False,
        site_properties: Optional[List[dict]] = None,
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

        Raises:
            ValueError: If species and positions have different lengths.
            ValueError: If positions are not 3D coordinates or contain invalid values.
            ValueError: If lattice is None (required for crystals).

        Note:
            Both fractional and Cartesian coordinates are maintained internally.
            The default coordinate system is fractional.
        """
        super().__init__(species, positions, lattice)
        self.lattice = lattice

        if coords_are_cartesian:
            self.cart_positions = np.array(positions)
            self.frac_positions = self._convert_to_fractional()
        else:
            self.frac_positions = np.array(positions)
            self.cart_positions = self._convert_to_cartesian()

        self._positions = (
            self.frac_positions
        )  # Set self._positions as the same as self.frac_positions by default
        self.site_properties = site_properties or []
        self._sites = (
            self._initialize_sites()
        )  # Add this line to initialize the _sites attribute
        self.pbc = pbc if pbc is not None else [True, True, True]

        # Add neighbor tree cache for optimized neighbor finding
        self._neighbor_tree: Optional[cKDTree] = None
        self._neighbor_tree_cutoff: Optional[float] = None
        self._neighbor_tree_positions: Optional[np.ndarray] = None
        self._neighbor_tree_use_pbc: Optional[bool] = None
        self._neighbor_tree_pbc: Optional[Tuple[bool, bool, bool]] = None

    # ========================================================================
    # Helper Methods - Reduce Code Duplication
    # ========================================================================

    def _invalidate_neighbor_tree(self) -> None:
        """
        Invalidate neighbor tree cache.

        Called when structure changes (add/remove atoms, substitute, etc.).
        """
        self._neighbor_tree = None
        self._neighbor_tree_positions = None
        self._neighbor_tree_cutoff = None
        self._neighbor_tree_use_pbc = None
        self._neighbor_tree_pbc = None

    def set_pbc(self, pbc: Union[List[bool], Tuple[bool, bool, bool]]) -> None:
        """
        Set periodic boundary conditions for the crystal.

        Args:
            pbc: List or tuple of 3 booleans indicating periodicity along a, b, c axes.
                 [True, True, True] for 3D, [True, True, False] for 2D, etc.

        Raises:
            ValueError: If pbc is not a list/tuple of 3 booleans.

        Examples:
            >>> crystal.set_pbc([True, True, True])  # 3D material
            >>> crystal.set_pbc([True, True, False])  # 2D material (slab)
            >>> crystal.set_pbc([True, False, False])  # 1D material (wire)
            >>> crystal.set_pbc([False, False, False])  # 0D (cluster)
        """
        # Validate input
        if not isinstance(pbc, (list, tuple)):
            raise ValueError("PBC must be a list or tuple of 3 booleans")

        if len(pbc) != 3:
            raise ValueError("PBC must have exactly 3 elements (for a, b, c axes)")

        if not all(isinstance(x, bool) for x in pbc):
            raise ValueError("All PBC elements must be booleans")

        # Set PBC
        self.pbc = list(pbc)

        # Invalidate caches that depend on PBC
        self._invalidate_neighbor_tree()
        # Note: area/length properties will recalculate on access
        # density() will use correct units based on new PBC

    def _update_coordinates_after_modification(self) -> None:
        """
        Update fractional and Cartesian coordinates after modification.

        Ensures consistency between frac_positions and cart_positions.
        """
        self.frac_positions = self.positions
        self.cart_positions = self._convert_to_cartesian()

    def _get_sorted_sites(self, sort_by: str = "element") -> List[CrystalSite]:
        """
        Get sites sorted by specified criterion.

        Args:
            sort_by: Sorting method - 'element' (by atomic number) or 'alphabet'.

        Returns:
            Sorted list of CrystalSite objects.

        Raises:
            ValueError: If sort_by is not 'element' or 'alphabet'.
        """
        if sort_by == "element":
            # Sort by atomic number, then by fractional coordinates
            # Use .elements for efficient Element access
            species_to_element = {
                spec: elem for spec, elem in zip(self.species, self.elements)
            }
            return sorted(
                self.sites,
                key=lambda s: (
                    species_to_element[s.specie].atomic_no,
                    s.frac_position[0],
                    s.frac_position[1],
                    s.frac_position[2],
                ),
            )
        elif sort_by == "alphabet":
            # Sort alphabetically by species, then by coordinates
            return sorted(
                self.sites,
                key=lambda s: (
                    s.specie,
                    s.frac_position[0],
                    s.frac_position[1],
                    s.frac_position[2],
                ),
            )
        else:
            raise ValueError(
                f"sort_by must be 'element' or 'alphabet', got '{sort_by}'"
            )

    @staticmethod
    def _get_sorted_element_counts(
        element_counts: Dict[str, int], sort_by: str
    ) -> List[Tuple[str, int]]:
        """
        Get sorted element counts for formula generation.

        Args:
            element_counts: Dictionary mapping element symbols to counts.
            sort_by: Sorting method - 'element' or 'alphabet'.

        Returns:
            Sorted list of (element, count) tuples.

        Raises:
            ValueError: If sort_by is invalid.
        """
        if sort_by == "alphabet":
            return sorted(element_counts.items(), key=lambda x: x[0])
        elif sort_by == "element":
            return sorted(
                element_counts.items(),
                key=lambda x: Element.get_element(x[0]).atomic_no,
            )
        else:
            raise ValueError(
                f"sort_by must be 'element' or 'alphabet', got '{sort_by}'"
            )

    # ========================================================================
    # Atom Modification Methods
    # ========================================================================

    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
        site_properties: Optional[Union[dict, List[dict]]] = None,
        coords_are_cartesian: bool = False,
    ) -> None:
        """
        Add one or more atoms to the crystal structure and update coordinates.

        Performs chemical reasonableness checks on interatomic distances with PBC support.
        Prevents adding duplicate atoms at the same position or atoms that are too close.
        Uses periodic boundary conditions to check distances across unit cell boundaries.

        Args:
            species: Atomic species (single string or list of strings).
            position: Atomic position(s). Either a single 3D coordinate or list of coordinates.
                     Format depends on coords_are_cartesian parameter.
            site_properties: Optional site properties (single dict or list of dicts).
                           If list, must match length of species.
            coords_are_cartesian: If True, positions are in Cartesian coordinates (Angstrom).
                                If False, positions are in fractional coordinates (default).

        Raises:
            ValueError: If site_properties length doesn't match number of atoms added.
            ValueError: If duplicate positions are detected (distance < 1e-6 Angstrom).
            ValueError: If atoms are too close (distance < 0.5 Angstrom).

        Examples:
            >>> from matsimpy.core import Crystal, Lattice
            >>> lattice = Lattice.cubic(5.0)
            >>> crystal = Crystal(['Si'], [[0, 0, 0]], lattice)
            >>>
            >>> # Add single atom at fractional coordinates (default)
            >>> crystal.add_atom('H', [0.5, 0.5, 0.5])
            >>> print(len(crystal))  # 2 atoms
            2
            >>>
            >>> # Add atom at Cartesian coordinates
            >>> crystal.add_atom('O', [2.5, 2.5, 2.5], coords_are_cartesian=True)
            >>>
            >>> # Add multiple atoms at once (fractional)
            >>> crystal.add_atom(['O', 'C'], [[0.25, 0.25, 0.25], [0.75, 0.75, 0.75]])
            >>> print(len(crystal))  # 4 atoms
            4
            >>>
            >>> # Add multiple atoms at Cartesian coordinates
            >>> crystal.add_atom(['H', 'O'], [[1.0, 1.0, 1.0], [3.0, 3.0, 3.0]],
            ...                  coords_are_cartesian=True)
            >>>
            >>> # Add atoms with site properties
            >>> crystal.add_atom(['H', 'O'], [[0.1, 0.1, 0.1], [0.9, 0.9, 0.9]],
            ...                  [{'charge': 1.0, 'magmom': 0.5}, {'charge': -2.0}])
            >>> print(crystal.site_properties[4])  # {'charge': 1.0, 'magmom': 0.5}
            {'charge': 1.0, 'magmom': 0.5}
            >>>
            >>> # PBC-aware distance checking prevents duplicates across boundaries
            >>> # This will raise ValueError if atom is too close to existing atoms
            >>> # crystal.add_atom('Si', [1.0, 0.0, 0.0])  # Would be duplicate with [0,0,0] due to PBC
        """
        # Guard for frozen state before mutation
        self._check_frozen()
        # Parse and normalize position input
        if isinstance(position, list):
            if len(position) == 0:
                # Empty list - nothing to check
                new_positions = []
            elif isinstance(position[0], (int, float)):
                # Single position [x, y, z]
                new_positions = [position]
            else:
                # Multiple positions [[x1,y1,z1], [x2,y2,z2], ...]
                new_positions = position
        else:
            new_positions = [position]

        # Convert to fractional coordinates if needed
        if new_positions:
            new_pos_array = np.array(new_positions, dtype=np.float64)
            if coords_are_cartesian:
                # Convert Cartesian to fractional
                new_frac_positions = np.dot(new_pos_array, self.lattice.inv_matrix)
                new_cart_positions = new_pos_array
            else:
                # Already fractional
                new_frac_positions = new_pos_array
                new_cart_positions = np.dot(new_frac_positions, self.lattice.matrix)
        else:
            new_frac_positions = np.array([]).reshape(0, 3)
            new_cart_positions = np.array([]).reshape(0, 3)

        # Check for duplicates within new positions using vectorized operations
        if len(new_cart_positions) > 1:
            # Use pdist for efficient pairwise distance calculation
            distances_condensed = pdist(new_cart_positions)

            if np.any(
                distances_condensed < 1e-6
            ):  # Essentially zero distance (duplicate)
                # Only convert to square form if we found a problem
                distances_square = squareform(distances_condensed)
                # Find pairs with distance < 1e-6 (excluding diagonal)
                np.fill_diagonal(distances_square, np.inf)
                i, j = np.where(distances_square < 1e-6)
                # Convert to list for error message
                pos_list = (
                    new_frac_positions.tolist()
                    if isinstance(new_frac_positions, np.ndarray)
                    else new_frac_positions
                )
                raise ValueError(
                    f"Duplicate positions detected in new atoms: "
                    f"positions {i[0]} and {j[0]} are at the same location "
                    f"({pos_list[i[0]]})."
                )

            if np.any(distances_condensed < 0.5):  # Too close
                # Only convert to square form if we found a problem
                min_dist = np.min(distances_condensed)
                distances_square = squareform(distances_condensed)
                # Find pairs with minimum distance (excluding diagonal)
                np.fill_diagonal(distances_square, np.inf)
                i, j = np.where(np.abs(distances_square - min_dist) < 1e-10)
                # Convert to list for error message
                pos_list = (
                    new_frac_positions.tolist()
                    if isinstance(new_frac_positions, np.ndarray)
                    else new_frac_positions
                )
                raise ValueError(
                    f"Atoms being added are too close: distance between "
                    f"positions {i[0]} and {j[0]} is {min_dist:.6f} Angstrom. "
                    f"Minimum allowed distance is 0.5 Angstrom."
                )

        # Check each new position against existing atoms (with PBC)
        # For PBC, we need to use minimum image convention, which requires
        # checking periodic images. This is more complex but we can still optimize.
        if len(self.frac_positions) > 0:
            existing_cart = self.cart_positions
            existing_frac = self.frac_positions

            # For non-PBC or when all PBC are False, use simple cdist
            if not any(self.pbc):
                # Simple case: no PBC, use vectorized cdist
                distances = cdist(new_cart_positions, existing_cart)
                min_distances = np.min(distances, axis=1)

                # Check for duplicates or too close
                for idx, min_dist in enumerate(min_distances):
                    pos_repr = (
                        new_frac_positions[idx].tolist()
                        if isinstance(new_frac_positions[idx], np.ndarray)
                        else new_frac_positions[idx]
                    )
                    if min_dist < 1e-6:
                        raise ValueError(
                            f"Cannot add atom at position {pos_repr}: "
                            f"atom already exists at this location (distance: {min_dist:.6f} Angstrom)."
                        )
                    elif min_dist < 0.5:
                        raise ValueError(
                            f"Cannot add atom at position {pos_repr}: "
                            f"too close to existing atom (distance: {min_dist:.6f} Angstrom). "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )
            else:
                # PBC case: need minimum image convention
                # Convert to arrays for vectorized operations
                new_frac_array = np.array(new_frac_positions)
                existing_frac_array = np.array(existing_frac)

                # Calculate fractional differences for all pairs at once
                # Shape: (n_new, n_existing, 3)
                frac_diffs = (
                    new_frac_array[:, np.newaxis, :]
                    - existing_frac_array[np.newaxis, :, :]
                )

                # Apply minimum image convention to all PBC dimensions at once (vectorized)
                pbc_mask = np.array(self.pbc, dtype=bool)
                if np.any(pbc_mask):
                    frac_diffs[:, :, pbc_mask] = frac_diffs[:, :, pbc_mask] - np.round(
                        frac_diffs[:, :, pbc_mask]
                    )

                # Convert to Cartesian differences
                # Shape: (n_new, n_existing, 3)
                cart_diffs = np.dot(frac_diffs, self.lattice.matrix)

                # Calculate distances
                distances = np.linalg.norm(
                    cart_diffs, axis=2
                )  # Shape: (n_new, n_existing)

                # Find minimum distance for each new atom
                min_distances = np.min(distances, axis=1)

                # Check for duplicates or too close
                for idx, min_dist in enumerate(min_distances):
                    pos_repr = (
                        new_frac_positions[idx].tolist()
                        if isinstance(new_frac_positions[idx], np.ndarray)
                        else new_frac_positions[idx]
                    )
                    if min_dist < 1e-6:
                        raise ValueError(
                            f"Cannot add atom at position {pos_repr}: "
                            f"atom already exists at this location (distance: {min_dist:.6f} Angstrom)."
                        )
                    elif min_dist < 0.5:
                        raise ValueError(
                            f"Cannot add atom at position {pos_repr}: "
                            f"too close to existing atom (distance: {min_dist:.6f} Angstrom). "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )

        # Store complete state for rollback in case of exception
        n_atoms_before = len(self.species)
        old_species = self.species
        old_positions = self.positions.copy()
        old_frac_positions = self.frac_positions.copy()
        old_cart_positions = self.cart_positions.copy()
        old_sites = self._sites.copy() if self._sites else None
        old_site_properties = (
            self.site_properties.copy() if self.site_properties else None
        )
        old_formula_dirty = self._formula_dirty
        old_cached_composition = self._cached_composition
        old_cached_formula = self._cached_formula

        try:
            # Convert fractional positions to list for parent method
            # Parent method expects:
            # - Single atom: position = [x, y, z] (single list)
            # - Multiple atoms: position = [[x1, y1, z1], [x2, y2, z2], ...] (list of lists)
            if isinstance(new_frac_positions, np.ndarray):
                if new_frac_positions.shape[0] == 1:
                    # Single position: extract first row as a list
                    new_frac_list = new_frac_positions[0].tolist()
                else:
                    # Multiple positions: convert 2D array to list of lists
                    new_frac_list = new_frac_positions.tolist()
            else:
                # Already a list
                if len(new_frac_positions) == 1:
                    # Single position: ensure it's a flat list
                    new_frac_list = (
                        new_frac_positions[0]
                        if isinstance(new_frac_positions[0], list)
                        else list(new_frac_positions[0])
                    )
                else:
                    new_frac_list = new_frac_positions

            # Call parent to add atoms (parent expects fractional coordinates)
            super().add_atom(species, new_frac_list)

            n_atoms_added = len(self.species) - n_atoms_before

            # Update coordinates and invalidate caches
            self._update_coordinates_after_modification()
            self._invalidate_neighbor_tree()

            # Update site properties
            if site_properties is not None:
                # Normalize to list
                if isinstance(site_properties, dict):
                    site_properties_list = [site_properties] * n_atoms_added
                else:
                    site_properties_list = site_properties

                # Validate length
                if len(site_properties_list) != n_atoms_added:
                    raise ValueError(
                        f"Number of site_properties ({len(site_properties_list)}) "
                        f"must match number of atoms added ({n_atoms_added})"
                    )

                # Initialize site_properties if needed
                if not self.site_properties:
                    self.site_properties = [{}] * n_atoms_before

                self.site_properties.extend(site_properties_list)
            elif self.site_properties:
                # Maintain existing site_properties with empty dicts
                self.site_properties.extend([{}] * n_atoms_added)

            # Reinitialize sites
            self._sites = self._initialize_sites()

        except Exception:
            # Complete rollback to restore all state using backing fields
            self._species = old_species
            self._positions = old_positions
            self.frac_positions = old_frac_positions
            self.cart_positions = old_cart_positions
            self._sites = old_sites
            if old_site_properties is not None:
                self.site_properties = old_site_properties
            # Restore cache flags
            self._formula_dirty = old_formula_dirty
            self._cached_composition = old_cached_composition
            self._cached_formula = old_cached_formula
            # Re-raise the original exception
            raise

    def remove_atom(self, indices: Union[int, List[int], "AtomSelection"]) -> None:
        """
        Remove one or more atoms from the crystal structure and update coordinates.

        Args:
            indices: Atom index, list of indices, or AtomSelection object to remove.
                    If list, atoms are removed in reverse order to avoid index shifting.

        Raises:
            IndexError: If any index is out of range.
            ValueError: If AtomSelection is from a different structure.

        Examples:
            >>> crystal.remove_atom(0)  # Remove atom at index 0
            >>> crystal.remove_atom([0, 1, 2])  # Remove multiple atoms
            >>> # Using AtomSelection
            >>> from matsimpy.utils.selection import AtomSelection
            >>> sel = AtomSelection(crystal).by_species('H')
            >>> crystal.remove_atom(sel)  # Remove selected atoms
        """
        # Handle AtomSelection object
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        # Guard for frozen state before mutation
        self._check_frozen()
        # Normalize to list
        if isinstance(indices, int):
            indices = [indices]
        elif not isinstance(indices, list):
            raise TypeError(
                f"indices must be int, list of int, or AtomSelection, got {type(indices)}"
            )

        # Validate all indices
        n_atoms = len(self.species)
        for idx in indices:
            if not (0 <= idx < n_atoms):
                raise IndexError(f"Atom index {idx} is out of range [0, {n_atoms-1}]")

        # Remove duplicates and sort in reverse order to avoid index shifting
        indices_to_remove = sorted(set(indices), reverse=True)

        # Remove atoms one by one in reverse order
        for idx in indices_to_remove:
            super().remove_atom(idx)

            # Update site properties
            if self.site_properties and len(self.site_properties) > idx:
                self.site_properties.pop(idx)

        # Update coordinates and caches (only once after all removals)
        self._update_coordinates_after_modification()
        self._invalidate_neighbor_tree()

        # Reinitialize sites
        self._sites = self._initialize_sites()

    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> None:
        """
        Substitute atoms with new species.

        This is a common operation for modifying crystals. For functional
        style (returning new object), use matsimpy.transformation.substitute().

        Args:
            indices: Atom index, list of indices, or AtomSelection object to substitute
            new_species: New species symbol, list of symbols, or dict mapping old->new species

        Raises:
            IndexError: If index is out of range
            ValueError: If number of indices doesn't match number of species
            KeyError: If dict mapping doesn't contain a species

        Examples:
            >>> crystal.substitute(0, 'Ge')  # Substitute atom at index 0
            >>> crystal.substitute([0, 1], ['Ge', 'Ge'])  # Substitute multiple
            >>> # Using AtomSelection
            >>> from matsimpy.utils.selection import AtomSelection
            >>> sel = AtomSelection(crystal).by_species('Si')
            >>> crystal.substitute(sel, 'Ge')  # Substitute selected atoms
            >>> # Using dict mapping (maps old species to new species)
            >>> crystal.substitute([0, 1, 2], {'Si': 'Ge', 'O': 'S'})
        """
        # Call parent implementation to handle the actual substitution
        # and cache invalidation (formula, composition)
        super().substitute(indices, new_species)

        # Crystal-specific updates: invalidate neighbor tree cache
        # and reinitialize sites with updated species
        self._invalidate_neighbor_tree()
        self._sites = self._initialize_sites()

    def _initialize_sites(self) -> List[CrystalSite]:
        """
        Initialize the list of CrystalSite objects.

        Creates CrystalSite objects for each atom, optionally including site properties.
        This method is called during initialization and when atoms are added/removed.

        Returns:
            List[CrystalSite]: A list of CrystalSite objects, one for each atom.

        Note:
            This is an internal method. Sites are automatically updated when
            the structure changes (add_atom, remove_atom, etc.).
        """
        if self.site_properties and len(self.site_properties) == len(self.species):
            return [
                CrystalSite(
                    position=pos,
                    specie=spec,
                    lattice=self.lattice,
                    properties=props,
                    coords_are_cartesian=False,
                )
                for pos, spec, props in zip(
                    self.positions, self.species, self.site_properties
                )
            ]
        else:
            return [
                CrystalSite(
                    position=pos,
                    specie=spec,
                    lattice=self.lattice,
                    coords_are_cartesian=False,
                )
                for pos, spec in zip(self.positions, self.species)
            ]

    @property
    def sites(self) -> List[CrystalSite]:
        """
        Get the list of CrystalSite objects for all atoms.

        Returns:
            List[CrystalSite]: List of CrystalSite objects, one for each atom in the crystal.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
            >>> crystal.sites[0].specie  # 'Na'
            >>> crystal.sites[0].frac_position  # [0, 0, 0]
            >>> len(crystal.sites)
            2
        """
        return self._sites

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
            "pbc": self.pbc,
            "lattice": self.lattice.as_dict(),
            "species": self.species,
            "positions": self.positions.tolist(),
            "site_properties": self.site_properties,  # Add site_properties to the dictionary
        }
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
            'ClNa'
        """
        species = d["species"]
        positions = d["positions"]
        lattice = Lattice.from_dict(d["lattice"])
        site_properties = d.get("site_properties", [])
        coords_are_cartesian = d.get("coords_are_cartesian", False)
        pbc = d.get("pbc")
        return cls(
            species=species,
            positions=positions,
            lattice=lattice,
            pbc=pbc,
            coords_are_cartesian=coords_are_cartesian,
            site_properties=site_properties,
        )

    @property
    def volume(self) -> float:
        """
        Calculate the volume of the unit cell.

        Returns:
            float: Unit cell volume in cubic Angstroms (Å³).

        Note:
            This property is only meaningful for 3D periodic systems
            (PBC = [True, True, True]). For 2D systems, use :attr:`area`.
            For 1D systems, use :attr:`length`.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
            >>> crystal.volume
            179.406...
        """
        a, b, c = self.lattice.lattice_vectors
        volume = np.dot(a, np.cross(b, c))
        return abs(volume)

    @property
    def area(self) -> float:
        """
        Calculate the area for 2D materials (when exactly one PBC is False).

        Returns:
            float: Unit cell area in square Angstroms (Å²).

        Raises:
            ValueError: If the crystal is not a 2D material (exactly 2 PBC True).

        Note:
            This property is only defined for 2D periodic systems
            (e.g., PBC = [True, True, False] for a slab).

        Example:
            >>> crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
            >>> crystal.set_pbc([True, True, False])  # 2D slab
            >>> crystal.area
            100.0
        """
        a, b, c = self.lattice.lattice_vectors
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
            float: Unit cell length in Angstroms (Å).

        Raises:
            ValueError: If the crystal is not a 1D material (exactly 1 PBC True).

        Note:
            This property is only defined for 1D periodic systems
            (e.g., PBC = [True, False, False] for a wire).

        Example:
            >>> crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(10))
            >>> crystal.set_pbc([True, False, False])  # 1D wire
            >>> crystal.length
            10.0
        """
        a, b, c = self.lattice.lattice_vectors
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

    def __str__(self) -> str:
        """
        Get human-readable string representation of Crystal.

        Returns:
            str: Formatted string with crystal information including:
                - Formula
                - Number of atoms
                - PBC information
                - Lattice parameters
                - Volume/Area/Length (depending on dimensionality)
                - Density
                - Table of atoms with coordinates

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
            >>> print(crystal)
            Crystal: ClNa
              Sites: 2 atoms
              PBC: [T T T]
              Lattice: a=5.6400 Å, b=5.6400 Å, c=5.6400 Å
                       α=90.00°, β=90.00°, γ=90.00°
              Volume: 179.4064 Å³
              Density: 2.1650 g/cm³
            ...
        """
        # Basic info
        info = f"{self.__class__.__name__}: {self.formula}\n"
        info += f"  Sites: {len(self)} atoms\n"

        # PBC information - compact format [T T T] or [T F T]
        pbc_str = "[" + " ".join("T" if p else "F" for p in self.pbc) + "]"
        info += f"  PBC: {pbc_str}\n"

        # Lattice parameters (use helper method from Lattice to avoid duplication)
        info += (
            f"  Lattice: {self.lattice._format_lattice_params(include_units=True)}\n"
        )

        # Volume/Area/Length and density based on PBC dimensionality
        pbc_count = sum(self.pbc)
        try:
            if pbc_count == 3:
                # 3D material
                info += f"  Volume: {self.volume:.4f} Å³\n"
                density = self.density()
                # Use appropriate formatting based on magnitude
                if density < 0.01 or density > 1000:
                    info += f"  Density: {density:.6e} g/cm³\n"
                else:
                    info += f"  Density: {density:.4f} g/cm³\n"
            elif pbc_count == 2:
                # 2D material
                info += f"  Area: {self.area:.4f} Å²\n"
                density = self.density()
                # 2D densities are typically very small, use scientific notation
                info += f"  Density: {density:.6e} g/cm²\n"
            elif pbc_count == 1:
                # 1D material
                info += f"  Length: {self.length:.4f} Å\n"
                density = self.density()
                # 1D densities are typically very small, use scientific notation
                info += f"  Density: {density:.6e} g/cm\n"
            else:
                # 0D material (no PBC) - still show volume
                info += f"  Volume: {self.volume:.4f} Å³\n"
                density = self.density()
                if density < 0.01 or density > 1000:
                    info += f"  Density: {density:.6e} g/cm³\n"
                else:
                    info += f"  Density: {density:.4f} g/cm³\n"
        except (ValueError, AttributeError) as e:
            info += "\n"

        # Atom coordinates and properties table
        has_properties = any(site.properties for site in self.sites)
        headers = ["Element", "Fractional Coordinates", "Cartesian Coordinates"]
        if has_properties:
            headers.append("Properties")

        # Display sites in insertion order to match internal species ordering
        display_sites = list(self.sites)

        rows = []
        for site in display_sites:
            element = str(site.specie)
            frac_coords = f"({site.frac_position[0]:.4f}, {site.frac_position[1]:.4f}, {site.frac_position[2]:.4f})"
            cart_coords = f"({site.cart_position[0]:.4f}, {site.cart_position[1]:.4f}, {site.cart_position[2]:.4f})"
            row = [element, frac_coords, cart_coords]
            if has_properties:
                props_str = (
                    ", ".join(f"{k}={v}" for k, v in site.properties.items())
                    if site.properties
                    else ""
                )
                row.append(props_str)
            rows.append(row)

        info += tabulate(rows, headers=headers, tablefmt="plain", stralign="left")

        return info

    def __repr__(self):
        """Unambiguous string representation of Crystal for debugging."""
        # Compact representation with key info
        # Use shorter lattice format: a×b×c, α°β°γ°
        lattice_str = (
            f"{self.lattice.a:.4f}×{self.lattice.b:.4f}×{self.lattice.c:.4f}, "
            f"{self.lattice.alpha:.1f}°/{self.lattice.beta:.1f}°/{self.lattice.gamma:.1f}°"
        )
        # Compact PBC format: [T,T,T] or [T,F,T]
        pbc_str = "[" + ",".join("T" if p else "F" for p in self.pbc) + "]"
        return (
            f"{self.__class__.__name__}(formula='{self.formula}', "
            f"nsites={len(self)}, lattice={lattice_str}, pbc={pbc_str})"
        )

    def __getitem__(self, item):
        return self.sites[item]

    def sort_atoms(self, sort_by: str = "element") -> None:
        """
        Sort atoms in the crystal by element (in-place).

        This method reorders internal species and positions arrays,
        unlike __str__ which only sorts for display.

        Args:
            sort_by: Sorting method - 'element' (atomic number) or 'alphabet'.

        Raises:
            ValueError: If sort_by is not 'element' or 'alphabet'.

        Examples:
            >>> crystal.sort_atoms('element')  # Sort by atomic number
            >>> crystal.sort_atoms('alphabet')  # Sort alphabetically
        """
        # Call parent method to sort species and positions
        super().sort_atoms(sort_by)

        # Update coordinates and caches using helper methods
        self._update_coordinates_after_modification()
        self._invalidate_neighbor_tree()
        self._sites = self._initialize_sites()

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

        Wraps all fractional coordinates to the standard unit cell range [0, 1)
        using modulo operation. This ensures that coordinates outside the unit
        cell are mapped back into the primary unit cell. Both fractional and
        Cartesian coordinates are updated accordingly, and all sites are refreshed.

        Returns:
            Crystal: Returns self for method chaining.

        Example:
            >>> from matsimpy.core import Crystal, Lattice
            >>> lattice = Lattice.cubic(10.0)
            >>> crystal = Crystal(['Fe', 'O'], [[1.5, -0.3, 0.5], [0.2, 0.2, 0.2]], lattice)
            >>> crystal.wrap()
            >>> crystal.frac_positions[0].tolist()
            [0.5, 0.7, 0.5]
            >>>
            >>> # Method chaining
            >>> crystal = Crystal(['Fe'], [[2.1, 0.5, 0.5]], lattice).wrap()
            >>> crystal.frac_positions[0].tolist()
            [0.1, 0.5, 0.5]
        """
        # Wrap each site using the CrystalSite.wrap() method
        for site in self._sites:
            site.wrap()
        
        # Update crystal's positions from the wrapped sites
        self.frac_positions = np.array([site.frac_position for site in self._sites])
        self.cart_positions = np.array([site.cart_position for site in self._sites])
        self.positions = self.frac_positions
        
        # Invalidate neighbor tree cache
        self._invalidate_neighbor_tree()
        return self

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

        # Calculate number of images needed along periodic directions.  Use the
        # shortest periodic vector as a conservative bound.
        periodic_lengths = np.linalg.norm(self.lattice.lattice_vectors[pbc_mask], axis=1)
        min_dist = np.min(periodic_lengths)
        n_images = int(np.ceil(cutoff / min_dist)) + 1

        n_atoms = len(self.cart_positions)
        n_periodic_dims = int(np.sum(pbc_mask))
        n_total_images = (2 * n_images + 1) ** n_periodic_dims - 1  # Exclude origin

        # Check for excessive memory usage
        max_cache_atoms = 1_000_000  # Limit to ~1M atoms in cache
        estimated_atoms = n_atoms * n_total_images
        if estimated_atoms > max_cache_atoms:
            warnings.warn(
                f"Large periodic image cache: {estimated_atoms:,} atoms. "
                f"This may use significant memory. Consider using a smaller cutoff "
                f"or disabling PBC if memory is limited.",
                UserWarning,
            )

        # Generate all translation vectors at once using meshgrid
        i_range = np.arange(-n_images, n_images + 1) if self.pbc[0] else np.array([0])
        j_range = np.arange(-n_images, n_images + 1) if self.pbc[1] else np.array([0])
        k_range = np.arange(-n_images, n_images + 1) if self.pbc[2] else np.array([0])
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
            i_flat[:, np.newaxis] * self.lattice.lattice_vectors[0]
            + j_flat[:, np.newaxis] * self.lattice.lattice_vectors[1]
            + k_flat[:, np.newaxis] * self.lattice.lattice_vectors[2]
        )

        # Add shifts to all positions using broadcasting
        # self.cart_positions: (n_atoms, 3)
        # shifts: (n_images, 3)
        # Result: (n_images, n_atoms, 3) -> reshape to (n_images * n_atoms, 3)
        image_positions = (
            self.cart_positions[np.newaxis, :, :] + shifts[:, np.newaxis, :]
        ).reshape(-1, 3)

        # Stack original positions with image positions
        return np.vstack([self.cart_positions, image_positions])

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
            list of (neighbor_index, distance) tuples. Distances are in Angstroms.
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
        n_atoms = len(self.cart_positions)
        rebuild_tree = (
            self._neighbor_tree is None
            or self._neighbor_tree_cutoff != cutoff
            or self._neighbor_tree_use_pbc != use_pbc
            or self._neighbor_tree_pbc != tuple(self.pbc)
            or (use_pbc and self._neighbor_tree_positions is None)
            or (
                self._neighbor_tree_positions is not None
                and len(self._neighbor_tree_positions) < n_atoms
            )  # Structure changed
        )

        if rebuild_tree:
            if use_pbc:
                positions = self._get_periodic_images(cutoff)
            else:
                positions = self.cart_positions

            self._neighbor_tree = cKDTree(positions)
            self._neighbor_tree_cutoff = cutoff
            self._neighbor_tree_positions = positions
            self._neighbor_tree_use_pbc = use_pbc
            self._neighbor_tree_pbc = tuple(self.pbc)

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
                if i != atom_index and distances[i] < cutoff
            ]
            return {atom_index: neighbors}

        # Query neighbors using KDTree
        neighbors_dict = {}
        # Determine which atoms to query
        atoms_to_query = [atom_index] if atom_index is not None else range(n_atoms)

        for i in atoms_to_query:
            pos = self.cart_positions[i]
            indices = self._neighbor_tree.query_ball_point(pos, cutoff)
            neighbors_by_index: Dict[int, float] = {}
            for idx in indices:
                if idx < n_atoms:
                    # Original atom
                    if idx != i:
                        dist = np.linalg.norm(pos - self._neighbor_tree_positions[idx])
                        if idx not in neighbors_by_index or dist < neighbors_by_index[idx]:
                            neighbors_by_index[idx] = float(dist)
                else:
                    # Periodic image
                    image_idx = idx % n_atoms
                    if image_idx != i:
                        dist = np.linalg.norm(pos - self._neighbor_tree_positions[idx])
                        if (
                            image_idx not in neighbors_by_index
                            or dist < neighbors_by_index[image_idx]
                        ):
                            neighbors_by_index[image_idx] = float(dist)

            neighbors_dict[i] = sorted(neighbors_by_index.items())

        return neighbors_dict

    def density(self) -> float:
        """
        Calculate the density of the crystal based on PBC dimensionality.

        The density calculation automatically adapts to the dimensionality
        of the periodic system (3D, 2D, or 1D) based on the PBC settings.

        Returns:
            float: Density in appropriate units:
                   - 3D (all PBC True): g/cm³
                   - 2D (two PBC True): g/cm²
                   - 1D (one PBC True): g/cm
                   - 0D (no PBC): g/cm³ (uses volume)

        Raises:
            ValueError: If crystal volume/area/length is zero or negative.

        Example:
            >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64))
            >>> crystal.density()  # 3D density in g/cm³
            2.165...
            >>>
            >>> # 2D material
            >>> crystal.set_pbc([True, True, False])
            >>> crystal.density()  # 2D density in g/cm²
            0.123...
        """
        # Mass is in atomic mass units (amu)
        # Conversion: 1 amu = 1.66053906660e-24 g
        AMU_TO_GRAM = 1.66053906660e-24

        mass_amu = self.composition.mass
        pbc_count = sum(self.pbc)

        if pbc_count == 3:
            # 3D material: use volume
            size = self.volume
            if size <= 0:
                raise ValueError(
                    "Cannot calculate density: crystal volume is zero or negative"
                )
            # Convert: (mass in amu * amu_to_g) / (volume in Å³ * Å³_to_cm³)
            # 1 Å³ = 1e-24 cm³
            return (mass_amu * AMU_TO_GRAM) / (size * 1e-24)
        elif pbc_count == 2:
            # 2D material: use area
            size = self.area
            if size <= 0:
                raise ValueError(
                    "Cannot calculate density: crystal area is zero or negative"
                )
            # Convert: (mass in amu * amu_to_g) / (area in Å² * Å²_to_cm²)
            # 1 Å² = 1e-16 cm²
            return (mass_amu * AMU_TO_GRAM) / (size * 1e-16)
        elif pbc_count == 1:
            # 1D material: use length
            size = self.length
            if size <= 0:
                raise ValueError(
                    "Cannot calculate density: crystal length is zero or negative"
                )
            # Convert: (mass in amu * amu_to_g) / (length in Å * Å_to_cm)
            # 1 Å = 1e-8 cm
            return (mass_amu * AMU_TO_GRAM) / (size * 1e-8)
        else:
            # 0D material (no PBC) - not periodic, use volume for display
            size = self.volume
            if size <= 0:
                raise ValueError(
                    "Cannot calculate density: crystal volume is zero or negative"
                )
            return (mass_amu * AMU_TO_GRAM) / (size * 1e-24)

    @classmethod
    def from_file(cls, filename: str, format: Optional[str] = None) -> "Crystal":
        """
        Create a Crystal from a file.

        Automatically detects file format from extension if not specified.
        Supported formats: .vasp, .poscar, .contcar, .cif, .xsf, .json, .ase

        This method uses the high-level read() interface. For more control,
        use matsimpy.io.read() directly.

        Args:
            filename: Path to the structure file
            format: Optional format specification (e.g., 'vasp', 'cif').
                   If None, format is detected from file extension.

        Returns:
            Crystal: Crystal structure from the file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is not supported or file format is invalid
            TypeError: If file contains a Molecule instead of Crystal

        Examples:
            >>> crystal = Crystal.from_file('structure.vasp')
            >>> crystal = Crystal.from_file('structure.cif', format='cif')
        """
        from ..io import read

        result = read(filename, format=format)

        if not isinstance(result, Crystal):
            raise TypeError(
                f"File contains {type(result).__name__}, not Crystal. "
                f"Use Molecule.from_file() for molecular structures."
            )

        return result

    def to_file(self, filename: str, format: Optional[str] = None, **kwargs) -> None:
        """
        Write Crystal to a file.

        Automatically detects file format from extension if not specified.
        Supported formats: .vasp, .poscar, .contcar, .cif, .xsf, .json, .ase

        This method uses the high-level write() interface. For more control,
        use matsimpy.io.write() directly.

        Args:
            filename: Output filename
            format: Optional format specification (e.g., 'vasp', 'cif').
                   If None, format is detected from file extension.
            **kwargs: Additional arguments passed to the format-specific writer
                     (e.g., title for file headers)

        Raises:
            ValueError: If format is not supported

        Examples:
            >>> crystal.to_file('structure.vasp')
            >>> crystal.to_file('structure.cif', title='My Crystal')
        """
        from ..io import write

        write(self, filename, format=format, **kwargs)

    def to_pymatgen(self):
        """
        Convert Crystal to pymatgen Structure.

        Returns:
            pymatgen.core.Structure: pymatgen Structure object

        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io.converters import to_pymatgen

        return to_pymatgen(self)

    def to_ase(self):
        """
        Convert Crystal to ASE Atoms.

        Returns:
            ase.Atoms: ASE Atoms object

        Raises:
            ImportError: If ASE is not installed
        """
        from ..io.converters import to_ase

        return to_ase(self)

    @classmethod
    def from_pymatgen(cls, pymatgen_structure):
        """
        Create Crystal from pymatgen Structure.

        Args:
            pymatgen_structure: pymatgen.core.Structure object

        Returns:
            Crystal: MatSimPy Crystal object

        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io.converters import from_pymatgen

        return from_pymatgen(pymatgen_structure)

    @classmethod
    def from_ase(cls, ase_atoms):
        """
        Create Crystal from ASE Atoms.

        Args:
            ase_atoms: ase.Atoms object (must have cell and PBC)

        Returns:
            Crystal: MatSimPy Crystal object

        Raises:
            ImportError: If ASE is not installed
            ValueError: If ASE Atoms doesn't have cell information
        """
        from ..io.converters import from_ase

        result = from_ase(ase_atoms)
        if not isinstance(result, Crystal):
            raise ValueError("ASE Atoms must have cell and PBC for Crystal conversion")
        return result

    def to_code(self, code: str, filename: str, **kwargs) -> None:
        """
        Write input file for a DFT code.

        Generic interface for writing DFT code input files. Supports multiple
        codes through the code parameter.

        Args:
            code: DFT code name (e.g., 'quantum_espresso', 'qe', 'vasp')
            filename: Output filename
            **kwargs: Additional parameters for the DFT code input
                     (code-specific parameters)

        Raises:
            ValueError: If code is not supported
            NotImplementedError: If code interface is not yet implemented

        Examples:
            >>> crystal.to_code('quantum_espresso', 'scf.in')
            >>> crystal.to_code('qe', 'pw.in', calculation='scf')
        """
        from ..code import get_code_interface

        try:
            interface = get_code_interface(code)
            write_input = interface["write_input"]
            write_input(self, filename, **kwargs)
        except ValueError as e:
            raise ValueError(f"Unsupported DFT code: {code}") from e

    @classmethod
    def from_code(cls, code: str, filename: str, **kwargs) -> "Crystal":
        """
        Read structure from DFT code output file.

        Generic interface for reading structures from DFT code output files.
        Currently not implemented.

        Args:
            code: DFT code name (e.g., 'quantum_espresso', 'qe', 'vasp')
            filename: Path to output file
            **kwargs: Additional parameters for parsing

        Returns:
            Crystal: Crystal structure from the output file

        Raises:
            ValueError: If code is not supported
            NotImplementedError: Output parsing not yet implemented

        Examples:
            >>> crystal = Crystal.from_code('quantum_espresso', 'scf.out')
        """
        from ..code import get_code_interface

        try:
            interface = get_code_interface(code)
            read_output = interface["read_output"]
            # TODO: Implement output parsing
            raise NotImplementedError(
                f"Reading {code} output files not yet implemented"
            )
        except ValueError as e:
            raise ValueError(f"Unsupported DFT code: {code}") from e

    @classmethod
    def random_crystal(
        cls, dim: int, group: int, species: list, num_ions: list, **kwargs
    ):
        """
        Generate a random crystal using PyXtal.

        This is a convenience method that calls the function in the generation module.
        For better organization, consider using matsimpy.generation.random.random_crystal() directly.

        Args:
            dim (int): The dimensionality of the crystal (2 or 3).
            group (int): The space group number.
            species (list): List of chemical symbols for the atoms in the crystal.
            num_ions (list): List of integers representing the number of ions of each species.
            **kwargs: Additional keyword arguments to pass to PyXtal.

        Returns:
            Crystal: A random crystal object.
        """
        from ..generation.random import random_crystal

        return random_crystal(dim, group, species, num_ions, **kwargs)

    @property
    def calc(self) -> Optional["Calculator"]:
        """
        Get the attached calculator.

        Returns:
            :obj:`~matsimpy.calculator.base.Calculator` or None: The attached calculator, or None if none attached.

        Example:
            >>> from matsimpy.calculator import LennardJones
            >>> crystal.calc = LennardJones()
            >>> crystal.calc  # <LennardJones object>
            >>> crystal.calc = None  # Remove calculator
            >>> crystal.calc  # None
        """
        from ..calculator.base import Calculator

        return getattr(self, "_calculator", None)

    @calc.setter
    def calc(self, calculator: Optional["Calculator"]) -> None:
        """
        Attach a calculator to this crystal.

        Sets a calculator that can be used to compute energies, forces, and stress.
        The calculator must be an instance of
        :class:`~matsimpy.calculator.base.Calculator`.

        Args:
            calculator: Calculator object (e.g., LennardJones, Mattersim, VASP)
                      or None to remove the calculator.

        Raises:
            TypeError: If calculator is not a Calculator instance or None.

        Example:
            >>> from matsimpy.calculator import LennardJones
            >>> crystal.calc = LennardJones()
            >>> energy = crystal.get_potential_energy()
        """
        from ..calculator.base import Calculator

        if calculator is not None and not isinstance(calculator, Calculator):
            raise TypeError(
                f"Calculator must be a Calculator instance, got {type(calculator)}"
            )
        self._calculator = calculator

    def get_potential_energy(self) -> float:
        """
        Get potential energy from attached calculator.

        Computes the potential energy using the attached calculator. If the
        calculation hasn't been performed yet, it will be triggered automatically.

        Returns:
            float: Potential energy in eV.

        Raises:
            ValueError: If no calculator is attached.

        Example:
            >>> from matsimpy.calculator import LennardJones
            >>> crystal.calc = LennardJones()
            >>> energy = crystal.get_potential_energy()
            >>> print(f"Energy: {energy:.4f} eV")
        """
        if self.calc is None:
            raise ValueError(
                "No calculator attached. Set crystal.calc = calculator first."
            )
        if not self.calc._calculation_performed:
            self.calc.calculate(self)
        return self.calc.get_potential_energy()

    def get_forces(self) -> np.ndarray:
        """
        Get forces from attached calculator.

        Computes the forces on all atoms using the attached calculator. If the
        calculation hasn't been performed yet, it will be triggered automatically.

        Returns:
            np.ndarray: Forces array of shape (N, 3) in eV/Å, where N is the
                       number of atoms. Each row contains [Fx, Fy, Fz] for one atom.

        Raises:
            ValueError: If no calculator is attached.

        Example:
            >>> from matsimpy.calculator import LennardJones
            >>> crystal.calc = LennardJones()
            >>> forces = crystal.get_forces()
            >>> forces.shape
            (2, 3)  # 2 atoms, 3 force components
            >>> forces[0]  # Force on first atom
            array([0.123, -0.456, 0.789])
        """
        if self.calc is None:
            raise ValueError(
                "No calculator attached. Set crystal.calc = calculator first."
            )
        if not self.calc._calculation_performed:
            self.calc.calculate(self)
        return self.calc.get_forces()

    def get_stress(self) -> np.ndarray:
        """
        Get stress tensor from attached calculator.

        Computes the stress tensor using the attached calculator. If the
        calculation hasn't been performed yet, it will be triggered automatically.

        Returns:
            np.ndarray: Stress tensor. Can be:
                - Shape (3, 3): Full stress tensor matrix
                - Shape (6,): Voigt notation [σxx, σyy, σzz, σyz, σxz, σxy]

            Units are in eV/Å³.

        Raises:
            ValueError: If no calculator is attached.
            AttributeError: If calculator doesn't support stress calculation.

        Example:
            >>> from matsimpy.calculator import VASP
            >>> crystal.calc = VASP(...)
            >>> stress = crystal.get_stress()
            >>> stress.shape
            (3, 3)  # or (6,) depending on calculator
        """
        if self.calc is None:
            raise ValueError(
                "No calculator attached. Set crystal.calc = calculator first."
            )
        if not self.calc._calculation_performed:
            self.calc.calculate(self)
        return self.calc.get_stress()

    def get_symmetry_info(
        self, symprec: float = 1e-5, angle_tolerance: float = -1.0
    ) -> Dict[str, Any]:
        """
        Get basic symmetry information for the crystal structure.

        Uses the symmetry module to analyze the crystal and return basic symmetry info.

        Args:
            symprec: Symmetry search tolerance (default: 1e-5)
            angle_tolerance: Angle tolerance in degrees (default: -1.0 for automatic)

        Returns:
            Dictionary containing:
            - space_group_number: International space group number
            - space_group_symbol: Space group symbol (Hermann-Mauguin)
            - point_group: Point group symbol
            - crystal_system: Crystal system name
            - hall_symbol: Hall symbol

        Examples:
            >>> from matsimpy.builders.bulk import from_prototype
            >>> crystal = from_prototype('diamond', 'Si', 5.43)
            >>> sym_info = crystal.get_symmetry_info()
            >>> print(sym_info['space_group_symbol'])
            'Fd-3m'
            >>> print(sym_info['crystal_system'])
            'Cubic'
        """
        from ..symmetry import SymmetryAnalyzer

        analyzer = SymmetryAnalyzer(symprec=symprec, angle_tolerance=angle_tolerance)
        full_info = analyzer.analyze_crystal(self)

        # Return only basic fields
        return {
            "space_group_number": full_info.get("space_group_number"),
            "space_group_symbol": full_info.get("space_group_symbol"),
            "point_group": full_info.get("point_group"),
            "crystal_system": full_info.get("crystal_system"),
            "hall_symbol": full_info.get("hall_symbol"),
        }

    def get_conventional_cell(
        self, symprec: float = 1e-5, angle_tolerance: float = -1.0
    ) -> "Crystal":
        """
        Get the standard conventional cell of the crystal structure.

        Uses the symmetry module to get the conventional cell representation.

        Args:
            symprec: Symmetry search tolerance (default: 1e-5)
            angle_tolerance: Angle tolerance in degrees (default: -1.0 for automatic)

        Returns:
            Crystal: New Crystal object with standardized conventional cell

        Examples:
            >>> from matsimpy.builders.bulk import from_prototype
            >>> # Start with primitive cell
            >>> primitive = from_prototype('diamond', 'Si', 5.43)
            >>> print(len(primitive))  # 2 atoms (primitive)
            2
            >>> # Get conventional cell
            >>> conventional = primitive.get_conventional_cell()
            >>> print(len(conventional))  # 8 atoms (conventional)
            8
        """
        from ..symmetry import get_conventional_cell

        return get_conventional_cell(
            self, symprec=symprec, angle_tolerance=angle_tolerance
        )

    def make_supercell(
        self,
        scaling_matrix: Union[List[int], List[List[int]], np.ndarray],
        inplace: bool = False,
    ) -> "Crystal":
        """
        Create a supercell from this crystal structure.

        Convenience method that calls the transformation module's make_supercell function.
        By default, returns a new crystal. Set inplace=True to modify in-place.

        Args:
            scaling_matrix: Scaling matrix for supercell generation.
                           Can be:
                           - Simple: [a, b, c] - repeats a times in a, b times in b, c times in c
                           - Matrix: [[a1, a2, a3], [b1, b2, b3], [c1, c2, c3]] - general transformation
            inplace: If True, modify this crystal in-place (default: False).
                    If False, return a new Crystal object.

        Returns:
            Crystal: Supercell structure (self if inplace=True, new object if inplace=False)

        Examples:
            >>> from matsimpy.builders.bulk import from_prototype
            >>> crystal = from_prototype('diamond', 'Si', 5.43)
            >>> # Create 2x2x2 supercell (returns new)
            >>> new_crystal = crystal.make_supercell([2, 2, 2])
            >>> print(len(new_crystal))  # 16 atoms (2*2*2*2)
            16
            >>> # Create supercell in-place
            >>> crystal.make_supercell([2, 2, 2], inplace=True)
            >>> print(len(crystal))  # 16 atoms
            16
        """
        from ..transformation.structural import make_supercell

        # Transformation function always returns a new object
        new_crystal = make_supercell(self, scaling_matrix)

        if inplace:
            # Copy data from new_crystal to self using backing fields to bypass
            # the strict setters that require parity between species and positions.
            self._species = new_crystal.species
            self._positions = new_crystal.positions
            self.frac_positions = new_crystal.frac_positions
            self.cart_positions = new_crystal.cart_positions
            self.lattice = new_crystal.lattice
            self.site_properties = new_crystal.site_properties
            # Invalidate caches
            self._neighbor_tree = None
            self._neighbor_tree_positions = None
            self._sites = self._initialize_sites()
            self._formula_dirty = True
            self._cached_composition = None
            self._cached_formula = None
            return self
        else:
            # Return the new object
            return new_crystal

    def perturb(
        self,
        amplitude: float,
        indices: Optional[Union[List[int], "AtomSelection"]] = None,
        seed: Optional[int] = None,
        inplace: bool = True,
        perturb_positions: bool = True,
        perturb_lattice: bool = False,
        amplitude_lattice: Optional[float] = None,
    ) -> "Crystal":
        """
        Add random perturbations to atomic positions, lattice, or both.

        Supports perturbing positions, lattice vectors, or both simultaneously.
        By default, only positions are perturbed (backward compatible).

        Args:
            amplitude: Maximum perturbation amplitude (Angstroms) for positions.
                      Used as default for lattice if amplitude_lattice is None.
            indices: Atom indices to perturb (default: all atoms).
                    Can be a list of indices or an AtomSelection object.
                    Only used when perturb_positions=True.
            seed: Random seed for reproducibility
            inplace: If True, modify this crystal in-place (default: True).
                    If False, return a new Crystal object.
            perturb_positions: If True, perturb atomic positions (default: True).
            perturb_lattice: If True, perturb lattice vectors (default: False).
            amplitude_lattice: Maximum perturbation amplitude for lattice vectors (Angstroms).
                             If None, uses the same value as amplitude.

        Returns:
            Crystal: Structure with perturbations applied (self if inplace=True, new object if inplace=False)

        Raises:
            ValueError: If both perturb_positions and perturb_lattice are False.

        Examples:
            >>> from matsimpy.builders.bulk import from_prototype
            >>> from matsimpy.utils.selection import AtomSelection
            >>> crystal = from_prototype('diamond', 'Si', 5.43)
            >>>
            >>> # Perturb positions only (default, backward compatible)
            >>> crystal.perturb(0.1)
            >>>
            >>> # Perturb lattice only
            >>> crystal.perturb(0.05, perturb_positions=False, perturb_lattice=True)
            >>>
            >>> # Perturb both positions and lattice
            >>> crystal.perturb(0.1, perturb_lattice=True, amplitude_lattice=0.05)
            >>>
            >>> # Perturb specific atoms (positions only)
            >>> perturbed = crystal.perturb(0.1, indices=[0, 1], inplace=False)
            >>>
            >>> # Perturb using AtomSelection
            >>> sel = AtomSelection(crystal).by_species('Si')
            >>> crystal.perturb(0.1, indices=sel)
        """
        if not perturb_positions and not perturb_lattice:
            raise ValueError(
                "At least one of perturb_positions or perturb_lattice must be True"
            )

        # Handle AtomSelection object
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        # Determine if we need to copy the structure
        if not inplace:
            result = self.copy()
        else:
            result = self

        # Set up random seed if provided
        if seed is not None:
            import numpy as np

            np.random.seed(seed)

        # Perturb positions if requested
        if perturb_positions:
            from ..transformation.atomic import perturb_positions

            # perturb_positions always returns a new structure
            result = perturb_positions(
                result, amplitude, indices=indices, seed=None
            )

        # Perturb lattice if requested
        if perturb_lattice:
            from ..transformation.lattice import perturb_lattice

            lattice_amplitude = (
                amplitude_lattice if amplitude_lattice is not None else amplitude
            )
            # perturb_lattice always returns a new structure
            result = perturb_lattice(result, lattice_amplitude, seed=None)

        if inplace:
            # Update self with result's attributes
            self.positions = result.positions
            self.frac_positions = result.frac_positions
            self.cart_positions = result.cart_positions
            self.lattice = result.lattice
            self._sites = result._sites
            self._neighbor_tree = None  # Invalidate neighbor tree
            self._neighbor_tree_positions = None
            return self
        return result
