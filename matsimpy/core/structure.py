import numpy as np
from typing import List, Union, Optional, Dict, Tuple, Any
import hashlib
from collections import Counter
from abc import ABC, abstractmethod
from monty.json import MSONable

from .lattice import Lattice
from .composition import Composition
from .periodic_table import Element


class Structure(ABC, MSONable):
    """
    An abstract base class for representing crystal and molecule structures.

    This class should not be instantiated directly. Use Crystal or Molecule instead.

    Args:
        species (List[str]): List of atomic species.
        positions (List[List[float]]): List of atomic positions.
        lattice (Lattice): Structure's lattice.

    Attributes:
        species (Tuple[str]): Tuple of atomic species.
        positions (np.ndarray): Numpy array of atomic positions.
        lattice (Lattice): Structure's lattice.
        formula (str): Chemical formula of the structure.
        composition (Composition): Composition of the structure.

    Methods:
        as_dict(): Returns a dictionary representation of the structure.
        from_dict(d): Constructs the structure from a dictionary.
        formula: Chemical formula property (cached).
        composition: Composition property (cached).
        add_atom(species, position): Adds an atom to the structure.
        remove_atom(index): Removes an atom from the structure.
        get_neighbor_list(cutoff): Returns a list of atoms within a cutoff radius of each atom.

    """

    def __init__(
        self,
        species: Union[List[str], List[int], List[Element]],
        positions: List[List[float]],
        lattice: Lattice = None,
    ) -> None:
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

        Args:
            positions: Input positions (list of lists, numpy array, etc.)

        Returns:
            np.ndarray: Validated positions array of shape (n_atoms, 3)

        Raises:
            ValueError: If positions are not 2D with 3 columns.
            TypeError: If positions cannot be converted to numeric array.
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
        Get positions as numpy array.

        Returns:
            np.ndarray: Array of positions with shape (n_atoms, 3)
        """
        return self._positions

    @positions.setter
    def positions(self, positions: Union[List, np.ndarray]) -> None:
        """
        Set positions with validation.

        Args:
            positions: New positions (list of lists or numpy array)

        Raises:
            ValueError: If positions are invalid or don't match species count.
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

    def as_dict(self):
        """
        Returns a dictionary representation of the structure.

        Returns:
            (dict): Dictionary representation of the structure.
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
        Constructs the structure from a dictionary.

        Args:
            d: Dictionary representation of the structure.

        Returns:
            Structure object.
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
        Calculates the chemical formula of the structure with caching.

        Preserves the original order of elements as they appear in the structure,
        rather than sorting alphabetically or by atomic number.

        Returns:
            (str): Chemical formula of the structure.
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

    def copy(self):
        """
        Create a copy of the structure.

        Returns:
            Structure: A new instance of the structure with copied data.

        Examples:
            >>> from matsimpy.core import Crystal, Lattice
            >>> crystal = Crystal(['Si', 'Si'], [[0,0,0], [0.25,0.25,0.25]], Lattice.cubic(5.43))
            >>> crystal_copy = crystal.copy()
            >>> crystal_copy is not crystal  # Different objects
            True
            >>> crystal_copy.species == crystal.species  # Same data
            True
        """
        return self.from_dict(self.as_dict())

    def __hash__(self):
        """
        Generate a hash for the structure.

        Positions are rounded to 8 decimal places to handle floating-point precision issues.
        This ensures that structures with nearly identical positions (within tolerance)
        hash to the same value.

        Returns:
            int: Hash value for the structure
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

    def __eq__(self, other):
        """
        Test equality between structures.

        Two structures are equal if they have the same species and positions
        (within floating-point tolerance of 1e-8).

        Args:
            other: Another Structure object

        Returns:
            bool: True if structures are equal
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
        Calculates the composition of the structure with caching.

        Returns:
            (Composition): Composition object.
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
        Adds one or more atoms to the structure and invalidates cache.

        Args:
            species: Atomic species (single string or list of strings).
            position: Atomic position(s). Either a single 3D coordinate [x, y, z]
                     or a list of 3D coordinates [[x1, y1, z1], [x2, y2, z2], ...].

        Raises:
            ValueError: If position is not 3D or if species/position counts don't match.

        Examples:
            >>> structure.add_atom('H', [0, 0, 0])  # Add single atom
            >>> structure.add_atom(['H', 'O'], [[0, 0, 0], [1, 0, 0]])  # Add multiple
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
        Removes an atom from the structure and invalidates cache.

        Args:
            index (int): Index of atom to be removed.
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
            indices: Atom index, list of indices, or AtomSelection object to substitute
            new_species: New species symbol, list of symbols, or dict mapping old->new species.
                       If dict, maps old species to new species (e.g., {'Si': 'Ge', 'O': 'S'})

        Raises:
            IndexError: If index is out of range
            ValueError: If number of indices doesn't match number of species
            KeyError: If dict mapping doesn't contain a species

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
        Sort atoms in the structure by element (in-place).

        This method actually reorders the internal species and positions arrays,
        unlike __str__ which only sorts for display.

        Args:
            sort_by: Sorting method ('element' for atomic number, 'alphabet' for alphabetical)

        Examples:
            >>> structure.sort_atoms('element')  # Sort by atomic number
            >>> structure.sort_atoms('alphabet')  # Sort alphabetically
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

        Args:
            cutoff: Cutoff radius for neighbor finding
            atom_index: Optional atom index. If None, returns neighbors for all atoms.
                       If specified, returns neighbors only for that atom.
            **kwargs: Additional subclass-specific parameters (e.g., use_pbc for Crystal)

        Returns:
            Dict mapping atom index to list of (neighbor_index, distance) tuples.
            If atom_index is provided, dict contains only that entry.
            If atom_index is None, dict contains entries for all atoms.

        Raises:
            NotImplementedError: If not implemented by subclass
            IndexError: If atom_index is out of range

        Examples:
            >>> # Get neighbors for all atoms
            >>> neighbors = structure.get_neighbor_list(5.0)
            >>> # Get neighbors for specific atom
            >>> neighbors = structure.get_neighbor_list(5.0, atom_index=0)
        """
        raise NotImplementedError("get_neighbor_list must be implemented by subclasses")

    def __len__(self):
        return len(self.species)
