import numpy as np
import warnings
from tabulate import tabulate
from typing import List, Optional, Union, Dict, Tuple, Any, Callable
from scipy.spatial import cKDTree
from scipy.spatial.distance import pdist, cdist, squareform
from collections import Counter
from .structure import Structure
from .lattice import Lattice
from .periodic_table import Element
from .site import CrystalSite


class Crystal(Structure):
    def __init__(
        self,
        species: Union[List[str], List[int], List[Element]],
        positions: List[List[float]],
        lattice: Lattice,
        pbc: Optional[List[bool]] = None,
        coords_are_cartesian: bool = False,
        site_properties: Optional[List[dict]] = None,
    ):  # Add site_properties as an optional argument)
        super().__init__(species, positions, lattice)
        self.lattice = lattice

        if coords_are_cartesian:
            self.cart_positions = np.array(positions)
            self.frac_positions = self._convert_to_fractional()
        else:
            self.frac_positions = np.array(positions)
            self.cart_positions = self._convert_to_cartesian()

        self.positions = (
            self.frac_positions
        )  # Set self.positions as the same as self.frac_positions by default
        self.site_properties = site_properties or []
        self._sites = (
            self._initialize_sites()
        )  # Add this line to initialize the _sites attribute
        self.pbc = pbc if pbc is not None else [True, True, True]

        # Add neighbor tree cache for optimized neighbor finding
        self._neighbor_tree: Optional[cKDTree] = None
        self._neighbor_tree_cutoff: Optional[float] = None
        self._neighbor_tree_positions: Optional[np.ndarray] = None

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
            return sorted(
                self.sites,
                key=lambda s: (
                    Element.get_element(s.specie).atomic_no,
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
    ) -> None:
        """
        Add one or more atoms to the crystal structure and update coordinates.

        Performs chemical reasonableness checks on interatomic distances with PBC support.
        Prevents adding duplicate atoms at the same position or atoms that are too close.
        Uses periodic boundary conditions to check distances across unit cell boundaries.

        Args:
            species: Atomic species (single string or list of strings).
            position: Atomic position(s) in fractional coordinates.
                     Either a single 3D coordinate or list of coordinates.
            site_properties: Optional site properties (single dict or list of dicts).
                           If list, must match length of species.

        Raises:
            ValueError: If site_properties length doesn't match number of atoms added.
            ValueError: If duplicate positions are detected (distance < 1e-6 Å).
            ValueError: If atoms are too close (distance < 0.5 Å).

        Examples:
            >>> from matsimpy.core import Crystal, Lattice
            >>> lattice = Lattice.cubic(5.0)
            >>> crystal = Crystal(['Si'], [[0, 0, 0]], lattice)
            >>> 
            >>> # Add single atom at fractional coordinates
            >>> crystal.add_atom('H', [0.5, 0.5, 0.5])
            >>> print(len(crystal))  # 2 atoms
            2
            >>> 
            >>> # Add multiple atoms at once
            >>> crystal.add_atom(['O', 'C'], [[0.25, 0.25, 0.25], [0.75, 0.75, 0.75]])
            >>> print(len(crystal))  # 4 atoms
            4
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
        # Chemical reasonableness check - validate interatomic distances with PBC
        # Convert to array for processing
        if isinstance(position, list):
            if len(position) == 0:
                # Empty list - nothing to check
                new_frac_positions = []
            elif isinstance(position[0], (int, float)):
                # Single position [x, y, z]
                new_frac_positions = [position]
            else:
                # Multiple positions [[x1,y1,z1], [x2,y2,z2], ...]
                new_frac_positions = position
        else:
            new_frac_positions = [position]

        # Convert fractional positions to Cartesian for distance calculation
        if new_frac_positions:
            new_frac_array = np.array(new_frac_positions, dtype=np.float64)
            new_cart_positions = np.dot(new_frac_array, self.lattice.matrix)
        else:
            new_cart_positions = np.array([]).reshape(0, 3)

        # Check for duplicates within new positions using vectorized operations
        if len(new_cart_positions) > 1:
            # Use pdist for efficient pairwise distance calculation
            distances_condensed = pdist(new_cart_positions)
            if np.any(distances_condensed < 1e-6):  # Essentially zero distance (duplicate)
                # Convert to square form to easily find indices
                distances_square = squareform(distances_condensed)
                # Find the pair with minimum distance (excluding diagonal)
                np.fill_diagonal(distances_square, np.inf)
                i, j = np.unravel_index(np.argmin(distances_square), distances_square.shape)
                raise ValueError(
                    f"Duplicate positions detected in new atoms: "
                    f"positions {i} and {j} are at the same location "
                    f"({new_frac_positions[i]})."
                )
            elif np.any(distances_condensed < 0.5):  # Too close
                # Convert to square form to easily find indices
                distances_square = squareform(distances_condensed)
                # Find the pair with minimum distance (excluding diagonal)
                np.fill_diagonal(distances_square, np.inf)
                min_dist = np.min(distances_square)
                i, j = np.unravel_index(np.argmin(distances_square), distances_square.shape)
                raise ValueError(
                    f"Atoms being added are too close: distance between "
                    f"positions {i} and {j} is {min_dist:.6f} Å. "
                    f"Minimum allowed distance is 0.5 Å."
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
                    if min_dist < 1e-6:
                        raise ValueError(
                            f"Cannot add atom at fractional position {new_frac_positions[idx]}: "
                            f"atom already exists at this location (distance: {min_dist:.6f} Å)."
                        )
                    elif min_dist < 0.5:
                        raise ValueError(
                            f"Cannot add atom at fractional position {new_frac_positions[idx]}: "
                            f"too close to existing atom (distance: {min_dist:.6f} Å). "
                            f"Minimum allowed distance is 0.5 Å."
                        )
            else:
                # PBC case: need minimum image convention
                # Convert to arrays for vectorized operations
                new_frac_array = np.array(new_frac_positions)
                existing_frac_array = np.array(existing_frac)

                # Calculate fractional differences for all pairs at once
                # Shape: (n_new, n_existing, 3)
                frac_diffs = new_frac_array[:, np.newaxis, :] - existing_frac_array[np.newaxis, :, :]

                # Apply minimum image convention for each PBC direction
                for dim in range(3):
                    if self.pbc[dim]:
                        frac_diffs[:, :, dim] = frac_diffs[:, :, dim] - np.round(
                            frac_diffs[:, :, dim]
                        )

                # Convert to Cartesian differences
                # Shape: (n_new, n_existing, 3)
                cart_diffs = np.dot(frac_diffs, self.lattice.matrix)

                # Calculate distances
                distances = np.linalg.norm(cart_diffs, axis=2)  # Shape: (n_new, n_existing)

                # Find minimum distance for each new atom
                min_distances = np.min(distances, axis=1)

                # Check for duplicates or too close
                for idx, min_dist in enumerate(min_distances):
                    if min_dist < 1e-6:
                        raise ValueError(
                            f"Cannot add atom at fractional position {new_frac_positions[idx]}: "
                            f"atom already exists at this location (distance: {min_dist:.6f} Å)."
                        )
                    elif min_dist < 0.5:
                        raise ValueError(
                            f"Cannot add atom at fractional position {new_frac_positions[idx]}: "
                            f"too close to existing atom (distance: {min_dist:.6f} Å). "
                            f"Minimum allowed distance is 0.5 Å."
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
            # Call parent to add atoms
            super().add_atom(species, position)

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

        except Exception as e:
            # Complete rollback to restore all state
            self.species = old_species
            self.positions = old_positions
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

    def remove_atom(self, index: int) -> None:
        """
        Remove an atom from the crystal structure and update coordinates.

        Args:
            index: Index of atom to be removed.

        Raises:
            IndexError: If index is out of range.
        """
        super().remove_atom(index)

        # Update coordinates and caches
        self._update_coordinates_after_modification()
        self._invalidate_neighbor_tree()

        # Update site properties
        if self.site_properties and len(self.site_properties) > index:
            self.site_properties.pop(index)

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
        Initializes the list of CrystalSite objects.

        Returns:
            List[CrystalSite]: A list of CrystalSite objects.
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
        return self._sites

    def as_dict(self):
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
    def from_dict(cls, d):
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
        """Calculate the volume of the crystal."""
        a, b, c = self.lattice.lattice_vectors
        volume = np.dot(a, np.cross(b, c))
        return abs(volume)

    def __str__(self):
        """Human-readable string representation of Crystal."""
        # Basic info
        info = f"{self.__class__.__name__}: {self.formula}\n"
        info += f"  Sites: {len(self)} atoms\n"

        # Lattice parameters (use helper method from Lattice to avoid duplication)
        info += (
            f"  Lattice: {self.lattice._format_lattice_params(include_units=True)}\n"
        )

        # Volume and density
        info += f"  Volume: {self.volume:.4f} Å³\n"
        try:
            density = self.density()
            info += f"  Density: {density:.4f} g/cm³\n"
        except (ValueError, AttributeError):
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
        lattice_params = (
            f"a={self.lattice.a:.4f}, b={self.lattice.b:.4f}, c={self.lattice.c:.4f}, "
            f"α={self.lattice.alpha:.1f}°, β={self.lattice.beta:.1f}°, γ={self.lattice.gamma:.1f}°"
        )
        return (
            f"{self.__class__.__name__}(formula='{self.formula}', "
            f"nsites={len(self)}, lattice={lattice_params})"
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

        Returns:
            Numpy array of Cartesian positions.
        """
        return np.dot(self.frac_positions, self.lattice.matrix)

    def _convert_to_fractional(self) -> np.ndarray:
        """
        Convert Cartesian coordinates to fractional coordinates.

        Returns:
            Numpy array of fractional positions.
        """
        # Use cached inverse matrix
        return np.dot(self.cart_positions, self.lattice.inv_matrix)

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
        # Calculate number of images needed
        max_dist = np.max(np.linalg.norm(self.lattice.lattice_vectors, axis=1))
        n_images = int(np.ceil(cutoff / max_dist)) + 1

        n_atoms = len(self.cart_positions)
        n_total_images = (2 * n_images + 1) ** 3 - 1  # Exclude (0,0,0)

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
        i_range = np.arange(-n_images, n_images + 1)
        j_range = np.arange(-n_images, n_images + 1)
        k_range = np.arange(-n_images, n_images + 1)
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

        Args:
            cutoff: Cutoff radius for neighbor finding
            atom_index: Optional atom index. If None, returns neighbors for all atoms.
                       If specified, returns neighbors only for that atom.
            use_pbc: Whether to use periodic boundary conditions

        Returns:
            Dict mapping atom index to list of (neighbor_index, distance) tuples.
            If atom_index is provided, dict contains only that entry.
            If atom_index is None, dict contains entries for all atoms.

        Raises:
            IndexError: If atom_index is out of range

        Examples:
            >>> crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], lattice)
            >>> # Get neighbors for all atoms
            >>> neighbors = crystal.get_neighbor_list(5.0)
            >>> # Get neighbors for specific atom
            >>> neighbors = crystal.get_neighbor_list(5.0, atom_index=0)
        """
        # Check if we need to rebuild tree
        n_atoms = len(self.cart_positions)
        rebuild_tree = (
            self._neighbor_tree is None
            or self._neighbor_tree_cutoff != cutoff
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

        # Validate atom_index if provided
        n_atoms = len(self.cart_positions)
        if atom_index is not None:
            if not (0 <= atom_index < n_atoms):
                raise IndexError(
                    f"Atom index {atom_index} is out of range [0, {n_atoms-1}]"
                )

        # Query neighbors
        neighbors_dict = {}
        # Determine which atoms to query
        atoms_to_query = [atom_index] if atom_index is not None else range(n_atoms)

        for i in atoms_to_query:
            pos = self.cart_positions[i]
            indices = self._neighbor_tree.query_ball_point(pos, cutoff)
            neighbors = []
            for idx in indices:
                if idx < n_atoms:
                    # Original atom
                    if idx != i:
                        dist = np.linalg.norm(pos - self._neighbor_tree_positions[idx])
                        neighbors.append((idx, dist))
                else:
                    # Periodic image
                    image_idx = idx % n_atoms
                    if image_idx != i:
                        dist = np.linalg.norm(pos - self._neighbor_tree_positions[idx])
                        neighbors.append((image_idx, dist))

            neighbors_dict[i] = neighbors

        return neighbors_dict

    def density(self) -> float:
        """
        Calculate the density of the crystal.

        Returns:
            float: Density in g/cm³

        Raises:
            ValueError: If crystal volume is zero or negative
        """
        mass = self.composition.mass  # mass is a property, not a method
        volume = self.volume
        if volume <= 0:
            raise ValueError(
                "Cannot calculate density: crystal volume is zero or negative"
            )
        return mass / volume

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
    def calc(self):
        """
        Get attached calculator.

        Returns:
            Calculator or None: The attached calculator, or None if none attached
        """
        return getattr(self, "_calculator", None)

    @calc.setter
    def calc(self, calculator):
        """
        Attach a calculator to this structure.

        Args:
            calculator: Calculator object (e.g., LennardJones, Mattersim, VASP)

        Raises:
            TypeError: If calculator is not a Calculator instance
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

        Returns:
            float: Potential energy in eV

        Raises:
            ValueError: If no calculator attached or calculation not performed
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

        Returns:
            np.ndarray: Forces array of shape (N, 3) in eV/Å

        Raises:
            ValueError: If no calculator attached or calculation not performed
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

        Returns:
            np.ndarray: Stress tensor of shape (3, 3) or (6,) in eV/Å³

        Raises:
            ValueError: If no calculator attached or calculation not performed
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
        inplace: bool = True,
    ) -> "Crystal":
        """
        Create a supercell from this crystal structure.

        Convenience method that calls the transformation module's make_supercell function.
        By default, modifies the structure in-place.

        Args:
            scaling_matrix: Scaling matrix for supercell generation.
                           Can be:
                           - Simple: [a, b, c] - repeats a times in a, b times in b, c times in c
                           - Matrix: [[a1, a2, a3], [b1, b2, b3], [c1, c2, c3]] - general transformation
            inplace: If True, modify this crystal in-place (default: True).
                    If False, return a new Crystal object.

        Returns:
            Crystal: Supercell structure (self if inplace=True, new object if inplace=False)

        Examples:
            >>> from matsimpy.builders.bulk import from_prototype
            >>> crystal = from_prototype('diamond', 'Si', 5.43)
            >>> # Create 2x2x2 supercell in-place
            >>> crystal.make_supercell([2, 2, 2])
            >>> print(len(crystal))  # 16 atoms (2*2*2*2)
            16
            >>> # Create supercell without modifying original
            >>> new_crystal = crystal.make_supercell([2, 2, 2], inplace=False)
        """
        from ..transformation.structural import make_supercell

        if inplace:
            # The transformation function modifies self and returns self when inplace=True
            result = make_supercell(self, scaling_matrix, inplace=True)
            # Ensure we return self for method chaining, even if transformation returns something else
            return self if result is self else result
        else:
            # Return new object when inplace=False
            return make_supercell(self, scaling_matrix, inplace=False)

    def perturb(
        self,
        amplitude: float,
        indices: Optional[Union[List[int], "AtomSelection"]] = None,
        seed: Optional[int] = None,
        inplace: bool = True,
    ) -> "Crystal":
        """
        Add random perturbations to atomic positions.

        Convenience method that calls the transformation module's perturb_positions function.
        By default, modifies the structure in-place.

        Args:
            amplitude: Maximum perturbation amplitude (Angstroms)
            indices: Atom indices to perturb (default: all atoms).
                    Can be a list of indices or an AtomSelection object.
            seed: Random seed for reproducibility
            inplace: If True, modify this crystal in-place (default: True).
                    If False, return a new Crystal object.

        Returns:
            Crystal: Structure with perturbed positions (self if inplace=True, new object if inplace=False)

        Examples:
            >>> from matsimpy.builders.bulk import from_prototype
            >>> from matsimpy.utils.selection import AtomSelection
            >>> crystal = from_prototype('diamond', 'Si', 5.43)
            >>> # Perturb all atoms by up to 0.1 Angstrom
            >>> crystal.perturb(0.1)
            >>> # Perturb specific atoms without modifying original
            >>> perturbed = crystal.perturb(0.1, indices=[0, 1], inplace=False)
            >>> # Perturb using AtomSelection
            >>> sel = AtomSelection(crystal).by_species('Si')
            >>> crystal.perturb(0.1, indices=sel)
        """
        # Handle AtomSelection object
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        from ..transformation.atomic import perturb_positions

        result = perturb_positions(
            self, amplitude, indices=indices, seed=seed, inplace=inplace
        )
        if inplace:
            # Update self with result's attributes
            self.positions = result.positions
            self.frac_positions = result.frac_positions
            self.cart_positions = result.cart_positions
            self._sites = result._sites
            self._neighbor_tree = None  # Invalidate neighbor tree
            self._neighbor_tree_positions = None
            return self
        return result
