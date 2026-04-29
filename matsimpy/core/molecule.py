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
    >>> molecule.to_file('molecule.xyz')
    >>> molecule2 = Molecule.from_file('molecule.xyz')
"""

import numpy as np
import warnings
from typing import List, Optional, Dict, Any, Union, Tuple, TYPE_CHECKING
from monty.json import MSONable
from .lattice import Lattice
from .structure import Structure
from .crystal import Crystal
from .composition import Composition
from .periodic_table import Element
from .site import Site
from scipy.spatial.distance import cdist

if TYPE_CHECKING:
    from ..utils.selection import AtomSelection
    from ..calculator.base import Calculator


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
        self.site_properties = site_properties or []  # Make public for consistency
        self._sites = self._initialize_sites()

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

    @property
    def sites(self) -> List[Site]:
        """
        Get the list of Site objects for all atoms.

        Returns:
            List[Site]: List of Site objects, one for each atom in the molecule.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> molecule.sites[0].specie  # 'O'
            >>> molecule.sites[0].position  # [0, 0, 0]
            >>> len(molecule.sites)
            3
        """
        return self._sites

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
        return self.sites[item]

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
        if not hasattr(self, "_cached_com") or self._cached_com is None:
            # Use .elements for better performance
            masses = np.array([elem.atomic_mass for elem in self.elements])
            center_of_mass = np.average(self.positions, weights=masses, axis=0)
            self._cached_com = center_of_mass.tolist()
        return self._cached_com

    def translate(self, vector: List[float], inplace: bool = False) -> "Molecule":
        """
        Translate the molecule by a given vector.

        Moves all atoms by the specified translation vector. By default,
        returns a new molecule. Set inplace=True to modify in-place.

        Args:
            vector: Translation vector [dx, dy, dz] in Angstroms.
            inplace: If True, modify this molecule in-place (default: False).
                    If False, return a new Molecule object.

        Returns:
            Molecule: Translated molecule. If inplace=True, returns self.
                    If inplace=False, returns a new Molecule object.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> # Return new molecule (default)
            >>> translated = molecule.translate([1.0, 0.0, 0.0])
            >>> translated.positions[0]
            array([1., 0., 0.])
            >>> # Modify in-place
            >>> molecule.translate([1.0, 0.0, 0.0], inplace=True)
            >>> molecule.positions[0]
            array([1., 0., 0.])
        """
        if inplace:
            self._check_frozen()
            self.positions += np.array(vector)
            # Invalidate center of mass cache
            if hasattr(self, "_cached_com"):
                self._cached_com = None
            # Update sites
            self._sites = self._initialize_sites()
            return self
        else:
            # Create new molecule with translated positions
            new_molecule = self.copy()
            new_molecule.positions += np.array(vector)
            # Invalidate center of mass cache
            if hasattr(new_molecule, "_cached_com"):
                new_molecule._cached_com = None
            # Update sites
            new_molecule._sites = new_molecule._initialize_sites()
            return new_molecule

    def rotate(self, angle: float, axis: List[float], inplace: bool = False) -> "Molecule":
        """
        Rotate the molecule around an axis.

        Rotates all atoms around the specified axis by the given angle.
        The rotation axis is automatically normalized. By default,
        returns a new molecule. Set inplace=True to modify in-place.

        Args:
            angle: Rotation angle in degrees.
            axis: Rotation axis vector [x, y, z] (will be normalized automatically).
            inplace: If True, modify this molecule in-place (default: False).
                    If False, return a new Molecule object.

        Returns:
            Molecule: Rotated molecule. If inplace=True, returns self.
                    If inplace=False, returns a new Molecule object.

        Note:
            Uses scipy.spatial.transform.Rotation for rotation.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> # Return new molecule (default)
            >>> rotated = molecule.rotate(90, [0, 0, 1])  # 90° rotation around z-axis
            >>> rotated.positions[1]  # H atom rotated
            array([0., 0.96, 0.])
            >>> # Modify in-place
            >>> molecule.rotate(90, [0, 0, 1], inplace=True)
            >>> molecule.positions[1]
            array([0., 0.96, 0.])
        """
        from scipy.spatial.transform import Rotation

        rotation = Rotation.from_rotvec(np.radians(angle) * np.array(axis))
        if inplace:
            self._check_frozen()
            self.positions = rotation.apply(self.positions)
            # Invalidate center of mass cache
            if hasattr(self, "_cached_com"):
                self._cached_com = None
            # Update sites
            self._sites = self._initialize_sites()
            return self
        else:
            # Create new molecule with rotated positions
            new_molecule = self.copy()
            new_molecule.positions = rotation.apply(new_molecule.positions)
            # Invalidate center of mass cache
            if hasattr(new_molecule, "_cached_com"):
                new_molecule._cached_com = None
            # Update sites
            new_molecule._sites = new_molecule._initialize_sites()
            return new_molecule

    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
        site_properties: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    ) -> None:
        """
        Add one or more atoms to the molecule and update sites.

        Performs chemical reasonableness checks on interatomic distances.
        Prevents adding duplicate atoms at the same position or atoms that are too close.

        Args:
            species: Atomic species (single string or list of strings).
            position: Atomic position(s). Either a single 3D coordinate or list of coordinates.
            site_properties: Optional site properties (single dict or list of dicts).
                           If list, must match length of species.

        Raises:
            ValueError: If site_properties length doesn't match number of atoms added.
            ValueError: If duplicate positions are detected (distance < 1e-6 Å).
            ValueError: If atoms are too close (distance < 0.5 Å).

        Examples:
            >>> molecule.add_atom('H', [0, 0, 0])  # Add single atom
            >>> molecule.add_atom(['H', 'O'], [[0, 0, 0], [1.2, 0, 0]])  # Add multiple
            >>> molecule.add_atom(['H', 'O'], [[0, 0, 0], [1.2, 0, 0]],
            ...                   [{'charge': 1}, {'charge': -2}])  # With properties
        """
        # Chemical reasonableness check - validate interatomic distances
        # Convert to array for processing
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

        # Check for duplicates within new positions
        if len(new_positions) > 1:
            new_positions_array = np.array(new_positions, dtype=np.float64)
            # Check pairwise distances within new positions
            for i in range(len(new_positions_array)):
                for j in range(i + 1, len(new_positions_array)):
                    dist = np.linalg.norm(
                        new_positions_array[i] - new_positions_array[j]
                    )
                    if dist < 1e-6:  # Essentially zero distance (duplicate)
                        raise ValueError(
                            f"Duplicate positions detected in new atoms: "
                            f"positions {i} and {j} are at the same location "
                            f"({new_positions[i]})."
                        )
                    elif dist < 0.5:  # Too close
                        raise ValueError(
                            f"Atoms being added are too close: distance between "
                            f"positions {i} and {j} is {dist:.6f} Å. "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )

        # Check each new position against existing atoms
        if len(self.positions) > 0:
            for idx, new_pos in enumerate(new_positions):
                if len(new_pos) == 3:  # Valid 3D position
                    new_pos_array = np.array(new_pos, dtype=np.float64).reshape(1, 3)
                    min_distance = np.min(cdist(new_pos_array, self.positions))

                    # Raise error for duplicates or too close
                    if min_distance < 1e-6:  # Essentially zero distance (duplicate)
                        raise ValueError(
                            f"Cannot add atom at position {new_pos}: atom already exists "
                            f"at this location (distance: {min_distance:.6f} Å)."
                        )
                    elif min_distance < 0.5:  # Too close
                        raise ValueError(
                            f"Cannot add atom at position {new_pos}: too close to existing "
                            f"atom (distance: {min_distance:.6f} Å). "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )

        # Determine number of atoms being added.  From this point on we may
        # mutate state, so keep a rollback snapshot in case validation of
        # site_properties fails after the parent mutation.
        n_atoms_before = len(self.species)
        old_species = self.species
        old_positions = self.positions.copy()
        old_sites = self._sites.copy()
        old_site_properties = self.site_properties.copy() if self.site_properties else []
        old_formula_dirty = self._formula_dirty
        old_cached_composition = self._cached_composition
        old_cached_formula = self._cached_formula
        old_cached_com = getattr(self, "_cached_com", None)
        try:
            self._check_frozen()
            # Call parent to add atoms
            super().add_atom(species, position)

            n_atoms_added = len(self.species) - n_atoms_before

            # Invalidate center of mass cache
            if hasattr(self, "_cached_com"):
                self._cached_com = None

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
            self.species = old_species
            self.positions = old_positions
            self._sites = old_sites
            self.site_properties = old_site_properties
            self._formula_dirty = old_formula_dirty
            self._cached_composition = old_cached_composition
            self._cached_formula = old_cached_formula
            if hasattr(self, "_cached_com"):
                self._cached_com = old_cached_com
            raise

    def remove_atom(self, indices: Union[int, List[int], "AtomSelection"]) -> None:
        """
        Remove one or more atoms from the molecule (in-place).

        Removes atoms by index and updates sites and cached properties.
        If multiple indices are provided, atoms are removed in reverse order
        to avoid index shifting issues.

        Args:
            indices: Atom index, list of indices, or :class:`~matsimpy.utils.selection.AtomSelection`
                    object to remove. If list, atoms are removed in reverse order
                    to avoid index shifting.

        Raises:
            IndexError: If any index is out of range.
            ValueError: If AtomSelection is from a different structure.
            TypeError: If indices is not int, list, or AtomSelection.

        Note:
            This method modifies the molecule in-place. Cached properties
            (formula, composition, center of mass) are invalidated and will
            be recalculated on next access.

        Example:
            >>> molecule = Molecule(['O', 'H', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> molecule.remove_atom(0)  # Remove atom at index 0 (O)
            >>> molecule.formula  # 'H2'
            >>>
            >>> # Remove multiple atoms
            >>> molecule.remove_atom([0, 1])  # Remove first two atoms
            >>>
            >>> # Using AtomSelection
            >>> from matsimpy.utils.selection import AtomSelection
            >>> sel = AtomSelection(molecule).by_species('H')
            >>> molecule.remove_atom(sel)  # Remove all H atoms
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

        # Reinitialize sites (only once after all removals)
        self._sites = self._initialize_sites()
        if hasattr(self, "_cached_com"):
            self._cached_com = None

    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> None:
        """
        Substitute atoms with new species.

        This is a common operation for modifying molecules. For functional
        style (returning new object), use matsimpy.transformation.substitute().

        Args:
            indices: Atom index, list of indices, or AtomSelection object to substitute
            new_species: New species symbol, list of symbols, or dict mapping old->new species

        Raises:
            IndexError: If index is out of range
            ValueError: If number of indices doesn't match number of species
            KeyError: If dict mapping doesn't contain a species

        Examples:
            >>> molecule.substitute(0, 'N')  # Substitute atom at index 0
            >>> molecule.substitute([0, 1], ['N', 'O'])  # Substitute multiple
            >>> # Using AtomSelection
            >>> from matsimpy.utils.selection import AtomSelection
            >>> sel = AtomSelection(molecule).by_species('C')
            >>> molecule.substitute(sel, 'N')  # Substitute selected atoms
            >>> # Using dict mapping (maps old species to new species)
            >>> molecule.substitute([0, 1, 2], {'C': 'N', 'O': 'S'})
        """
        # Call parent implementation to handle the actual substitution
        # and cache invalidation (formula, composition)
        super().substitute(indices, new_species)

        # Molecule-specific updates: reinitialize sites with updated species
        self._sites = self._initialize_sites()
        if hasattr(self, "_cached_com"):
            self._cached_com = None

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
            d["site_properties"] = self.site_properties
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

    def to_crystal(self, vacuum: float = 15.0) -> Crystal:
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
        if atom_index is not None:
            # Single atom query
            if not (0 <= atom_index < len(self)):
                raise IndexError(
                    f"Atom index {atom_index} is out of range [0, {len(self)-1}]"
                )

            distances = cdist([self.positions[atom_index]], self.positions)[0]
            neighbors = [
                (i, float(d))
                for i, d in enumerate(distances)
                if d < cutoff and i != atom_index
            ]
            return {atom_index: neighbors}
        else:
            # All atoms query
            distances = cdist(self.positions, self.positions)
            neighbors_dict = {}
            for i in range(len(self)):
                neighbors = [
                    (j, float(distances[i, j]))
                    for j in range(len(self))
                    if distances[i, j] < cutoff and j != i
                ]
                neighbors_dict[i] = neighbors
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

    @classmethod
    def from_file(
        cls, filename: str, format: Optional[str] = None, **kwargs
    ) -> "Molecule":
        """
        Create a Molecule from a file.

        Automatically detects file format from extension if not specified.
        Supported formats: .xyz, .pdb, .mol, .json

        This method uses the high-level read() interface. For more control,
        use matsimpy.io.read() directly.

        Args:
            filename: Path to the structure file
            format: Optional format specification (e.g., 'xyz', 'pdb').
                   If None, format is detected from file extension.
            **kwargs: Additional arguments passed to the format-specific reader
                     (e.g., as_crystal for PDB format)

        Returns:
            Molecule: Molecule structure from the file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is not supported or file format is invalid
            TypeError: If file contains a Crystal instead of Molecule

        Examples:
            >>> molecule = Molecule.from_file('molecule.xyz')
            >>> molecule = Molecule.from_file('molecule.pdb', as_crystal=False)
        """
        from ..io import read
        from ..core import Crystal

        result = read(filename, format=format, **kwargs)

        # Ensure we return a Molecule
        if isinstance(result, Crystal):
            # Convert crystal to molecule if needed
            # Preserve site properties if available
            site_props = getattr(result, "site_properties", None)
            return cls(
                result.species,
                result.cart_positions.tolist(),
                site_properties=site_props,
            )

        if not isinstance(result, Molecule):
            raise TypeError(
                f"File contains {type(result).__name__}, not Molecule. "
                f"Use Crystal.from_file() for crystal structures."
            )

        return result

    def to_file(self, filename: str, format: Optional[str] = None, **kwargs) -> None:
        """
        Write Molecule to a file.

        Automatically detects file format from extension if not specified.
        Supported formats: .xyz, .pdb, .mol, .json

        This method uses the high-level write() interface. For more control,
        use matsimpy.io.write() directly.

        Args:
            filename: Output filename
            format: Optional format specification (e.g., 'xyz', 'pdb').
                   If None, format is detected from file extension.
            **kwargs: Additional arguments passed to the format-specific writer
                     (e.g., title for file headers)

        Raises:
            ValueError: If format is not supported

        Examples:
            >>> molecule.to_file('molecule.xyz')
            >>> molecule.to_file('molecule.pdb', title='Water')
        """
        from ..io import write

        write(self, filename, format=format, **kwargs)

    def to_pymatgen(self):
        """
        Convert Molecule to pymatgen Molecule.

        Returns:
            pymatgen.core.structure.Molecule: pymatgen Molecule object

        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io.converters import to_pymatgen

        return to_pymatgen(self)

    def to_ase(self):
        """
        Convert Molecule to ASE Atoms.

        Returns:
            ase.Atoms: ASE Atoms object

        Raises:
            ImportError: If ASE is not installed
        """
        from ..io.converters import to_ase

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
        from ..io.converters import from_pymatgen

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
        from ..io.converters import from_ase

        result = from_ase(ase_atoms)
        if not isinstance(result, Molecule):
            raise ValueError("ASE Atoms without cell/PBC will be converted to Molecule")
        return result

    def to_code(self, code: str, filename: str, **kwargs) -> None:
        """
        Write input file for a DFT code.

        Generic interface for writing DFT code input files. Supports multiple
        codes through the code parameter. Molecules are typically treated as
        isolated systems in a large cell.

        Args:
            code: DFT code name (e.g., 'quantum_espresso', 'qe', 'vasp')
            filename: Output filename
            **kwargs: Additional parameters for the DFT code input
                     (code-specific parameters)

        Raises:
            ValueError: If code is not supported
            NotImplementedError: If code interface is not yet implemented

        Examples:
            >>> molecule.to_code('quantum_espresso', 'mol_scf.in')
            >>> molecule.to_code('qe', 'molecule.in')
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
            code: DFT code name (e.g., 'quantum_espresso', 'qe', 'vasp')
            filename: Path to output file
            **kwargs: Additional parameters for parsing

        Returns:
            Molecule: Molecule structure from the output file

        Raises:
            ValueError: If code is not supported
            NotImplementedError: Output parsing not yet implemented

        Examples:
            >>> molecule = Molecule.from_code('quantum_espresso', 'mol_scf.out')
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

    @property
    def calc(self) -> Optional["Calculator"]:
        """
        Get the attached calculator.

        Returns:
            :obj:`~matsimpy.calculator.base.Calculator` or None: The attached calculator, or None if none attached.

        Example:
            >>> from matsimpy.calculator import LennardJones
            >>> molecule.calc = LennardJones()
            >>> molecule.calc  # <LennardJones object>
            >>> molecule.calc = None  # Remove calculator
            >>> molecule.calc  # None
        """
        from ..calculator.base import Calculator

        return getattr(self, "_calculator", None)

    @calc.setter
    def calc(self, calculator: Optional["Calculator"]) -> None:
        """
        Attach a calculator to this molecule.

        Sets a calculator that can be used to compute energies and forces.
        The calculator must be an instance of
        :class:`~matsimpy.calculator.base.Calculator`.

        Args:
            calculator: Calculator object (e.g., LennardJones, Mattersim, VASP)
                      or None to remove the calculator.

        Raises:
            TypeError: If calculator is not a Calculator instance or None.

        Example:
            >>> from matsimpy.calculator import LennardJones
            >>> molecule.calc = LennardJones()
            >>> energy = molecule.get_potential_energy()
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
            >>> molecule.calc = LennardJones()
            >>> energy = molecule.get_potential_energy()
            >>> print(f"Energy: {energy:.4f} eV")
        """
        if self.calc is None:
            raise ValueError(
                "No calculator attached. Set molecule.calc = calculator first."
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
            >>> molecule.calc = LennardJones()
            >>> forces = molecule.get_forces()
            >>> forces.shape
            (3, 3)  # 3 atoms, 3 force components
            >>> forces[0]  # Force on first atom
            array([0.123, -0.456, 0.789])
        """
        if self.calc is None:
            raise ValueError(
                "No calculator attached. Set molecule.calc = calculator first."
            )
        if not self.calc._calculation_performed:
            self.calc.calculate(self)
        return self.calc.get_forces()

    def perturb(
        self,
        amplitude: float,
        indices: Optional[Union[List[int], "AtomSelection"]] = None,
        seed: Optional[int] = None,
        inplace: bool = True,
    ) -> "Molecule":
        """
        Add random perturbations to atomic positions.

        Convenience method that calls the transformation module's perturb_positions function.
        By default, modifies the structure in-place.

        Args:
            amplitude: Maximum perturbation amplitude (Angstroms)
            indices: Atom indices to perturb (default: all atoms).
                    Can be a list of indices or an AtomSelection object.
            seed: Random seed for reproducibility
            inplace: If True, modify this molecule in-place (default: True).
                    If False, return a new Molecule object.

        Returns:
            Molecule: Structure with perturbed positions (self if inplace=True, new object if inplace=False)

        Examples:
            >>> from matsimpy.core import Molecule
            >>> from matsimpy.utils.selection import AtomSelection
            >>> molecule = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> # Perturb all atoms by up to 0.1 Angstrom
            >>> molecule.perturb(0.1)
            >>> # Perturb specific atoms without modifying original
            >>> perturbed = molecule.perturb(0.1, indices=[0, 1], inplace=False)
            >>> # Perturb using AtomSelection
            >>> sel = AtomSelection(molecule).by_species('H')
            >>> molecule.perturb(0.1, indices=sel)
        """
        # Handle AtomSelection object
        from ..utils.selection import AtomSelection

        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices

        from ..transformation.atomic import perturb_positions

        # perturb_positions always returns a new structure
        result = perturb_positions(
            self, amplitude, indices=indices, seed=seed
        )
        if inplace:
            # Update self with result's attributes
            self.positions = result.positions
            self._sites = result._sites
            self._cached_com = None  # Invalidate center of mass cache
            return self
        return result
