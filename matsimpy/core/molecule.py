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

import copy
import numpy as np
import warnings
from typing import List, Optional, Dict, Any, Union, Tuple, TYPE_CHECKING
from monty.json import MSONable
from .lattice import Lattice
from .structure import Structure
from .composition import Composition
from .periodic_table import Element
from .site import Site
from ._validation import normalize_species, validate_site_properties
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist

if TYPE_CHECKING:
    from ..analysis.selection import AtomSelection
    from ..calculator.base import Calculator
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

    @classmethod
    def _construct(
        cls,
        species: Tuple[str, ...],
        positions: np.ndarray,
        lattice: Optional[Lattice] = None,
        site_properties: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> "Molecule":
        """
        Internal lightweight constructor.

        ``positions`` must be Cartesian coordinates (this matches the internal
        ``Structure._positions`` convention for Molecule).
        """
        obj = cls.__new__(cls)
        obj._species = tuple(normalize_species(s) for s in species)
        obj._positions = np.array(positions, dtype=np.float64, copy=True)
        if obj._positions.ndim != 2 or obj._positions.shape[1] != 3:
            raise ValueError("positions must have shape (n_atoms, 3)")
        obj._positions.flags.writeable = False
        obj.lattice = lattice
        obj._composition = None
        obj._formula = None

        obj._site_properties = validate_site_properties(site_properties, len(obj._species))
        obj._sites = None  # lazy — populated on first .sites access
        obj._cached_com = None
        return obj

    def _construct_kwargs(self) -> Dict[str, Any]:
        return {
            "site_properties": self.site_properties if self.site_properties else None,
        }

    def __init__(
        self,
        species: List[str],
        positions: List[List[float]],
        site_properties: Optional[List[Dict[str, Any]]] = None,
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
        super().__init__(species, positions, None)
        self._site_properties: Tuple[Dict[str, Any], ...] = validate_site_properties(
            site_properties, len(self.species)
        )
        self._sites = self._initialize_sites()
        self._cached_com: Optional[List[float]] = None

    @classmethod
    def from_file(
        cls, filename: str, format: Optional[str] = None, **kwargs
    ) -> "Molecule":
        """Read a molecule from a file, rejecting crystal-only results."""
        from matsimpy.exceptions import StructureTypeError
        from matsimpy.io import read_file

        structure = read_file(filename, format=format, **kwargs)
        if not isinstance(structure, cls):
            raise StructureTypeError(
                f"Expected {cls.__name__} from {filename!r}, got "
                f"{type(structure).__name__}."
            )
        return structure

    @property
    def site_properties(self) -> Tuple[Dict[str, Any], ...]:
        """Per-site metadata as deep-copied dictionaries."""
        return tuple(copy.deepcopy(p) for p in self._site_properties)

    @site_properties.setter
    def site_properties(self, site_properties: Optional[List[Dict[str, Any]]]) -> None:
        self._site_properties = validate_site_properties(site_properties, len(self.species))

    def _initialize_sites(self) -> List[Site]:
        """
        Initialize the list of Site objects.

        Creates Site objects for each atom, optionally including site properties.
        This method is called during initialization and when atoms are added/removed.

        Returns:
            List[Site]: A list of Site objects, one for each atom.

        Note:
            This is an internal method. Sites are automatically updated when
            the structure changes (add_atom, remove_atom, etc.).
        """
        if self.site_properties and len(self.site_properties) == len(self.species):
            return [
                Site(position=pos, specie=spec, properties=props)
                for pos, spec, props in zip(
                    self.positions, self.species, self.site_properties
                )
            ]
        else:
            return [
                Site(position=pos, specie=spec)
                for pos, spec in zip(self.positions, self.species)
            ]

    # ======================================================================
    # Subclass extension hooks / extra serialisation fields
    # ======================================================================

    def _extra_dict_fields(self) -> Dict[str, Any]:
        if self.site_properties:
            return {"site_properties": list(self.site_properties)}
        return {}

    # ----------------------------------------------------------------------
    # Per-atom metadata adjustment hooks (Structure base helpers)
    # ----------------------------------------------------------------------

    def _filter_per_atom_data(self, kept_indices: List[int]) -> Dict[str, Any]:
        """Return site_properties filtered to kept_indices after atom removal."""
        if not self.site_properties:
            return {}
        return {"site_properties": [self.site_properties[i] for i in kept_indices]}

    def _reorder_per_atom_data(self, new_order: List[int]) -> Dict[str, Any]:
        """Return site_properties reordered to new_order after atom sorting."""
        if not self.site_properties:
            return {}
        return {"site_properties": [self.site_properties[i] for i in new_order]}

    # ======================================================================
    # Sites / indexing
    # ======================================================================

    def _site_snapshot(self, index: int) -> Site:
        """Return a detached Site snapshot for one atom."""
        if self._sites is None:
            self._sites = self._initialize_sites()
        site = self._sites[index]
        return Site(
            position=site.position,
            specie=site.specie,
            properties=site.properties,
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
        if self._sites is None:
            self._sites = self._initialize_sites()
        return tuple(self._site_snapshot(i) for i in range(len(self._sites)))

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
        return self._site_snapshot(item)

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
        new_positions = self.positions + np.array(vector)
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

    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
        site_properties: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    ) -> "Molecule":
        """
        Add one or more atoms to the molecule and return a new Molecule.

        Performs chemical reasonableness checks on interatomic distances.
        Prevents adding duplicate atoms at the same position or atoms that are too close.
        The original molecule is not modified.

        Args:
            species: Atomic species (single string or list of strings).
            position: Atomic position(s). Either a single 3D coordinate or list of coordinates.
            site_properties: Optional site properties (single dict or list of dicts).
                           If list, must match length of species.

        Returns:
            Molecule: New molecule with the added atom(s).

        Raises:
            ValueError: If site_properties length doesn't match number of atoms added.
            ValueError: If duplicate positions are detected (distance < 1e-6 Angstrom).
            ValueError: If atoms are too close (distance < 0.5 Angstrom).

        Examples:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> new_mol = molecule.add_atom('H', [2.0, 0, 0])  # Add single atom
            >>> new_mol = molecule.add_atom(['H', 'O'], [[2.0, 0, 0], [3.0, 0, 0]])  # Add multiple
            >>> new_mol = molecule.add_atom(['H', 'O'], [[2.0, 0, 0], [3.0, 0, 0]],
            ...                             [{'charge': 1}, {'charge': -2}])  # With properties
        """
        # Parse position input
        if isinstance(position, np.ndarray):
            if position.ndim == 1:
                new_positions = [position.tolist()]
            else:
                new_positions = position.tolist()
        elif isinstance(position, list):
            if len(position) == 0:
                new_positions = []
            elif isinstance(position[0], (int, float)):
                new_positions = [position]
            else:
                new_positions = position
        else:
            new_positions = [position]

        # Validate that all positions are 3D
        for idx, pos in enumerate(new_positions):
            if not isinstance(pos, (list, tuple, np.ndarray)) or len(pos) != 3:
                raise ValueError(
                    f"Each position must be a 3D coordinate [x, y, z], "
                    f"got {pos} at index {idx}."
                )

        # Check for duplicates within new positions
        if len(new_positions) > 1:
            new_positions_array = np.array(new_positions, dtype=np.float64)
            for i in range(len(new_positions_array)):
                for j in range(i + 1, len(new_positions_array)):
                    dist = np.linalg.norm(new_positions_array[i] - new_positions_array[j])
                    if dist < 1e-6:
                        raise ValueError(
                            f"Duplicate positions detected in new atoms: "
                            f"positions {i} and {j} are at the same location "
                            f"({new_positions[i]})."
                        )
                    elif dist < 0.5:
                        raise ValueError(
                            f"Atoms being added are too close: distance between "
                            f"positions {i} and {j} is {dist:.6f} Angstrom. "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )

        # Check each new position against existing atoms
        if len(self.positions) > 0:
            for idx, new_pos in enumerate(new_positions):
                if len(new_pos) == 3:
                    new_pos_array = np.array(new_pos, dtype=np.float64).reshape(1, 3)
                    min_distance = np.min(cdist(new_pos_array, self.positions))
                    if min_distance < 1e-6:
                        raise ValueError(
                            f"Cannot add atom at position {new_pos}: "
                            f"atom already exists at this location "
                            f"(distance: {min_distance:.6f} Angstrom)."
                        )
                    elif min_distance < 0.5:
                        raise ValueError(
                            f"Cannot add atom at position {new_pos}: "
                            f"too close to existing atom "
                            f"(distance: {min_distance:.6f} Angstrom). "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )

        # Normalize species
        if isinstance(species, str):
            species_list = [species]
        else:
            species_list = list(species)

        if len(species_list) != len(new_positions):
            raise ValueError(
                f"Number of species ({len(species_list)}) must match "
                f"number of positions ({len(new_positions)})"
            )

        if not species_list:
            return self.copy()

        new_species = list(self.species) + species_list
        new_positions_arr = (
            np.vstack([self.positions, np.array(new_positions, dtype=np.float64)])
            if new_positions
            else self.positions.copy()
        )

        n_atoms_before = len(self.species)
        n_atoms_added = len(new_species) - n_atoms_before

        # Handle site_properties
        new_site_props = list(self.site_properties) if self.site_properties else []
        if site_properties is not None:
            if isinstance(site_properties, dict):
                # Deep-copy so each atom gets an independent dict; a shallow
                # list-multiply would share one dict object across all entries.
                site_properties_list = [
                    copy.deepcopy(site_properties) for _ in range(n_atoms_added)
                ]
            else:
                site_properties_list = list(site_properties)
            if len(site_properties_list) != n_atoms_added:
                raise ValueError(
                    f"Number of site_properties ({len(site_properties_list)}) "
                    f"must match number of atoms added ({n_atoms_added})"
                )
            if not new_site_props:
                new_site_props = [{} for _ in range(n_atoms_before)]
            new_site_props.extend(site_properties_list)
        elif new_site_props:
            new_site_props.extend({} for _ in range(n_atoms_added))

        return self.__class__._construct(
            species=tuple(new_species),
            positions=new_positions_arr,
            site_properties=new_site_props if new_site_props else None,
        )

    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> "Molecule":
        """
        Substitute atoms with new species and return a new Molecule.

        The original molecule is not modified.

        Args:
            indices: Atom index, list of indices, or AtomSelection object to substitute
            new_species: New species symbol, list of symbols, or dict mapping old->new species

        Returns:
            Molecule: New molecule with the substituted species.

        Raises:
            IndexError: If index is out of range
            ValueError: If number of indices doesn't match number of species
            KeyError: If dict mapping doesn't contain a species

        Examples:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> new_mol = molecule.substitute(0, 'N')  # Substitute atom at index 0
            >>> new_mol = molecule.substitute([0, 1], ['N', 'O'])  # Substitute multiple
            >>> # Using AtomSelection
            >>> from matsimpy.analysis.selection import AtomSelection
            >>> sel = AtomSelection(molecule).by_species('H')
            >>> new_mol = molecule.substitute(sel, 'N')  # Substitute selected atoms
            >>> # Using dict mapping (maps old species to new species)
            >>> new_mol = molecule.substitute([0, 1, 2], {'H': 'F', 'O': 'S'})
        """
        from ..analysis.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        indices = self._validate_atom_indices(indices)

        if isinstance(new_species, dict):
            new_species_list = []
            for idx in indices:
                old_spec = self.species[idx]
                if old_spec not in new_species:
                    raise KeyError(
                        f"Species '{old_spec}' at index {idx} not found in substitution mapping"
                    )
                new_species_list.append(new_species[old_spec])
            new_species = new_species_list

        if isinstance(new_species, str):
            new_species = [new_species] * len(indices)

        if len(indices) != len(new_species):
            raise ValueError(
                f"Number of indices ({len(indices)}) must match number of new species ({len(new_species)})"
            )

        species_list = list(self.species)
        for idx, new_spec in zip(indices, new_species):
            species_list[idx] = new_spec

        return self.__class__._construct(
            species=tuple(species_list),
            positions=self._positions,
            **self._construct_kwargs(),
        )

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
        if self.site_properties:
            d["site_properties"] = list(self.site_properties)
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
        site_properties = d.get("site_properties", [])
        return cls(species, positions, site_properties=site_properties)

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
        )

        return crystal

    def __str__(self) -> str:
        """
        Get human-readable string representation of Molecule.

        Returns a formatted string with molecule information including:
        - Formula
        - Number of atoms
        - Center of mass
        - Table of atoms with coordinates and properties

        Returns:
            str: Formatted string representation of the molecule.

        Note:
            Atoms are displayed in their original insertion order to match
            the internal structure (species, positions). Use sort_atoms() if you
            want to actually reorder the internal data.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> print(molecule)
            Molecule: H2O
              Sites: 3 atoms
              Center of mass: (0.1234, 0.1234, 0.0000) Å
            Element  Cartesian Coordinates
            O        (0.0000, 0.0000, 0.0000)
            H        (0.9600, 0.0000, 0.0000)
            H        (-0.2400, 0.9300, 0.0000)
        """
        from tabulate import tabulate

        info = f"{self.__class__.__name__}: {self.formula}\n"
        info += f"  Sites: {len(self)} atoms\n"

        # Center of mass
        try:
            com = self.get_center_of_mass()
            info += f"  Center of mass: ({com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f}) Å\n"
        except (ValueError, AttributeError):
            info += "\n"

        # Atom coordinates and properties table
        has_properties = any(site.properties for site in self.sites)
        headers = ["Element", "Cartesian Coordinates"]
        if has_properties:
            headers.append("Properties")

        # Display sites in insertion order to match internal species ordering
        display_sites = list(self.sites)

        rows = []
        for site in display_sites:
            element = str(site.specie)
            cart_coords = f"({site.position[0]:.4f}, {site.position[1]:.4f}, {site.position[2]:.4f})"
            row = [element, cart_coords]
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
        from ..analysis.neighbors import validate_cutoff
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
        if cutoff < 0:
            raise ValueError(f"Cutoff must be non-negative, got {cutoff}")

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
            mask = distance_matrix[i] < cutoff
            neighbors = np.where(mask)[0].tolist()
            neighbor_lists.append(neighbors)

        return neighbor_lists


    def to_pymatgen(self):
        """
        Convert Molecule to pymatgen Molecule.

        Returns:
            pymatgen.core.structure.Molecule: pymatgen Molecule object

        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io import to_pymatgen

        return to_pymatgen(self)

    def to_ase(self):
        """
        Convert Molecule to ASE Atoms.

        Returns:
            ase.Atoms: ASE Atoms object

        Raises:
            ImportError: If ASE is not installed
        """
        from ..io import to_ase

        return to_ase(self)

    @classmethod
    def from_pymatgen(cls, pymatgen_molecule):
        """
        Create Molecule from pymatgen Molecule.

        Args:
            pymatgen_molecule: pymatgen.core.structure.Molecule object

        Returns:
            Molecule: MatSimPy Molecule object

        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io import from_pymatgen

        return from_pymatgen(pymatgen_molecule)

    @classmethod
    def from_ase(cls, ase_atoms):
        """
        Create Molecule from ASE Atoms.

        Args:
            ase_atoms: ase.Atoms object (without cell or with cell=False)

        Returns:
            Molecule: MatSimPy Molecule object

        Raises:
            ImportError: If ASE is not installed
        """
        from ..io import from_ase

        result = from_ase(ase_atoms)
        if not isinstance(result, Molecule):
            raise ValueError(
                "Molecule.from_ase() requires non-periodic ASE Atoms (no cell/PBC). "
                f"Got {type(result).__name__} instead. "
                "Use Crystal.from_ase() for periodic structures."
            )
        return result

    def to_code(self, code: str, filename: str, **kwargs) -> None:
        """
        Write input file for a supported DFT code.

        Generic interface for writing supported DFT code input files through
        the code parameter. Molecules are typically treated as isolated systems
        in a large cell.

        Args:
            code: DFT code name (for example, 'vasp')
            filename: Output filename
            **kwargs: Additional parameters for the DFT code input
                     (code-specific parameters)

        Raises:
            ValueError: If code is not supported
            NotImplementedError: If code interface is not yet implemented

        Examples:
            >>> molecule.to_code('vasp', 'POSCAR')
        """
        from ..code import get_code_interface

        try:
            interface = get_code_interface(code)
            write_input = interface["write_input"]
            write_input(self, filename, **kwargs)
        except ValueError as e:
            raise ValueError(f"Unsupported DFT code: {code}") from e

    @classmethod
    def from_code(cls, code: str, filename: str, **kwargs) -> "Molecule":
        """
        Read structure from DFT code output file.

        Generic interface for reading structures from DFT code output files.
        Currently not implemented.

        Args:
            code: DFT code name (for example, 'vasp')
            filename: Path to output file
            **kwargs: Additional parameters for parsing

        Returns:
            Molecule: Molecule structure from the output file

        Raises:
            ValueError: If code is not supported
            NotImplementedError: Output parsing not yet implemented

        Examples:
            >>> molecule = Molecule.from_code('vasp', 'OUTCAR')
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

    def perturb(
        self,
        amplitude: float,
        indices: Optional[Union[List[int], "AtomSelection"]] = None,
        seed: Optional[int] = None,
    ) -> "Molecule":
        """
        Add random perturbations to atomic positions.

        Returns a new molecule with perturbed positions; the original is not modified.

        Args:
            amplitude: Maximum perturbation amplitude (Angstroms)
            indices: Atom indices to perturb (default: all atoms).
                    Can be a list of indices or an AtomSelection object.
            seed: Random seed for reproducibility

        Returns:
            Molecule: New molecule with perturbed positions.

        Examples:
            >>> from matsimpy.core import Molecule
            >>> from matsimpy.analysis.selection import AtomSelection
            >>> molecule = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> # Perturb all atoms by up to 0.1 Angstrom
            >>> perturbed = molecule.perturb(0.1)
            >>> # Perturb specific atoms
            >>> perturbed = molecule.perturb(0.1, indices=[0, 1])
            >>> # Perturb using AtomSelection
            >>> sel = AtomSelection(molecule).by_species('H')
            >>> perturbed = molecule.perturb(0.1, indices=sel)
        """
        from ..analysis.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        from ..transformation.atomic import perturb_positions
        return perturb_positions(self, amplitude, indices=indices, seed=seed)
