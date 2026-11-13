"""
Molecule module for MatSimPy.

This module provides the Molecule class for representing non-periodic molecular
structures. Molecules are atomic structures without periodic boundary conditions,
typically used for isolated molecules, clusters, or gas-phase systems.

The Molecule class extends Structure and provides:
- Non-periodic structure representation
- Center of mass calculations
- Molecular transformations (translation, rotation)
- Neighbor finding (without PBC)
- File I/O support (XYZ, PDB, MOL, JSON)
- Converter support (pymatgen, ASE)
- DFT code interface
- Calculator integration

Example:
    >>> from matsimpy.core.molecule import Molecule
    >>>
    >>> # Create a water molecule
    >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
    >>> molecule.formula  # 'H2O'
    >>> molecule.get_center_of_mass()
    [0.123..., 0.123..., 0.0]
    >>>
    >>> # Transformations
    >>> molecule.translate([1.0, 0.0, 0.0])
    >>> molecule.rotate(90, [0, 0, 1])
    >>>
    >>> # File I/O
    >>> from matsimpy.io import write, read
    >>> write(molecule, 'molecule.xyz')
    >>> molecule2 = read('molecule.xyz')
"""

import numpy as np
from typing import List, Mapping, Optional, Sequence, Dict, Any, Union, Tuple, TYPE_CHECKING
from .lattice import Lattice
from .structure import Structure
from .site import Site
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist

if TYPE_CHECKING:
    from .crystal import Crystal


