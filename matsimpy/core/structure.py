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

        self.species = tuple(species_list)  # Make immutable
        self.positions = np.array(positions, dtype=np.float64)
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


    def __hash__(self):
        # Use hashlib to generate an MD5 hash of the Crystal object's dictionary representation
        hash_str = str(self.as_dict()).encode('utf-8')
        return int(hashlib.md5(hash_str).hexdigest(), 16)

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
            position (List[float]): Atomic position.
        """
        # Maintain tuple immutability
        species_list = list(self.species)
        species_list.append(species)
        self.species = tuple(species_list)
        self.positions = np.vstack([self.positions, position])
        self._formula_dirty = True
        self._cached_composition = None
        # Update cached properties
        self.formula = self.get_formula()
        self.composition = self.get_composition()

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
            # Update cached properties
            self.formula = self.get_formula()
            self.composition = self.get_composition()
        else:
            raise IndexError("Invalid atom index.")

    def get_neighbor_list(self, cutoff: float, use_pbc: bool = True) -> Dict[int, List[Tuple[int, float]]]:
        """
        Get neighbor list. To be implemented by subclasses.
        
        Args:
            cutoff: Cutoff radius for neighbor finding
            use_pbc: Whether to use periodic boundary conditions
            
        Returns:
            Dict mapping atom index to list of (neighbor_index, distance) tuples
        """
        pass


    def __len__(self):
        return len(self.species)

