import numpy as np
from typing import List, Union, Optional, Dict, Tuple
import hashlib
from collections import Counter
from monty.json import MSONable

from .lattice import Lattice
from .composition import Composition
from .periodic_table import Element

class Structure(MSONable):
    """
    A base class for representing crystal and molecule structures.

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
        get_formula(): Calculates the chemical formula of the structure.
        get_composition(): Calculates the composition of the structure.
        add_atom(species, position): Adds an atom to the structure.
        remove_atom(index): Removes an atom from the structure.
        get_neighbor_list(cutoff): Returns a list of atoms within a cutoff radius of each atom.

    """
    def __init__(self, species: Union[List[str], List[int], List[Element]],
                 positions: List[List[float]], 
                 lattice: Lattice = None):
        # Convert to list first, then tuple for immutability
        if all(isinstance(s, str) for s in species):
            species_list = list(species)
        elif all(isinstance(s, int) for s in species):
            species_list = [Element.from_Z(s).symbol for s in species]
        elif all(isinstance(s, Element) for s in species):
            species_list = [s.symbol for s in species]
        else:
            raise TypeError("Invalid type for species. \
                    Must be a list of atomic symbols, \
                    a list of atomic numbers, or a list of Element objects.")

        # Validate input lengths match
        if len(species_list) != len(positions):
            raise ValueError(
                f"Number of species ({len(species_list)}) must match "
                f"number of positions ({len(positions)})"
            )

        self.species = tuple(species_list)  # Make immutable
        self.positions = np.array(positions, dtype=np.float64)
        
        # Validate positions are 3D
        if self.positions.ndim != 2 or self.positions.shape[1] != 3:
            raise ValueError("Positions must be a list of 3D coordinates")
        
        self.lattice = lattice
        
        # Add cache attributes
        self._cached_composition: Optional[Composition] = None
        self._cached_formula: Optional[str] = None
        self._formula_dirty = True
        
        # Initialize cached properties
        self.formula = self.get_formula()
        self.composition = self.get_composition()

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
    def from_dict(cls, d):
        """
        Constructs the structure from a dictionary.

        Args:
            d (dict): Dictionary representation of the structure.

        Returns:
            (Structure): Structure object.
        """
        species = d["species"]
        positions = d["positions"]
        lattice = Lattice.from_dict(d["lattice"]) if d.get("lattice") is not None else None
        return cls(species, positions, lattice)

    def get_formula(self):
        """
        Calculates the chemical formula of the structure with caching.

        Returns:
            (str): Chemical formula of the structure.
        """
        if self._cached_formula is None or self._formula_dirty:
            element_counter = Counter(self.species)
            formula = ""
            for element, count in sorted(element_counter.items()):
                formula += element + (str(count) if count > 1 else "")
            self._cached_formula = formula
            self._formula_dirty = False
        return self._cached_formula

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
        # Use hashlib to generate a SHA256 hash of the structure's dictionary representation
        hash_str = str(self.as_dict()).encode('utf-8')
        return int(hashlib.sha256(hash_str).hexdigest(), 16)

    def get_composition(self):
        """
        Calculates the composition of the structure with caching.

        Returns:
            (Composition): Composition object.
        """
        if self._cached_composition is None:
            self._cached_composition = Composition(self.get_formula())
        return self._cached_composition

    def add_atom(self, species: str, position: List[float]) -> None:
        """
        Adds an atom to the structure and invalidates cache.

        Args:
            species (str): Atomic species.
            position (List[float]): Atomic position (must be 3D).
        """
        # Validate position is 3D
        position = np.array(position, dtype=np.float64)
        if position.ndim != 1 or len(position) != 3:
            raise ValueError("Position must be a 3D coordinate")
        
        # Maintain tuple immutability
        species_list = list(self.species)
        species_list.append(species)
        self.species = tuple(species_list)
        self.positions = np.vstack([self.positions, position])
        self._formula_dirty = True
        self._cached_composition = None
        # Properties computed lazily on access

    def remove_atom(self, index: int) -> None:
        """
        Removes an atom from the structure and invalidates cache.

        Args:
            index (int): Index of atom to be removed.
        """
        if 0 <= index < len(self.species):
            # Maintain tuple immutability
            species_list = list(self.species)
            species_list.pop(index)
            self.species = tuple(species_list)
            self.positions = np.delete(self.positions, index, axis=0)
            self._formula_dirty = True
            self._cached_composition = None
            # Properties computed lazily on access
        else:
            raise IndexError("Invalid atom index.")

    def substitute(self, indices: Union[int, List[int], 'AtomSelection'], 
                   new_species: Union[str, List[str], Dict[str, str]]) -> None:
        """
        Substitute atoms with new species.
        
        This is a common operation for modifying structures. For functional
        style (returning new object), use matsimpy.transformation.substitute().
        
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
        # Handle AtomSelection object
        from ..utils.selection import AtomSelection
        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices
        
        # Handle dict-based species mapping
        if isinstance(new_species, dict):
            # Convert dict to list based on current species at selected indices
            new_species_list = []
            for idx in indices:
                old_spec = self.species[idx]
                if old_spec not in new_species:
                    raise KeyError(f"Species '{old_spec}' at index {idx} not found in substitution mapping")
                new_species_list.append(new_species[old_spec])
            new_species = new_species_list
        
        # Normalize inputs
        if isinstance(indices, int):
            indices = [indices]
            if isinstance(new_species, str):
                new_species = [new_species]
            else:
                new_species = [new_species[0]]  # Take first if list
        elif isinstance(new_species, str):
            # Multiple indices, single species
            new_species = [new_species] * len(indices)
        elif isinstance(new_species, list):
            # Both are lists
            pass
        else:
            raise TypeError(f"new_species must be str, List[str], or Dict[str, str], got {type(new_species)}")
        
        if len(indices) != len(new_species):
            raise ValueError(
                f"Number of indices ({len(indices)}) must match "
                f"number of species ({len(new_species)})"
            )
        
        # Validate indices
        for idx in indices:
            if not (0 <= idx < len(self.species)):
                raise IndexError(f"Atom index {idx} is out of range [0, {len(self.species)-1}]")
        
        # Perform substitutions
        species_list = list(self.species)
        for idx, species in zip(indices, new_species):
            species_list[idx] = species
        
        # Update species tuple
        self.species = tuple(species_list)
        
        # Invalidate caches
        self._formula_dirty = True
        self._cached_composition = None
    
    def substitute_all(self, old_species: str, new_species: str) -> None:
        """
        Substitute all atoms of a given species with a new species.
        
        This is a convenience method for bulk substitution. For functional
        style (returning new object), use matsimpy.transformation.substitute_all().
        
        Args:
            old_species: Species to replace
            new_species: Replacement species
            
        Examples:
            >>> structure.substitute_all('Si', 'Ge')  # Replace all Si with Ge
        """
        # Find all indices of old_species
        indices = [i for i, spec in enumerate(self.species) if spec == old_species]
        
        if not indices:
            # No substitution needed
            return
        
        # Substitute all at once
        self.substitute(indices, [new_species] * len(indices))
    
    def sort_atoms(self, sort_by: str = 'element') -> None:
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
        if sort_by == 'element':
            # Sort by atomic number, then by position for same element
            sorted_atoms = sorted(
                atoms,
                key=lambda a: (
                    Element.get_element(a[1]).atomic_no,
                    a[2][0], a[2][1], a[2][2]
                )
            )
        elif sort_by == 'alphabet':
            # Sort alphabetically by species symbol, then by position
            sorted_atoms = sorted(
                atoms,
                key=lambda a: (a[1], a[2][0], a[2][1], a[2][2])
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
        if hasattr(self, '_sites'):
            if hasattr(self, '_initialize_sites'):
                self._sites = self._initialize_sites()

    def get_neighbor_list(self, cutoff: float, use_pbc: bool = True) -> Dict[int, List[Tuple[int, float]]]:
        """
        Get neighbor list. To be implemented by subclasses.
        
        Args:
            cutoff: Cutoff radius for neighbor finding
            use_pbc: Whether to use periodic boundary conditions
            
        Returns:
            Dict mapping atom index to list of (neighbor_index, distance) tuples
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("get_neighbor_list must be implemented by subclasses")


    def __len__(self):
        return len(self.species)