class Molecule(Structure):
    """
    A class representing a non-periodic molecular structure.

    Molecule extends :class:`~matsimpy.core.structure.Structure` to represent
    atomic structures without periodic boundary conditions. Molecules are
    typically used for isolated molecules, clusters, or gas-phase systems.

    The Molecule class provides:
    - Non-periodic structure representation (no lattice)
    - Center of mass calculations
    - Molecular transformations (translation, rotation)
    - Neighbor finding (without PBC)
    - Site-based access to atoms
    - File I/O support (XYZ, PDB, MOL, JSON)
    - Converter support (pymatgen, ASE)
    - DFT code interface
    - Calculator integration

    Attributes:
        species (Tuple[str]): Immutable tuple of atomic species symbols.
        positions (np.ndarray): Numpy array of Cartesian positions with shape (n_atoms, 3).
        sites (List[Site]): List of Site objects for each atom.
        site_properties (List[Dict[str, Any]]): List of site property dictionaries.
        formula (str): Chemical formula of the molecule (cached property).
        composition (Composition): Composition object (cached property).
        lattice (None): Always None for molecules (no periodic boundary conditions).

    Args:
        species: List of atomic species symbols (e.g., ['O', 'H', 'H']).
        positions: List of Cartesian atomic positions in Angstroms.
                  Each position is a 3D coordinate [x, y, z].
        site_properties: Optional list of site property dictionaries.
                        Each dict can contain properties like 'charge', 'magmom', etc.
                        Length must match number of atoms if provided.

    Raises:
        ValueError: If species and positions have different lengths.
        ValueError: If positions are not 3D coordinates or contain invalid values.

    Note:
        Molecules have no lattice (lattice=None). All positions are Cartesian
        coordinates in Angstroms. For periodic structures, use
        :class:`~matsimpy.core.crystal.Crystal` instead.

    Examples:
        >>> from matsimpy.core.molecule import Molecule
        >>>
        >>> # Create a water molecule
        >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
        >>> molecule.formula
        'H2O'
        >>> len(molecule)
        3
        >>>
        >>> # Access sites
        >>> molecule.sites[0].specie  # 'O'
        >>> molecule.sites[0].position  # [0, 0, 0]
        >>>
        >>> # Center of mass
        >>> com = molecule.get_center_of_mass()
        >>> print(com)  # [0.123..., 0.123..., 0.0]
        >>>
        >>> # With site properties
        >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
        ...                     site_properties=[{'charge': -2}, {'charge': 1}, {'charge': 1}])
        >>> molecule.sites[0].properties['charge']
        -2
    """

    # ======================================================================
    # Construction & internal helpers
    # ======================================================================

    def _set_state(
        self,
        species: Sequence[Any],
        positions: Any,
        lattice: Optional[Lattice] = None,
        site_properties: Optional[List[dict]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Assign state; ``positions`` are Cartesian.  Molecules have no lattice."""
        super()._set_state(species, positions, None, site_properties=site_properties, metadata=metadata)
        self._cached_com: Optional[List[float]] = None

    def __init__(
        self,
        species: List[str],
        positions: List[List[float]],
        site_properties: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """
        Initialize a Molecule object.

        Args:
            species: List of atomic species symbols (e.g., ['O', 'H', 'H']).
            positions: List of Cartesian atomic positions in Angstroms.
                      Each position is a 3D coordinate [x, y, z].
            site_properties: Optional list of site property dictionaries.
                           Each dict can contain properties like 'charge', 'magmom', etc.
                           Length must match number of atoms if provided.

        Raises:
            ValueError: If species and positions have different lengths.
            ValueError: If positions are not 3D coordinates or contain invalid values.
            ValueError: If site_properties length doesn't match number of atoms.

        Note:
            Molecules have no lattice (lattice=None). All positions are Cartesian
            coordinates in Angstroms.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]],
            ...                     site_properties=[{'charge': 0}, {'charge': -2}])
        """
        species_list = self._normalize_species_input(species)
        if len(species_list) != len(positions):
            raise ValueError(
                f"Number of species ({len(species_list)}) must match "
                f"number of positions ({len(positions)})"
            )
        self._set_state(
            species_list,
            self._validate_positions(positions),
            site_properties=site_properties,
            metadata=metadata,
        )

    def _initialize_sites(self) -> List[Site]:
        """Build a fresh Site snapshot for every atom."""
        return [self._site_snapshot(i) for i in range(len(self._species))]

    # ======================================================================
    # Subclass extension hooks / extra serialisation fields
    # ======================================================================

    # ----------------------------------------------------------------------
    # Per-atom metadata adjustment hooks (Structure base helpers)
    # ----------------------------------------------------------------------

    # ======================================================================
    # Sites / indexing
    # ======================================================================

    def _site_snapshot(self, index: int) -> Site:
        """Return a detached Site snapshot for one atom (O(1), no cache)."""
        props = self._site_properties[index] if self._site_properties else None
        return Site(
            position=self._coords[index],
            specie=self._species[index],
            properties=props,
        )

    @property
    def sites(self) -> Tuple[Site, ...]:
        """
        Get the list of Site objects for all atoms.

        Returns:
            Tuple[Site, ...]: Fresh Site snapshots, one for each atom in the molecule.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> molecule.sites[0].specie  # 'O'
            >>> molecule.sites[0].position  # [0, 0, 0]
            >>> len(molecule.sites)
            3
        """
        return tuple(self._initialize_sites())

    def __getitem__(self, item: Union[int, slice]) -> Union[Site, List[Site]]:
        """
        Get Site object(s) by index or slice.

        Args:
            item: Integer index or slice object.

        Returns:
            Site: Single Site object if item is int.
            List[Site]: List of Site objects if item is slice.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> molecule[0]  # First Site (O atom)
            <Site object>
            >>> molecule[0:2]  # First two Sites
            [<Site object>, <Site object>]
        """
        if isinstance(item, slice):
            return self.sites[item]
        return self._site_snapshot(self._site_index(item))

    # ======================================================================
    # Geometry & transformations (immutable)
    # ======================================================================

    def get_center_of_mass(self) -> List[float]:
        """
        Calculate center of mass of the molecule with caching.

        Computes weighted average of atomic positions using atomic masses.
        Result is cached for performance - invalidated when structure changes.

        Returns:
            Center of mass coordinates as [x, y, z] in Angstroms.

        Examples:
            >>> molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
            >>> com = molecule.get_center_of_mass()
            >>> print(com)  # Weighted average based on C and O masses
        """
        if self._cached_com is None:
            # Use .elements for better performance
            masses = np.array([elem.atomic_mass for elem in self.elements])
            total_mass = np.sum(masses)
            if total_mass == 0:
                raise ValueError("Cannot compute center of mass for molecule with only zero-mass species")
            center_of_mass = np.average(self.positions, weights=masses, axis=0)
            self._cached_com = center_of_mass.tolist()
        return list(self._cached_com)

    def translate(self, vector: List[float]) -> "Molecule":
        """
        Translate the molecule by a given vector.

        Moves all atoms by the specified translation vector.
        Returns a new molecule; the original is not modified.

        Args:
            vector: Translation vector [dx, dy, dz] in Angstroms.

        Returns:
            Molecule: Translated molecule.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> translated = molecule.translate([1.0, 0.0, 0.0])
            >>> translated.positions[0]
            array([1., 0., 0.])
        """
        vec = np.asarray(vector)
        if vec.shape != (3,) or vec.dtype == bool or not np.issubdtype(vec.dtype, np.number):
            raise ValueError(f"vector must be 3 numbers, got {vector!r}")
        vec = vec.astype(np.float64)
        if not np.all(np.isfinite(vec)):
            raise ValueError(f"vector must be finite, got {vector!r}")
        new_positions = self.positions + vec
        return self.__class__._construct(
            species=tuple(self.species),
            positions=new_positions,
            **self._construct_kwargs(),
        )

    def rotate(self, angle: float, axis: List[float]) -> "Molecule":
        """
        Rotate the molecule around an axis.

        Rotates all atoms around the specified axis by the given angle.
        The rotation axis is automatically normalized.
        Returns a new molecule; the original is not modified.

        Args:
            angle: Rotation angle in degrees.
            axis: Rotation axis vector [x, y, z] (will be normalized automatically).

        Returns:
            Molecule: Rotated molecule.

        Note:
            Uses scipy.spatial.transform.Rotation for rotation.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> rotated = molecule.rotate(90, [0, 0, 1])  # 90° rotation around z-axis
            >>> rotated.positions[1]  # H atom rotated
            array([0., 0.96, 0.])
        """
        from scipy.spatial.transform import Rotation

        axis_arr = np.array(axis, dtype=np.float64)
        axis_norm = np.linalg.norm(axis_arr)
        if axis_norm == 0:
            raise ValueError("Rotation axis cannot be zero vector")
        rotation = Rotation.from_rotvec(np.radians(angle) * (axis_arr / axis_norm))
        # Copy to a writeable array; older scipy versions reject read-only buffers
        # even though Rotation.apply() only reads from the input.
        new_positions = rotation.apply(np.array(self.positions))
        return self.__class__._construct(
            species=tuple(self.species),
            positions=new_positions,
            **self._construct_kwargs(),
        )

    # ======================================================================
    # Structure editing (immutable: returns new instances)
    # ======================================================================

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert molecule to dictionary representation for serialization.

        Implements the MSONable interface for JSON serialization.
        The dictionary includes module and class information for proper
        deserialization.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - @module: Module path of the class
                - @class: Class name ('Molecule')
                - species: List of species symbols
                - positions: List of positions (converted from numpy array)
                - site_properties: List of site property dictionaries (if any)

        Example:
            >>> d = molecule.as_dict()
            >>> d['@class']
            'Molecule'
            >>> d['species']
            ['O', 'H', 'H']
            >>> d['positions']
            [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]]
        """
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": self.species,
            "positions": self.positions.tolist(),
        }
        d.update(self._site_properties_dict())
        d.update(self._metadata_dict())
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Molecule":
        """
        Create Molecule object from dictionary representation.

        Implements the MSONable interface for JSON deserialization.
        Restores a Molecule object from its dictionary representation.

        Args:
            d: Dictionary containing:
                - species: List of species symbols
                - positions: List of positions
                - site_properties: Optional list of site property dictionaries

        Returns:
            Molecule: A new Molecule instance.

        Raises:
            KeyError: If required keys ('species', 'positions') are missing.
            ValueError: If species and positions have different lengths.

        Example:
            >>> d = {
            ...     '@module': 'matsimpy.core.molecule',
            ...     '@class': 'Molecule',
            ...     'species': ['O', 'H', 'H'],
            ...     'positions': [[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]],
            ...     'site_properties': [{'charge': -2}, {'charge': 1}, {'charge': 1}]
            ... }
            >>> molecule = Molecule.from_dict(d)
            >>> molecule.formula
            'H2O'
        """
        species = d["species"]
        positions = d["positions"]
        site_properties = cls._site_properties_from_dict(d)
        return cls(species, positions, site_properties=site_properties, metadata=cls._metadata_from_dict(d))

    # ======================================================================
    # Conversion helpers
    # ======================================================================

    def to_crystal(self, vacuum: float = 15.0) -> "Crystal":
        """
        Convert a Molecule to a Crystal structure by automatically creating a box
        with vacuum padding around the molecule.

        The resulting Crystal has PBC set to [False, False, False] since molecules
        are non-periodic structures. This is important for correct behavior in
        calculations and neighbor finding.

        Args:
            vacuum (float): Vacuum padding in Angstroms to add around the molecule.
                           Default is 15.0 Å.

        Returns:
            Crystal: The Crystal structure with the molecule centered in a cubic box.
                    PBC is set to [False, False, False] to indicate non-periodic structure.

        Examples:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> crystal = molecule.to_crystal()
            >>> print(crystal.pbc)  # [False, False, False]
            >>> # Use custom vacuum padding
            >>> crystal = molecule.to_crystal(vacuum=20.0)
        """
        from .crystal import Crystal

        if len(self.positions) == 0:
            raise ValueError("Cannot convert empty molecule to crystal")
        if isinstance(vacuum, bool) or not isinstance(vacuum, (int, float, np.integer, np.floating)):
            raise TypeError(f"vacuum must be a number, got {type(vacuum).__name__}")
        vacuum = float(vacuum)
        if not np.isfinite(vacuum) or vacuum < 0:
            raise ValueError(f"vacuum must be finite and non-negative, got {vacuum}")

        # Calculate bounding box of the molecule
        positions = np.array(self.positions)
        min_coords = np.min(positions, axis=0)
        max_coords = np.max(positions, axis=0)

        # Calculate the size needed for the box (including vacuum padding)
        box_size = (max_coords - min_coords) + 2 * vacuum

        # Ensure minimum box size (in case molecule is a single atom or very small)
        min_box_size = 2 * vacuum
        box_size = np.maximum(box_size, min_box_size)

        # Center the molecule in the box
        # Shift positions so that the bounding box is centered at origin
        center_offset = (min_coords + max_coords) / 2
        centered_positions = positions - center_offset

        # Shift to center of box (add half the box size)
        centered_positions = centered_positions + box_size / 2

        # Create cubic lattice vectors
        lattice_vectors = [
            [box_size[0], 0.0, 0.0],
            [0.0, box_size[1], 0.0],
            [0.0, 0.0, box_size[2]],
        ]

        # Create Crystal with Cartesian coordinates
        # Set PBC to [False, False, False] since molecules are non-periodic
        crystal = Crystal(
            list(self.species),
            centered_positions.tolist(),
            Lattice(lattice_vectors),
            coords_are_cartesian=True,
            pbc=[False, False, False],  # Molecules are non-periodic
            site_properties=list(self.site_properties) or None,
        )

        return crystal

    def _summary_lines(self) -> List[str]:
        try:
            com = self.get_center_of_mass()
        except (ValueError, AttributeError):
            return []
        return [f"  Center of mass: ({com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f}) Å"]

    def __repr__(self) -> str:
        """
        Get unambiguous string representation of Molecule for debugging.

        Returns:
            str: Compact representation with formula and number of sites.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> repr(molecule)
            "Molecule(formula='H2O', nsites=3)"
        """
        # Compact representation with key info
        return (
            f"{self.__class__.__name__}(formula='{self.formula}', "
            f"nsites={len(self)})"
        )

    def get_moment_of_inertia(self) -> np.ndarray:
        """
        Calculate the moment of inertia tensor around the center of mass.

        Computes the 3x3 moment of inertia tensor for the molecule, calculated
        with respect to the center of mass. This is useful for rotational
        dynamics and spectroscopy calculations.

        Returns:
            np.ndarray: The moment of inertia tensor as a 3x3 numpy array.
                      Units are in atomic mass units × Angstrom² (amu·Å²).

        Note:
            The tensor is symmetric and calculated with respect to the center
            of mass. Diagonal elements represent moments of inertia about
            principal axes, off-diagonal elements represent products of inertia.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> I = molecule.get_moment_of_inertia()
            >>> I.shape
            (3, 3)
            >>> I[0, 0]  # Moment of inertia about x-axis
            1.234...
        """
        masses = np.array([elem.atomic_mass for elem in self.elements])
        total_mass = np.sum(masses)
        if total_mass == 0:
            raise ValueError("Cannot compute moment of inertia for molecule with only zero-mass species")
        com = self.get_center_of_mass()
        positions = self.positions - com
        moment_tensor = np.zeros((3, 3))
        for i in range(len(self.species)):
            r = positions[i]
            moment_tensor[0, 0] += masses[i] * (r[1] ** 2 + r[2] ** 2)
            moment_tensor[1, 1] += masses[i] * (r[0] ** 2 + r[2] ** 2)
            moment_tensor[2, 2] += masses[i] * (r[0] ** 2 + r[1] ** 2)
            moment_tensor[0, 1] -= masses[i] * r[0] * r[1]
            moment_tensor[0, 2] -= masses[i] * r[0] * r[2]
            moment_tensor[1, 2] -= masses[i] * r[1] * r[2]
            moment_tensor[1, 0] = moment_tensor[0, 1]
            moment_tensor[2, 0] = moment_tensor[0, 2]
            moment_tensor[2, 1] = moment_tensor[1, 2]
        # eigenvalues, eigenvectors = np.linalg.eigh(moment_tensor)
        return moment_tensor

    def get_neighbor_list(
        self, cutoff: float, atom_index: Optional[int] = None, **kwargs
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Get neighbor list with consistent interface.

        Args:
            cutoff: Cutoff radius in Angstroms.
            atom_index: Optional atom index. If None, returns neighbors for all atoms.
                       If specified, returns neighbors only for that atom.
            **kwargs: Ignored (for compatibility with Crystal interface)

        Returns:
            Dict mapping atom index to list of (neighbor_index, distance) tuples.
            If atom_index is provided, dict contains only that entry.
            If atom_index is None, dict contains entries for all atoms.

        Raises:
            IndexError: If atom_index is out of range.

        Examples:
            >>> molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
            >>> # Get neighbors for specific atom
            >>> neighbors = molecule.get_neighbor_list(2.0, atom_index=0)
            >>> print(neighbors)  # {0: [(1, 1.2)]} - atom 1 is within 2.0 Å
            >>> # Get neighbors for all atoms
            >>> all_neighbors = molecule.get_neighbor_list(2.0)
            >>> print(all_neighbors)  # {0: [(1, 1.2)], 1: [(0, 1.2)]}
        """
        n_atoms = len(self.positions)
        from ._validation import validate_cutoff
        validate_cutoff(cutoff)
        if atom_index is not None:
            if not (0 <= atom_index < n_atoms):
                raise IndexError(
                    f"Atom index {atom_index} is out of range [0, {n_atoms-1}]"
                )

        # Build KDTree once (O(n log n)) and query neighbors efficiently.
        positions = self.positions
        tree = cKDTree(positions)

        neighbors_dict: Dict[int, List[Tuple[int, float]]] = {}
        atoms_to_query = [atom_index] if atom_index is not None else range(n_atoms)
        for i in atoms_to_query:
            idxs = tree.query_ball_point(positions[i], cutoff)
            # Exclude self and compute exact distances only for candidates.
            neigh: List[Tuple[int, float]] = []
            for j in idxs:
                if j == i:
                    continue
                dist = float(np.linalg.norm(positions[i] - positions[j]))
                neigh.append((j, dist))
            neighbors_dict[i] = neigh

        return neighbors_dict

    def get_all_neighbor_lists(self, cutoff: float) -> List[List[int]]:
        """
        Get neighbor lists for all atoms using vectorized operations.

        Optimized implementation using distance matrix and vectorization
        instead of loop-based approach. Much faster for large molecules.

        Args:
            cutoff: Cutoff radius in Angstroms.

        Returns:
            List of neighbor lists for all atoms. Each inner list contains
            indices of neighbors within cutoff distance of that atom.

        Raises:
            ValueError: If cutoff is negative.

        Examples:
            >>> molecule = Molecule(['C', 'O', 'H'], [[0,0,0], [1.2,0,0], [2.5,0,0]])
            >>> all_neighbors = molecule.get_all_neighbor_lists(2.0)
            >>> print(all_neighbors)  # [[1], [0], []]

        Notes:
            - Uses vectorized operations for better performance
            - Time complexity: O(n²) for distance matrix, but vectorized
            - Memory complexity: O(n²) for distance matrix
            - For n > 1000 atoms, consider using spatial trees
        """
        from ._validation import validate_cutoff
        cutoff = validate_cutoff(cutoff)

        if len(self.positions) == 0:
            return []

        # Use vectorized operations for performance
        positions = np.array(self.positions)

        # Compute all pairwise distances at once
        distance_matrix = cdist(positions, positions)

        # Ignore self-distances by setting diagonal to infinity
        np.fill_diagonal(distance_matrix, np.inf)

        # Find neighbors using vectorized operations
        neighbor_lists = []
        for i in range(len(positions)):
            # Use boolean mask for efficient filtering
            mask = distance_matrix[i] <= cutoff
            neighbors = np.where(mask)[0].tolist()
            neighbor_lists.append(neighbors)

        return neighbor_lists


